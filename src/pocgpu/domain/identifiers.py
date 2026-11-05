"""Strict opaque identifiers and version values."""

from __future__ import annotations

import re
from dataclasses import dataclass

from pocgpu.domain.errors import DomainValidationError

MAX_IDENTIFIER_LENGTH = 128
IDENTIFIER_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
SEMANTIC_VERSION_PATTERN = re.compile(
    r"(0|[1-9][0-9]*)\."
    r"(0|[1-9][0-9]*)\."
    r"(0|[1-9][0-9]*)"
    r"(?:-((?:0|[1-9][0-9]*|[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*)"
    r"(?:\.(?:0|[1-9][0-9]*|[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*))*))?"
    r"(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
)


@dataclass(frozen=True, slots=True)
class OpaqueId:
    """Opaque protocol identifier with no embedded business semantics."""

    value: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.value, str)
            or len(self.value) > MAX_IDENTIFIER_LENGTH
            or IDENTIFIER_PATTERN.fullmatch(self.value) is None
        ):
            raise DomainValidationError("INVALID_IDENTIFIER", (type(self).__name__,))

    def __str__(self) -> str:
        return self.value


class TenantId(OpaqueId):
    """Tenant identity."""


class OrganizationId(OpaqueId):
    """Organization identity."""


class RecordId(OpaqueId):
    """Governed record identity."""


class PolicyPackId(OpaqueId):
    """Policy pack identity."""


class PolicyKey(OpaqueId):
    """Policy setting identity."""


class ScenarioId(OpaqueId):
    """Scenario identity."""


class SnapshotId(OpaqueId):
    """Snapshot identity."""


class FormulaId(OpaqueId):
    """Formula identity."""


class SchemaId(OpaqueId):
    """Schema identity."""


class EngineId(OpaqueId):
    """Engine identity."""


class RoleId(OpaqueId):
    """Responsible role identity."""


class UnitId(OpaqueId):
    """Unit identity."""


class DimensionId(OpaqueId):
    """Physical or economic dimension identity."""


class GateId(OpaqueId):
    """Certification gate identity."""


@dataclass(frozen=True, slots=True)
class SemanticVersion:
    """Semantic Versioning 2.0.0 value."""

    value: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.value, str)
            or SEMANTIC_VERSION_PATTERN.fullmatch(self.value) is None
        ):
            raise DomainValidationError("INVALID_SEMANTIC_VERSION", ("version",))

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class RecordRevision:
    """Positive revision scoped to one stable record identity."""

    value: int

    def __post_init__(self) -> None:
        if type(self.value) is not int or self.value <= 0:
            raise DomainValidationError("INVALID_RECORD_REVISION", ("revision",))


@dataclass(frozen=True, slots=True)
class ContentHash:
    """Lowercase SHA-256 content identity."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or re.fullmatch(r"[0-9a-f]{64}", self.value) is None:
            raise DomainValidationError("INVALID_CONTENT_HASH", ("content_hash",))

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class CurrencyCode:
    """Normalized ISO 4217 currency identity without invented support metadata."""

    value: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.value, str)
            or len(self.value) != 3
            or not self.value.isascii()
            or not self.value.isalpha()
            or not self.value.isupper()
        ):
            raise DomainValidationError("INVALID_CURRENCY_CODE", ("currency",))

    def __str__(self) -> str:
        return self.value
