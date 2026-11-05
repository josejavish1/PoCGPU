"""Versioned unit definitions and dimension-safe quantities."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from pocgpu.domain.errors import DomainValidationError
from pocgpu.domain.identifiers import DimensionId, SemanticVersion, UnitId
from pocgpu.domain.numeric import require_decimal


@dataclass(frozen=True, slots=True)
class UnitDefinition:
    """Affine conversion from one unit to its governed dimension base unit."""

    unit_id: UnitId
    dimension_id: DimensionId
    version: SemanticVersion
    scale_to_base: Decimal
    offset_to_base: Decimal

    def __post_init__(self) -> None:
        scale = require_decimal(self.scale_to_base, "scale_to_base")
        require_decimal(self.offset_to_base, "offset_to_base")
        if scale <= 0:
            raise DomainValidationError("INVALID_UNIT_SCALE", ("scale_to_base",))


@dataclass(frozen=True, slots=True)
class Quantity:
    """Exact magnitude with explicit unit and dimension identity."""

    magnitude: Decimal
    unit_id: UnitId
    dimension_id: DimensionId

    def __post_init__(self) -> None:
        require_decimal(self.magnitude, "magnitude")


def convert_quantity(
    value: Quantity,
    source: UnitDefinition,
    target: UnitDefinition,
) -> Quantity:
    """Convert a quantity through compatible versioned unit definitions."""

    if value.unit_id != source.unit_id or value.dimension_id != source.dimension_id:
        raise DomainValidationError("UNIT_DEFINITION_MISMATCH", ("source",))
    if source.dimension_id != target.dimension_id:
        raise DomainValidationError("DIMENSION_MISMATCH", ("target",))
    if source.version != target.version:
        raise DomainValidationError("UNIT_VERSION_MISMATCH", ("target", "version"))
    base_value = value.magnitude * source.scale_to_base + source.offset_to_base
    converted = (base_value - target.offset_to_base) / target.scale_to_base
    return Quantity(converted, target.unit_id, target.dimension_id)
