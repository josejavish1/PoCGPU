"""Versioned unit-definition repository port."""

from __future__ import annotations

from typing import Protocol

from pocgpu.domain.identifiers import SemanticVersion, UnitId
from pocgpu.domain.quantities import UnitDefinition


class UnitRegistry(Protocol):
    """Resolve one exact unit definition version."""

    def get(self, unit_id: UnitId, version: SemanticVersion) -> UnitDefinition | None: ...
