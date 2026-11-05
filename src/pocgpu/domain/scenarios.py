"""Immutable scenario requests and canonical result envelopes."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pocgpu.domain.errors import DomainIssue, DomainValidationError
from pocgpu.domain.identifiers import (
    ContentHash,
    EngineId,
    OrganizationId,
    RecordId,
    RecordRevision,
    ScenarioId,
    SchemaId,
    SemanticVersion,
    SnapshotId,
    TenantId,
)
from pocgpu.domain.policies import CanonicalValue, PolicyResolutionPlan
from pocgpu.domain.results import ResultState
from pocgpu.domain.time import UtcInstant


class OutputDomain(StrEnum):
    """Separately requested canonical output domains."""

    FOUNDATION = "FOUNDATION"
    CAPACITY = "CAPACITY"
    TCO = "TCO"
    UNIT_ECONOMICS = "UNIT_ECONOMICS"
    PRICING = "PRICING"
    EXTERNAL_COMPARISON = "EXTERNAL_COMPARISON"


def _assert_unique(values: tuple[object, ...], path: str) -> None:
    if len(values) != len(set(values)):
        raise DomainValidationError("DUPLICATE_SCENARIO_REFERENCE", (path,))


@dataclass(frozen=True, slots=True)
class ScenarioDraft:
    """Explicit immutable scenario version."""

    scenario_id: ScenarioId
    tenant_id: TenantId
    organization_id: OrganizationId
    revision: RecordRevision
    schema_id: SchemaId
    schema_version: SemanticVersion
    engine_id: EngineId
    engine_version: SemanticVersion
    input_record_ids: tuple[RecordId, ...]
    evidence_record_ids: tuple[RecordId, ...]
    accepted_assumption_record_ids: tuple[RecordId, ...]
    policy_resolution_plan: PolicyResolutionPlan
    requested_domains: tuple[OutputDomain, ...]
    created_at: UtcInstant

    def __post_init__(self) -> None:
        for path, values in (
            ("input_record_ids", self.input_record_ids),
            ("evidence_record_ids", self.evidence_record_ids),
            ("accepted_assumption_record_ids", self.accepted_assumption_record_ids),
            ("requested_domains", self.requested_domains),
        ):
            _assert_unique(values, path)
        if not self.requested_domains:
            raise DomainValidationError("OUTPUT_DOMAIN_REQUIRED", ("requested_domains",))
        if self.policy_resolution_plan.tenant_id != self.tenant_id:
            raise DomainValidationError("POLICY_TENANT_MISMATCH", ("policy_resolution_plan",))


@dataclass(frozen=True, slots=True)
class ResultSection:
    """One typed output-domain section without presentation formatting."""

    domain: OutputDomain
    values: tuple[tuple[str, CanonicalValue], ...]

    def __post_init__(self) -> None:
        names = tuple(name for name, _ in self.values)
        if any(not name or not name.isascii() for name in names):
            raise DomainValidationError("INVALID_RESULT_FIELD", ("values",))
        if len(names) != len(set(names)):
            raise DomainValidationError("DUPLICATE_RESULT_FIELD", ("values",))


@dataclass(frozen=True, slots=True)
class CanonicalResult:
    """Immutable canonical result consumed by every future interface."""

    scenario_id: ScenarioId
    scenario_revision: RecordRevision
    snapshot_id: SnapshotId
    snapshot_hash: ContentHash
    engine_id: EngineId
    engine_version: SemanticVersion
    state: ResultState
    issues: tuple[DomainIssue, ...]
    sections: tuple[ResultSection, ...]
    evaluated_at: UtcInstant

    def __post_init__(self) -> None:
        domains = tuple(section.domain for section in self.sections)
        if len(domains) != len(set(domains)):
            raise DomainValidationError("DUPLICATE_RESULT_SECTION", ("sections",))
