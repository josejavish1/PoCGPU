"""Explicit in-memory reference adapters for contract verification."""

from __future__ import annotations

from pocgpu.domain.errors import DomainValidationError
from pocgpu.domain.identifiers import PolicyPackId, RecordId, SnapshotId, TenantId
from pocgpu.domain.policies import PolicyPack
from pocgpu.domain.provenance import GovernedRecord
from pocgpu.domain.snapshots import ScenarioSnapshot
from pocgpu.domain.time import UtcInstant


class FixedClock:
    """Clock returning one explicitly supplied captured instant."""

    def __init__(self, instant: UtcInstant) -> None:
        self._instant = instant

    def now(self) -> UtcInstant:
        return self._instant


class SequenceIdentityProvider:
    """Deterministic identity provider backed by an explicit finite sequence."""

    def __init__(self, snapshot_ids: tuple[SnapshotId, ...]) -> None:
        if len(snapshot_ids) != len(set(snapshot_ids)):
            raise DomainValidationError("DUPLICATE_IDENTITY", ("snapshot_ids",))
        self._snapshot_ids = snapshot_ids
        self._next_index = 0

    def new_snapshot_id(self) -> SnapshotId:
        if self._next_index >= len(self._snapshot_ids):
            raise DomainValidationError("IDENTITY_SEQUENCE_EXHAUSTED", ("snapshot_ids",))
        value = self._snapshot_ids[self._next_index]
        self._next_index += 1
        return value


class InMemoryGovernedRecordRepository:
    """Tenant-scoped immutable governed record repository."""

    def __init__(self, records: tuple[GovernedRecord[object], ...]) -> None:
        self._records: dict[tuple[TenantId, RecordId], GovernedRecord[object]] = {}
        for record in records:
            key = (record.metadata.tenant_id, record.metadata.record_id)
            if key in self._records:
                raise DomainValidationError("DUPLICATE_RECORD", (record.metadata.record_id.value,))
            self._records[key] = record

    def get(self, tenant_id: TenantId, record_id: RecordId) -> GovernedRecord[object] | None:
        return self._records.get((tenant_id, record_id))


class InMemoryPolicyRepository:
    """Tenant-scoped immutable policy repository."""

    def __init__(self, records: tuple[GovernedRecord[PolicyPack], ...]) -> None:
        self._records: dict[tuple[TenantId, PolicyPackId], GovernedRecord[PolicyPack]] = {}
        for record in records:
            key = (record.metadata.tenant_id, record.value.pack_id)
            if key in self._records:
                raise DomainValidationError("DUPLICATE_POLICY_PACK", (record.value.pack_id.value,))
            self._records[key] = record

    def get(self, tenant_id: TenantId, pack_id: PolicyPackId) -> GovernedRecord[PolicyPack] | None:
        return self._records.get((tenant_id, pack_id))


class InMemorySnapshotRepository:
    """Tenant-scoped immutable snapshot repository."""

    def __init__(self, snapshots: tuple[ScenarioSnapshot, ...]) -> None:
        self._snapshots: dict[tuple[TenantId, SnapshotId], ScenarioSnapshot] = {}
        for snapshot in snapshots:
            self.add(snapshot)

    def add(self, snapshot: ScenarioSnapshot) -> None:
        key = (snapshot.tenant_id, snapshot.snapshot_id)
        existing = self._snapshots.get(key)
        if existing is not None and existing != snapshot:
            raise DomainValidationError(
                "IMMUTABLE_SNAPSHOT_CONFLICT", (snapshot.snapshot_id.value,)
            )
        self._snapshots[key] = snapshot

    def get(self, tenant_id: TenantId, snapshot_id: SnapshotId) -> ScenarioSnapshot | None:
        return self._snapshots.get((tenant_id, snapshot_id))
