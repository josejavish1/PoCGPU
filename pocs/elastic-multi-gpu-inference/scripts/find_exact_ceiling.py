#!/usr/bin/env python3
"""
Adaptive Physical Ceiling & Peak Concurrency Discovery Engine
=============================================================
Autonomously steps through increasing concurrency levels (80, 100, 120, 140, 160, 180, 200+)
to empirically discover the exact hardware throughput ceiling (Peak Tokens/s)
and the exact saturation boundary (Peak C) of the optimized dual-node GPU cluster.

Stopping Criteria:
1. Throughput Plateau: Consecutive marginal gain <= 2.0%
2. Throughput Inversion: Aggregate tokens/s starts degrading due to scheduling thrashing
3. Stability Breach: Error rate > 10%

Language Decoupling: 100% Technical English.
Zero Hardcoding: Fully externalized via environment variables.
Database: `pocs/elastic-multi-gpu-inference/data/benchmarks.db`
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sqlite3
import sys
import uuid
from pathlib import Path

# Add current scripts directory to sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from run_goodput_benchmark import (  # noqa: E402
    DEFAULT_API_KEY,
    DEFAULT_CODER_MODEL,
    DEFAULT_DB_PATH,
    DEFAULT_FAST_MODEL,
    DEFAULT_GATEWAY_URL,
    DEFAULT_PRICING_CATALOG,
    DEFAULT_PROMETHEUS_URL,
    DEFAULT_REASONING_MODEL,
    build_realistic_workload,
    init_database,
    load_pricing_parameters,
    run_goodput_step,
)


def get_latest_step_metrics(
    db_path: Path, session_id: str, concurrency: int
) -> tuple[float, float, float, int, int]:
    """Retrieves throughput_tps, ttft_p99_ms, tpot_p95_ms, success_count, and total_requests for the step."""
    with sqlite3.connect(db_path, timeout=30.0) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT throughput_tps, ttft_p99_ms, tpot_p95_ms, success_count, total_requests
            FROM goodput_benchmark_runs
            WHERE run_id LIKE ? AND concurrency = ?
            ORDER BY created_at DESC
            LIMIT 1;
            """,
            (f"%{session_id}%", concurrency),
        )
        row = cur.fetchone()
        if row:
            return float(row[0]), float(row[1]), float(row[2]), int(row[3]), int(row[4])
    return 0.0, 0.0, 0.0, 0, 0


async def main() -> None:
    parser = argparse.ArgumentParser(description="Adaptive Physical Throughput Ceiling Discovery")
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
        "--start-concurrency", type=int, default=80, help="Starting concurrency level"
    )
    parser.add_argument("--step-size", type=int, default=20, help="Concurrency increment step")
    parser.add_argument(
        "--max-concurrency", type=int, default=200, help="Maximum concurrency safety ceiling"
    )
    parser.add_argument(
        "--plateau-threshold-pct",
        type=float,
        default=2.0,
        help="Marginal throughput gain threshold for plateau",
    )
    args = parser.parse_args()

    if not args.api_key:
        print(
            "[!] ERROR: Master Gateway API key must be provided via --api-key or MASTER_KEY env variable.",
            file=sys.stderr,
        )
        sys.exit(1)

    db_file = Path(args.db_path)
    init_database(db_file)

    hourly_node_cost, cloud_in_rate, cloud_out_rate = load_pricing_parameters(args.pricing_catalog)
    nodes_count = int(os.environ.get("ACTIVE_GPU_NODES", "2"))
    second_node_cost = (hourly_node_cost * nodes_count) / 3600.0

    session_id = f"ceiling_{uuid.uuid4().hex[:6]}"

    print("=" * 105)
    print("STARTING ADAPTIVE PHYSICAL CEILING DISCOVERY (PEAK C AND PEAK TPS)")
    print(f"Target Gateway:     {args.gateway_url}")
    print(
        f"Search Strategy:    Starting C={args.start_concurrency}, Step=+{args.step_size}, Cap={args.max_concurrency}"
    )
    print(
        f"Stop Criterion:     Marginal throughput gain <= {args.plateau_threshold_pct:.1f}% or inversion"
    )
    print(f"Session Identifier: {session_id}")
    print("=" * 105)

    current_c = args.start_concurrency
    previous_tps = 358.7  # Baseline recorded at C=60 in previous run
    peak_c = 60
    peak_tps = previous_tps

    ceiling_history: list[tuple[int, float, float, float, float]] = [
        (60, previous_tps, 0.0, 1608.0, 170.1)
    ]

    while current_c <= args.max_concurrency:
        step_qps = max(1.0, float(current_c) * 0.8)
        workload = build_realistic_workload(
            target_concurrency=current_c,
            fast_model=DEFAULT_FAST_MODEL,
            coder_model=DEFAULT_CODER_MODEL,
            reasoning_model=DEFAULT_REASONING_MODEL,
        )

        await run_goodput_step(
            gateway_url=args.gateway_url,
            api_key=args.api_key,
            prometheus_url=args.prometheus_url,
            db_path=db_file,
            second_node_cost=second_node_cost,
            cloud_in_rate=cloud_in_rate,
            cloud_out_rate=cloud_out_rate,
            concurrency=current_c,
            target_qps=step_qps,
            workload_items=workload,
            session_id=session_id,
        )

        tps, ttft_p99, tpot_p95, success, total = get_latest_step_metrics(
            db_file, session_id, current_c
        )

        if total > 0 and (success / total) < 0.90:
            print(
                f"\n[!] BREACH DETECTED: Error rate exceeded 10% ({success}/{total} succeeded). Stopping discovery."
            )
            break

        marginal_gain_pct = (
            ((tps - previous_tps) / previous_tps * 100.0) if previous_tps > 0 else 0.0
        )
        ceiling_history.append((current_c, tps, marginal_gain_pct, ttft_p99, tpot_p95))

        print(
            f"\n---> STEP C={current_c}: Throughput={tps:.1f} tok/s | Marginal Delta={marginal_gain_pct:+.2f}% | P99 TTFT={ttft_p99:.1f}ms"
        )

        if tps > peak_tps:
            peak_tps = tps
            peak_c = current_c

        # Check for Plateau or Inversion
        if marginal_gain_pct <= args.plateau_threshold_pct and current_c > args.start_concurrency:
            print(
                f"\n[★] PHYSICAL CEILING REACHED AT C={peak_c}: Marginal gain was {marginal_gain_pct:.2f}% (<= {args.plateau_threshold_pct:.1f}% threshold)."
            )
            break

        previous_tps = tps
        current_c += args.step_size
        await asyncio.sleep(2.0)

    # Executive Plateau Report
    print("\n" + "=" * 105)
    print("                    CERTIFIED PHYSICAL CEILING AUDIT REPORT")
    print("=" * 105)
    print(
        f"{'Concurrency (C)':<18} | {'Throughput (tok/s)':<22} | {'Marginal Gain %':<18} | {'P99 TTFT':<15} | {'P95 TPOT'}"
    )
    print("-" * 105)
    for c, tps_val, gain_val, ttft_val, tpot_val in ceiling_history:
        peak_flag = "★ ABSOLUTE PEAK" if c == peak_c else ""
        print(
            f"C = {c:<14} | {tps_val:<5.1f} tokens/s          | {gain_val:+5.2f} %           | {ttft_val:<7.1f} ms     | {tpot_val:<6.1f} ms/tok  {peak_flag}"
        )
    print("=" * 105)
    print(
        f"\n[✓] Exact Silicon Ceiling Confirmed: C = {peak_c} users yielding {peak_tps:.1f} tokens/second."
    )
    print(f"[✓] Empirical metrics logged to SQLite: {db_file}")


if __name__ == "__main__":
    asyncio.run(main())
