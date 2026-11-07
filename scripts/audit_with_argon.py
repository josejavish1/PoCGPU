#!/usr/bin/env python3
"""
Adversarial Code Review Gateway using gemini-4-argon
===================================================
Dispatches full codebases of the newly developed benchmark scripts to gemini-4-argon
for rigorous Tier-1 enterprise architectural, security, language, and reliability audit.
"""

from __future__ import annotations

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

FILES_TO_AUDIT = [
    "pocs/elastic-multi-gpu-inference/scripts/characterize_performance_matrix.py",
    "pocs/elastic-multi-gpu-inference/scripts/sweep_model_curve.py",
    "pocs/elastic-multi-gpu-inference/scripts/exhaustive_api_sweep.py",
]


def load_file_contents() -> str:
    combined = []
    for rel_path in FILES_TO_AUDIT:
        full_path = REPO_ROOT / rel_path
        if full_path.exists():
            content = full_path.read_text(encoding="utf-8")
            combined.append(f"=== FILE: {rel_path} ===\n{content}\n")
        else:
            combined.append(f"=== FILE: {rel_path} (NOT FOUND) ===\n")
    return "\n".join(combined)


def build_audit_prompt(code_bundle: str) -> str:
    return f"""You are 'gemini-4-argon', the Principal AI Infrastructure Architect and Adversarial Gatekeeper for an enterprise-grade sovereign AI engine.

Perform an unsparing, exhaustive code quality, security, and architectural audit of the following 3 Python benchmark scripts:

{code_bundle}

Audit strictly against these enterprise mandates:
1. ZERO HARDCODING MANDATE:
   - Must be able to run seamlessly for ANY company in the world (from mid-market to top Tier-1 global institutions in banking, defense, telecom, or healthcare).
   - Verify that all URLs, API keys, database paths, pricing numbers, model lists, and hardware parameters are externalized or dynamically configurable via environment variables, CLI flags, or catalog files.
   - Flag any lingering hardcoded values.

2. LANGUAGE DECOUPLING MANDATE:
   - All code, identifiers, function signatures, docstrings, comments, log messages, exception messages, and console outputs MUST be 100% Technical English.
   - Zero tolerance for any Spanish words or phrases in code/comments.

3. CONCURRENCY, RELIABILITY & PERFORMANCE:
   - Check SQLite concurrency handling (WAL mode, busy timeout, connection locking).
   - Check async event loop safety (are there any blocking I/O calls?).
   - Check HTTP client connection pooling, memory growth during streaming, and exception classification.

4. BUGS, VULNERABILITIES & ANTI-PATTERNS:
   - Identify any hidden bugs, off-by-one errors, math or statistical calculation flaws, resource leaks, or edge-case crashes.

Format your response with:
- [EXECUTIVE VERDICT]: PASS, PASS WITH OBSERVATIONS, or FAIL
- [CRITICAL FINDINGS]: Numbered list with exact file name, line/block reference, severity (BLOCKER, CRITICAL, MAJOR, MINOR), and technical rationale.
- [LANGUAGE DECOUPLING AUDIT]: Specific pass/fail evaluation on English purity.
- [ZERO-HARDCODING AUDIT]: Specific pass/fail evaluation on configuration externalization.
- [ACTIONABLE REMEDIATIONS]: Exact, minimal code patches if any issues remain.
"""


def main() -> None:
    print(f"[*] Initializing connection to Architect Model: {ARCHITECT_MODEL}...")
    client = get_genai_client()
    code_bundle = load_file_contents()
    prompt = build_audit_prompt(code_bundle)

    print("[*] Dispatching adversarial review to gemini-4-argon...")
    review = call_model_with_fallback(
        client=client,
        primary_model=ARCHITECT_MODEL,
        fallback_model=ARCHITECT_FALLBACK,
        prompt=prompt,
        temperature=0.0,
    )

    print("\n" + "=" * 90)
    print("                GEMINI-4-ARGON ADVERSARIAL AUDIT REPORT")
    print("=" * 90)
    print(review)
    print("=" * 90)


if __name__ == "__main__":
    main()
