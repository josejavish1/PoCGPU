#!/usr/bin/env python3
"""
Adversarial Quality Gate: Gemini-4-Argon Forensic Audit of Phase 1 Implementation
=================================================================================
Inspects all files in src/domain/, config/, and tests/architecture/ to find bugs,
anti-patterns, lingering hardcoded assumptions, and language purity violations.
Produces docs/AUDIT_REPORT_PHASE1_ARGON.md with a definitive architectural verdict.
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

FILES_TO_AUDIT = [
    REPO_ROOT / "src/domain/exceptions.py",
    REPO_ROOT / "src/domain/models/financial.py",
    REPO_ROOT / "src/domain/models/hardware.py",
    REPO_ROOT / "src/domain/models/workload.py",
    REPO_ROOT / "src/domain/models/assessment.py",
    REPO_ROOT / "src/domain/models/__init__.py",
    REPO_ROOT / "src/domain/ports/hardware_registry.py",
    REPO_ROOT / "src/domain/ports/pricing_provider.py",
    REPO_ROOT / "src/domain/ports/assessment_questionnaire.py",
    REPO_ROOT / "src/domain/ports/roofline_simulation.py",
    REPO_ROOT / "src/domain/ports/actuarial_risk.py",
    REPO_ROOT / "src/domain/ports/constitutional_gate.py",
    REPO_ROOT / "src/domain/ports/hybrid_tco.py",
    REPO_ROOT / "src/domain/ports/audit_ledger.py",
    REPO_ROOT / "src/domain/ports/__init__.py",
    REPO_ROOT / "config/locales.json",
    REPO_ROOT / "config/taxonomies/verticals.json",
    REPO_ROOT / "tests/architecture/test_domain_purity.py",
    REPO_ROOT / "tests/architecture/test_zero_spanish_literals.py",
]


def assemble_codebase_payload() -> str:
    payload_parts = []
    for f in FILES_TO_AUDIT:
        if f.is_file():
            rel_path = f.relative_to(REPO_ROOT)
            content = f.read_text(encoding="utf-8")
            payload_parts.append(f"### FILE: `{rel_path}`\n```\n{content}\n```\n")
        else:
            payload_parts.append(f"### FILE: `{f}` (MISSING / NOT FOUND)\n")
    return "\n".join(payload_parts)


AUDIT_PROMPT_TEMPLATE = """
Role: Principal Adversarial Auditor & Chief Quality Officer (OpenAI / Anthropic / Google Core Infrastructure).

USER INSTRUCTIONS & CONTEXT:
The user has issued an explicit command:
"Before continuing, I want you to tell gemini-4-argon to do a complete review of what you have just programmed and look for bugs, problems, or anti-patterns. I want nothing hardcoded, remember the goal is that it serves any company in the world from mid-market to global top tier-1, of any vertical, in any language, and the code must be 100% in English—not a single word of Spanish. Spanish is solely the conversational language between the user and the agent, and one of the output languages of the deliverables."

REVIEW TARGET:
We have implemented Phase 1 (Domain Models, Domain Ports, Declarative Schemas, and AST Fitness Gates) of RFC 063/RFC 065.

HERE IS THE COMPLETE CODEBASE DELIVERABLE FOR PHASE 1:
{codebase_payload}

YOUR ADVERSARIAL AUDIT MANDATE:
Conduct an exhaustive forensic review across the following 5 dimensions:

1. BUGS, RUNTIME HAZARDS & NUMERICAL DEFECTS:
   - Are there any type inconsistencies, unhandled None values, missing edge cases in `MonetaryAmount`, `compute_kv_cache_bytes_per_token`, or dataclass initializers?
   - Is Banker's Rounding (`ROUND_HALF_EVEN`) applied strictly without floating-point precision loss?
   - Are dataclasses properly frozen and immutable?

2. ANTI-PATTERNS & CODE SMELLS:
   - Does any domain entity leak infrastructure concerns, I/O, or network assumptions?
   - Are ports properly abstract with clear signatures and return types?
   - Are exceptions structured, typed, and informative?

3. ZERO-HARDCODING & UNIVERSAL SCALABILITY:
   - Is there ANY hardcoded business constant, tax rate, hardware SKU, or pricing literal lurking in `src/domain/`?
   - Can this schema seamlessly support a 1-node mid-market retail cluster (€5,000 CapEx) up to a 1024-node Tier-1 sovereign defense datacenter ($250,000,000 CapEx) across any currency (USD, EUR, JPY, GBP, CHF) without code modifications?
   - Are the declarative schemas (`config/locales.json`, `config/taxonomies/verticals.json`) comprehensive, extensible, and free of architectural deadlocks?

4. LINGUISTIC PURITY & DECOUPLING:
   - Verify that 100% of all Python source code in `src/` and `tests/` is written in pure Technical English.
   - Verify that Spanish only exists within localized data resource payloads (`config/locales.json`).
   - Audit the effectiveness of `tests/architecture/test_zero_spanish_literals.py`.

5. ARCHITECTURAL FITNESS & READINESS FOR PHASE 2:
   - Are the domain models and ports sufficient and completely prepared to receive the implementation of the 5 Phase 2 calculation services (`QuestionnaireDecisionEngine`, `RooflinePhysicsEngine`, `OpenFairActuarialEngine`, `CfoActuarialGate`, `HybridTcoAggregator`)?

DELIVERABLE FORMAT:
Provide a structured Forensic Audit Report in Markdown containing:
- Executive Summary & Numerical Score (0 to 100).
- Detailed Findings per Dimension (Pass/Warn/Fail with line-level references).
- Required or Recommended Corrections (if any).
- Formal Binding Verdict: `APPROVED (READY FOR PHASE 2)` or `REJECTED (REMEDIATION REQUIRED)`.
"""


def main() -> None:
    client = create_genai_client()
    model_name = get_model(ModelTier.REASONING)
    print(f"[+] Consulting Cognitive Arbiter: {model_name}...")
    print(f"[+] Assembling codebase payload from {len(FILES_TO_AUDIT)} files...")

    codebase_payload = assemble_codebase_payload()
    prompt = AUDIT_PROMPT_TEMPLATE.format(codebase_payload=codebase_payload)

    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
    )

    out_file = REPO_ROOT / "docs/AUDIT_REPORT_PHASE1_ARGON.md"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(response.text, encoding="utf-8")

    print("\n" + "=" * 80)
    print(f" GEMINI-4-ARGON AUDIT REPORT COMPLETED ({len(response.text)} chars)")
    print(f" Target File: {out_file}")
    print("=" * 80)


if __name__ == "__main__":
    main()
