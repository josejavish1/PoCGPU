#!/usr/bin/env python3
"""
Argon-4 Consultation: Phase 2 Pure Domain Services Specification (RFC 064)
==========================================================================
Prompts gemini-4-argon to design an uncompromised, bug-free, zero-hardcoding
mathematical specification and reference implementation plan for Phase 2:
Pure Domain Services (Questionnaire Decision Matrix, Roofline Physics Engine,
Open FAIR Actuarial Risk Engine, CFO Constitutional Audit Gate, and Hybrid TCO Aggregator).
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add assessment_engine source to path for genai_client infrastructure
REPO_ROOT = Path(__file__).resolve().parents[1]
ASSESSMENT_ENGINE_SRC = Path("/home/jsanchhi/assessment_engine/src")
if str(ASSESSMENT_ENGINE_SRC) not in sys.path:
    sys.path.insert(0, str(ASSESSMENT_ENGINE_SRC))

from assessment_engine.infrastructure.genai_client import (
    ModelTier,
    create_genai_client,
    get_model,
)

PROMPT_TEXT = """
Role: Chief Systems Architect & Principal Actuary (Tier-1 AI Infrastructure / Google Core / OpenAI).

CONTEXT & USER DIRECTIVES:
We have certified Phase 1 of RFC 063 with 100% pure hexagonal domain models and ports under tests/architecture/test_domain_purity.py (0 violations).
Now, BEFORE WRITING A SINGLE LINE OF CODE IN PHASE 2 (Domain Services), we must establish an uncompromised,
mathematically rigorous, bug-free architectural design for all domain calculation engines.

The user mandates:
1. BEFORE ANY PROGRAMMING: Deep conceptual architecture planning to ensure 100% quality and zero bugs/anti-patterns.
2. ZERO HARDCODING: Must scale dynamically to ANY enterprise (mid-market to global Fortune 10), ANY industry vertical
   (banking, defense, retail, healthcare, telecom), ANY currency, and ANY human language. No static dictionaries.
3. HYBRID EQUALITY (CLOUD & ON-PREMISE): The platform MUST NOT be Cloud-only. On-Premise (Private Datacenter / Bare-Metal)
   is the PRIMARY area of commercial interest, alongside Public Cloud (GCP/AWS/Azure/RunPod) and Hybrid Cloud-Bursting.
4. QUESTIONNAIRE-DRIVEN ADVISORY PARADIGM: Non-technical executives cannot configure raw GPU hardware parameters.
   The entry point must be a Guided Assessment Wizard asking strategic, non-functional questions (data sovereignty,
   duty cycle, datacenter readiness, CapEx vs OpEx preference, operational SRE maturity) that algorithmically outputs
   an optimal architectural archetype with side-by-side financial comparison.
5. ACTUARIAL RIGOR: Integrate Open FAIR quantitative risk modeling (Hardware RMA / Silicon AFR on-premise vs Spot Preemption in Cloud).
6. 100% TECHNICAL ENGLISH: All engineering, data schemas, class definitions, and prompts must be in pure Technical English.

YOUR MISSION:
Synthesize an authoritative, exhaustive Technical Specification (RFC 064: Phase 2 Pure Domain Services) in Markdown covering:

1. `QuestionnaireDecisionEngine` (`src/domain/services/questionnaire_engine.py`):
   - Mathematical algorithm evaluating dynamic questionnaire schema against client responses.
   - Weighted affinity normalization:
     S_onprem = (sum w_i * s_i_onprem) / sum w_i
     S_cloud = (sum w_i * s_i_cloud) / sum w_i
   - Hard Veto Logic: Immediate override if `is_hard_on_prem_veto` or `is_hard_cloud_veto` is triggered.
   - Peak-to-Average Ratio (PAR = peak_burst_rps / baseline_rps) divergence logic:
     When PAR >= 3.0 and both regimes are viable, recommend Archetype 3 (Tiered Hybrid Cloud-Bursting)
     and calculate the exact load split percentages.

2. `RooflinePhysicsEngine` (`src/domain/services/roofline_engine.py`):
   - Universal memory footprint calculation:
     * Weights memory based on parameter count and quantization bits.
     * KV cache calculation supporting MHA, GQA (Grouped-Query Attention), and MLA (Multi-head Latent Attention).
     * Activation buffer estimation scaled to peak concurrent sequences.
   - Distributed topology derivation:
     * Optimal Tensor Parallelism (TP in {1, 2, 4, 8}) and Pipeline Parallelism (PP).
     * Interconnect penalty factors (NVLink vs PCIe Gen4/Gen5 vs InfiniBand).
   - Roofline Latency bounds:
     * Prefill TTFT (Time to First Token) based on arithmetic intensity and Model FLOPs Utilization (MFU).
     * Decode TPOT (Time Per Output Token) based on Memory Bandwidth Utilization (MBU).
     * Aggregate cluster throughput (tokens/second).

3. `OpenFairActuarialEngine` (`src/domain/services/actuarial_engine.py`):
   - On-Premise Silicon Failure Modeling:
     * Annualized Failure Rate (AFR) & Mean Time Between Failures (MTBF).
     * Erlang-B / Poisson spare depletion probability.
     * Single Loss Expectancy (SLE_onprem) & Annualized Loss Expectancy (ALE_onprem).
   - Cloud Spot Preemption Modeling:
     * Daily eviction probability & Loss Event Frequency (LEF_spot).
     * Cold Rebuild penalty (image pull, weight loading, SLA credit) -> SLE_spot & ALE_spot.
   - Strict `decimal.Decimal` with `ROUND_HALF_EVEN`.

4. `CfoActuarialGate` (`src/domain/services/cfo_gate.py`):
   - Inviolable pre-flight boundary validation:
     * GATE-PHY-001: Rack power density ceiling.
     * GATE-PHY-002: Cooling topology limits (>35 kW requires DLC/Immersion).
     * GATE-PHY-003: Carnot PUE thermodynamic floor (PUE >= 1.08).
     * GATE-SIL-001: Mandatory 10% VRAM runtime buffer (utilization <= 0.90).
     * GATE-SIL-002: Memory bandwidth saturation ceiling (bus utilization <= 0.85).
     * GATE-FIN-001: Strict positive economic floor (> 0).
     * GATE-FIN-002: Amortization horizon bounds (36 to 60 months, salvage <= 0.35).

5. `HybridTcoAggregator` (`src/domain/services/tco_aggregator.py`):
   - CapEx linear depreciation over N months with residual salvage value.
   - Facility OpEx (Chassis TDP kW * PUE * Electricity kWh rate + Colocation rack fee + OEM Care Pack).
   - Public Cloud OpEx (Hourly instance rates, Zonal storage, Egress).
   - Side-by-side 36-month and 60-month TCO synthesis with Risk-Adjusted Total Cost (TCO* = TCO + ALE / 12).

6. Automated Unit & Property-Based Test Suite Plan (`tests/domain/`):
   - Property tests asserting idempotency, boundary rejection, and veto determinism.

Deliver a definitive architectural approval verdict.
"""

def main() -> None:
    client = create_genai_client()
    model_name = get_model(ModelTier.REASONING)
    print(f"[+] Consulting Cognitive Arbiter: {model_name}...")

    response = client.models.generate_content(
        model=model_name,
        contents=PROMPT_TEXT,
    )

    out_file = REPO_ROOT / "docs/RFC_064_PHASE2_DOMAIN_SERVICES_SPECIFICATION_ARGON.md"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(response.text, encoding="utf-8")

    print("\n" + "=" * 80)
    print(f" RFC 064 MASTER SPECIFICATION GENERATED SUCCESSFULLY ({len(response.text)} chars)")
    print(f" Target File: {out_file}")
    print("=" * 80)


if __name__ == "__main__":
    main()
