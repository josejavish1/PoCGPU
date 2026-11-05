"""Integrity and classification tests for captured legacy behavior."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_PATH = REPOSITORY_ROOT / "tests/fixtures/migration/legacy-evidence.json"
EXPECTED_BASELINE = "eda8c880ba94b4922b4e70cbb0331542ae4884f9"
ALLOWED_DISPOSITIONS = frozenset({"PRESERVED", "CORRECTED", "DEFERRED", "REJECTED"})


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_legacy_evidence_is_complete_and_content_addressed() -> None:
    evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))

    assert evidence["schema_version"] == "1.0.0"
    assert evidence["runtime_baseline_commit"] == EXPECTED_BASELINE
    assert len(evidence["cases"]) == 3

    case_ids: set[str] = set()
    for case in evidence["cases"]:
        assert case["case_id"] not in case_ids
        case_ids.add(case["case_id"])
        assert case["disposition"] in ALLOWED_DISPOSITIONS
        assert re.fullmatch(r"[A-Z][A-Z0-9_]+", case["reason_code"])
        assert re.fullmatch(r"[0-9a-f]{64}", case["source_sha256"])

        output = (REPOSITORY_ROOT / case["output_path"]).resolve()
        output.relative_to(REPOSITORY_ROOT)
        assert output.is_file()
        assert _sha256(output) == case["output_sha256"]


def test_legacy_advisor_fixture_excludes_nondeterministic_audit_identity() -> None:
    output = json.loads(
        (REPOSITORY_ROOT / "tests/fixtures/migration/legacy_advisor.stable-output.json").read_text(
            encoding="utf-8"
        )
    )

    assert "entry_hash" not in output
    assert output["constitutional_gate"]["is_certified"] is True
