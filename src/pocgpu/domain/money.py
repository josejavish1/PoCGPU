"""Exact money and governed foreign-exchange observations."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from pocgpu.domain.errors import DomainValidationError
from pocgpu.domain.identifiers import CurrencyCode, RecordId
from pocgpu.domain.numeric import require_decimal
from pocgpu.domain.time import UtcInstant


@dataclass(frozen=True, slots=True)
class Money:
    """Exact unrounded monetary amount in one currency."""

    amount: Decimal
    currency: CurrencyCode

    def __post_init__(self) -> None:
        require_decimal(self.amount, "amount")


@dataclass(frozen=True, slots=True)
class FxObservation:
    """Versionable evidence for one directional FX conversion rate."""

    observation_id: RecordId
    base_currency: CurrencyCode
    quote_currency: CurrencyCode
    rate: Decimal
    observed_at: UtcInstant
    valid_until: UtcInstant
    source_record_id: RecordId

    def __post_init__(self) -> None:
        rate = require_decimal(self.rate, "rate")
        if rate <= 0:
            raise DomainValidationError("INVALID_FX_RATE", ("rate",))
        if self.valid_until.value <= self.observed_at.value:
            raise DomainValidationError("INVALID_TIME_INTERVAL", ("valid_until",))
        if self.base_currency == self.quote_currency:
            raise DomainValidationError("INVALID_FX_PAIR", ("currency",))


@dataclass(frozen=True, slots=True)
class ConvertedMoney:
    """Converted money retaining original value and FX evidence identity."""

    original: Money
    converted: Money
    fx_observation_id: RecordId


def convert_money(
    original: Money,
    target_currency: CurrencyCode,
    observation: FxObservation,
) -> ConvertedMoney:
    """Convert money using an explicit matching FX observation."""

    if (
        original.currency != observation.base_currency
        or target_currency != observation.quote_currency
    ):
        raise DomainValidationError("FX_CURRENCY_MISMATCH", ("currency",))
    converted = Money(original.amount * observation.rate, target_currency)
    return ConvertedMoney(original, converted, observation.observation_id)
