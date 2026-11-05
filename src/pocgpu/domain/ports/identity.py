"""Identity-generation port."""

from __future__ import annotations

from typing import Protocol

from pocgpu.domain.identifiers import SnapshotId


class IdentityProvider(Protocol):
    """Generate snapshot identities without domain randomness."""

    def new_snapshot_id(self) -> SnapshotId: ...
