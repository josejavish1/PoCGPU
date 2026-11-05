"""Organization and immutable scenario contract tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from pocgpu.domain.errors import DomainValidationError
from pocgpu.domain.identifiers import (
    EngineId,
    OrganizationId,
    PolicyKey,
    PolicyPackId,
    RecordId,
    RecordRevision,
    ScenarioId,
    SchemaId,
    SemanticVersion,
    TenantId,
)
from pocgpu.domain.organizations import OrganizationProfile
from pocgpu.domain.policies import PolicyResolutionPlan
from pocgpu.domain.scenarios import OutputDomain, ScenarioDraft
from pocgpu.domain.time import UtcInstant


def test_organization_profile_carries_context_as_data() -> None:
    profile = OrganizationProfile(
        tenant_id=TenantId("tenant.synthetic"),
        organization_id=OrganizationId("org.synthetic"),
        display_name="Synthetic Organization",
        policy_pack_ids=(PolicyPackId("policy.organization"),),
        locale_preferences=("en-US", "es-ES"),
        jurisdiction_ids=("jurisdiction.synthetic",),
        context_ids=("vertical.synthetic", "scale.synthetic"),
    )

    assert profile.context_ids == ("vertical.synthetic", "scale.synthetic")

    with pytest.raises(DomainValidationError, match="DUPLICATE_CONTEXT_ID"):
        OrganizationProfile(
            tenant_id=profile.tenant_id,
            organization_id=profile.organization_id,
            display_name=profile.display_name,
            policy_pack_ids=profile.policy_pack_ids,
            locale_preferences=profile.locale_preferences,
            jurisdiction_ids=profile.jurisdiction_ids,
            context_ids=("duplicate", "duplicate"),
        )


def test_scenario_requires_explicit_unique_references() -> None:
    plan = PolicyResolutionPlan(
        tenant_id=TenantId("tenant.synthetic"),
        pack_ids=(PolicyPackId("policy.organization"),),
        required_keys=(PolicyKey("foundation.mode"),),
    )
    scenario = ScenarioDraft(
        scenario_id=ScenarioId("scenario.synthetic"),
        tenant_id=TenantId("tenant.synthetic"),
        organization_id=OrganizationId("org.synthetic"),
        revision=RecordRevision(1),
        schema_id=SchemaId("schema.scenario"),
        schema_version=SemanticVersion("1.0.0"),
        engine_id=EngineId("engine.canonical"),
        engine_version=SemanticVersion("0.1.0"),
        input_record_ids=(RecordId("record.input"),),
        evidence_record_ids=(RecordId("record.evidence"),),
        accepted_assumption_record_ids=(),
        policy_resolution_plan=plan,
        requested_domains=(OutputDomain.FOUNDATION,),
        created_at=UtcInstant(datetime(2026, 11, 4, 8, 0, tzinfo=UTC)),
    )

    assert scenario.requested_domains == (OutputDomain.FOUNDATION,)

    with pytest.raises(DomainValidationError, match="DUPLICATE_SCENARIO_REFERENCE"):
        ScenarioDraft(
            scenario_id=scenario.scenario_id,
            tenant_id=scenario.tenant_id,
            organization_id=scenario.organization_id,
            revision=scenario.revision,
            schema_id=scenario.schema_id,
            schema_version=scenario.schema_version,
            engine_id=scenario.engine_id,
            engine_version=scenario.engine_version,
            input_record_ids=(RecordId("record.input"), RecordId("record.input")),
            evidence_record_ids=scenario.evidence_record_ids,
            accepted_assumption_record_ids=scenario.accepted_assumption_record_ids,
            policy_resolution_plan=plan,
            requested_domains=scenario.requested_domains,
            created_at=scenario.created_at,
        )
