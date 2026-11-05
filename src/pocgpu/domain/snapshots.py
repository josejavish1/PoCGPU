"""Content-addressed immutable scenario snapshot contracts."""

from __future__ import annotations

from dataclasses import dataclass

from pocgpu.domain.errors import DomainValidationError
from pocgpu.domain.identifiers import (
    ContentHash,
    PolicyPackId,
    RecordId,
    RecordRevision,
    ScenarioId,
    SnapshotId,
    TenantId,
)
from pocgpu.domain.time import UtcInstant


@dataclass(frozen=True, slots=True)
class SnapshotRecord:
    """Content identity for one resolved governed record version."""

    record_id: RecordId
    revision: RecordRevision
    content_hash: ContentHash


@dataclass(frozen=True, slots=True)
class ScenarioSnapshot:
    """Replayable set of resolved scenario dependencies."""

    snapshot_id: SnapshotId
    tenant_id: TenantId
    scenario_id: ScenarioId
    scenario_revision: RecordRevision
    captured_at: UtcInstant
    records: tuple[SnapshotRecord, ...]
    policy_pack_ids: tuple[PolicyPackId, ...]
    content_hash: ContentHash

    def __post_init__(self) -> None:
        record_ids = tuple(record.record_id for record in self.records)
        if len(record_ids) != len(set(record_ids)):
            raise DomainValidationError("DUPLICATE_SNAPSHOT_RECORD", ("records",))
        if len(self.policy_pack_ids) != len(set(self.policy_pack_ids)):
            raise DomainValidationError("DUPLICATE_POLICY_PACK", ("policy_pack_ids",))
