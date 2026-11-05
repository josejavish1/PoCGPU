"""Exact decimal parsing, canonicalization, and explicit rounding."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import (
    ROUND_CEILING,
    ROUND_DOWN,
    ROUND_FLOOR,
    ROUND_HALF_EVEN,
    ROUND_HALF_UP,
    ROUND_UP,
    Decimal,
)
from enum import StrEnum

from pocgpu.domain.errors import DomainValidationError

CANONICAL_DECIMAL_PATTERN = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?")


def require_decimal(value: object, field_name: str) -> Decimal:
    """Require a finite Decimal without accepting implicit coercion."""

    if type(value) is not Decimal or not value.is_finite():
        raise DomainValidationError("DECIMAL_REQUIRED", (field_name,))
    return value


def parse_decimal_string(value: str, field_name: str) -> Decimal:
    """Parse a locale-neutral canonical decimal string."""

    if not isinstance(value, str) or CANONICAL_DECIMAL_PATTERN.fullmatch(value) is None:
        raise DomainValidationError("INVALID_DECIMAL_STRING", (field_name,))
    return Decimal(value)


def canonical_decimal(value: Decimal) -> str:
    """Serialize a finite Decimal as normalized non-exponent text."""

    decimal_value = require_decimal(value, "value")
    if decimal_value.is_zero():
        return "0"
    text = format(decimal_value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


class RoundingMode(StrEnum):
    """Supported explicit decimal rounding modes."""

    HALF_EVEN = "HALF_EVEN"
    HALF_UP = "HALF_UP"
    DOWN = "DOWN"
    UP = "UP"
    FLOOR = "FLOOR"
    CEILING = "CEILING"


ROUNDING_MAP = {
    RoundingMode.HALF_EVEN: ROUND_HALF_EVEN,
    RoundingMode.HALF_UP: ROUND_HALF_UP,
    RoundingMode.DOWN: ROUND_DOWN,
    RoundingMode.UP: ROUND_UP,
    RoundingMode.FLOOR: ROUND_FLOOR,
    RoundingMode.CEILING: ROUND_CEILING,
}


@dataclass(frozen=True, slots=True)
class RoundingPolicy:
    """Explicit rounding boundary."""

    scale: int
    mode: RoundingMode

    def __post_init__(self) -> None:
        if type(self.scale) is not int or self.scale < 0:
            raise DomainValidationError("INVALID_ROUNDING_SCALE", ("scale",))

    def apply(self, value: Decimal) -> Decimal:
        decimal_value = require_decimal(value, "value")
        quantum = Decimal(1).scaleb(-self.scale)
        return decimal_value.quantize(quantum, rounding=ROUNDING_MAP[self.mode])
