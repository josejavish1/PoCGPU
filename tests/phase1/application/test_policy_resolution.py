"""Policy resolution tests for explicit overrides and fail-closed conflicts."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from pocgpu.application.policy_resolution import PolicyResolver
from pocgpu.domain.identifiers import (
    OrganizationId,
    PolicyKey,
    PolicyPackId,
    RecordId,
    RecordRevision,
    RoleId,
    SchemaId,
    SemanticVersion,
    TenantId,
)
from pocgpu.domain.policies import (
    PolicyOverride,
    PolicyPack,
    PolicyResolutionPlan,
    PolicySetting,
)
from pocgpu.domain.provenance import (
    ApprovalState,
    EvidenceClass,
    GovernedRecord,
    ProvenanceMetadata,
    QualityStatus,
    RecordOwner,
)
from pocgpu.domain.time import UtcInstant, ValidityInterval

TENANT = TenantId("tenant.synthetic")
NOW = UtcInstant(datetime(2026, 11, 4, 8, 0, tzinfo=UTC))


def governed_pack(pack: PolicyPack) -> GovernedRecord[PolicyPack]:
    metadata = ProvenanceMetadata(
        tenant_id=TENANT,
        record_id=RecordId(f"record.{pack.pack_id.value}"),
        schema_id=SchemaId("schema.policy-pack"),
        schema_version=SemanticVersion("1.0.0"),
        revision=RecordRevision(1),
        evidence_class=EvidenceClass.CONFIGURED,
        source=None,
        observed_at=None,
        validity=ValidityInterval(
            UtcInstant(datetime(2026, 1, 1, tzinfo=UTC)),
            UtcInstant(datetime(2027, 1, 1, tzinfo=UTC)),
        ),
        owner=RecordOwner(OrganizationId("org.synthetic"), RoleId("role.owner")),
        quality_status=QualityStatus.VERIFIED,
        collection_method="synthetic-test",
        formula_id=None,
        approval_state=ApprovalState.APPROVED,
        supersedes_record_id=None,
        source_record_ids=(),
        assumption_acceptance=None,
    )
    return GovernedRecord(metadata, pack)


def pack(
    identifier: str,
    value: Decimal,
    overrides: tuple[PolicyOverride, ...],
) -> GovernedRecord[PolicyPack]:
    return governed_pack(
        PolicyPack(
            pack_id=PolicyPackId(identifier),
            tenant_id=TENANT,
            version=SemanticVersion("1.0.0"),
            settings=(
                PolicySetting(
                    key=PolicyKey("capacity.headroom"),
                    value_schema_id=SchemaId("schema.ratio"),
                    value=value,
                ),
            ),
            overrides=overrides,
        )
    )


def test_policy_conflict_fails_without_explicit_override() -> None:
    first = pack("policy.first", Decimal("0.10"), ())
    second = pack("policy.second", Decimal("0.20"), ())
    plan = PolicyResolutionPlan(
        tenant_id=TENANT,
        pack_ids=(first.value.pack_id, second.value.pack_id),
        required_keys=(PolicyKey("capacity.headroom"),),
    )

    result = PolicyResolver().resolve(plan, (second, first), NOW)

    assert result.values == ()
    assert [issue.code for issue in result.issues] == ["POLICY_CONFLICT"]


def test_explicit_override_is_deterministic_under_reordering() -> None:
    first = pack("policy.first", Decimal("0.10"), ())
    second = pack(
        "policy.second",
        Decimal("0.20"),
        (
            PolicyOverride(
                target_pack_id=first.value.pack_id,
                keys=(PolicyKey("capacity.headroom"),),
            ),
        ),
    )
    plan = PolicyResolutionPlan(
        tenant_id=TENANT,
        pack_ids=(first.value.pack_id, second.value.pack_id),
        required_keys=(PolicyKey("capacity.headroom"),),
    )

    forward = PolicyResolver().resolve(plan, (first, second), NOW)
    reverse = PolicyResolver().resolve(plan, (second, first), NOW)

    assert forward == reverse
    assert forward.issues == ()
    assert forward.values[0].value == Decimal("0.20")
    assert forward.values[0].source_pack_id == second.value.pack_id


def test_missing_required_policy_and_override_cycle_fail_closed() -> None:
    missing_plan = PolicyResolutionPlan(
        tenant_id=TENANT,
        pack_ids=(),
        required_keys=(PolicyKey("capacity.headroom"),),
    )
    missing = PolicyResolver().resolve(missing_plan, (), NOW)
    assert [issue.code for issue in missing.issues] == ["POLICY_REQUIRED"]

    first_id = PolicyPackId("policy.first")
    second_id = PolicyPackId("policy.second")
    first = pack(
        first_id.value,
        Decimal("0.10"),
        (PolicyOverride(second_id, (PolicyKey("capacity.headroom"),)),),
    )
    second = pack(
        second_id.value,
        Decimal("0.20"),
        (PolicyOverride(first_id, (PolicyKey("capacity.headroom"),)),),
    )
    cycle_plan = PolicyResolutionPlan(
        tenant_id=TENANT,
        pack_ids=(first_id, second_id),
        required_keys=(PolicyKey("capacity.headroom"),),
    )
    cycle = PolicyResolver().resolve(cycle_plan, (first, second), NOW)
    assert [issue.code for issue in cycle.issues] == ["POLICY_OVERRIDE_CYCLE"]
