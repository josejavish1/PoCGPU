"""Organization profiles without contextual source branches."""

from __future__ import annotations

from dataclasses import dataclass

from pocgpu.domain.errors import DomainValidationError
from pocgpu.domain.identifiers import OrganizationId, PolicyPackId, TenantId


def _require_unique(values: tuple[object, ...], code: str, path: str) -> None:
    if len(values) != len(set(values)):
        raise DomainValidationError(code, (path,))


@dataclass(frozen=True, slots=True)
class OrganizationProfile:
    """Tenant-scoped organization context expressed entirely as data."""

    tenant_id: TenantId
    organization_id: OrganizationId
    display_name: str
    policy_pack_ids: tuple[PolicyPackId, ...]
    locale_preferences: tuple[str, ...]
    jurisdiction_ids: tuple[str, ...]
    context_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.display_name or not self.display_name.strip():
            raise DomainValidationError("ORGANIZATION_NAME_REQUIRED", ("display_name",))
        _require_unique(self.policy_pack_ids, "DUPLICATE_POLICY_PACK", "policy_pack_ids")
        _require_unique(self.locale_preferences, "DUPLICATE_LOCALE", "locale_preferences")
        _require_unique(self.jurisdiction_ids, "DUPLICATE_JURISDICTION", "jurisdiction_ids")
        _require_unique(self.context_ids, "DUPLICATE_CONTEXT_ID", "context_ids")
        for name, values in (
            ("locale_preferences", self.locale_preferences),
            ("jurisdiction_ids", self.jurisdiction_ids),
            ("context_ids", self.context_ids),
        ):
            if any(not value or not value.isascii() for value in values):
                raise DomainValidationError("INVALID_CONTEXT_VALUE", (name,))
