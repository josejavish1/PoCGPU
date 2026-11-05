"""Governed record and policy repository ports."""

from __future__ import annotations

from typing import Protocol

from pocgpu.domain.identifiers import PolicyPackId, RecordId, TenantId
from pocgpu.domain.policies import PolicyPack
from pocgpu.domain.provenance import GovernedRecord


class GovernedRecordRepository(Protocol):
    """Retrieve exact governed record versions within one tenant."""

    def get(self, tenant_id: TenantId, record_id: RecordId) -> GovernedRecord[object] | None: ...


class PolicyRepository(Protocol):
    """Retrieve exact policy pack records within one tenant."""

    def get(
        self, tenant_id: TenantId, pack_id: PolicyPackId
    ) -> GovernedRecord[PolicyPack] | None: ...
