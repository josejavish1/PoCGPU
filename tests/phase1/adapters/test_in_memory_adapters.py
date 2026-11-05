"""Shared behavior for tenant-scoped reference adapters."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from pocgpu.adapters.in_memory import FixedClock, SequenceIdentityProvider
from pocgpu.domain.errors import DomainValidationError
from pocgpu.domain.identifiers import SnapshotId
from pocgpu.domain.time import UtcInstant


def test_fixed_clock_and_sequence_identity_are_explicit_and_deterministic() -> None:
    instant = UtcInstant(datetime(2026, 11, 4, 8, 0, tzinfo=UTC))
    clock = FixedClock(instant)
    identities = SequenceIdentityProvider(
        (SnapshotId("snapshot.first"), SnapshotId("snapshot.second"))
    )

    assert clock.now() == instant
    assert identities.new_snapshot_id() == SnapshotId("snapshot.first")
    assert identities.new_snapshot_id() == SnapshotId("snapshot.second")
    with pytest.raises(DomainValidationError, match="IDENTITY_SEQUENCE_EXHAUSTED"):
        identities.new_snapshot_id()
