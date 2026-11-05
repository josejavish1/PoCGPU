"""Explicit UTC instants, validity intervals, and aggregation windows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from pocgpu.domain.errors import DomainValidationError


@dataclass(frozen=True, slots=True, order=True)
class UtcInstant:
    """Timezone-aware instant normalized to UTC."""

    value: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.value, datetime) or self.value.tzinfo is None:
            raise DomainValidationError("TIMEZONE_REQUIRED", ("instant",))
        if self.value.utcoffset() is None:
            raise DomainValidationError("TIMEZONE_REQUIRED", ("instant",))
        object.__setattr__(self, "value", self.value.astimezone(UTC))


@dataclass(frozen=True, slots=True)
class ValidityInterval:
    """Inclusive-start and exclusive-end validity interval."""

    start: UtcInstant
    end: UtcInstant

    def __post_init__(self) -> None:
        if self.start.value >= self.end.value:
            raise DomainValidationError("INVALID_TIME_INTERVAL", ("validity",))

    def contains(self, instant: UtcInstant) -> bool:
        return self.start.value <= instant.value < self.end.value


class AggregationKind(StrEnum):
    """Semantic interpretation of values over a time window."""

    POINT_IN_TIME = "POINT_IN_TIME"
    TOTAL = "TOTAL"
    AVERAGE = "AVERAGE"
    MAXIMUM = "MAXIMUM"
    MINIMUM = "MINIMUM"


@dataclass(frozen=True, slots=True)
class TimeWindow:
    """Explicit period and aggregation meaning."""

    start: UtcInstant
    end: UtcInstant
    aggregation: AggregationKind

    def __post_init__(self) -> None:
        if self.start.value >= self.end.value:
            raise DomainValidationError("INVALID_TIME_INTERVAL", ("time_window",))

    @property
    def duration(self) -> timedelta:
        return self.end.value - self.start.value
