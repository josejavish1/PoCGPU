#!/usr/bin/env python3
"""
Comprehensive Adversarial Quality Gate: Gemini-4-Argon Full System Audit
========================================================================
Inspects 100% of the codebase across domain, adapters, application orchestrator,
declarative catalogs, configuration schemas, and tests to identify bugs,
lingering hardcoded assumptions, architectural anti-patterns, and language leakage.
Produces docs/AUDIT_REPORT_PHASE3_ARGON.md with a binding quality score and verdict.
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
    REPO_ROOT / "src/domain/ports/model_registry.py",
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
    REPO_ROOT / "src/adapters/json_hardware_registry.py",
    REPO_ROOT / "src/adapters/json_pricing_provider.py",
    REPO_ROOT / "src/adapters/json_model_registry.py",
    REPO_ROOT / "src/adapters/json_questionnaire_loader.py",
    REPO_ROOT / "src/adapters/crypto_audit_ledger.py",
    REPO_ROOT / "src/adapters/__init__.py",
    REPO_ROOT / "src/application/finops_advisor_service.py",
    REPO_ROOT / "src/application/__init__.py",
    REPO_ROOT / "scripts/web_calculator.py",
    REPO_ROOT / "scripts/web_calculator.html",
    REPO_ROOT / "config/locales.json",
    REPO_ROOT / "config/taxonomies/verticals.json",
    REPO_ROOT / "config/catalogs/hardware_catalog.json",
    REPO_ROOT / "config/catalogs/pricing_catalog.json",
    REPO_ROOT / "config/catalogs/models_catalog.json",
    REPO_ROOT / "config/questionnaires/questionnaires.json",
    REPO_ROOT / "tests/architecture/test_domain_purity.py",
    REPO_ROOT / "tests/architecture/test_zero_spanish_literals.py",
    REPO_ROOT / "tests/adapters/test_adapters.py",
    REPO_ROOT / "tests/integration/test_finops_advisor_service.py",
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

USER INSTRUCTIONS & MANDATE:
The user has issued an explicit command:
"Before continuing, I want you to tell gemini-4-argon to do a complete review of what you have programmed and look for bugs, problems, or anti-patterns. I want nothing hardcoded, remember the goal is that it serves any company in the world from mid-market to global top tier-1, of any vertical, in any language, and the code must be 100% in English—not a single word of Spanish. Spanish is solely the conversational language between the user and the agent, and one of the output languages of the deliverables."

REVIEW TARGET:
Complete End-to-End System (Domain Models, Ports, Domain Services, Adapters, Catalogs, Taxonomies, Application Orchestrator, Web Server API, and Automated Fitness Gates).

HERE IS THE COMPLETE CODEBASE DELIVERABLE (39 FILES):
{codebase_payload}

YOUR ADVERSARIAL AUDIT MANDATE:
Conduct an exhaustive forensic review across the following 5 dimensions:

1. BUGS, RUNTIME HAZARDS & NUMERICAL INTEGRITY:
   - Audit all mathematical logic: Roofline sizing (MHA/GQA vs DeepSeek MLA), Open FAIR actuarial risk modeling, Banker's Rounding, pure Decimal ceiling, sum reconciliation, and currency conversion.
   - Look for unhandled None, division by zero, float pollution, or unhandled exceptions in the application and web server layers.

2. ANTI-PATTERNS & ARCHITECTURAL PURITY:
   - Verify Hexagonal Architecture: zero infrastructure or I/O leaks inside `src/domain/`.
   - Verify that Adapters (`src/adapters/`) properly encapsulate file I/O, JSON decoding, cryptographic hashing, and currency conversion without polluting domain models.
   - Verify deep immutability (`MappingProxyType`, frozen dataclasses, tuple sequences).

3. ZERO-HARDCODING & UNIVERSAL SCALABILITY:
   - Verify that NO hardware constants, cloud prices, SI scale factors, or threshold limits are hardcoded.
   - Verify universal applicability: can a 1-node mid-market retail edge deployment (€5k) run seamlessly alongside a 1024-node sovereign defense supercluster ($250M) across any vertical (Banking, Defense, Healthcare, Retail, Telecom, SaaS, Manufacturing) and any currency (USD, EUR, JPY, GBP, CHF) without modifying Python source code?

4. LINGUISTIC PURITY & DECOUPLING:
   - Verify that 100% of all Python source code in `src/`, `scripts/`, and `tests/` is written in pure Technical English.
   - Verify that Spanish exclusively exists inside the `"es"` dictionary of `config/locales.json`.
   - Verify that all JSON keys, taxonomy identifiers, and configuration objects are written strictly in Technical English.

5. DELIVERABLE FORMAT:
   - Detailed Findings per Dimension (Pass / Warn / Fail with exact file and line references).
   - Numerical Score (0 to 100).
   - Formal Binding Verdict: `APPROVED (PRODUCTION READY)` or `REJECTED (REMEDIATION REQUIRED)`.
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

    out_file = REPO_ROOT / "docs" / "AUDIT_REPORT_PHASE3_ARGON.md"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(response.text, encoding="utf-8")

    print("\n" + "=" * 80)
    print(f" GEMINI-4-ARGON FULL SYSTEM AUDIT REPORT COMPLETED ({len(response.text)} chars)")
    print(f" Target File: {out_file}")
    print("=" * 80)


if __name__ == "__main__":
    main()
