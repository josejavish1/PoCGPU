"""Strict version 1 transport contracts used to generate JSON Schema."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

type CanonicalJsonScalar = None | bool | int | str
type CanonicalJsonValue = (
    CanonicalJsonScalar | list[CanonicalJsonValue] | dict[str, CanonicalJsonValue]
)


class StrictContractModel(BaseModel):
    """Base boundary contract with strict, immutable, closed fields."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ProvenanceContract(StrictContractModel):
    tenant_id: str
    record_id: str
    schema_id: str
    schema_version: str
    revision: int
    evidence_class: str
    source_id: str | None
    observed_at: str | None
    valid_from: str
    valid_until: str
    owner_organization_id: str
    owner_role_id: str
    quality_status: str
    collection_method: str
    formula_id: str | None
    approval_state: str
    supersedes_record_id: str | None
    source_record_ids: list[str]


class GovernedRecordContract(StrictContractModel):
    metadata: ProvenanceContract
    value: CanonicalJsonValue


class OrganizationProfileContract(StrictContractModel):
    tenant_id: str
    organization_id: str
    display_name: str
    policy_pack_ids: list[str]
    locale_preferences: list[str]
    jurisdiction_ids: list[str]
    context_ids: list[str]


class PolicySettingContract(StrictContractModel):
    key: str
    value_schema_id: str
    value: CanonicalJsonValue


class PolicyOverrideContract(StrictContractModel):
    target_pack_id: str
    keys: list[str]


class PolicyPackContract(StrictContractModel):
    pack_id: str
    tenant_id: str
    version: str
    settings: list[PolicySettingContract]
    overrides: list[PolicyOverrideContract]


class PolicyResolutionPlanContract(StrictContractModel):
    tenant_id: str
    pack_ids: list[str]
    required_keys: list[str]


class ScenarioContract(StrictContractModel):
    scenario_id: str
    tenant_id: str
    organization_id: str
    revision: int
    schema_id: str
    schema_version: str
    engine_id: str
    engine_version: str
    input_record_ids: list[str]
    evidence_record_ids: list[str]
    accepted_assumption_record_ids: list[str]
    policy_resolution_plan: PolicyResolutionPlanContract
    requested_domains: list[str]
    created_at: str


class IssueContract(StrictContractModel):
    code: str
    kind: str
    severity: str
    path: list[str]
    parameters: dict[str, CanonicalJsonScalar]
    localization_key: str


class ResultSectionContract(StrictContractModel):
    domain: str
    values: dict[str, CanonicalJsonValue]


class CanonicalResultContract(StrictContractModel):
    scenario_id: str
    scenario_revision: int
    snapshot_id: str
    snapshot_hash: str
    engine_id: str
    engine_version: str
    state: str
    issues: list[IssueContract]
    sections: list[ResultSectionContract]
    evaluated_at: str
