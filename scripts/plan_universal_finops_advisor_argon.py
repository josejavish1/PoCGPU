#!/usr/bin/env python3
"""
Argon-4 Consultation: Universal Hybrid LLM FinOps Advisor Architecture (RFC 063)
================================================================================
Prompts gemini-4-argon to design an uncompromised, zero-hardcoding, institutional-grade
architectural blueprint for a universal LLM infrastructure capacity planner, questionnaire-driven
decision matrix, and actuarial chargeback platform supporting both On-Premise and Cloud regimes.
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
We are evolving the PoCGPU FinOps Platform from a simplistic local demo calculator into a world-class,
institutional-grade decision support platform ("Universal Hybrid FinOps Advisor") designed to impress
Principal/Staff infrastructure engineers at Tier-1 AI labs (OpenAI, Anthropic, DeepMind) and enterprise CIOs/CFOs.

The user mandates:
1. BEFORE ANY PROGRAMMING BEGINS, perform deep conceptual architecture planning to ensure 100% quality and zero bugs/anti-patterns.
2. ZERO HARDCODING: Must scale dynamically to ANY enterprise (mid-market to global Fortune 10), ANY industry vertical
   (banking, defense, retail, healthcare, telecom), ANY currency, and ANY human language. No static dictionaries in Python.
3. HYBRID EQUALITY (CLOUD & ON-PREMISE): The platform MUST NOT be Cloud-only. On-Premise (Private Datacenter / Bare-Metal)
   is the PRIMARY area of commercial interest, alongside Public Cloud (GCP/AWS/Azure/RunPod) and Hybrid Cloud-Bursting.
4. QUESTIONNAIRE-DRIVEN ADVISORY PARADIGM: Non-technical executives cannot configure raw GPU hardware parameters.
   The entry point must be a Guided Assessment Wizard asking strategic, non-functional questions (data sovereignty,
   duty cycle, datacenter readiness, CapEx vs OpEx preference, operational SRE maturity) that algorithmically outputs
   an optimal architectural archetype with side-by-side financial comparison.
5. ACTUARIAL RIGOR: Integrate Open FAIR quantitative risk modeling (Hardware RMA / Silicon AFR on-premise vs Spot Preemption in Cloud).
6. 100% TECHNICAL ENGLISH: All engineering, data schemas, class definitions, and prompts must be in pure Technical English.

YOUR MISSION:
Synthesize an authoritative, exhaustive Architectural Blueprint (RFC 063: Universal Hybrid LLM FinOps Advisor) in Markdown covering:

SECTION 1: DOMAIN ARCHITECTURE & PORTS (HEXAGONAL ARCHITECTURE)
- Define the pure domain layer boundaries: zero filesystem, network, or UI dependencies.
- Define domain interfaces (Ports):
  - `HardwareRegistryPort` & `PricingProviderPort` (JIT dynamic resolution with TTL caching).
  - `AssessmentQuestionnairePort` & `ArchetypeRecommendationPort`.
  - `RooflineSimulationPort` & `ActuarialRiskPort`.
  - `AuditLedgerPort` (Immutable cryptographic recording).

SECTION 2: QUESTIONNAIRE DECISION MATRIX & ARCHETYPE TAXONOMY
- Define the exact schema and scoring weights for the 5 strategic assessment questions.
- Formalize the mathematical decision function mapping responses to:
  * Archetype 1: Sovereign On-Premise Bare-Metal Cluster.
  * Archetype 2: Elastic Public Cloud Dedicated Cluster.
  * Archetype 3: Tiered Hybrid Sovereign Base with Cloud-Bursting.

SECTION 3: ON-PREMISE VS CLOUD FINANCIAL MODELING INVARIANTS
- Formulate the exact CapEx depreciation equations (36 to 60 months amortization + residual value).
- Model On-Premise Datacenter OpEx:
  * Server chassis thermal dissipation (TDP kW) * PUE (1.1 to 1.5) * Electricity cost (kWh).
  * High-density colocation rack rental (€/month per 20kW/40kW).
  * 24/7 OEM Mission-Critical Care Pack warranties.
- Contrast with Cloud OpEx (Hourly Spot vs On-Demand, Zonal SSDs, Egress).
- Formulate the Open FAIR Actuarial Risk:
  * On-Premise Annualized Failure Rate (AFR) & RMA MTTR replacement penalties.
  * Cloud Spot Loss Event Frequency (LEF) & cold rebuild preemption penalties.

SECTION 4: PRE-FLIGHT CFO CONSTITUTIONAL AUDIT GATE (`CfoActuarialGate`)
- Define inviolable physical, electrical, and economic boundary invariants:
  * Rack power density ceilings (e.g. rejecting 10 kW server on 5 kW uncooled rack).
  * PUE physical floors (rejecting PUE < 1.08).
  * Memory bandwidth saturation ceiling (rejecting decode > 85% bus capacity).
  * VRAM allocation hard ceiling (mandatory 10% runtime buffer).
  * Economic floor (rejecting negative margins or 0-cost infrastructure).

SECTION 5: VERIFIABLE IMPLEMENTATION ROADMAP & TEST ORACLES
- Detail the exact step-by-step implementation order.
- Define automated AST domain purity verification rules and Playwright E2E verification criteria.
- Deliver an unambiguous verdict on the architectural soundness.
"""

def main() -> None:
    client = create_genai_client()
    model_name = get_model(ModelTier.REASONING)
    print(f"[+] Consulting Cognitive Arbiter: {model_name}...")

    response = client.models.generate_content(
        model=model_name,
        contents=PROMPT_TEXT,
    )

    out_file = REPO_ROOT / "docs/RFC_063_UNIVERSAL_HYBRID_FINOPS_ADVISOR_ARGON.md"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(response.text, encoding="utf-8")

    print("\n" + "=" * 80)
    print(f" RFC 063 MASTER BLUEPRINT GENERATED SUCCESSFULLY ({len(response.text)} chars)")
    print(f" Target File: {out_file}")
    print("=" * 80)


if __name__ == "__main__":
    main()
