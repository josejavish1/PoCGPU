#!/usr/bin/env python3
"""
Empirical Master Report Generator via gemini-4-argon
====================================================
Extracts all historical benchmarking telemetry and physical milestones
from `pocs/elastic-multi-gpu-inference/data/benchmarks.db` and dispatches
a comprehensive prompt to `gemini-4-argon` to synthesize an authoritative,
exhaustive, and enduring engineering milestone report in Technical English.

Target: `docs/engineering-constitution/EMPIRICAL_OPTIMIZATION_MASTER_REPORT.md`
"""

from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from run_autonomous_mission import (  # type: ignore # noqa: E402
    ARCHITECT_FALLBACK,
    ARCHITECT_MODEL,
    call_model_with_fallback,
    get_genai_client,
)

DB_PATH = REPO_ROOT / "pocs" / "elastic-multi-gpu-inference" / "data" / "benchmarks.db"
OUTPUT_REPORT_PATH = REPO_ROOT / "docs" / "engineering-constitution" / "EMPIRICAL_OPTIMIZATION_MASTER_REPORT.md"


def extract_database_summary() -> str:
    """Queries benchmarks.db to generate structured empirical tables for the prompt."""
    if not DB_PATH.exists():
        return "Database not found."

    summary_lines = []
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()

        # 1. Overall stats
        cur.execute("SELECT count(*) FROM benchmark_runs")
        total_runs = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM goodput_benchmark_runs")
        total_goodput_runs = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM goodput_request_records")
        total_goodput_reqs = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM bayesian_optimization_trials")
        total_bayesian_trials = cur.fetchone()[0]

        summary_lines.append(f"Total Classical Benchmark Runs: {total_runs}")
        summary_lines.append(f"Total Goodput Benchmark Runs: {total_goodput_runs}")
        summary_lines.append(f"Total Detailed Request Records: {total_goodput_reqs}")
        summary_lines.append(f"Total Bayesian Optimization Trials: {total_bayesian_trials}\n")

        # 2. Phase 5 Multi-Step Run summary
        cur.execute("""
            SELECT concurrency, throughput_tps, ttft_p50_ms, ttft_p99_ms, tpot_mean_ms, tpot_p95_ms, quality_pass_rate_pct
            FROM goodput_benchmark_runs
            WHERE run_id LIKE '%multistep_gemini_ux_bench%'
            ORDER BY concurrency;
        """)
        summary_lines.append("=== PHASE 5: MULTI-STEP SCHEDULING & NATIVE FP8 WEIGHTS RESULTS ===")
        for row in cur.fetchall():
            summary_lines.append(f"C={row[0]}: Throughput={row[1]:.1f} tok/s, TTFT_P50={row[2]:.1f}ms, TTFT_P99={row[3]:.1f}ms, TPOT_Mean={row[4]:.1f}ms, TPOT_P95={row[5]:.1f}ms, Quality={row[6]:.1f}%")

        # 3. Native FP8 weights run summary
        cur.execute("""
            SELECT concurrency, throughput_tps, ttft_p50_ms, ttft_p99_ms, tpot_mean_ms, tpot_p95_ms, quality_pass_rate_pct
            FROM goodput_benchmark_runs
            WHERE run_id LIKE '%fp8_native_weights_bench%'
            ORDER BY concurrency;
        """)
        summary_lines.append("\n=== PHASE 5: NATIVE FP8 W8A8 WEIGHTS RUN ===")
        for row in cur.fetchall():
            summary_lines.append(f"C={row[0]}: Throughput={row[1]:.1f} tok/s, TTFT_P50={row[2]:.1f}ms, TTFT_P99={row[3]:.1f}ms, TPOT_Mean={row[4]:.1f}ms, TPOT_P95={row[5]:.1f}ms, Quality={row[6]:.1f}%")

        # 4. Ceiling discovery summary
        cur.execute("""
            SELECT concurrency, throughput_tps, ttft_p99_ms, tpot_p95_ms, peak_kv_cache_pct
            FROM goodput_benchmark_runs
            WHERE run_id LIKE '%ceiling%'
            ORDER BY concurrency;
        """)
        summary_lines.append("\n=== ASYMPTOTIC CEILING RUNS ===")
        for row in cur.fetchall():
            summary_lines.append(f"C={row[0]}: Throughput={row[1]:.1f} tok/s, P99_TTFT={row[2]:.1f}ms, P95_TPOT={row[3]:.1f}ms, KVCache={row[4]:.1f}%")

    return "\n".join(summary_lines)


def build_generation_prompt(db_summary: str) -> str:
    return f"""You are the Principal AI Systems & Infrastructure Architect at a Tier-1 AI Laboratory (DeepMind / OpenAI / Anthropic level).
Your task is to write the definitive, authoritative, academic-grade Engineering Retrospective and Mastery Report documenting the complete journey of optimizing our sovereign enterprise multi-GPU inference platform in Zurich (GKE cluster `poc-gpu-cluster-ch` on 2x `g2-standard-24` Spot nodes with 4x NVIDIA L4 GPUs = 96 GB total VRAM).

The report must be written in 100% Technical English and structured as an enduring architectural document so that any staff engineer or executive returning to this repository in 6 months or 2 years can understand every physical constraint, empirical discovery, mathematical equation, and architectural victory achieved.

### EMPIRICAL BENCHMARK DATA RECORDED IN SQLITE:
{db_summary}

### REQUIRED REPORT STRUCTURE:
1. **Executive Summary & High-Level Financial Impact**
   - The primary milestone: from Vanilla FP16 (Phase 1) to Fully Optimized FP8 W8A8 + FlashInfer + Multi-Step Scheduling (Phase 5).
   - Net capacity gain: $\times 4.5$ user density.
   - Net TCO reduction: 80.2% recurrent infrastructure cost savings for a 20,000-employee enterprise.
   - The 5-Phase Evolution Table comparing Phase 1 (Vanilla FP16) to Phase 5 (Golden State).

2. **The Hardware Baseline & Physics of the Silicon**
   - Physical constraints of the 4x NVIDIA L4 GPUs (Ada Lovelace, 24GB GDDR6 each, 300 GB/s bandwidth per card, PCIe 4.0 interconnect).
   - Why raw bandwidth was the true bottleneck, not memory capacity.
   - The Goodput Definition (P99 TTFT <= 1.0s, P95 TPOT <= 60ms) vs the Frontier Cloud User Experience SLA (Gemini/ChatGPT Standard: TTFT <= 2.5s, TPOT <= 150ms).

3. **Chronological Deep-Dive Across the 5 Architectural Phases**
   - **Phase 1: Factory Baseline (Vanilla FP16):** 13.5 GB weights, 6,050 KV blocks, 20 users capacity knee, queuing collapse at >30 users.
   - **Phase 2: Engine Tuning (FP8 KV-Cache + Prefix Caching + 32-token Blocks):** Memory blocks doubled to 12,130, VRAM headroom doubled, zero OOM risk.
   - **Phase 3: SLA Calibration vs Frontier Cloud UX:** Real-world Gemini 2.5 Flash latency audit (697 ms end-to-end); how relaxing to 2.5s UX doubles effective node density to 45 users.
   - **Phase 4: Low-Level Assembly Kernels (FlashInfer):** Replacing xFormers with FlashInfer native PTX kernels (+29.2% throughput boost at C=30, P99 TTFT dropping to 943 ms into strict SLA).
   - **Phase 5: Native FP8 W8A8 Model Weights & Multi-Step Scheduling:**
     * Downloading `RedHatAI/Mistral-7B-Instruct-v0.3-FP8` (7.1 GB).
     * Slashing weight memory by 50% and freeing PCIe bandwidth.
     * Multi-Step Scheduling (`--num-scheduler-steps=8`) reducing CPU-GPU synchronization overhead.
     * Record-breaking token fluidity of 25.2 ms/token (38-40 words/sec).

4. **Hard-Learned Invariants & vLLM Architectural Discoveries**
   - Invariant A: Incompatibility of `--enable-lora` with `--enable-chunked-prefill` in vLLM v0.6.3 (`ValueError`).
   - Invariant B: Why unquantized weights crash with `--quantization=fp8` (`TypeError: MistralConfig not iterable`) and why pre-quantized calibrated checkpoints (`RedHatAI/...`) are mandatory.
   - Invariant C: Speculative N-gram decoding limitations on PCIe distributed TP=2 setups (CUDA graph capture event loop blocking).
   - Invariant D: Asymptotic silicon saturation ceiling measured at C=120 with 372-380 tokens/sec.
   - Invariant E: Separation of concerns between Memory Footprint (VRAM) and Throughput Bandwidth (tokens/sec).

5. **Transfer to the Canonical Calculators (`calculators/sizing` and `calculators/chargeback`)**
   - Mathematical formula connections: Roofline Model calibration factor (eta_runtime), GQA KV-cache calculations, and asymmetric 3:1 decode-to-prefill bandwidth chargeback.
   - Concrete sizing case study: 20,000 employees enterprise requiring 3-4 nodes ($1,150/mo) instead of 15 nodes ($5,800/mo).

6. **Definitive Production Manifests & Operational Runbook**
   - Exact validated CLI flags and environment variables for the Golden Profile.
   - Safe cluster hibernation and reactivation procedures (`0.00/h` cost).

Make the document rigorous, deeply analytical, complete with mathematical formulas, Markdown tables, and concrete citations of MLPerf and OSDI/MLSys literature.
"""


def main() -> None:
    print("[*] Generating Empirical Master Report via gemini-4-argon...")
    print(f"    - Database: {DB_PATH}")
    print(f"    - Target:   {OUTPUT_REPORT_PATH}")

    db_summary = extract_database_summary()
    prompt = build_generation_prompt(db_summary)

    client = get_genai_client()
    print(f"[*] Dispatching prompt to {ARCHITECT_MODEL}...")
    report_content = call_model_with_fallback(
        client=client,
        primary_model=ARCHITECT_MODEL,
        fallback_model=ARCHITECT_FALLBACK,
        prompt=prompt,
        temperature=0.1,
    )

    OUTPUT_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_REPORT_PATH.write_text(report_content, encoding="utf-8")

    print(f"[✓] Empirical Master Report successfully generated ({len(report_content)} characters) at:")
    print(f"    {OUTPUT_REPORT_PATH}")


if __name__ == "__main__":
    main()
