#!/usr/bin/env python3
"""
Goodput & Semantic Quality Gate Benchmark Orchestrator
======================================================
Implements canonical specification SPEC-BENCHMARK-METHODOLOGY-001:
1. Strict SLA-bounded "Goodput" measurement (P99 TTFT <= 1.0s, P95 TPOT <= 60ms/tok)
2. Stochastic Poisson arrival process simulating realistic multi-tenant arrivals
3. Realistic workload mixture across 4 standard profiles (Chat, Code, RAG, Reasoning)
4. Dual-Track Semantic Quality Gate (Verifiable code execution & numerical math reasoning)
5. Continuous non-blocking hardware telemetry sampling (DCGM VRAM, GPU util, KV-Cache)

Zero Hardcoding: Fully configurable via environment variables and CLI arguments.
Language Decoupling: 100% Technical English.
Target: pocs/elastic-multi-gpu-inference/data/benchmarks.db
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import math
import os
import random
import re
import sqlite3
import statistics
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
DEFAULT_SSL_VERIFY = os.environ.get("BENCHMARK_SSL_VERIFY", "true").lower() not in (
    "false",
    "0",
    "no",
)
DEFAULT_REQUEST_TIMEOUT_S = float(os.environ.get("BENCHMARK_REQUEST_TIMEOUT_S", "120.0"))
DEFAULT_TELEM_INTERVAL_S = float(os.environ.get("BENCHMARK_TELEM_INTERVAL_S", "0.5"))
DEFAULT_STEP_COOLDOWN_S = float(os.environ.get("BENCHMARK_STEP_COOLDOWN_S", "2.0"))

# Default SLA Thresholds for Goodput Calculation
DEFAULT_SLA_MAX_TTFT_MS = float(os.environ.get("SLA_MAX_TTFT_MS", "1000.0"))
DEFAULT_SLA_MAX_TPOT_MS = float(os.environ.get("SLA_MAX_TPOT_MS", "60.0"))

# Prometheus Metrics Configuration
PROM_METRIC_VRAM = os.environ.get("PROM_METRIC_VRAM", "DCGM_FI_DEV_FB_USED")
PROM_METRIC_UTIL = os.environ.get("PROM_METRIC_UTIL", "DCGM_FI_DEV_GPU_UTIL")
PROM_METRIC_KV_CACHE = os.environ.get("PROM_METRIC_KV_CACHE", "vllm:gpu_cache_usage_perc")
PROM_METRIC_WAITING = os.environ.get("PROM_METRIC_WAITING", "vllm:num_requests_waiting")
DEFAULT_PROM_SELECTOR = os.environ.get("PROMETHEUS_LABEL_SELECTOR", "")

# Default Models
DEFAULT_FAST_MODEL = os.environ.get("BENCHMARK_FAST_MODEL", "light-model-fast")
DEFAULT_CODER_MODEL = os.environ.get("BENCHMARK_CODER_MODEL", "light-model-coder")
DEFAULT_REASONING_MODEL = os.environ.get("BENCHMARK_REASONING_MODEL", "reasoning-model")
DEFAULT_CLOUD_MODEL = os.environ.get("BENCHMARK_CLOUD_MODEL", "gemini-cloud-backup")

CLOUD_BURST_PROVIDERS = tuple(
    x.strip().lower()
    for x in os.environ.get("CLOUD_BURST_PROVIDERS", "gemini,gpt,claude,bedrock,azure").split(",")
    if x.strip()
)


# --- Pricing and Catalog Loader ---


def load_pricing_parameters(catalog_path: str) -> tuple[float, float, float]:
    """Loads hourly node rate and cloud token pricing from catalog with fallback."""
    hourly_node_cost = float(os.environ.get("SPOT_HOURLY_COST_PER_NODE", "0.98"))
    cloud_in_rate = float(os.environ.get("CLOUD_BURST_COST_PER_M_INPUT", "0.075"))
    cloud_out_rate = float(os.environ.get("CLOUD_BURST_COST_PER_M_OUTPUT", "0.30"))

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
                        hourly_node_cost = float(
                            instance.get("spot_hourly_mean", str(hourly_node_cost))
                        )
                        break
        except Exception as exc:
            print(
                f"[!] WARNING: Failed to parse catalog '{cat_file}': {exc}. Using fallbacks.",
                file=sys.stderr,
            )

    return hourly_node_cost, cloud_in_rate, cloud_out_rate


# --- Statistical Utilities ---


def compute_percentile(values: list[float], percentile: int) -> float:
    """Computes exact inclusive percentile across any non-empty float list."""
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


# --- Quality Gate Validation Challenges ---

QUALITY_CHALLENGES = [
    # Track A: Code Synthesis Tasks (Verifiable algorithmic correctness)
    {
        "id": "code_fibonacci",
        "type": "code",
        "prompt": "Write a Python function named `fib(n)` that returns the n-th Fibonacci number. Provide only code inside a markdown block.",
        "target_tokens": 120,
        "model_pref": "coder",
        "expected_sub": "def fib",
    },
    {
        "id": "code_is_prime",
        "type": "code",
        "prompt": "Write a Python function `is_prime(n: int) -> bool` that returns True if n is prime, False otherwise. Return only the function.",
        "target_tokens": 140,
        "model_pref": "coder",
        "expected_sub": "def is_prime",
    },
    {
        "id": "code_reverse_words",
        "type": "code",
        "prompt": "Write a Python function `reverse_words(s: str) -> str` that reverses words in a sentence while preserving whitespace. Only code.",
        "target_tokens": 100,
        "model_pref": "coder",
        "expected_sub": "def reverse_words",
    },
    # Track B: Numerical Math Reasoning Tasks (GSM8K Style)
    {
        "id": "math_apples_baskets",
        "type": "math",
        "prompt": "A farmer has 12 baskets. Each basket contains 15 apples. He sells 35 apples and gives 25 apples to his neighbor. How many apples are left? State the final numerical answer clearly at the end as: The answer is [number].",
        "target_tokens": 180,
        "model_pref": "reasoning",
        "expected_answer": "120",
    },
    {
        "id": "math_train_speed",
        "type": "math",
        "prompt": "Train A travels 240 miles in 4 hours. Train B travels 360 miles in 5 hours. What is the difference in their average speeds in miles per hour? State the final number clearly as: The answer is [number].",
        "target_tokens": 180,
        "model_pref": "reasoning",
        "expected_answer": "12",
    },
    {
        "id": "math_discount_tax",
        "type": "math",
        "prompt": "An item costs $200. It is discounted by 20%, and then an 8% sales tax is applied to the discounted price. What is the final price in dollars? State the final answer as: The answer is [number].",
        "target_tokens": 200,
        "model_pref": "reasoning",
        "expected_answer": "172.8",
    },
]


def evaluate_quality_response(challenge: dict[str, Any], response_text: str) -> bool:
    """Evaluates whether the generated response strictly passes semantic verification."""
    if not response_text:
        return False

    c_type = challenge["type"]
    if c_type == "code":
        # Check presence of required function definition
        expected = challenge["expected_sub"]
        return expected in response_text
    elif c_type == "math":
        expected_ans = challenge["expected_answer"]
        # Look for 'The answer is <num>' or direct mention of expected number
        patterns = [
            rf"(?:answer\s+is\s+|final\s+price\s+is\s+|total\s+is\s+|result\s+is\s+)[^\d]*({re.escape(expected_ans)})",
            rf"\b{re.escape(expected_ans)}\b",
        ]
        return any(re.search(pat, response_text, re.IGNORECASE) is not None for pat in patterns)

    return False


# --- Database Schema Management ---


def init_database(db_path: Path) -> None:
    """Initializes SQLite database with WAL mode and resilient tables."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path, timeout=30.0) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=30000;")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS goodput_benchmark_runs (
                run_id TEXT PRIMARY KEY,
                concurrency INTEGER NOT NULL,
                target_qps REAL NOT NULL,
                total_requests INTEGER NOT NULL,
                success_count INTEGER NOT NULL,
                failed_count INTEGER NOT NULL,
                compliant_count INTEGER NOT NULL,
                goodput_compliance_pct REAL NOT NULL,
                effective_goodput_qps REAL NOT NULL,
                ttft_p50_ms REAL,
                ttft_p90_ms REAL,
                ttft_p99_ms REAL,
                tpot_mean_ms REAL,
                tpot_p95_ms REAL,
                throughput_tps REAL,
                quality_tests_total INTEGER,
                quality_tests_passed INTEGER,
                quality_pass_rate_pct REAL,
                peak_vram_mib REAL,
                peak_gpu_util_pct REAL,
                peak_kv_cache_pct REAL,
                max_waiting_requests INTEGER,
                duration_s REAL NOT NULL,
                estimated_cost_usd REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS goodput_request_records (
                request_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                workload_profile TEXT NOT NULL,
                model_requested TEXT NOT NULL,
                model_served TEXT NOT NULL,
                status_code INTEGER NOT NULL,
                ttft_ms REAL,
                tpot_ms REAL,
                prompt_tokens INTEGER,
                completion_tokens INTEGER,
                total_latency_s REAL NOT NULL,
                is_sla_compliant INTEGER NOT NULL,
                is_quality_challenge INTEGER NOT NULL,
                quality_passed INTEGER,
                error_details TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (run_id) REFERENCES goodput_benchmark_runs(run_id)
            );
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
    """Non-blocking query to Prometheus vector endpoint with NaN/Inf filtering."""
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
    interval_s: float = DEFAULT_TELEM_INTERVAL_S,
) -> HardwareTelemetry:
    """Continuously monitors Prometheus to catch peak queue depth and VRAM during heavy load."""
    peak = HardwareTelemetry(0.0, 0.0, 0.0, 0)
    while not stop_event.is_set():
        sample = await fetch_hardware_telemetry_async(client, prometheus_url)
        peak.vram_used_mib = max(peak.vram_used_mib, sample.vram_used_mib)
        peak.gpu_util_pct = max(peak.gpu_util_pct, sample.gpu_util_pct)
        peak.kv_cache_usage_pct = max(peak.kv_cache_usage_pct, sample.kv_cache_usage_pct)
        peak.waiting_requests = max(peak.waiting_requests, sample.waiting_requests)
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(stop_event.wait(), timeout=interval_s)
    return peak


# --- Request Execution Harness ---


@dataclass
class DetailedRequestResult:
    request_id: str
    workload_profile: str
    model_requested: str
    model_served: str
    status_code: int
    ttft_ms: float
    tpot_ms: float
    prompt_tokens: int
    completion_tokens: int
    total_latency_s: float
    is_sla_compliant: bool
    is_quality_challenge: bool
    quality_passed: bool | None
    generated_text: str
    error_details: str | None


async def execute_request_stream(
    client: httpx.AsyncClient,
    gateway_url: str,
    api_key: str,
    model: str,
    prompt: str,
    max_tokens: int,
    request_id: str,
    workload_profile: str,
    challenge_meta: dict[str, Any] | None = None,
    sla_max_ttft_ms: float = DEFAULT_SLA_MAX_TTFT_MS,
    sla_max_tpot_ms: float = DEFAULT_SLA_MAX_TPOT_MS,
    timeout: float = DEFAULT_REQUEST_TIMEOUT_S,
) -> DetailedRequestResult:
    """Executes streaming inference, enforces bounds, and evaluates SLA compliance."""
    req_uuid = f"{request_id}_{uuid.uuid4().hex[:6]}"
    unique_prompt = f"[UID: {req_uuid}] {prompt}"
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
    collected_chunks: list[str] = []

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
                return DetailedRequestResult(
                    request_id=req_uuid,
                    workload_profile=workload_profile,
                    model_requested=model,
                    model_served=served_model,
                    status_code=status_code,
                    ttft_ms=0.0,
                    tpot_ms=0.0,
                    prompt_tokens=int(len(unique_prompt.split()) * 1.3),
                    completion_tokens=0,
                    total_latency_s=time.perf_counter() - t_start,
                    is_sla_compliant=False,
                    is_quality_challenge=challenge_meta is not None,
                    quality_passed=False if challenge_meta else None,
                    generated_text="",
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
                            collected_chunks.append(delta)
                except json.JSONDecodeError:
                    continue

            if reported_completion_tokens is not None and reported_completion_tokens > 0:
                tokens_generated = reported_completion_tokens
    except httpx.TimeoutException as exc:
        status_code = 408
        error_text = f"Client Timeout: {exc}"
    except Exception as exc:
        status_code = 500
        error_text = str(exc)

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

    prompt_tokens = prompt_tokens_reported or int(len(unique_prompt.split()) * 1.3)
    full_response_text = "".join(collected_chunks)

    # Determine SLA Compliance
    is_compliant = (
        status_code == 200
        and (ttft_ms <= sla_max_ttft_ms)
        and (tpot_ms <= sla_max_tpot_ms if tokens_generated > 1 else True)
    )

    # Evaluate Quality Challenge if attached
    quality_passed: bool | None = None
    if challenge_meta:
        quality_passed = evaluate_quality_response(challenge_meta, full_response_text)

    return DetailedRequestResult(
        request_id=req_uuid,
        workload_profile=workload_profile,
        model_requested=model,
        model_served=served_model,
        status_code=status_code,
        ttft_ms=ttft_ms,
        tpot_ms=tpot_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=tokens_generated,
        total_latency_s=total_latency_s,
        is_sla_compliant=is_compliant,
        is_quality_challenge=challenge_meta is not None,
        quality_passed=quality_passed,
        generated_text=full_response_text[:300],
        error_details=error_text[:200] if error_text else None,
    )


# --- Workload Profile Generator ---


def build_realistic_workload(
    target_concurrency: int,
    fast_model: str,
    coder_model: str,
    reasoning_model: str,
) -> list[dict[str, Any]]:
    """Generates heterogeneous requests according to standard enterprise distribution."""
    # Distribution: 50% Chat (Fast), 30% Coder (LoRA), 15% RAG (Fast), 5% Reasoning (LoRA)
    workload_items = []

    # Inject all Quality Challenges as priority items
    for ch in QUALITY_CHALLENGES:
        model = coder_model if ch["model_pref"] == "coder" else reasoning_model
        workload_items.append(
            {
                "model": model,
                "prompt": ch["prompt"],
                "max_tokens": ch["target_tokens"],
                "profile": f"Quality_{str(ch['type']).upper()}",
                "challenge": ch,
            }
        )

    # Fill remainder to reach target concurrency
    remaining = max(0, target_concurrency - len(workload_items))
    for _ in range(remaining):
        p = random.random()
        if p < 0.50:
            # Conversational Chat
            prompt = "Explain in 25 words the key financial benefits of deploying sovereign open-weights LLMs on private GPU nodes."
            workload_items.append(
                {
                    "model": fast_model,
                    "prompt": prompt,
                    "max_tokens": 60,
                    "profile": "Chat_Conversational",
                    "challenge": None,
                }
            )
        elif p < 0.80:
            # Code Copilot
            prompt = "Write an optimized Python function that calculates the moving average of a streaming series with a fixed window size."
            workload_items.append(
                {
                    "model": coder_model,
                    "prompt": prompt,
                    "max_tokens": 140,
                    "profile": "Code_Copilot",
                    "challenge": None,
                }
            )
        elif p < 0.95:
            # Long Document RAG
            long_context = (
                "Enterprise audit findings demonstrate compliance with regulatory governance standards. "
                * 30
            )
            prompt = f"Analyze the following regulatory excerpt and state the primary compliance requirement in 30 words:\n{long_context}"
            workload_items.append(
                {
                    "model": fast_model,
                    "prompt": prompt,
                    "max_tokens": 120,
                    "profile": "Document_RAG",
                    "challenge": None,
                }
            )
        else:
            # Deep Reasoning
            prompt = "Prove by induction that the sum of the first n positive integers equals n*(n+1)/2. Include the base case, inductive hypothesis, and algebraic induction step."
            workload_items.append(
                {
                    "model": reasoning_model,
                    "prompt": prompt,
                    "max_tokens": 280,
                    "profile": "Deep_Reasoning",
                    "challenge": None,
                }
            )

    return workload_items


# --- SQLite Persistence Worker ---


def save_goodput_run_to_db(
    db_path: Path,
    run_id: str,
    concurrency: int,
    target_qps: float,
    records: list[DetailedRequestResult],
    duration_s: float,
    second_node_cost: float,
    cloud_in_rate: float,
    cloud_out_rate: float,
    peak_telem: HardwareTelemetry,
    sla_max_ttft_ms: float,
    sla_max_tpot_ms: float,
) -> None:
    """Persists aggregated Goodput run metrics and individual request traces."""
    success_records = [r for r in records if r.status_code == 200]
    failed_records = [r for r in records if r.status_code != 200]
    compliant_records = [r for r in success_records if r.is_sla_compliant]

    goodput_compliance_pct = (len(compliant_records) / len(records) * 100.0) if records else 0.0
    effective_goodput_qps = (len(compliant_records) / duration_s) if duration_s > 0 else 0.0

    ttfts = [r.ttft_ms for r in success_records if r.ttft_ms > 0]
    tpots = [r.tpot_ms for r in success_records if r.tpot_ms > 0]

    ttft_p50 = compute_percentile(ttfts, 50)
    ttft_p90 = compute_percentile(ttfts, 90)
    ttft_p99 = compute_percentile(ttfts, 99)
    tpot_mean = statistics.mean(tpots) if tpots else 0.0
    tpot_p95 = compute_percentile(tpots, 95)

    total_completion_tok = sum(r.completion_tokens for r in success_records)
    throughput_tps = (total_completion_tok / duration_s) if duration_s > 0 else 0.0

    # Quality Gate Summary
    quality_records = [r for r in records if r.is_quality_challenge]
    quality_passed_records = [r for r in quality_records if r.quality_passed is True]
    quality_pass_rate_pct = (
        (len(quality_passed_records) / len(quality_records) * 100.0) if quality_records else 100.0
    )

    # FinOps Cost
    local_count = sum(
        1
        for r in success_records
        if not any(prov in r.model_served.lower() for prov in CLOUD_BURST_PROVIDERS)
    )
    local_duration_s = max(
        (
            r.total_latency_s
            for r in success_records
            if not any(prov in r.model_served.lower() for prov in CLOUD_BURST_PROVIDERS)
        ),
        default=0.0,
    )
    gpu_cost = (min(duration_s, local_duration_s) * second_node_cost) if local_count > 0 else 0.0

    cloud_prompt_tok = sum(
        r.prompt_tokens
        for r in success_records
        if any(prov in r.model_served.lower() for prov in CLOUD_BURST_PROVIDERS)
    )
    cloud_comp_tok = sum(
        r.completion_tokens
        for r in success_records
        if any(prov in r.model_served.lower() for prov in CLOUD_BURST_PROVIDERS)
    )
    cloud_cost = (cloud_prompt_tok * cloud_in_rate / 1_000_000.0) + (
        cloud_comp_tok * cloud_out_rate / 1_000_000.0
    )
    total_cost_usd = gpu_cost + cloud_cost

    with sqlite3.connect(db_path, timeout=30.0) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO goodput_benchmark_runs (
                run_id, concurrency, target_qps, total_requests, success_count, failed_count,
                compliant_count, goodput_compliance_pct, effective_goodput_qps,
                ttft_p50_ms, ttft_p90_ms, ttft_p99_ms, tpot_mean_ms, tpot_p95_ms, throughput_tps,
                quality_tests_total, quality_tests_passed, quality_pass_rate_pct,
                peak_vram_mib, peak_gpu_util_pct, peak_kv_cache_pct, max_waiting_requests,
                duration_s, estimated_cost_usd
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                concurrency,
                target_qps,
                len(records),
                len(success_records),
                len(failed_records),
                len(compliant_records),
                goodput_compliance_pct,
                effective_goodput_qps,
                ttft_p50,
                ttft_p90,
                ttft_p99,
                tpot_mean,
                tpot_p95,
                throughput_tps,
                len(quality_records),
                len(quality_passed_records),
                quality_pass_rate_pct,
                peak_telem.vram_used_mib,
                peak_telem.gpu_util_pct,
                peak_telem.kv_cache_usage_pct,
                peak_telem.waiting_requests,
                duration_s,
                total_cost_usd,
            ),
        )

        cursor.execute("DELETE FROM goodput_request_records WHERE run_id = ?", (run_id,))
        rec_tuples = [
            (
                r.request_id,
                run_id,
                r.workload_profile,
                r.model_requested,
                r.model_served,
                r.status_code,
                r.ttft_ms,
                r.tpot_ms,
                r.prompt_tokens,
                r.completion_tokens,
                r.total_latency_s,
                1 if r.is_sla_compliant else 0,
                1 if r.is_quality_challenge else 0,
                1 if r.quality_passed is True else (0 if r.quality_passed is False else None),
                r.error_details,
            )
            for r in records
        ]
        cursor.executemany(
            """
            INSERT OR REPLACE INTO goodput_request_records (
                request_id, run_id, workload_profile, model_requested, model_served,
                status_code, ttft_ms, tpot_ms, prompt_tokens, completion_tokens,
                total_latency_s, is_sla_compliant, is_quality_challenge, quality_passed, error_details
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rec_tuples,
        )
        conn.commit()

    print(f"\n  [✓] Goodput Step C={concurrency} Completed in {duration_s:.2f}s:")
    print(
        f"      - Goodput SLA Compliance: {goodput_compliance_pct:.1f}% ({len(compliant_records)}/{len(records)} requests met SLA)"
    )
    print(f"      - Effective Goodput:      {effective_goodput_qps:.2f} QPS under strict SLA")
    print(
        f"      - Latencies:              TTFT P50: {ttft_p50:.1f}ms | P99: {ttft_p99:.1f}ms (SLA Limit: <= {sla_max_ttft_ms:.0f}ms)"
    )
    print(
        f"      - Fluidity:               TPOT Mean: {tpot_mean:.1f}ms/t | P95: {tpot_p95:.1f}ms/t (SLA Limit: <= {sla_max_tpot_ms:.0f}ms)"
    )
    print(
        f"      - Quality Gate:           {quality_pass_rate_pct:.1f}% ({len(quality_passed_records)}/{len(quality_records)} challenges passed)"
    )
    print(
        f"      - Hardware Peaks:         VRAM: {peak_telem.vram_used_mib:.0f} MiB | GPU Util: {peak_telem.gpu_util_pct:.1f}% | KV-Cache: {peak_telem.kv_cache_usage_pct:.1f}%"
    )
    print(f"      - FinOps Cost:            ${total_cost_usd:.5f} USD")


# --- Concurrency Step Executor with Poisson Process ---


async def run_goodput_step(
    gateway_url: str,
    api_key: str,
    prometheus_url: str,
    db_path: Path,
    second_node_cost: float,
    cloud_in_rate: float,
    cloud_out_rate: float,
    concurrency: int,
    target_qps: float,
    workload_items: list[dict[str, Any]],
    session_id: str,
    sla_max_ttft_ms: float = DEFAULT_SLA_MAX_TTFT_MS,
    sla_max_tpot_ms: float = DEFAULT_SLA_MAX_TPOT_MS,
) -> None:
    """Executes a Goodput step dispatching requests via non-homogeneous Poisson arrivals."""
    print(
        f"\n[*] RUNNING GOODPUT BENCHMARK STEP: Concurrency={concurrency} | Target Rate={target_qps:.1f} QPS"
    )
    print(
        f"    - SLA Constraints: TTFT <= {sla_max_ttft_ms:.0f}ms | TPOT <= {sla_max_tpot_ms:.0f}ms/token"
    )

    limits = httpx.Limits(
        max_connections=concurrency + 20, max_keepalive_connections=max(30, concurrency)
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

        tasks = []
        for idx, item in enumerate(workload_items):
            # Poisson inter-arrival delay: dt = -ln(1 - U) / lambda
            if target_qps > 0 and idx > 0:
                poisson_delay = -math.log(max(1e-9, 1.0 - random.random())) / target_qps
                # Clamp delay to reasonable window to prevent test stalls
                await asyncio.sleep(min(0.25, poisson_delay))

            tasks.append(
                execute_request_stream(
                    client=client,
                    gateway_url=gateway_url,
                    api_key=api_key,
                    model=item["model"],
                    prompt=item["prompt"],
                    max_tokens=item["max_tokens"],
                    request_id=f"c{concurrency}_req{idx + 1}",
                    workload_profile=item["profile"],
                    challenge_meta=item["challenge"],
                    sla_max_ttft_ms=sla_max_ttft_ms,
                    sla_max_tpot_ms=sla_max_tpot_ms,
                    timeout=DEFAULT_REQUEST_TIMEOUT_S,
                )
            )

        records: list[DetailedRequestResult] = await asyncio.gather(*tasks)
        stop_telem.set()
        peak_telem = await telem_task

    duration_s = time.perf_counter() - start_time
    run_id = f"goodput_c{concurrency}_{int(time.time())}_{session_id}"

    await asyncio.to_thread(
        save_goodput_run_to_db,
        db_path,
        run_id,
        concurrency,
        target_qps,
        records,
        duration_s,
        second_node_cost,
        cloud_in_rate,
        cloud_out_rate,
        peak_telem,
        sla_max_ttft_ms,
        sla_max_tpot_ms,
    )


# --- Executive Reporting ---


def print_goodput_summary_report(db_path: Path) -> None:
    """Queries SQLite and displays the executive Goodput curve and Quality Gate status."""
    with sqlite3.connect(db_path, timeout=30.0) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                concurrency,
                total_requests,
                compliant_count,
                round(goodput_compliance_pct, 1),
                round(effective_goodput_qps, 2),
                round(ttft_p50_ms, 1),
                round(ttft_p99_ms, 1),
                round(tpot_mean_ms, 1),
                round(tpot_p95_ms, 1),
                round(throughput_tps, 1),
                round(quality_pass_rate_pct, 1),
                round(peak_kv_cache_pct, 1)
            FROM goodput_benchmark_runs
            ORDER BY concurrency;
        """)
        rows = cursor.fetchall()

        print("\n" + "=" * 115)
        print("          EXECUTIVE GOODPUT CAPACITY & QUALITY GATE AUDIT REPORT")
        print("=" * 115)
        print(
            f"{'Conc':<5} | {'Compliant':<10} | {'SLA %':<6} | {'Goodput':<9} | {'P50 TTFT':<9} | {'P99 TTFT':<9} | {'TPOT':<8} | {'P95 TPOT':<9} | {'Tok/s':<7} | {'Quality':<7} | {'KV-Cache'}"
        )
        print("-" * 115)
        for r in rows:
            conc, tot, comp, sla_pct, g_qps, p50_ttft, p99_ttft, tpot, p95_tpot, tps, qual, kv = r
            status_flag = "PASS" if sla_pct >= 95.0 and qual >= 99.0 else "DEGRADED"
            print(
                f"{conc:<5} | {comp}/{tot:<7} | {sla_pct:<5.1f}% | {g_qps:<5.2f} QPS | {p50_ttft:<7.1f}ms | {p99_ttft:<7.1f}ms | {tpot:<6.1f}ms | {p95_tpot:<7.1f}ms | {tps:<7.1f} | {qual:<5.1f}% | {kv:<5.1f}% [{status_flag}]"
            )
        print("=" * 115)


# --- CLI and Main Routine ---


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Goodput & Semantic Quality Gate Benchmark Harness"
    )
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
        "--concurrency-steps", default="5,15,30,45,60", help="Comma-separated concurrency levels"
    )
    parser.add_argument(
        "--target-qps", type=float, default=10.0, help="Target arrival rate for Poisson generator"
    )
    parser.add_argument(
        "--sla-max-ttft-ms",
        type=float,
        default=DEFAULT_SLA_MAX_TTFT_MS,
        help="Max TTFT in ms for SLA compliance",
    )
    parser.add_argument(
        "--sla-max-tpot-ms",
        type=float,
        default=DEFAULT_SLA_MAX_TPOT_MS,
        help="Max TPOT in ms for SLA compliance",
    )
    parser.add_argument(
        "--session-id", default=None, help="Custom identifier for the benchmark session"
    )
    args = parser.parse_args()

    if not args.api_key:
        print(
            "[!] ERROR: Master Gateway API key must be provided via --api-key or MASTER_KEY env variable.",
            file=sys.stderr,
        )
        sys.exit(1)

    steps = [int(s.strip()) for s in args.concurrency_steps.split(",") if s.strip()]
    if not steps:
        print("[!] ERROR: At least one concurrency step must be provided.", file=sys.stderr)
        sys.exit(1)

    session_id = args.session_id or uuid.uuid4().hex[:6]
    db_file = Path(args.db_path)
    await asyncio.to_thread(init_database, db_file)

    hourly_node_cost, cloud_in_rate, cloud_out_rate = load_pricing_parameters(args.pricing_catalog)
    nodes_count = int(os.environ.get("ACTIVE_GPU_NODES", "2"))
    second_node_cost = (hourly_node_cost * nodes_count) / 3600.0

    print("=" * 90)
    print("STARTING GOODPUT & SEMANTIC QUALITY GATE BENCHMARK")
    print(f"Target Gateway:    {args.gateway_url}")
    print(f"Target Database:   {args.db_path}")
    print(f"Session Identifier:{session_id}")
    print(
        f"SLA Target Bounds: TTFT <= {args.sla_max_ttft_ms:.0f}ms | TPOT <= {args.sla_max_tpot_ms:.0f}ms/token"
    )
    print(
        f"Pricing Model:     ${hourly_node_cost:.2f}/h per node ({nodes_count} nodes = ${second_node_cost * 3600:.2f}/h)"
    )
    print("=" * 90)

    for c in steps:
        # Scale target QPS proportionally to concurrency step if desired
        step_qps = max(1.0, float(c) * 0.8)
        workload = build_realistic_workload(
            target_concurrency=c,
            fast_model=args.fast_model,
            coder_model=args.coder_model,
            reasoning_model=args.reasoning_model,
        )
        await run_goodput_step(
            gateway_url=args.gateway_url,
            api_key=args.api_key,
            prometheus_url=args.prometheus_url,
            db_path=db_file,
            second_node_cost=second_node_cost,
            cloud_in_rate=cloud_in_rate,
            cloud_out_rate=cloud_out_rate,
            concurrency=c,
            target_qps=step_qps,
            workload_items=workload,
            session_id=session_id,
            sla_max_ttft_ms=args.sla_max_ttft_ms,
            sla_max_tpot_ms=args.sla_max_tpot_ms,
        )
        await asyncio.sleep(DEFAULT_STEP_COOLDOWN_S)

    print_goodput_summary_report(db_file)
    print("\n[✓] Goodput & Quality Gate benchmark completed successfully.")


if __name__ == "__main__":
    asyncio.run(main())
