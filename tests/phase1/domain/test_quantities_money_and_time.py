"""Contracts for dimension-safe quantities, money, FX, and explicit time."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from pocgpu.domain.errors import DomainValidationError
from pocgpu.domain.identifiers import (
    CurrencyCode,
    DimensionId,
    RecordId,
    SemanticVersion,
    UnitId,
)
from pocgpu.domain.money import FxObservation, Money, convert_money
from pocgpu.domain.quantities import Quantity, UnitDefinition, convert_quantity
from pocgpu.domain.time import AggregationKind, TimeWindow, UtcInstant, ValidityInterval


def test_quantity_conversion_requires_matching_versioned_dimensions() -> None:
    length = DimensionId("length")
    meter = UnitDefinition(
        unit_id=UnitId("m"),
        dimension_id=length,
        version=SemanticVersion("1.0.0"),
        scale_to_base=Decimal("1"),
        offset_to_base=Decimal("0"),
    )
    centimeter = UnitDefinition(
        unit_id=UnitId("cm"),
        dimension_id=length,
        version=SemanticVersion("1.0.0"),
        scale_to_base=Decimal("0.01"),
        offset_to_base=Decimal("0"),
    )
    value = Quantity(Decimal("1.25"), meter.unit_id, length)

    assert convert_quantity(value, meter, centimeter) == Quantity(
        Decimal("125"), centimeter.unit_id, length
    )

    incompatible = UnitDefinition(
        unit_id=UnitId("s"),
        dimension_id=DimensionId("time"),
        version=SemanticVersion("1.0.0"),
        scale_to_base=Decimal("1"),
        offset_to_base=Decimal("0"),
    )
    with pytest.raises(DomainValidationError, match="DIMENSION_MISMATCH"):
        convert_quantity(value, meter, incompatible)


def test_affine_quantity_conversion_applies_both_offsets() -> None:
    dimension = DimensionId("temperature.synthetic")
    version = SemanticVersion("1.0.0")
    source = UnitDefinition(UnitId("source"), dimension, version, Decimal("2"), Decimal("3"))
    target = UnitDefinition(UnitId("target"), dimension, version, Decimal("5"), Decimal("7"))

    assert convert_quantity(
        Quantity(Decimal("4"), source.unit_id, dimension), source, target
    ) == Quantity(Decimal("0.8"), target.unit_id, dimension)


def test_money_conversion_preserves_original_value_and_observation() -> None:
    captured = UtcInstant(datetime(2026, 11, 4, 8, 0, tzinfo=UTC))
    observation = FxObservation(
        observation_id=RecordId("fx.2026-11-04.usd-eur"),
        base_currency=CurrencyCode("USD"),
        quote_currency=CurrencyCode("EUR"),
        rate=Decimal("0.92"),
        observed_at=captured,
        valid_until=UtcInstant(datetime(2026, 11, 5, 8, 0, tzinfo=UTC)),
        source_record_id=RecordId("source.fx.provider"),
    )
    original = Money(Decimal("100.00"), CurrencyCode("USD"))

    converted = convert_money(original, CurrencyCode("EUR"), observation)

    assert converted.original == original
    assert converted.converted == Money(Decimal("92.0000"), CurrencyCode("EUR"))
    assert converted.fx_observation_id == observation.observation_id

    with pytest.raises(DomainValidationError, match="FX_CURRENCY_MISMATCH"):
        convert_money(Money(Decimal("1"), CurrencyCode("GBP")), CurrencyCode("EUR"), observation)
    with pytest.raises(DomainValidationError, match="FX_CURRENCY_MISMATCH"):
        convert_money(original, CurrencyCode("GBP"), observation)


def test_validity_and_time_window_use_utc_and_end_exclusive_semantics() -> None:
    start = UtcInstant(datetime(2026, 1, 1, tzinfo=UTC))
    end = UtcInstant(datetime(2026, 2, 1, tzinfo=UTC))
    interval = ValidityInterval(start=start, end=end)

    assert interval.contains(start)
    assert not interval.contains(end)
    assert TimeWindow(start, end, AggregationKind.TOTAL).duration == timedelta(days=31)

    offset_time = UtcInstant(datetime(2026, 1, 1, 1, tzinfo=timezone(timedelta(hours=1))))
    assert offset_time.value == start.value

    with pytest.raises(DomainValidationError, match="TIMEZONE_REQUIRED"):
        UtcInstant(datetime(2026, 1, 1))
    with pytest.raises(DomainValidationError, match="INVALID_TIME_INTERVAL"):
        ValidityInterval(start=end, end=start)
