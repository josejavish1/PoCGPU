#!/usr/bin/env python3
"""
Adversarial Quality Gate: Gemini-4-Argon Forensic Audit of Phase 2 Implementation
=================================================================================
Inspects all Phase 1 and Phase 2 files in src/domain/, config/, and tests/ to evaluate
domain purity, zero-hardcoding compliance, numerical accuracy, and language decoupling.
Produces docs/AUDIT_REPORT_PHASE2_ARGON.md with a definitive architectural verdict.
"""

from __future__ import annotations

import sys
from pathlib import Path

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
    REPO_ROOT / "src/domain/models/validation.py",
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
    REPO_ROOT / "src/domain/services/questionnaire_engine.py",
    REPO_ROOT / "src/domain/services/roofline_engine.py",
    REPO_ROOT / "src/domain/services/actuarial_engine.py",
    REPO_ROOT / "src/domain/services/cfo_gate.py",
    REPO_ROOT / "src/domain/services/tco_aggregator.py",
    REPO_ROOT / "src/domain/services/__init__.py",
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
            payload_parts.append(f"### FILE: `{rel_path}`\n```python\n{content}\n```\n")
        else:
            payload_parts.append(f"### FILE: `{f}` (MISSING / NOT FOUND)\n")
    return "\n".join(payload_parts)


AUDIT_PROMPT_TEMPLATE = """
Role: Principal Adversarial Auditor & Chief Quality Officer (OpenAI / Anthropic / Google Core Infrastructure).

USER INSTRUCTIONS & CONTEXT:
The user has issued an explicit command:
"Before continuing, I want you to tell gemini-4-argon to do a complete review of what you have just programmed and look for bugs, problems, or anti-patterns. I want nothing hardcoded, remember the goal is that it serves any company in the world from mid-market to global top tier-1, of any vertical, in any language, and the code must be 100% in English—not a single word of Spanish. Spanish is solely the conversational language between the user and the agent, and one of the output languages of the deliverables."

REVIEW TARGET:
Phase 2 Implementation (Pure Domain Services, Models, Ports, Declarative Schemas, and 59 Automated Tests passing 100%).

HERE IS THE COMPLETE CODEBASE DELIVERABLE (PHASE 1 + PHASE 2):
{codebase_payload}

YOUR ADVERSARIAL AUDIT MANDATE:
Conduct an exhaustive forensic review across the following 5 dimensions:

1. BUGS, RUNTIME HAZARDS & NUMERICAL DEFECTS:
   - Audit the 5 services: QuestionnaireDecisionEngine, RooflinePhysicsEngine, OpenFairActuarialEngine, CfoActuarialGate, HybridTcoAggregator.
   - Verify Banker's Rounding (ROUND_HALF_EVEN), Decimal precision preservation, and absence of IEEE-754 precision loss.
   - Check Roofline mathematics: GQA/MHA K+V tensor factor (2) vs MLA shared latent vector factor (1).

2. ANTI-PATTERNS & CODE SMELLS:
   - Verify Hexagonal Architecture: zero infrastructure, network, or OS leaks in `src/domain/`.
   - Verify typed exception handling via `ConstitutionalGateViolationError` with structured `i18n_params`.

3. ZERO-HARDCODING & UNIVERSAL SCALABILITY:
   - Verify that all business policies, thresholds, and PUE limits are injected from `ConstitutionalGatePolicy`, `AssessmentDecisionPolicy`, and `verticals.json`.
   - Verify scalability from €5k 1-node mid-market edge clusters to $250M 1024-node sovereign superclusters.

4. LINGUISTIC PURITY & DECOUPLING:
   - Verify that 100% of all Python source code in `src/` and `tests/` is written in pure Technical English.
   - Verify that Spanish only exists within localized data resource payloads (`config/locales.json`).

5. VERDICT:
   - Formal Score (0 to 100).
   - Binding Verdict: `APPROVED (PRODUCTION READY)` or `REJECTED (REMEDIATION REQUIRED)`.
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

    out_file = REPO_ROOT / "docs/AUDIT_REPORT_PHASE2_ARGON.md"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(response.text, encoding="utf-8")

    print("\n" + "=" * 80)
    print(f" GEMINI-4-ARGON PHASE 2 AUDIT REPORT COMPLETED ({len(response.text)} chars)")
    print(f" Target File: {out_file}")
    print("=" * 80)


if __name__ == "__main__":
    main()
