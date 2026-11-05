"""Integrity ledger port separated from correctness and certification."""

from __future__ import annotations

from typing import Protocol

from pocgpu.domain.identifiers import ContentHash, SnapshotId, TenantId
from pocgpu.domain.results import ResultState


class AuditLedger(Protocol):
    """Append and verify integrity evidence without changing result state."""

    def append(
        self,
        tenant_id: TenantId,
        snapshot_id: SnapshotId,
        snapshot_hash: ContentHash,
        result_state: ResultState,
    ) -> ContentHash: ...

    def verify(self) -> bool: ...
