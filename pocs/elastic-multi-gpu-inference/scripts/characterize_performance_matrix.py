#!/usr/bin/env python3
"""
Empirical Performance and Saturation Matrix Orchestrator
=======================================================
Executes multi-phase benchmark sweeps across served models and multi-LoRA adapters:
- Phase A: Isolated concurrency curves per model
- Phase B: Mixed traffic contention and LoRA dynamic switching
- Phase C: Extreme saturation and automatic cloud burst failover

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
DEFAULT_API_KEY = os.environ.get("MASTER_KEY", os.environ.get("LITELLM_MASTER_KEY", ""))
DEFAULT_DB_PATH = os.environ.get("BENCHMARK_DB_PATH", str(POC_DIR / "data" / "benchmarks.db"))
DEFAULT_PRICING_CATALOG = os.environ.get(
    "PRICING_CATALOG_PATH", str(ROOT_DIR / "config" / "catalogs" / "pricing_catalog.json")
)

TARGET_INSTANCE_FILTER = os.environ.get("TARGET_INSTANCE_FILTER", "l4,g2-standard,a100,h100,b200")
CLOUD_BURST_PROVIDERS = tuple(
    x.strip().lower()
    for x in os.environ.get("CLOUD_BURST_PROVIDERS", "gemini,gpt,claude,bedrock,azure").split(",")
    if x.strip()
)
DEFAULT_FAST_MODEL = os.environ.get("BENCHMARK_FAST_MODEL", "light-model-fast")
DEFAULT_CODER_MODEL = os.environ.get("BENCHMARK_CODER_MODEL", "light-model-coder")
DEFAULT_REASONING_MODEL = os.environ.get("BENCHMARK_REASONING_MODEL", "reasoning-model")
DEFAULT_CLOUD_MODEL = os.environ.get("BENCHMARK_CLOUD_MODEL", "gemini-cloud-backup")

DEFAULT_TOKENS_FAST = int(os.environ.get("BENCHMARK_TOKENS_FAST", "60"))
DEFAULT_TOKENS_CODER = int(os.environ.get("BENCHMARK_TOKENS_CODER", "120"))
DEFAULT_TOKENS_REASONING = int(os.environ.get("BENCHMARK_TOKENS_REASONING", "300"))
DEFAULT_PROM_SELECTOR = os.environ.get("PROMETHEUS_LABEL_SELECTOR", "")

# Test Prompts
PROMPT_FAST = os.environ.get(
    "BENCHMARK_PROMPT_FAST",
    "Summarize in 20 words the primary architectural benefit of continuous batching in high-throughput LLM serving.",
)
PROMPT_CODER = os.environ.get(
    "BENCHMARK_PROMPT_CODER",
    "Write an optimized Python function implementing an asynchronous worker pool with task retry and backoff.",
)
PROMPT_REASONING = os.environ.get(
    "BENCHMARK_PROMPT_REASONING",
    "Provide a rigorous step-by-step mathematical proof that the square root of 2 is irrational. "
    "Include the classic proof by contradiction, parity arguments on coprime integers, and algebraic implications.",
)
DEFAULT_REQUEST_TIMEOUT_S = float(os.environ.get("BENCHMARK_REQUEST_TIMEOUT_S", "120.0"))
DEFAULT_TELEM_INTERVAL_S = float(os.environ.get("BENCHMARK_TELEM_INTERVAL_S", "0.5"))
DEFAULT_STEP_COOLDOWN_S = float(os.environ.get("BENCHMARK_STEP_COOLDOWN_S", "2.0"))
DEFAULT_SSL_VERIFY = os.environ.get("BENCHMARK_SSL_VERIFY", "true").lower() not in (
    "false",
    "0",
    "no",
)

PROM_METRIC_VRAM = os.environ.get("PROM_METRIC_VRAM", "DCGM_FI_DEV_FB_USED")
PROM_METRIC_UTIL = os.environ.get("PROM_METRIC_UTIL", "DCGM_FI_DEV_GPU_UTIL")
PROM_METRIC_KV_CACHE = os.environ.get("PROM_METRIC_KV_CACHE", "vllm:gpu_cache_usage_perc")
PROM_METRIC_WAITING = os.environ.get("PROM_METRIC_WAITING", "vllm:num_requests_waiting")

# --- Pricing and FinOps Catalog Loader ---


def load_pricing_parameters(catalog_path: str) -> tuple[float, float, float]:
    """Loads hourly node rates and token rates from catalog or environment defaults."""
    hourly_node_cost = float(os.environ.get("SPOT_HOURLY_COST_PER_NODE", "0.98"))
    cloud_in_rate = float(os.environ.get("CLOUD_BURST_COST_PER_M_INPUT", "0.075"))
    cloud_out_rate = float(os.environ.get("CLOUD_BURST_COST_PER_M_OUTPUT", "0.30"))

    cat_file = Path(catalog_path)
    if cat_file.exists():
        try:
            with open(cat_file, encoding="utf-8") as f:
                data = json.load(f)
                cloud_instances = data.get("cloud_instances", {})
                filters = [
                    f.strip().lower() for f in TARGET_INSTANCE_FILTER.split(",") if f.strip()
                ]
                for key, instance in cloud_instances.items():
                    if any(f in key.lower() for f in filters):
                        spot_str = instance.get("spot_hourly_mean", str(hourly_node_cost))
                        hourly_node_cost = float(spot_str)
                        break
        except Exception as exc:
            print(
                f"[!] WARNING: Failed to parse pricing catalog '{cat_file}': {exc}. Using fallback rates.",
                file=sys.stderr,
            )

    return hourly_node_cost, cloud_in_rate, cloud_out_rate


# --- Statistical Math Utility ---


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


def init_database(db_path: Path) -> None:
    """Initializes SQLite relational database with WAL mode and resilient busy timeout."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path, timeout=30.0) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA busy_timeout=30000;")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS benchmark_runs (
                run_id TEXT PRIMARY KEY,
                phase TEXT NOT NULL,
                scenario_name TEXT NOT NULL,
                concurrency_level INTEGER NOT NULL,
                models_evaluated TEXT NOT NULL,
                total_requests INTEGER NOT NULL,
                success_count INTEGER NOT NULL,
                fail_count INTEGER NOT NULL,
                ttft_p50_ms REAL,
                ttft_p90_ms REAL,
                ttft_p99_ms REAL,
                tpot_mean_ms REAL,
                throughput_tps REAL,
                total_prompt_tokens INTEGER,
                total_completion_tokens INTEGER,
                local_served_count INTEGER NOT NULL,
                cloud_burst_count INTEGER NOT NULL,
                estimated_cost_usd REAL,
                peak_vram_used_mib REAL,
                peak_gpu_util_pct REAL,
                vllm_kv_cache_usage_pct REAL,
                max_waiting_requests INTEGER,
                duration_s REAL NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS benchmark_requests (
                request_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                model_requested TEXT NOT NULL,
                model_served TEXT NOT NULL,
                served_by_layer TEXT NOT NULL,
                target_node TEXT,
                status_code INTEGER NOT NULL,
                ttft_ms REAL,
                tpot_ms REAL,
                prompt_tokens INTEGER,
                completion_tokens INTEGER,
                total_latency_s REAL NOT NULL,
                retry_count INTEGER DEFAULT 0,
                fallback_trigger_reason TEXT,
                error_details TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (run_id) REFERENCES benchmark_runs(run_id)
            );
        """)

        cursor.execute("""
            CREATE VIEW IF NOT EXISTS vw_saturation_curve AS
            SELECT 
                phase,
                scenario_name,
                concurrency_level,
                total_requests,
                success_count,
                ttft_p50_ms,
                ttft_p99_ms,
                tpot_mean_ms,
                throughput_tps,
                local_served_count,
                cloud_burst_count,
                peak_vram_used_mib,
                peak_gpu_util_pct,
                vllm_kv_cache_usage_pct,
                max_waiting_requests,
                duration_s
            FROM benchmark_runs
            ORDER BY phase, concurrency_level;
        """)
        conn.commit()


# --- Asynchronous Telemetry Continuous Background Sampler ---


@dataclass
class HardwareTelemetry:
    vram_used_mib: float
    gpu_util_pct: float
    kv_cache_usage_pct: float
    waiting_requests: int


async def query_prometheus_scalar_async(
    client: httpx.AsyncClient, prometheus_url: str, query: str
) -> float | None:
    """Non-blocking query to Prometheus vector endpoint."""
    try:
        resp = await client.get(
            f"{prometheus_url}/api/v1/query", params={"query": query}, timeout=3.0
        )
        if resp.status_code == 200:
            data = resp.json().get("data", {}).get("result", [])
            if data:
                values = [
                    float(item["value"][1])
                    for item in data
                    if "value" in item
                    and len(item["value"]) > 1
                    and not math.isnan(float(item["value"][1]))
                    and not math.isinf(float(item["value"][1]))
                ]
                return sum(values) if values else None
    except Exception:
        pass
    return None


async def fetch_hardware_telemetry_async(
    client: httpx.AsyncClient, prometheus_url: str
) -> HardwareTelemetry:
    """Fetches instantaneous DCGM and vLLM metrics concurrently."""
    clean_sel = DEFAULT_PROM_SELECTOR.strip().strip("{}")
    sel = f"{{{clean_sel}}}" if clean_sel else ""
    vram_raw, util_raw, kv_raw, waiting_raw = await asyncio.gather(
        query_prometheus_scalar_async(client, prometheus_url, f"max({PROM_METRIC_VRAM}{sel})"),
        query_prometheus_scalar_async(client, prometheus_url, f"avg({PROM_METRIC_UTIL}{sel})"),
        query_prometheus_scalar_async(client, prometheus_url, f"max({PROM_METRIC_KV_CACHE}{sel})"),
        query_prometheus_scalar_async(client, prometheus_url, f"sum({PROM_METRIC_WAITING}{sel})"),
    )
    vram_val = vram_raw or 0.0
    util_val = util_raw or 0.0
    kv_val = kv_raw or 0.0
    if 0.0 < kv_val <= 1.0:
        kv_val *= 100.0
    waiting_val = int(waiting_raw or 0)
    return HardwareTelemetry(
        vram_used_mib=vram_val,
        gpu_util_pct=util_val,
        kv_cache_usage_pct=kv_val,
        waiting_requests=waiting_val,
    )


async def poll_telemetry_during_run(
    client: httpx.AsyncClient,
    prometheus_url: str,
    stop_event: asyncio.Event,
    interval_s: float = 0.5,
) -> HardwareTelemetry:
    """Continuously polls Prometheus during execution to capture genuine intra-run peaks."""
    peak = HardwareTelemetry(0.0, 0.0, 0.0, 0)
    while not stop_event.is_set():
        sample = await fetch_hardware_telemetry_async(client, prometheus_url)
        peak.vram_used_mib = max(peak.vram_used_mib, sample.vram_used_mib)
        peak.gpu_util_pct = max(peak.gpu_util_pct, sample.gpu_util_pct)
        peak.kv_cache_usage_pct = max(peak.kv_cache_usage_pct, sample.kv_cache_usage_pct)
        peak.waiting_requests = max(peak.waiting_requests, sample.waiting_requests)
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(stop_event.wait(), timeout=interval_s)
    return peak


# --- Request Execution Harness ---


@dataclass
class RequestRecord:
    request_id: str
    model_requested: str
    model_served: str
    served_by_layer: str
    target_node: str
    status_code: int
    ttft_ms: float
    tpot_ms: float
    prompt_tokens: int
    completion_tokens: int
    total_latency_s: float
    retry_count: int
    fallback_trigger_reason: str | None
    error_details: str | None


async def execute_inference_stream(
    client: httpx.AsyncClient,
    gateway_url: str,
    api_key: str,
    model: str,
    prompt: str,
    max_tokens: int,
    request_id: str,
    timeout: float = DEFAULT_REQUEST_TIMEOUT_S,
) -> RequestRecord:
    """Executes streaming inference, parses SSE deltas, and extracts precision telemetry."""
    req_uuid = f"{request_id}_{uuid.uuid4().hex[:6]}"
    unique_prompt = f"[Nonce: {req_uuid}] {prompt}"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": unique_prompt}],
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
    tokens_generated = 0
    prompt_tokens_reported = 0
    status_code = 0
    served_model = model
    error_text: str | None = None
    fallback_reason: str | None = None

    try:
        async with client.stream(
            "POST", gateway_url, json=payload, headers=headers, timeout=timeout
        ) as resp:
            status_code = resp.status_code
            if status_code != 200:
                error_chunks = []
                bytes_read = 0
                async for err_chunk in resp.aiter_bytes(chunk_size=512):
                    error_chunks.append(err_chunk)
                    bytes_read += len(err_chunk)
                    if bytes_read >= 512:
                        break
                error_text = b"".join(error_chunks).decode("utf-8", errors="ignore")
                return RequestRecord(
                    request_id=req_uuid,
                    model_requested=model,
                    model_served=served_model,
                    served_by_layer="ERROR",
                    target_node="unknown",
                    status_code=status_code,
                    ttft_ms=0.0,
                    tpot_ms=0.0,
                    prompt_tokens=int(len(unique_prompt.split()) * 1.3),
                    completion_tokens=0,
                    total_latency_s=time.perf_counter() - t_start,
                    retry_count=0,
                    fallback_trigger_reason=f"HTTP_{status_code}",
                    error_details=error_text[:200],
                )

            async for line in resp.aiter_lines():
                if not line.strip() or not line.startswith("data: "):
                    continue
                data_str = line[6:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    if chunk.get("model"):
                        served_model = chunk["model"]
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
                            tokens_generated += 1
                            if first_token_time is None:
                                first_token_time = now
                            last_token_time = now
                except json.JSONDecodeError:
                    continue

            if reported_completion_tokens is not None and reported_completion_tokens > 0:
                tokens_generated = reported_completion_tokens
    except httpx.TimeoutException as exc:
        status_code = 408
        error_text = f"Client Timeout: {exc}"
        fallback_reason = "CLIENT_TIMEOUT"
    except Exception as exc:
        status_code = 500
        error_text = str(exc)
        fallback_reason = "CONNECTION_EXCEPTION"

    t_end = time.perf_counter()
    total_latency_s = t_end - t_start
    ttft_ms = (
        ((first_token_time - t_start) * 1000.0)
        if first_token_time
        else (total_latency_s * 1000.0 if status_code == 200 else 0.0)
    )

    decode_end = last_token_time or t_end
    if tokens_generated > 1 and first_token_time and decode_end > first_token_time:
        tpot_ms = ((decode_end - first_token_time) / (tokens_generated - 1)) * 1000.0
    else:
        tpot_ms = 0.0

    is_cloud_burst = any(prov in served_model.lower() for prov in CLOUD_BURST_PROVIDERS)
    served_by_layer = "CLOUD_BURST" if is_cloud_burst else "LOCAL_GPU"
    target_node = "cloud-burst-endpoint" if is_cloud_burst else "local-gpu-worker"
    prompt_tokens = prompt_tokens_reported or int(len(unique_prompt.split()) * 1.3)

    return RequestRecord(
        request_id=req_uuid,
        model_requested=model,
        model_served=served_model,
        served_by_layer=served_by_layer,
        target_node=target_node,
        status_code=status_code,
        ttft_ms=ttft_ms,
        tpot_ms=tpot_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=tokens_generated,
        total_latency_s=total_latency_s,
        retry_count=1
        if is_cloud_burst and not any(prov in model.lower() for prov in CLOUD_BURST_PROVIDERS)
        else 0,
        fallback_trigger_reason="OVERFLOW_FAILOVER"
        if is_cloud_burst and model != served_model
        else fallback_reason,
        error_details=error_text[:200] if error_text else None,
    )


# --- Scenario Execution ---


@dataclass
class ScenarioSpec:
    run_id: str
    phase: str
    scenario_name: str
    concurrency_level: int
    requests_spec: list[tuple[str, str, int]]


def save_scenario_results_to_db(
    db_path: Path,
    spec: ScenarioSpec,
    records: list[RequestRecord],
    duration_s: float,
    second_node_cost: float,
    cloud_in_rate: float,
    cloud_out_rate: float,
    peak_telem: HardwareTelemetry,
) -> None:
    """Persists scenario metrics to SQLite on a dedicated worker thread."""
    success_records = [r for r in records if r.status_code == 200]
    fail_records = [r for r in records if r.status_code != 200]
    local_count = sum(1 for r in success_records if r.served_by_layer == "LOCAL_GPU")
    cloud_count = sum(1 for r in success_records if r.served_by_layer == "CLOUD_BURST")

    ttft_values = [r.ttft_ms for r in success_records if r.ttft_ms > 0]
    tpot_values = [r.tpot_ms for r in success_records if r.tpot_ms > 0]

    ttft_p50 = compute_percentile(ttft_values, 50)
    ttft_p90 = compute_percentile(ttft_values, 90)
    ttft_p99 = compute_percentile(ttft_values, 99)
    tpot_mean = statistics.mean(tpot_values) if tpot_values else 0.0

    total_prompt_tok = sum(r.prompt_tokens for r in success_records)
    total_completion_tok = sum(r.completion_tokens for r in success_records)
    throughput_tps = (total_completion_tok / duration_s) if duration_s > 0 else 0.0

    local_duration_s = max(
        (r.total_latency_s for r in success_records if r.served_by_layer == "LOCAL_GPU"),
        default=0.0,
    )
    gpu_cost = (min(duration_s, local_duration_s) * second_node_cost) if local_count > 0 else 0.0
    cloud_prompt_tok = sum(
        r.prompt_tokens for r in success_records if r.served_by_layer == "CLOUD_BURST"
    )
    cloud_comp_tok = sum(
        r.completion_tokens for r in success_records if r.served_by_layer == "CLOUD_BURST"
    )
    cloud_cost = (cloud_prompt_tok * cloud_in_rate / 1_000_000.0) + (
        cloud_comp_tok * cloud_out_rate / 1_000_000.0
    )
    total_cost_usd = gpu_cost + cloud_cost

    unique_models = sorted({m for m, _, _ in spec.requests_spec})

    with sqlite3.connect(db_path, timeout=30.0) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO benchmark_runs (
                run_id, phase, scenario_name, concurrency_level, models_evaluated,
                total_requests, success_count, fail_count,
                ttft_p50_ms, ttft_p90_ms, ttft_p99_ms, tpot_mean_ms, throughput_tps,
                total_prompt_tokens, total_completion_tokens, local_served_count, cloud_burst_count,
                estimated_cost_usd, peak_vram_used_mib, peak_gpu_util_pct, vllm_kv_cache_usage_pct,
                max_waiting_requests, duration_s
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                spec.run_id,
                spec.phase,
                spec.scenario_name,
                spec.concurrency_level,
                json.dumps(unique_models),
                len(records),
                len(success_records),
                len(fail_records),
                ttft_p50,
                ttft_p90,
                ttft_p99,
                tpot_mean,
                throughput_tps,
                total_prompt_tok,
                total_completion_tok,
                local_count,
                cloud_count,
                total_cost_usd,
                peak_telem.vram_used_mib,
                peak_telem.gpu_util_pct,
                peak_telem.kv_cache_usage_pct,
                peak_telem.waiting_requests,
                duration_s,
            ),
        )

        req_tuples = [
            (
                r.request_id,
                spec.run_id,
                r.model_requested,
                r.model_served,
                r.served_by_layer,
                r.target_node,
                r.status_code,
                r.ttft_ms,
                r.tpot_ms,
                r.prompt_tokens,
                r.completion_tokens,
                r.total_latency_s,
                r.retry_count,
                r.fallback_trigger_reason,
                r.error_details,
            )
            for r in records
        ]
        cursor.execute("DELETE FROM benchmark_requests WHERE run_id = ?", (spec.run_id,))
        cursor.executemany(
            """
            INSERT OR REPLACE INTO benchmark_requests (
                request_id, run_id, model_requested, model_served, served_by_layer,
                target_node, status_code, ttft_ms, tpot_ms, prompt_tokens,
                completion_tokens, total_latency_s, retry_count, fallback_trigger_reason, error_details
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            req_tuples,
        )
        conn.commit()

    print(f"  [✓] Execution Completed in {duration_s:.2f}s")
    print(
        f"      - Requests: {len(records)} total | {len(success_records)} success | {len(fail_records)} failed"
    )
    print(f"      - Routing:  {local_count} served by Local GPU | {cloud_count} Cloud Burst")
    print(
        f"      - Latency:  TTFT P50: {ttft_p50:.1f}ms | P90: {ttft_p90:.1f}ms | P99: {ttft_p99:.1f}ms"
    )
    print(
        f"      - Fluidity: TPOT: {tpot_mean:.1f} ms/token | Throughput: {throughput_tps:.1f} tok/s"
    )
    print(
        f"      - Hardware: Peak VRAM: {peak_telem.vram_used_mib:.0f} MiB | GPU Util: {peak_telem.gpu_util_pct:.1f}% | KV Cache: {peak_telem.kv_cache_usage_pct:.1f}%"
    )
    print(f"      - FinOps:   Estimated Cost: ${total_cost_usd:.5f} USD")


async def run_scenario(
    spec: ScenarioSpec,
    gateway_url: str,
    api_key: str,
    prometheus_url: str,
    db_path: Path,
    second_node_cost: float,
    cloud_in_rate: float,
    cloud_out_rate: float,
) -> None:
    """Runs scenario with asynchronous background telemetry sampling."""
    print(f"\n[*] RUNNING SCENARIO: [{spec.phase.upper()}] {spec.scenario_name}")
    print(f"    - Concurrency: {spec.concurrency_level} parallel client(s)")
    print(f"    - Total Requests: {len(spec.requests_spec)}")

    limits = httpx.Limits(
        max_connections=spec.concurrency_level + 20,
        max_keepalive_connections=max(30, spec.concurrency_level),
    )
    start_time = time.perf_counter()

    async with (
        httpx.AsyncClient(limits=limits, verify=DEFAULT_SSL_VERIFY, trust_env=True) as client,
        httpx.AsyncClient(verify=DEFAULT_SSL_VERIFY, trust_env=True) as telem_client,
    ):
        stop_telem = asyncio.Event()
        telem_task = asyncio.create_task(
            poll_telemetry_during_run(
                telem_client, prometheus_url, stop_telem, interval_s=DEFAULT_TELEM_INTERVAL_S
            )
        )

        tasks = [
            execute_inference_stream(
                client,
                gateway_url=gateway_url,
                api_key=api_key,
                model=model_name,
                prompt=prompt,
                max_tokens=max_tok,
                request_id=f"{spec.run_id}_req_{idx + 1}",
                timeout=DEFAULT_REQUEST_TIMEOUT_S,
            )
            for idx, (model_name, prompt, max_tok) in enumerate(spec.requests_spec)
        ]
        records: list[RequestRecord] = await asyncio.gather(*tasks)

        stop_telem.set()
        peak_telem = await telem_task

    duration_s = time.perf_counter() - start_time

    await asyncio.to_thread(
        save_scenario_results_to_db,
        db_path,
        spec,
        records,
        duration_s,
        second_node_cost,
        cloud_in_rate,
        cloud_out_rate,
        peak_telem,
    )


# --- Dynamic Matrix Builder ---


def build_benchmark_matrix(
    fast_model: str,
    coder_model: str,
    reasoning_model: str,
    cloud_model: str,
    phase_a_steps: list[int],
    phase_c_concurrency: int,
    phase_c_cloud_concurrency: int = 10,
    session_id: str | None = None,
) -> list[ScenarioSpec]:
    """Generates analytical matrix across Phase A, B, and Phase C saturation/failover."""
    scenarios: list[ScenarioSpec] = []
    sfx = f"_{session_id}" if session_id else f"_{int(time.time())}_{uuid.uuid4().hex[:6]}"

    # Phase A: Isolated sweeps
    for c in phase_a_steps:
        scenarios.append(
            ScenarioSpec(
                f"phase_a_fast_c{c}{sfx}",
                "phase_a_isolated",
                f"Isolated Base: {fast_model} (C={c})",
                c,
                [(fast_model, PROMPT_FAST, DEFAULT_TOKENS_FAST) for _ in range(c)],
            )
        )
        scenarios.append(
            ScenarioSpec(
                f"phase_a_coder_c{c}{sfx}",
                "phase_a_isolated",
                f"Isolated LoRA: {coder_model} (C={c})",
                c,
                [(coder_model, PROMPT_CODER, DEFAULT_TOKENS_CODER) for _ in range(c)],
            )
        )
        scenarios.append(
            ScenarioSpec(
                f"phase_a_reasoning_c{c}{sfx}",
                "phase_a_isolated",
                f"Isolated LoRA: {reasoning_model} (C={c})",
                c,
                [(reasoning_model, PROMPT_REASONING, DEFAULT_TOKENS_REASONING) for _ in range(c)],
            )
        )

    # Phase B: Enterprise Mixed Concurrency
    mixed_c = max(phase_a_steps)
    models_cycle = [
        (reasoning_model, PROMPT_REASONING, DEFAULT_TOKENS_REASONING),
        (coder_model, PROMPT_CODER, DEFAULT_TOKENS_CODER),
        (fast_model, PROMPT_FAST, DEFAULT_TOKENS_FAST),
    ]
    spec_b = [models_cycle[i % len(models_cycle)] for i in range(mixed_c)]
    scenarios.append(
        ScenarioSpec(
            f"phase_b_enterprise_workload_c{len(spec_b)}{sfx}",
            "phase_b_mixed",
            f"Enterprise Tri-Model Workload (C={len(spec_b)})",
            len(spec_b),
            spec_b,
        )
    )

    # Phase C: Extreme Saturation & Cloud Burst Failover Verification
    scenarios.append(
        ScenarioSpec(
            f"phase_c_saturation_knee_c{phase_c_concurrency}{sfx}",
            "phase_c_overflow",
            f"Extreme Saturation Knee: Deep Reasoning (C={phase_c_concurrency})",
            phase_c_concurrency,
            [
                (reasoning_model, PROMPT_REASONING, DEFAULT_TOKENS_REASONING)
                for _ in range(phase_c_concurrency)
            ],
        )
    )

    scenarios.append(
        ScenarioSpec(
            f"phase_c_cloud_tier_reference_c{phase_c_cloud_concurrency}{sfx}",
            "phase_c_overflow",
            f"Cloud Burst Baseline: {cloud_model} (C={phase_c_cloud_concurrency})",
            phase_c_cloud_concurrency,
            [
                (cloud_model, PROMPT_FAST, DEFAULT_TOKENS_FAST)
                for _ in range(phase_c_cloud_concurrency)
            ],
        )
    )

    return scenarios


async def main() -> None:
    parser = argparse.ArgumentParser(description="Empirical Performance Matrix Benchmark")
    parser.add_argument(
        "--gateway-url", default=DEFAULT_GATEWAY_URL, help="Inference Gateway API URL"
    )
    parser.add_argument(
        "--prometheus-url", default=DEFAULT_PROMETHEUS_URL, help="Prometheus telemetry URL"
    )
    parser.add_argument("--api-key", default=DEFAULT_API_KEY, help="Master Gateway API key")
    parser.add_argument(
        "--db-path", default=DEFAULT_DB_PATH, help="Path to SQLite results database"
    )
    parser.add_argument(
        "--pricing-catalog", default=DEFAULT_PRICING_CATALOG, help="Path to pricing catalog JSON"
    )
    parser.add_argument(
        "--fast-model", default=DEFAULT_FAST_MODEL, help="Base fast model identifier"
    )
    parser.add_argument(
        "--coder-model", default=DEFAULT_CODER_MODEL, help="Coder adapter model identifier"
    )
    parser.add_argument(
        "--reasoning-model",
        default=DEFAULT_REASONING_MODEL,
        help="Reasoning adapter model identifier",
    )
    parser.add_argument(
        "--cloud-model", default=DEFAULT_CLOUD_MODEL, help="Cloud burst fallback model identifier"
    )
    parser.add_argument(
        "--phase-a-steps", default="5,15,30", help="Comma-separated concurrency steps for Phase A"
    )
    parser.add_argument(
        "--phase-c-concurrency", type=int, default=35, help="Saturation concurrency for Phase C"
    )
    parser.add_argument(
        "--phase-c-cloud-concurrency",
        type=int,
        default=10,
        help="Cloud burst baseline concurrency for Phase C",
    )
    parser.add_argument(
        "--session-id", default=None, help="Optional custom session identifier suffix"
    )
    args = parser.parse_args()

    if not args.api_key:
        print(
            "[!] ERROR: Master Gateway API key must be provided via --api-key or MASTER_KEY env variable."
        )
        sys.exit(1)

    db_file = Path(args.db_path)
    await asyncio.to_thread(init_database, db_file)

    hourly_node_cost, cloud_in_rate, cloud_out_rate = load_pricing_parameters(args.pricing_catalog)
    nodes_count = int(os.environ.get("ACTIVE_GPU_NODES", "2"))
    second_node_cost = (hourly_node_cost * nodes_count) / 3600.0

    steps = [int(s.strip()) for s in args.phase_a_steps.split(",") if s.strip()]
    if not steps:
        print("[!] ERROR: At least one concurrency step must be specified.", file=sys.stderr)
        sys.exit(1)

    print("=" * 80)
    print("STARTING EMPIRICAL PERFORMANCE MATRIX BENCHMARK")
    print(f"Target Gateway:    {args.gateway_url}")
    print(f"Target Database:   {args.db_path}")
    print(
        f"Pricing Model:     ${hourly_node_cost:.2f}/h per node ({nodes_count} nodes = ${second_node_cost * 3600:.2f}/h)"
    )
    print("=" * 80)

    scenarios = build_benchmark_matrix(
        fast_model=args.fast_model,
        coder_model=args.coder_model,
        reasoning_model=args.reasoning_model,
        cloud_model=args.cloud_model,
        phase_a_steps=steps,
        phase_c_concurrency=args.phase_c_concurrency,
        phase_c_cloud_concurrency=args.phase_c_cloud_concurrency,
        session_id=args.session_id,
    )

    for sc in scenarios:
        await run_scenario(
            spec=sc,
            gateway_url=args.gateway_url,
            api_key=args.api_key,
            prometheus_url=args.prometheus_url,
            db_path=db_file,
            second_node_cost=second_node_cost,
            cloud_in_rate=cloud_in_rate,
            cloud_out_rate=cloud_out_rate,
        )
        await asyncio.sleep(DEFAULT_STEP_COOLDOWN_S)

    print("\n[✓] Benchmark matrix executed successfully.")


if __name__ == "__main__":
    asyncio.run(main())
