"""State precedence, certification, and canonical serialization tests."""

from __future__ import annotations

import json
from decimal import Decimal

import pytest

from pocgpu.domain.errors import DomainIssue, IssueKind, IssueSeverity
from pocgpu.domain.identifiers import GateId, RecordId, SchemaId, SemanticVersion
from pocgpu.domain.results import (
    CertificationGateEvidence,
    ResultState,
    derive_result_state,
)
from pocgpu.domain.serialization import canonical_json_bytes, content_hash


def issue(kind: IssueKind) -> DomainIssue:
    return DomainIssue(
        code=f"TEST_{kind.value}",
        kind=kind,
        severity=IssueSeverity.ERROR,
        path=("scenario",),
        parameters=(),
        localization_key="error.test",
    )


@pytest.mark.parametrize(
    ("issues", "expected"),
    [
        ((issue(IssueKind.INVALID),), ResultState.REJECTED),
        ((issue(IssueKind.STALE),), ResultState.STALE),
        ((issue(IssueKind.INPUT_REQUIRED),), ResultState.INPUT_REQUIRED),
        ((issue(IssueKind.POLICY_REQUIRED),), ResultState.POLICY_REQUIRED),
        ((issue(IssueKind.BENCHMARK_REQUIRED),), ResultState.BENCHMARK_REQUIRED),
    ],
)
def test_result_state_precedence(issues: tuple[DomainIssue, ...], expected: ResultState) -> None:
    assert (
        derive_result_state(
            evaluation_requested=True,
            issues=issues,
            calculations_complete=False,
            contains_assumptions=False,
            certification_requested=False,
            certification_gates=(),
        )
        is expected
    )


def test_certification_requires_complete_passing_gate_evidence() -> None:
    passing = CertificationGateEvidence(
        gate_id=GateId("gate.synthetic"),
        passed=True,
        evidence_record_ids=(RecordId("record.evidence"),),
    )
    failing = CertificationGateEvidence(
        gate_id=GateId("gate.synthetic"),
        passed=False,
        evidence_record_ids=(RecordId("record.evidence"),),
    )

    assert derive_result_state(False, (), False, False, False, ()) is ResultState.DRAFT
    assert derive_result_state(True, (), True, True, False, ()) is ResultState.ASSUMPTION_BASED
    assert derive_result_state(True, (), True, False, False, ()) is ResultState.VALID
    assert derive_result_state(True, (), True, False, True, (passing,)) is ResultState.CERTIFIED
    assert derive_result_state(True, (), True, False, True, ()) is ResultState.REJECTED
    assert derive_result_state(True, (), True, False, True, (failing,)) is ResultState.REJECTED


def test_canonical_serialization_normalizes_semantic_equivalents() -> None:
    first = {"b": Decimal("1.2300"), "a": "caf\u00e9", "zero": Decimal("-0.00")}
    second = {"zero": Decimal("0"), "a": "cafe\u0301", "b": Decimal("1.23")}

    first_bytes = canonical_json_bytes(
        first, SchemaId("schema.synthetic"), SemanticVersion("1.0.0")
    )
    second_bytes = canonical_json_bytes(
        second, SchemaId("schema.synthetic"), SemanticVersion("1.0.0")
    )

    assert first_bytes == second_bytes
    assert json.loads(first_bytes)["payload"] == {"a": "caf\u00e9", "b": "1.23", "zero": "0"}
    assert content_hash(first_bytes).value == content_hash(second_bytes).value


def test_canonical_serialization_rejects_float_and_unknown_objects() -> None:
    with pytest.raises(TypeError, match="FLOAT_PROHIBITED"):
        canonical_json_bytes({"value": 1.0}, SchemaId("schema.synthetic"), SemanticVersion("1.0.0"))
    with pytest.raises(TypeError, match="UNSUPPORTED_CANONICAL_TYPE"):
        canonical_json_bytes(
            {"value": object()}, SchemaId("schema.synthetic"), SemanticVersion("1.0.0")
        )
