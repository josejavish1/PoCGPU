#!/usr/bin/env python3
"""
PoCGPU — Turnkey Resilient Autonomous Execution Pipeline (Two-Tier Incremental Architecture).
- Architect & Adversarial Gatekeeper: gemini-4-argon (fallback: gemini-3.1-pro-preview)
- Synthesizer / Implementation Worker: gemini-2.5-flash (fallback: gemini-3.8-flash)
- Execution Model: Atomic Increments (1 target file + 1 test file per step) to avoid timeouts.
- Deterministic Verification: Python 3.12, validate_engineering_constitution.py and pytest.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [AUTONOMOUS-PIPELINE] %(message)s",
)
logger = logging.getLogger("pocgpu_mission")

REPO_ROOT = Path(__file__).resolve().parent.parent

# Two-tier model configuration
ARCHITECT_MODEL = os.environ.get("AI_REASONING_MODEL", "gemini-4-argon")
ARCHITECT_FALLBACK = "gemini-3.1-pro-preview"

SYNTHESIZER_MODEL = os.environ.get("AI_FAST_MODEL", "gemini-2.5-flash")
SYNTHESIZER_FALLBACK = "gemini-3.8-flash"

MAX_INCREMENT_ROUNDS = 5

VENV_DIR = REPO_ROOT / ".venv"
VENV_PYTHON = VENV_DIR / "bin" / "python3"
VENV_PYTEST = VENV_DIR / "bin" / "pytest"


def get_genai_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        return genai.Client(api_key=api_key, http_options={"timeout": 180000})
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "sub403o4u0q5")
    return genai.Client(vertexai=True, project=project_id, location="global", http_options={"timeout": 180000})


def call_model_with_fallback(
    client: genai.Client,
    primary_model: str,
    fallback_model: str,
    prompt: str,
    response_schema: Optional[dict[str, Any]] = None,
    temperature: float = 0.0,
) -> str:
    config_args: dict[str, Any] = {"temperature": temperature}
    if response_schema:
        config_args["response_mime_type"] = "application/json"
        config_args["response_schema"] = response_schema

    config = types.GenerateContentConfig(**config_args)

    for target_model in [primary_model, fallback_model]:
        try:
            logger.info(f"   [Cognitive Request] Dispatching inference to '{target_model}'...")
            response = client.models.generate_content(
                model=target_model,
                contents=prompt,
                config=config,
            )
            if response.text:
                return response.text
        except Exception as ex:
            logger.warning(f"   [Model Warning] '{target_model}' failed ({ex}). Attempting fallback...")
            if target_model == fallback_model:
                raise ex

    raise RuntimeError("All candidate models exhausted.")


def run_deterministic_verification(target_test: Optional[str] = None) -> tuple[bool, str]:
    python_bin = str(VENV_PYTHON if VENV_PYTHON.exists() else sys.executable)
    pytest_bin = str(VENV_PYTEST if VENV_PYTEST.exists() else "pytest")

    res_const = subprocess.run(
        [python_bin, "scripts/validate_engineering_constitution.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if res_const.returncode != 0:
        return False, f"Constitution violation:\nSTDOUT:\n{res_const.stdout}\nSTDERR:\n{res_const.stderr}"

    test_args = [pytest_bin, "-q", "--import-mode=importlib"]
    if target_test:
        test_args.append(target_test)
        test_args.append("tests/phase1/architecture")
    else:
        test_args.append("tests")

    res_pytest = subprocess.run(
        test_args,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": f"{REPO_ROOT}:{REPO_ROOT / 'src'}"},
    )
    if res_pytest.returncode != 0:
        return False, f"Pytest failure:\nSTDOUT:\n{res_pytest.stdout}\nSTDERR:\n{res_pytest.stderr}"

    return True, "All constitutional and test gates passed."


def plan_phase_increments(phase: int, client: genai.Client) -> list[dict[str, str]]:
    plan_path = REPO_ROOT / f"docs/engineering-constitution/PHASE_{phase}_PLAN.md"
    plan_text = plan_path.read_text(encoding="utf-8")
    roadmap_text = (REPO_ROOT / "docs/engineering-constitution/DELIVERY_ROADMAP.md").read_text(encoding="utf-8")

    prompt = f"""
You are the Principal Systems Architect (gemini-4-argon).
Break down Phase {phase} plan into 4 to 6 atomic, sequential delivery increments.
Each increment MUST specify:
- target_file: production code file path relative to repo root (e.g. src/pocgpu/domain/capacity/contracts.py)
- test_file: corresponding test file path relative to repo root (e.g. tests/phase2/domain/test_contracts.py)
- specification: clear, detailed technical requirements, mathematical invariants, and domain rules.

DELIVERY ROADMAP:
{roadmap_text}

PHASE {phase} PLAN:
{plan_text}
"""
    increments_schema = {
        "type": "object",
        "properties": {
            "increments": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "increment_id": {"type": "integer"},
                        "name": {"type": "string"},
                        "target_file": {"type": "string"},
                        "test_file": {"type": "string"},
                        "specification": {"type": "string"},
                    },
                    "required": ["increment_id", "name", "target_file", "test_file", "specification"],
                },
            }
        },
        "required": ["increments"],
    }

    raw = call_model_with_fallback(
        client=client,
        primary_model=ARCHITECT_MODEL,
        fallback_model=ARCHITECT_FALLBACK,
        prompt=prompt,
        response_schema=increments_schema,
    )
    data = json.loads(raw)
    return data.get("increments", [])


def execute_phase(phase: int, client: genai.Client) -> bool:
    logger.info(f"\n{'='*75}\n🏁 STARTING PHASE {phase} ATOMIC INCREMENTAL EXECUTION\n{'='*75}")
    increments = plan_phase_increments(phase, client)
    logger.info(f"   [Architect] Planned {len(increments)} atomic increments for Phase {phase}.")

    for inc in increments:
        inc_id = inc["increment_id"]
        name = inc["name"]
        target_file = inc["target_file"]
        test_file = inc["test_file"]
        spec = inc["specification"]

        # Check if increment is already implemented and passing all gates
        t_path = REPO_ROOT / target_file
        test_path = REPO_ROOT / test_file
        if t_path.exists() and test_path.exists():
            already_passed, _ = run_deterministic_verification(target_test=test_file)
            if already_passed:
                logger.info(f"   [Resume] Increment {inc_id}/{len(increments)} ('{name}') already verified. Skipping.")
                continue

        logger.info(f"\n--- [Increment {inc_id}/{len(increments)}] {name} ---")
        logger.info(f"    Target: {target_file}")
        logger.info(f"    Test:   {test_file}")

        last_error = ""
        success = False

        for round_idx in range(1, MAX_INCREMENT_ROUNDS + 1):
            # Dynamic Cognitive Tier Escalation:
            # Rounds 1-2: Fast Tier (gemini-2.5-flash) for rapid initial generation
            # Rounds 3-5: Reasoning Tier (gemini-4-argon) for deep root-cause remediation & anti-oscillation
            if round_idx <= 2:
                active_model = SYNTHESIZER_MODEL
                active_fallback = SYNTHESIZER_FALLBACK
                logger.info(f"    [Synthesizer Round {round_idx}/{MAX_INCREMENT_ROUNDS}] Generating via {active_model} (Fast Tier)...")
            else:
                active_model = ARCHITECT_MODEL
                active_fallback = ARCHITECT_FALLBACK
                logger.info(f"    [ESCALATED Cognitive Round {round_idx}/{MAX_INCREMENT_ROUNDS}] Escalating to {active_model} (Reasoning Tier) to break defect oscillation...")

            existing_context = ""
            if round_idx > 1 and t_path.exists() and test_path.exists():
                existing_context = f"""
EXISTING TARGET SOURCE (REFINE THIS TO FIX BUGS - DO NOT DISCARD WORKING LOGIC):
```python
{t_path.read_text(encoding="utf-8")}
```

EXISTING TEST SUITE (SPECIFICATION ORACLE - DO NOT WEAKEN ASSERTIONS):
```python
{test_path.read_text(encoding="utf-8")}
```
"""

            synth_prompt = f"""
You are the Lead Systems Engineer and Synthesizer ({active_model}).
Implement the atomic increment strictly adhering to the specification.

MANDATES:
- 100% Technical English (identifiers, comments, docstrings, error messages).
- Zero placeholders, zero ellipses.
- Python 3.12+ syntax (PEP 695 type aliases allowed).
- Domain purity: ZERO external library imports (NO pydantic in domain). Use pure dataclasses.
- Dataclass field defaults rule: in domain dataclasses, do NOT assign default values in field annotations (e.g. no 'field: int = 0'). Use custom __init__ if default values are needed.
- In pytest.raises(..., match=...): remember match is a regex pattern, escape special characters like '+' (use r'\\+' or re.escape).
- In datetime operations: use timezone-aware UtcInstant or datetime.now(timezone.utc) (avoid datetime.UTC if importing datetime module as datetime).
- PRESERVATION MANDATE: When fixing errors, patch ONLY the failing methods/assertions. Preserve all working classes, methods, and tests.

INCREMENT SPECIFICATION:
{spec}

TARGET FILE TO GENERATE: {target_file}
TEST FILE TO GENERATE:   {test_file}

{existing_context}

{f'PREVIOUS VERIFICATION ERRORS (MUST FIX WITHOUT CAUSING REGRESSIONS):{last_error}' if last_error else ''}

Output JSON with keys 'target_code' and 'test_code'.
"""
            synth_schema = {
                "type": "object",
                "properties": {
                    "target_code": {"type": "string"},
                    "test_code": {"type": "string"},
                },
                "required": ["target_code", "test_code"],
            }

            raw_code = call_model_with_fallback(
                client=client,
                primary_model=active_model,
                fallback_model=active_fallback,
                prompt=synth_prompt,
                response_schema=synth_schema,
            )

            try:
                code_data = json.loads(raw_code)
                t_code = code_data["target_code"]
                test_code = code_data["test_code"]
            except Exception as ex:
                last_error = f"\nJSON parsing error: {ex}"
                continue

            # Write files
            t_path = REPO_ROOT / target_file
            t_path.parent.mkdir(parents=True, exist_ok=True)
            t_path.write_text(t_code, encoding="utf-8")

            test_path = REPO_ROOT / test_file
            test_path.parent.mkdir(parents=True, exist_ok=True)
            test_path.write_text(test_code, encoding="utf-8")

            # Validate increment
            passed, err = run_deterministic_verification(target_test=test_file)
            if passed:
                logger.info(f"    [Increment PASS] Increment {inc_id} passed all gates.")
                success = True
                break
            else:
                logger.warning(f"    [Increment FAILED] Round {round_idx} errors:\n{err[:400]}")
                last_error = f"\n{err}"

        if not success:
            logger.error(f"Phase {phase} stopped: increment {inc_id} failed after {MAX_INCREMENT_ROUNDS} rounds.")
            return False

    # Run full regression suite after all increments
    logger.info("   [Phase Regression] Running full test suite for Phase {phase}...")
    full_pass, full_err = run_deterministic_verification()
    if not full_pass:
        logger.error(f"Full regression suite failed for Phase {phase}:\n{full_err}")
        return False

    # Completion report
    report_file = REPO_ROOT / f"docs/engineering-constitution/PHASE_{phase}_COMPLETION_REPORT.md"
    report_file.write_text(
        f"# Phase {phase} Completion Report\n\n"
        f"- Status: CERTIFIED\n"
        f"- Architect: {ARCHITECT_MODEL}\n"
        f"- Synthesizer: {SYNTHESIZER_MODEL}\n"
        f"- Increments: {len(increments)} atomic increments certified.\n"
        f"- Deterministic Gates: 100% PASS.\n",
        encoding="utf-8",
    )
    logger.info(f"🏆 PHASE {phase} CERTIFIED AND COMPLETION REPORT WRITTEN.")
    return True


def main() -> None:
    client = get_genai_client()
    logger.info(f"Initialized autonomous pipeline. Architect: {ARCHITECT_MODEL} | Synthesizer: {SYNTHESIZER_MODEL}")

    for phase in range(2, 9):
        report_file = REPO_ROOT / f"docs/engineering-constitution/PHASE_{phase}_COMPLETION_REPORT.md"
        if report_file.exists():
            logger.info(f"Phase {phase} already completed. Skipping.")
            continue

        success = execute_phase(phase, client)
        if not success:
            logger.error(f"Pipeline stopped at Phase {phase}.")
            sys.exit(1)

    logger.info("🏆 ALL PHASES (2 THROUGH 8) AUTONOMOUSLY IMPLEMENTED AND CERTIFIED.")


if __name__ == "__main__":
    main()
