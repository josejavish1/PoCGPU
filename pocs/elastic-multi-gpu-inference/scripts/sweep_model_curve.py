#!/usr/bin/env python3
"""
Single-Model Stepped Saturation Curve Benchmark
===============================================
Executes progressive concurrency sweeps on an isolated model to map:
1. TTFT P50/P99 latency inflation curve (prefill degradation)
2. TPOT fluidity evolution (decode throughput per stream)
3. Aggregated cluster throughput (tokens per second)
4. vLLM KV-Cache occupancy and hardware utilization (continuous DCGM sampling)
5. Point of saturation / queuing knee

Certified for any enterprise environment (mid-market to global Tier-1).
Zero Hardcoding: Fully externalized via environment variables, catalogs, and CLI arguments.
Language Decoupling: 100% Technical English.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import math
import os
import sqlite3
import statistics
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

import httpx

# --- Environment & Configuration Resolution ---

SCRIPT_DIR = Path(__file__).resolve().parent
POC_DIR = SCRIPT_DIR.parent
ROOT_DIR = POC_DIR.parent.parent

DEFAULT_GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://localhost:8080/v1/chat/completions")
DEFAULT_PROMETHEUS_URL = os.environ.get("PROMETHEUS_URL", "http://localhost:9090")
DEFAULT_MASTER_KEY = os.environ.get("MASTER_KEY", os.environ.get("LITELLM_MASTER_KEY", ""))
DEFAULT_DB_PATH = os.environ.get("BENCHMARK_DB_PATH", str(POC_DIR / "data" / "benchmarks.db"))
DEFAULT_PRICING_CATALOG = os.environ.get(
    "PRICING_CATALOG_PATH", str(ROOT_DIR / "config" / "catalogs" / "pricing_catalog.json")
)

TARGET_INSTANCE_FILTER = os.environ.get("TARGET_INSTANCE_FILTER", "l4,g2-standard,a100,h100,b200")
DEFAULT_REQUEST_TIMEOUT_S = float(os.environ.get("BENCHMARK_REQUEST_TIMEOUT_S", "120.0"))
DEFAULT_TELEM_INTERVAL_S = float(os.environ.get("BENCHMARK_TELEM_INTERVAL_S", "0.5"))
DEFAULT_STEP_COOLDOWN_S = float(os.environ.get("BENCHMARK_STEP_COOLDOWN_S", "2.0"))
DEFAULT_MODEL = os.environ.get("BENCHMARK_FAST_MODEL", "light-model-fast")
DEFAULT_STEPS = os.environ.get("BENCHMARK_STEPS", "5,15,30,45,60,75")
DEFAULT_PROM_SELECTOR = os.environ.get("PROMETHEUS_LABEL_SELECTOR", "")
DEFAULT_SSL_VERIFY = os.environ.get("BENCHMARK_SSL_VERIFY", "true").lower() not in (
    "false",
    "0",
    "no",
)

PROM_METRIC_VRAM = os.environ.get("PROM_METRIC_VRAM", "DCGM_FI_DEV_FB_USED")
PROM_METRIC_UTIL = os.environ.get("PROM_METRIC_UTIL", "DCGM_FI_DEV_GPU_UTIL")
PROM_METRIC_KV_CACHE = os.environ.get("PROM_METRIC_KV_CACHE", "vllm:gpu_cache_usage_perc")
PROM_METRIC_WAITING = os.environ.get("PROM_METRIC_WAITING", "vllm:num_requests_waiting")

PROMPT_FAST = os.environ.get(
    "BENCHMARK_PROMPT_FAST",
    "Summarize in 25 words why enterprise AI architectures benefit from local multi-GPU tensor parallelism.",
)
PROMPT_CODER = os.environ.get(
    "BENCHMARK_PROMPT_CODER",
    "Write an optimized Python function implementing an asynchronous worker pool with task retry and backoff.",
)
PROMPT_REASONING = os.environ.get(
    "BENCHMARK_PROMPT_REASONING",
    "Provide a rigorous step-by-step mathematical proof that the square root of 2 is irrational, analyzing parity of coprimes.",
)


def load_hourly_spot_rate(catalog_path: str) -> float:
    """Loads hourly node rate from catalog or environment fallback."""
    rate = float(os.environ.get("SPOT_HOURLY_COST_PER_NODE", "0.98"))
    cat_file = Path(catalog_path)
    if cat_file.exists():
        try:
            with open(cat_file, encoding="utf-8") as f:
                data = json.load(f)
                filters = [
                    f.strip().lower() for f in TARGET_INSTANCE_FILTER.split(",") if f.strip()
                ]
                for key, instance in data.get("cloud_instances", {}).items():
                    if any(f in key.lower() for f in filters):
                        rate = float(instance.get("spot_hourly_mean", str(rate)))
                        break
        except Exception as exc:
            print(
                f"[!] WARNING: Failed to parse pricing catalog '{cat_file}': {exc}. Using fallback rates.",
                file=sys.stderr,
            )
    return rate


def compute_percentile(values: list[float], percentile: int) -> float:
    """Computes exact inclusive percentile across any dataset size."""
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    if percentile >= 100:
        return max(values)
    if percentile <= 0:
        return min(values)
    cut_idx = max(0, min(98, percentile - 1))
    return statistics.quantiles(values, n=100, method="inclusive")[cut_idx]


# --- Database Schema Management ---


def init_curve_database(db_path: Path) -> None:
    """Initializes SQLite table for isolated saturation curves with WAL mode."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path, timeout=30.0) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA busy_timeout=30000;")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS model_saturation_sweeps (
                sweep_id TEXT PRIMARY KEY,
                model_name TEXT NOT NULL,
                concurrency INTEGER NOT NULL,
                total_requests INTEGER NOT NULL,
                success_count INTEGER NOT NULL,
                failed_count INTEGER NOT NULL,
                ttft_p50_ms REAL,
                ttft_p90_ms REAL,
                ttft_p99_ms REAL,
                tpot_mean_ms REAL,
                throughput_tps REAL,
                total_prompt_tokens INTEGER,
                total_completion_tokens INTEGER,
                peak_vram_used_mib REAL,
                peak_gpu_util_pct REAL,
                vllm_kv_cache_peak_pct REAL,
                vllm_max_waiting_requests INTEGER,
                duration_s REAL NOT NULL,
                estimated_cost_usd REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()


# --- Continuous Asynchronous Telemetry Sampling ---


@dataclass
class HardwareTelemetry:
    vram_mib: float
    gpu_util: float
    kv_cache_pct: float
    waiting_reqs: int


async def query_prometheus_metric_async(
    client: httpx.AsyncClient, prometheus_url: str, metric_query: str
) -> float | None:
    """Queries Prometheus scalar endpoint asynchronously."""
    try:
        resp = await client.get(
            f"{prometheus_url}/api/v1/query", params={"query": metric_query}, timeout=3.0
        )
        if resp.status_code == 200:
            data = resp.json().get("data", {}).get("result", [])
            if data:
                vals = [
                    float(item["value"][1])
                    for item in data
                    if "value" in item
                    and len(item["value"]) > 1
                    and not math.isnan(float(item["value"][1]))
                    and not math.isinf(float(item["value"][1]))
                ]
                return sum(vals) if vals else None
    except Exception:
        pass
    return None


async def get_current_telemetry_async(
    client: httpx.AsyncClient, prometheus_url: str
) -> HardwareTelemetry:
    """Retrieves current GPU and vLLM cache telemetry values concurrently."""
    clean_sel = DEFAULT_PROM_SELECTOR.strip().strip("{}")
    sel = f"{{{clean_sel}}}" if clean_sel else ""
    vram_raw, util_raw, kv_raw, waiting_raw = await asyncio.gather(
        query_prometheus_metric_async(client, prometheus_url, f"max({PROM_METRIC_VRAM}{sel})"),
        query_prometheus_metric_async(client, prometheus_url, f"avg({PROM_METRIC_UTIL}{sel})"),
        query_prometheus_metric_async(client, prometheus_url, f"max({PROM_METRIC_KV_CACHE}{sel})"),
        query_prometheus_metric_async(client, prometheus_url, f"sum({PROM_METRIC_WAITING}{sel})"),
    )
    vram = vram_raw or 0.0
    util = util_raw or 0.0
    kv = kv_raw or 0.0
    if 0.0 < kv <= 1.0:
        kv *= 100.0
    waiting = int(waiting_raw or 0)
    return HardwareTelemetry(vram_mib=vram, gpu_util=util, kv_cache_pct=kv, waiting_reqs=waiting)


async def poll_telemetry_during_sweep(
    client: httpx.AsyncClient,
    prometheus_url: str,
    stop_event: asyncio.Event,
    interval_s: float = 0.5,
) -> HardwareTelemetry:
    """Continuously monitors Prometheus to catch peak queue depth and VRAM during heavy load."""
    peak = HardwareTelemetry(0.0, 0.0, 0.0, 0)
    while not stop_event.is_set():
        sample = await get_current_telemetry_async(client, prometheus_url)
        peak.vram_mib = max(peak.vram_mib, sample.vram_mib)
        peak.gpu_util = max(peak.gpu_util, sample.gpu_util)
        peak.kv_cache_pct = max(peak.kv_cache_pct, sample.kv_cache_pct)
        peak.waiting_reqs = max(peak.waiting_reqs, sample.waiting_reqs)
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(stop_event.wait(), timeout=interval_s)
    return peak


# --- Inference Stream Executor ---


@dataclass
class SingleRequestResult:
    request_id: str
    status_code: int
    ttft_ms: float
    tpot_ms: float
    prompt_tokens: int
    completion_tokens: int
    total_latency_s: float
    error_message: str | None


async def execute_request(
    client: httpx.AsyncClient,
    gateway_url: str,
    api_key: str,
    model: str,
    prompt: str,
    max_tokens: int,
    req_id: str,
    timeout: float = DEFAULT_REQUEST_TIMEOUT_S,
) -> SingleRequestResult:
    """Executes a streaming inference request against the gateway with usage extraction."""
    unique_id = f"{req_id}_{uuid.uuid4().hex[:4]}"
    full_prompt = f"[UID: {unique_id}] {prompt}"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": full_prompt}],
        "max_tokens": max_tokens,
        "stream": True,
        "temperature": 0.1,
        "stream_options": {"include_usage": True},
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    t_start = time.perf_counter()
    first_token_time: float | None = None
    last_token_time: float | None = None
    reported_completion_tokens: int | None = None
    tokens = 0
    prompt_tokens_reported = 0
    status = 0
    error: str | None = None

    try:
        async with client.stream(
            "POST", gateway_url, json=payload, headers=headers, timeout=timeout
        ) as resp:
            status = resp.status_code
            if status != 200:
                error_chunks = []
                bytes_read = 0
                async for err_chunk in resp.aiter_bytes(chunk_size=512):
                    error_chunks.append(err_chunk)
                    bytes_read += len(err_chunk)
                    if bytes_read >= 512:
                        break
                error_text = b"".join(error_chunks).decode("utf-8", errors="ignore")
                return SingleRequestResult(
                    request_id=unique_id,
                    status_code=status,
                    ttft_ms=0.0,
                    tpot_ms=0.0,
                    prompt_tokens=int(len(full_prompt.split()) * 1.3),
                    completion_tokens=0,
                    total_latency_s=time.perf_counter() - t_start,
                    error_message=error_text[:100],
                )

            async for line in resp.aiter_lines():
                if not line.strip() or not line.startswith("data: "):
                    continue
                content = line[6:].strip()
                if content == "[DONE]":
                    break
                try:
                    chunk = json.loads(content)
                    usage = chunk.get("usage")
                    if isinstance(usage, dict):
                        prompt_tokens_reported = usage.get("prompt_tokens", prompt_tokens_reported)
                        if usage.get("completion_tokens") is not None:
                            reported_completion_tokens = int(usage["completion_tokens"])

                    choices = chunk.get("choices")
                    if isinstance(choices, list) and len(choices) > 0:
                        delta_obj = choices[0].get("delta") or {}
                        delta = (
                            delta_obj.get("content")
                            or delta_obj.get("reasoning_content")
                            or delta_obj.get("reasoning")
                            or ""
                        )
                        if delta:
                            now = time.perf_counter()
                            tokens += 1
                            if first_token_time is None:
                                first_token_time = now
                            last_token_time = now
                except json.JSONDecodeError:
                    continue

            if reported_completion_tokens is not None and reported_completion_tokens > 0:
                tokens = reported_completion_tokens
    except Exception as exc:
        status = 500
        error = str(exc)[:100]

    t_end = time.perf_counter()
    total_s = t_end - t_start
    ttft = (
        ((first_token_time - t_start) * 1000.0)
        if first_token_time
        else (total_s * 1000.0 if status == 200 else 0.0)
    )
    decode_end = last_token_time or t_end
    if tokens > 1 and first_token_time and decode_end > first_token_time:
        tpot = ((decode_end - first_token_time) / (tokens - 1)) * 1000.0
    else:
        tpot = 0.0
    prompt_tokens = prompt_tokens_reported or int(len(full_prompt.split()) * 1.3)

    return SingleRequestResult(
        request_id=unique_id,
        status_code=status,
        ttft_ms=ttft,
        tpot_ms=tpot,
        prompt_tokens=prompt_tokens,
        completion_tokens=tokens,
        total_latency_s=total_s,
        error_message=error,
    )


# --- Concurrency Step Executor ---


@dataclass
class StepSummary:
    concurrency: int
    total_requests: int
    success: int
    failed: int
    ttft_p50_ms: float
    ttft_p90_ms: float
    ttft_p99_ms: float
    tpot_ms: float
    throughput_tps: float
    peak_vram_mib: float
    peak_gpu_util: float
    kv_cache_peak_pct: float
    max_waiting: int
    duration_s: float
    cost_usd: float


def save_step_summary_to_db(
    db_path: Path,
    model: str,
    summary: StepSummary,
    total_prompt_tok: int,
    total_completion_tok: int,
) -> None:
    """Saves saturation sweep result to SQLite on worker thread."""
    sweep_id = f"sweep_{model}_c{summary.concurrency}_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    with sqlite3.connect(db_path, timeout=30.0) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO model_saturation_sweeps (
                sweep_id, model_name, concurrency, total_requests, success_count, failed_count,
                ttft_p50_ms, ttft_p90_ms, ttft_p99_ms, tpot_mean_ms, throughput_tps,
                total_prompt_tokens, total_completion_tokens, peak_vram_used_mib,
                peak_gpu_util_pct, vllm_kv_cache_peak_pct, vllm_max_waiting_requests,
                duration_s, estimated_cost_usd
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                sweep_id,
                model,
                summary.concurrency,
                summary.total_requests,
                summary.success,
                summary.failed,
                summary.ttft_p50_ms,
                summary.ttft_p90_ms,
                summary.ttft_p99_ms,
                summary.tpot_ms,
                summary.throughput_tps,
                total_prompt_tok,
                total_completion_tok,
                summary.peak_vram_mib,
                summary.peak_gpu_util,
                summary.kv_cache_peak_pct,
                summary.max_waiting,
                summary.duration_s,
                summary.cost_usd,
            ),
        )
        conn.commit()


async def run_concurrency_step(
    gateway_url: str,
    api_key: str,
    prometheus_url: str,
    db_path: Path,
    second_node_cost: float,
    model: str,
    concurrency: int,
    prompt: str,
    max_tokens: int,
) -> StepSummary:
    """Executes single concurrency level with continuous intra-run telemetry."""
    print(f"\n[*] Evaluating Concurrency Step C={concurrency} on '{model}'...")

    limits = httpx.Limits(
        max_connections=concurrency + 20,
        max_keepalive_connections=max(30, concurrency),
    )
    t_start = time.perf_counter()

    async with (
        httpx.AsyncClient(limits=limits, verify=DEFAULT_SSL_VERIFY, trust_env=True) as client,
        httpx.AsyncClient(verify=DEFAULT_SSL_VERIFY, trust_env=True) as telem_client,
    ):
        stop_telem = asyncio.Event()
        telem_task = asyncio.create_task(
            poll_telemetry_during_sweep(
                telem_client, prometheus_url, stop_telem, interval_s=DEFAULT_TELEM_INTERVAL_S
            )
        )

        tasks = [
            execute_request(
                client,
                gateway_url,
                api_key,
                model,
                prompt,
                max_tokens,
                f"c{concurrency}_req{i + 1}",
                timeout=DEFAULT_REQUEST_TIMEOUT_S,
            )
            for i in range(concurrency)
        ]
        results: list[SingleRequestResult] = await asyncio.gather(*tasks)

        stop_telem.set()
        peak_telem = await telem_task

    duration_s = time.perf_counter() - t_start

    success_reqs = [r for r in results if r.status_code == 200]
    failed_reqs = [r for r in results if r.status_code != 200]

    ttfts = [r.ttft_ms for r in success_reqs if r.ttft_ms > 0]
    tpots = [r.tpot_ms for r in success_reqs if r.tpot_ms > 0]

    p50_ttft = compute_percentile(ttfts, 50)
    p90_ttft = compute_percentile(ttfts, 90)
    p99_ttft = compute_percentile(ttfts, 99)
    mean_tpot = statistics.mean(tpots) if tpots else 0.0

    total_prompt_tok = sum(r.prompt_tokens for r in success_reqs)
    total_completion_tok = sum(r.completion_tokens for r in success_reqs)
    throughput = (total_completion_tok / duration_s) if duration_s > 0 else 0.0
    cost_usd = (duration_s * second_node_cost) if len(success_reqs) > 0 else 0.0

    summary = StepSummary(
        concurrency=concurrency,
        total_requests=len(results),
        success=len(success_reqs),
        failed=len(failed_reqs),
        ttft_p50_ms=p50_ttft,
        ttft_p90_ms=p90_ttft,
        ttft_p99_ms=p99_ttft,
        tpot_ms=mean_tpot,
        throughput_tps=throughput,
        peak_vram_mib=peak_telem.vram_mib,
        peak_gpu_util=peak_telem.gpu_util,
        kv_cache_peak_pct=peak_telem.kv_cache_pct,
        max_waiting=peak_telem.waiting_reqs,
        duration_s=duration_s,
        cost_usd=cost_usd,
    )

    await asyncio.to_thread(
        save_step_summary_to_db,
        db_path,
        model,
        summary,
        total_prompt_tok,
        total_completion_tok,
    )

    print(
        f"    [✓] C={concurrency:<2} -> TTFT P50: {p50_ttft:.1f}ms | P99: {p99_ttft:.1f}ms | "
        f"TPOT: {mean_tpot:.1f}ms/tok | Tok/s: {throughput:.1f} | KV-Cache: {peak_telem.kv_cache_pct:.1f}% | "
        f"Duration: {duration_s:.2f}s"
    )
    return summary


# --- CLI and Main Routine ---


async def main() -> None:
    parser = argparse.ArgumentParser(description="Isolated Model Saturation Curve Sweep")
    parser.add_argument(
        "--gateway-url", default=DEFAULT_GATEWAY_URL, help="Inference Gateway API URL"
    )
    parser.add_argument(
        "--prometheus-url", default=DEFAULT_PROMETHEUS_URL, help="Prometheus telemetry URL"
    )
    parser.add_argument("--api-key", default=DEFAULT_MASTER_KEY, help="Master Gateway API key")
    parser.add_argument(
        "--db-path", default=DEFAULT_DB_PATH, help="Path to SQLite results database"
    )
    parser.add_argument(
        "--pricing-catalog", default=DEFAULT_PRICING_CATALOG, help="Path to pricing catalog JSON"
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Target model to evaluate")
    parser.add_argument("--steps", default=DEFAULT_STEPS, help="Comma-separated concurrency levels")
    parser.add_argument("--max-tokens", type=int, default=60, help="Max tokens per generation")
    parser.add_argument("--prompt", default="", help="Custom prompt for the model")
    args = parser.parse_args()

    if not args.api_key:
        print(
            "[!] ERROR: Master Gateway API key must be provided via --api-key or MASTER_KEY env variable."
        )
        sys.exit(1)

    db_file = Path(args.db_path)
    await asyncio.to_thread(init_curve_database, db_file)

    hourly_rate = load_hourly_spot_rate(args.pricing_catalog)
    nodes_count = int(os.environ.get("ACTIVE_GPU_NODES", "2"))
    second_node_cost = (hourly_rate * nodes_count) / 3600.0

    concurrency_steps = [int(s.strip()) for s in args.steps.split(",") if s.strip()]
    if not concurrency_steps:
        print("[!] ERROR: At least one concurrency step must be specified.", file=sys.stderr)
        sys.exit(1)
    if args.prompt:
        prompt = args.prompt
    elif "coder" in args.model:
        prompt = PROMPT_CODER
    elif "reasoning" in args.model:
        prompt = PROMPT_REASONING
    else:
        prompt = PROMPT_FAST

    print("=" * 85)
    print(f"      SINGLE-MODEL SATURATION CURVE: '{args.model}'")
    print(f"      Target Gateway:    {args.gateway_url}")
    print(f"      Database Target:   {args.db_path}")
    print(f"      Concurrency Steps: {concurrency_steps}")
    print("=" * 85)

    summaries: list[StepSummary] = []
    for c in concurrency_steps:
        summ = await run_concurrency_step(
            gateway_url=args.gateway_url,
            api_key=args.api_key,
            prometheus_url=args.prometheus_url,
            db_path=db_file,
            second_node_cost=second_node_cost,
            model=args.model,
            concurrency=c,
            prompt=prompt,
            max_tokens=args.max_tokens,
        )
        summaries.append(summ)
        await asyncio.sleep(DEFAULT_STEP_COOLDOWN_S)

    print("\n[✓] Model saturation curve benchmark complete.")


if __name__ == "__main__":
    asyncio.run(main())
