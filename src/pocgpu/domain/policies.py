"""Immutable policy packs, resolution plans, and resolution evidence."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from pocgpu.domain.errors import DomainIssue, DomainValidationError
from pocgpu.domain.identifiers import (
    OpaqueId,
    PolicyKey,
    PolicyPackId,
    SchemaId,
    SemanticVersion,
    TenantId,
)
from pocgpu.domain.money import Money
from pocgpu.domain.quantities import Quantity
from pocgpu.domain.time import UtcInstant

type CanonicalScalar = None | bool | int | str | Decimal | OpaqueId | Quantity | Money | UtcInstant


@dataclass(frozen=True, slots=True)
class CanonicalObject:
    """Immutable typed object used by generic versioned settings."""

    schema_id: SchemaId
    fields: tuple[tuple[str, CanonicalValue], ...]

    def __post_init__(self) -> None:
        names = tuple(name for name, _ in self.fields)
        if any(not name or not name.isascii() for name in names):
            raise DomainValidationError("INVALID_CANONICAL_FIELD", ("fields",))
        if len(names) != len(set(names)):
            raise DomainValidationError("DUPLICATE_CANONICAL_FIELD", ("fields",))


type CanonicalValue = CanonicalScalar | tuple[CanonicalValue, ...] | CanonicalObject


@dataclass(frozen=True, slots=True)
class PolicySetting:
    """One schema-identified immutable policy value."""

    key: PolicyKey
    value_schema_id: SchemaId
    value: CanonicalValue


@dataclass(frozen=True, slots=True)
class PolicyOverride:
    """Explicit permission to supersede named settings from one pack."""

    target_pack_id: PolicyPackId
    keys: tuple[PolicyKey, ...]

    def __post_init__(self) -> None:
        if not self.keys:
            raise DomainValidationError("POLICY_OVERRIDE_KEY_REQUIRED", ("keys",))
        if len(self.keys) != len(set(self.keys)):
            raise DomainValidationError("DUPLICATE_POLICY_OVERRIDE_KEY", ("keys",))


@dataclass(frozen=True, slots=True)
class PolicyPack:
    """Tenant-scoped immutable policy pack."""

    pack_id: PolicyPackId
    tenant_id: TenantId
    version: SemanticVersion
    settings: tuple[PolicySetting, ...]
    overrides: tuple[PolicyOverride, ...]

    def __post_init__(self) -> None:
        setting_keys = tuple(setting.key for setting in self.settings)
        if len(setting_keys) != len(set(setting_keys)):
            raise DomainValidationError("DUPLICATE_POLICY_SETTING", ("settings",))


@dataclass(frozen=True, slots=True)
class PolicyResolutionPlan:
    """Explicit applicable pack set and mandatory setting keys."""

    tenant_id: TenantId
    pack_ids: tuple[PolicyPackId, ...]
    required_keys: tuple[PolicyKey, ...]

    def __post_init__(self) -> None:
        if len(self.pack_ids) != len(set(self.pack_ids)):
            raise DomainValidationError("DUPLICATE_POLICY_PACK", ("pack_ids",))
        if len(self.required_keys) != len(set(self.required_keys)):
            raise DomainValidationError("DUPLICATE_POLICY_KEY", ("required_keys",))


@dataclass(frozen=True, slots=True)
class ResolvedPolicySetting:
    """Selected value and complete contributing source identities."""

    key: PolicyKey
    value_schema_id: SchemaId
    value: CanonicalValue
    source_pack_id: PolicyPackId
    considered_pack_ids: tuple[PolicyPackId, ...]


@dataclass(frozen=True, slots=True)
class PolicyResolutionResult:
    """Deterministic policy values or structured fail-closed issues."""

    values: tuple[ResolvedPolicySetting, ...]
    issues: tuple[DomainIssue, ...]
