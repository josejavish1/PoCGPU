"""Canonical result states and certification construction rules."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pocgpu.domain.errors import DomainIssue, IssueKind
from pocgpu.domain.identifiers import GateId, RecordId


class ResultState(StrEnum):
    """Normative primary scenario result state."""

    DRAFT = "DRAFT"
    INPUT_REQUIRED = "INPUT_REQUIRED"
    BENCHMARK_REQUIRED = "BENCHMARK_REQUIRED"
    POLICY_REQUIRED = "POLICY_REQUIRED"
    ASSUMPTION_BASED = "ASSUMPTION_BASED"
    VALID = "VALID"
    CERTIFIED = "CERTIFIED"
    REJECTED = "REJECTED"
    STALE = "STALE"


@dataclass(frozen=True, slots=True)
class CertificationGateEvidence:
    """Evidence that one mandatory certification gate was evaluated."""

    gate_id: GateId
    passed: bool
    evidence_record_ids: tuple[RecordId, ...]


ISSUE_PRECEDENCE = (
    (frozenset({IssueKind.INVALID, IssueKind.UNSUPPORTED}), ResultState.REJECTED),
    (frozenset({IssueKind.STALE}), ResultState.STALE),
    (frozenset({IssueKind.INPUT_REQUIRED}), ResultState.INPUT_REQUIRED),
    (frozenset({IssueKind.POLICY_REQUIRED}), ResultState.POLICY_REQUIRED),
    (frozenset({IssueKind.BENCHMARK_REQUIRED}), ResultState.BENCHMARK_REQUIRED),
)


def derive_result_state(
    evaluation_requested: bool,
    issues: tuple[DomainIssue, ...],
    calculations_complete: bool,
    contains_assumptions: bool,
    certification_requested: bool,
    certification_gates: tuple[CertificationGateEvidence, ...],
) -> ResultState:
    """Derive exactly one state using the constitutional precedence."""

    if not evaluation_requested:
        return ResultState.DRAFT

    issue_kinds = frozenset(issue.kind for issue in issues)
    for blocking_kinds, state in ISSUE_PRECEDENCE:
        if issue_kinds.intersection(blocking_kinds):
            return state

    if not calculations_complete:
        return ResultState.INPUT_REQUIRED
    if contains_assumptions:
        return ResultState.ASSUMPTION_BASED
    if certification_requested:
        if not certification_gates:
            return ResultState.REJECTED
        if any(not gate.passed or not gate.evidence_record_ids for gate in certification_gates):
            return ResultState.REJECTED
        if len({gate.gate_id for gate in certification_gates}) != len(certification_gates):
            return ResultState.REJECTED
        return ResultState.CERTIFIED
    return ResultState.VALID
