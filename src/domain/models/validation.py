"""Domain Validation Helpers for Universal Hybrid FinOps Advisor."""

from __future__ import annotations

from decimal import Decimal, ROUND_CEILING


def assert_strict_decimal(value: object, field_name: str) -> Decimal:
    """Guards against float, bool, or non-Decimal values leaking into domain physics."""
    if isinstance(value, (float, bool)) or not isinstance(value, Decimal):
        raise TypeError(
            f"Field '{field_name}' must be an instance of decimal.Decimal (not float or bool), "
            f"got {type(value).__name__} ({value!r})."
        )
    if not value.is_finite():
        raise ValueError(f"Field '{field_name}' must be finite, got {value}.")
    return value


def decimal_ceil_div(numerator: Decimal, denominator: Decimal) -> int:
    """Pure Decimal ceiling division without IEEE-754 float intermediate coercion."""
    if denominator <= Decimal("0"):
        raise ZeroDivisionError("Denominator in decimal_ceil_div must be strictly positive.")
    return int((numerator / denominator).to_integral_value(rounding=ROUND_CEILING))
