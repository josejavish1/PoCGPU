"""Immutable snapshot persistence port."""

from __future__ import annotations

from typing import Protocol

from pocgpu.domain.identifiers import SnapshotId, TenantId
from pocgpu.domain.snapshots import ScenarioSnapshot


class SnapshotRepository(Protocol):
    """Store and retrieve immutable content-addressed snapshots."""

    def add(self, snapshot: ScenarioSnapshot) -> None: ...

    def get(self, tenant_id: TenantId, snapshot_id: SnapshotId) -> ScenarioSnapshot | None: ...
