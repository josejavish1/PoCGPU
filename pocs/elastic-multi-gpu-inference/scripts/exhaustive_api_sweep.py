#!/usr/bin/env python3
"""
Exhaustive Combinatorial API Parameter Sweep
============================================
Executes a Cartesian product of API-level variables (Model, Input Length, Output Length, Concurrency).
Infrastructure-level variables (KV Cache budget, Quantization, GPU Type, PCIe/NVLink)
require node pool mutations and vLLM restart, thus are handled in separate physical phases.

Certified for any enterprise environment (mid-market to global Tier-1).
Zero Hardcoding: Fully externalized via environment variables and CLI arguments.
Language Decoupling: 100% Technical English.
Target: pocs/elastic-multi-gpu-inference/data/benchmarks.db
"""

from __future__ import annotations

import argparse
import asyncio
import itertools
import json
import os
import sqlite3
import statistics
import sys
import time
import uuid
from pathlib import Path

import httpx

# --- Environment & Configuration Resolution ---

SCRIPT_DIR = Path(__file__).resolve().parent
POC_DIR = SCRIPT_DIR.parent
ROOT_DIR = POC_DIR.parent.parent

DEFAULT_GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://localhost:8080/v1/chat/completions")
DEFAULT_API_KEY = os.environ.get("MASTER_KEY", os.environ.get("LITELLM_MASTER_KEY", ""))
DEFAULT_DB_PATH = os.environ.get("BENCHMARK_DB_PATH", str(POC_DIR / "data" / "benchmarks.db"))
DEFAULT_REQUEST_TIMEOUT_S = float(os.environ.get("BENCHMARK_REQUEST_TIMEOUT_S", "120.0"))
DEFAULT_SWEEP_MODELS = os.environ.get(
    "BENCHMARK_SWEEP_MODELS", "light-model-fast,reasoning-model,light-model-coder"
)
DEFAULT_BASE_SENTENCE = os.environ.get(
    "BENCHMARK_SYNTHETIC_SENTENCE",
    "The enterprise architecture guarantees high throughput and low latency inference. ",
)


DEFAULT_SSL_VERIFY = os.environ.get("BENCHMARK_SSL_VERIFY", "true").lower() not in (
    "false",
    "0",
    "no",
)
DEFAULT_STEP_COOLDOWN_S = float(os.environ.get("BENCHMARK_STEP_COOLDOWN_S", "1.0"))
DEFAULT_CHARS_PER_TOKEN = int(os.environ.get("BENCHMARK_CHARS_PER_TOKEN", "4"))


def generate_prompt(target_tokens: int) -> str:
    """Generates synthetic English prompt text calibrated to target token count."""
    target_chars = max(1, int(target_tokens * DEFAULT_CHARS_PER_TOKEN))
    repetitions = (target_chars // max(1, len(DEFAULT_BASE_SENTENCE))) + 2
    return (DEFAULT_BASE_SENTENCE * repetitions)[:target_chars]


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


def init_database(db_path: Path) -> None:
    """Initializes SQLite table for combinatorial sweeps with WAL mode."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path, timeout=30.0) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=30000;")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS combinatorial_sweeps (
                run_id TEXT PRIMARY KEY,
                model TEXT NOT NULL,
                input_len INTEGER NOT NULL,
                output_len INTEGER NOT NULL,
                concurrency INTEGER NOT NULL,
                success_rate REAL NOT NULL,
                p50_ttft_ms REAL,
                p99_ttft_ms REAL,
                mean_tpot_ms REAL,
                throughput_tps REAL,
                duration_s REAL NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()


async def execute_request(
    client: httpx.AsyncClient,
    gateway_url: str,
    api_key: str,
    model: str,
    prompt: str,
    max_tokens: int,
    req_id: str,
    timeout: float = DEFAULT_REQUEST_TIMEOUT_S,
) -> tuple[int, float, float, int]:
    """Executes a streaming inference request against the gateway with strict delta validation."""
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": f"[UID: {req_id}] {prompt}"}],
        "max_tokens": max_tokens,
        "stream": True,
        "temperature": 0.0,
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
    status = 0

    try:
        async with client.stream(
            "POST", gateway_url, json=payload, headers=headers, timeout=timeout
        ) as resp:
            status = resp.status_code
            if status == 200:
                async for line in resp.aiter_lines():
                    if not line.strip() or not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        usage = chunk.get("usage")
                        if isinstance(usage, dict) and usage.get("completion_tokens") is not None:
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
    except Exception:
        status = 500

    t_end = time.perf_counter()
    ttft = ((first_token_time - t_start) * 1000.0) if first_token_time else 0.0
    decode_end = last_token_time or t_end
    if tokens > 1 and first_token_time and decode_end > first_token_time:
        tpot = ((decode_end - first_token_time) / (tokens - 1)) * 1000.0
    else:
        tpot = 0.0
    return status, ttft, tpot, tokens


def save_combination_to_db(
    db_path: Path,
    run_id: str,
    model: str,
    in_len: int,
    out_len: int,
    conc: int,
    success_rate: float,
    p50_ttft: float,
    p99_ttft: float,
    mean_tpot: float,
    tps: float,
    duration: float,
) -> None:
    """Persists combination summary to SQLite on dedicated worker thread."""
    with sqlite3.connect(db_path, timeout=30.0) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO combinatorial_sweeps 
            (run_id, model, input_len, output_len, concurrency, success_rate, p50_ttft_ms, p99_ttft_ms, mean_tpot_ms, throughput_tps, duration_s)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                model,
                in_len,
                out_len,
                conc,
                success_rate,
                p50_ttft,
                p99_ttft,
                mean_tpot,
                tps,
                duration,
            ),
        )
        conn.commit()


async def run_combination(
    client: httpx.AsyncClient,
    gateway_url: str,
    api_key: str,
    db_path: Path,
    model: str,
    in_len: int,
    out_len: int,
    conc: int,
) -> None:
    """Runs a single combination using shared persistent connection pool."""
    prompt = generate_prompt(in_len)
    t0 = time.perf_counter()

    tasks = [
        execute_request(client, gateway_url, api_key, model, prompt, out_len, uuid.uuid4().hex[:6])
        for _ in range(conc)
    ]
    results = await asyncio.gather(*tasks)

    duration = time.perf_counter() - t0
    success = [r for r in results if r[0] == 200]

    ttfts = [r[1] for r in success if r[1] > 0]
    tpots = [r[2] for r in success if r[2] > 0]
    total_out_toks = sum(r[3] for r in success)

    p50_ttft = compute_percentile(ttfts, 50)
    p99_ttft = compute_percentile(ttfts, 99)
    mean_tpot = statistics.mean(tpots) if tpots else 0.0
    tps = total_out_toks / duration if duration > 0 else 0.0
    success_rate = len(success) / conc if conc > 0 else 0.0

    run_id = f"comb_{model}_{in_len}_{out_len}_{conc}_{int(time.time())}_{uuid.uuid4().hex[:6]}"

    await asyncio.to_thread(
        save_combination_to_db,
        db_path,
        run_id,
        model,
        in_len,
        out_len,
        conc,
        success_rate,
        p50_ttft,
        p99_ttft,
        mean_tpot,
        tps,
        duration,
    )

    print(
        f"    [✓] {model[:18]:<18} | In={in_len:<4} | Out={out_len:<3} | C={conc:<2} -> "
        f"P50 TTFT: {p50_ttft:<6.1f}ms | P99: {p99_ttft:<6.1f}ms | TPOT: {mean_tpot:<5.1f}ms/t | "
        f"TPS: {tps:<6.1f} | Succ: {len(success)}/{conc}"
    )


async def main() -> None:
    parser = argparse.ArgumentParser(description="Exhaustive Combinatorial Parameter Sweep")
    parser.add_argument(
        "--gateway-url", default=DEFAULT_GATEWAY_URL, help="Inference Gateway API URL"
    )
    parser.add_argument("--api-key", default=DEFAULT_API_KEY, help="Master Gateway API key")
    parser.add_argument(
        "--db-path", default=DEFAULT_DB_PATH, help="Path to SQLite results database"
    )
    parser.add_argument(
        "--models",
        default=DEFAULT_SWEEP_MODELS,
        help="Comma-separated model names",
    )
    parser.add_argument(
        "--input-lengths", default="50,500,1000", help="Comma-separated prompt token lengths"
    )
    parser.add_argument(
        "--output-lengths", default="25,150,400", help="Comma-separated max output tokens"
    )
    parser.add_argument(
        "--concurrencies", default="5,20,40", help="Comma-separated concurrency levels"
    )
    args = parser.parse_args()

    if not args.api_key:
        print(
            "[!] ERROR: Master Gateway API key must be provided via --api-key or MASTER_KEY env variable."
        )
        sys.exit(1)

    db_file = Path(args.db_path)
    await asyncio.to_thread(init_database, db_file)

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    input_lens = [int(i.strip()) for i in args.input_lengths.split(",") if i.strip()]
    output_lens = [int(o.strip()) for o in args.output_lengths.split(",") if o.strip()]
    concurrencies = [int(c.strip()) for c in args.concurrencies.split(",") if c.strip()]

    if not (models and input_lens and output_lens and concurrencies):
        print(
            "[!] ERROR: Models, input-lengths, output-lengths, and concurrencies must not be empty.",
            file=sys.stderr,
        )
        sys.exit(1)

    matrix = list(itertools.product(models, input_lens, output_lens, concurrencies))
    print("=" * 80)
    print("STARTING EXHAUSTIVE COMBINATORIAL PARAMETER SWEEP")
    print(f"Target Gateway:    {args.gateway_url}")
    print(f"Target Database:   {args.db_path}")
    print(f"Total Scenarios:   {len(matrix)}")
    print("=" * 80)

    max_c = max(concurrencies) if concurrencies else 1
    limits = httpx.Limits(max_connections=max_c + 20, max_keepalive_connections=max(30, max_c))
    async with httpx.AsyncClient(
        limits=limits, verify=DEFAULT_SSL_VERIFY, trust_env=True
    ) as shared_client:
        for _idx, combination in enumerate(matrix):
            await run_combination(
                shared_client, args.gateway_url, args.api_key, db_file, *combination
            )
            await asyncio.sleep(DEFAULT_STEP_COOLDOWN_S)

    print("\n[✓] Exhaustive combinatorial sweep completed.")


if __name__ == "__main__":
    asyncio.run(main())
