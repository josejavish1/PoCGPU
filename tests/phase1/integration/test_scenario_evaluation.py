"""End-to-end foundation evaluation with explicit reference adapters."""

from __future__ import annotations

from datetime import UTC, datetime

from pocgpu.adapters.in_memory import (
    FixedClock,
    InMemoryGovernedRecordRepository,
    InMemoryPolicyRepository,
    InMemorySnapshotRepository,
    SequenceIdentityProvider,
)
from pocgpu.application.policy_resolution import PolicyResolver
from pocgpu.application.scenario_evaluation import ScenarioEvaluationService
from pocgpu.domain.identifiers import (
    EngineId,
    OrganizationId,
    PolicyKey,
    PolicyPackId,
    RecordId,
    RecordRevision,
    RoleId,
    ScenarioId,
    SchemaId,
    SemanticVersion,
    SnapshotId,
    TenantId,
)
from pocgpu.domain.policies import PolicyPack, PolicyResolutionPlan, PolicySetting
from pocgpu.domain.provenance import (
    ApprovalState,
    EvidenceClass,
    GovernedRecord,
    ProvenanceMetadata,
    QualityStatus,
    RecordOwner,
)
from pocgpu.domain.results import ResultState
from pocgpu.domain.scenarios import OutputDomain, ScenarioDraft
from pocgpu.domain.time import UtcInstant, ValidityInterval

TENANT = TenantId("tenant.synthetic")
NOW = UtcInstant(datetime(2026, 11, 4, 8, 0, tzinfo=UTC))


def metadata(record_id: str, evidence_class: EvidenceClass) -> ProvenanceMetadata:
    return ProvenanceMetadata(
        tenant_id=TENANT,
        record_id=RecordId(record_id),
        schema_id=SchemaId("schema.synthetic"),
        schema_version=SemanticVersion("1.0.0"),
        revision=RecordRevision(1),
        evidence_class=evidence_class,
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


def scenario(domains: tuple[OutputDomain, ...]) -> ScenarioDraft:
    return ScenarioDraft(
        scenario_id=ScenarioId("scenario.synthetic"),
        tenant_id=TENANT,
        organization_id=OrganizationId("org.synthetic"),
        revision=RecordRevision(1),
        schema_id=SchemaId("schema.scenario"),
        schema_version=SemanticVersion("1.0.0"),
        engine_id=EngineId("engine.canonical"),
        engine_version=SemanticVersion("0.1.0"),
        input_record_ids=(RecordId("record.input"),),
        evidence_record_ids=(),
        accepted_assumption_record_ids=(),
        policy_resolution_plan=PolicyResolutionPlan(
            tenant_id=TENANT,
            pack_ids=(PolicyPackId("policy.foundation"),),
            required_keys=(PolicyKey("foundation.mode"),),
        ),
        requested_domains=domains,
        created_at=NOW,
    )


def service(
    input_records: tuple[GovernedRecord[object], ...],
    policy_value: str = "explicit",
) -> tuple[ScenarioEvaluationService, InMemorySnapshotRepository]:
    policy = PolicyPack(
        pack_id=PolicyPackId("policy.foundation"),
        tenant_id=TENANT,
        version=SemanticVersion("1.0.0"),
        settings=(
            PolicySetting(
                PolicyKey("foundation.mode"),
                SchemaId("schema.identifier"),
                policy_value,
            ),
        ),
        overrides=(),
    )
    policy_record = GovernedRecord(metadata("record.policy", EvidenceClass.CONFIGURED), policy)
    snapshots = InMemorySnapshotRepository(())
    evaluator = ScenarioEvaluationService(
        clock=FixedClock(NOW),
        identity_provider=SequenceIdentityProvider((SnapshotId("snapshot.synthetic"),)),
        record_repository=InMemoryGovernedRecordRepository(input_records),
        policy_repository=InMemoryPolicyRepository((policy_record,)),
        snapshot_repository=snapshots,
        policy_resolver=PolicyResolver(),
    )
    return evaluator, snapshots


def test_foundation_scenario_produces_valid_replayable_snapshot() -> None:
    input_record: GovernedRecord[object] = GovernedRecord(
        metadata("record.input", EvidenceClass.CONFIGURED), "synthetic-input"
    )
    evaluator, snapshots = service((input_record,))

    result = evaluator.evaluate(scenario((OutputDomain.FOUNDATION,)))

    assert result.state is ResultState.VALID
    assert result.issues == ()
    stored_snapshot = snapshots.get(TENANT, SnapshotId("snapshot.synthetic"))
    assert stored_snapshot is not None
    assert result.snapshot_hash == stored_snapshot.content_hash
    assert len(stored_snapshot.records) == 2


def test_policy_content_is_part_of_replay_identity() -> None:
    input_record: GovernedRecord[object] = GovernedRecord(
        metadata("record.input", EvidenceClass.CONFIGURED), "synthetic-input"
    )
    first, _ = service((input_record,), policy_value="first")
    second, _ = service((input_record,), policy_value="second")

    first_result = first.evaluate(scenario((OutputDomain.FOUNDATION,)))
    second_result = second.evaluate(scenario((OutputDomain.FOUNDATION,)))

    assert first_result.snapshot_hash != second_result.snapshot_hash


def test_unsupported_calculation_domain_is_rejected_without_numeric_output() -> None:
    input_record: GovernedRecord[object] = GovernedRecord(
        metadata("record.input", EvidenceClass.CONFIGURED), "synthetic-input"
    )
    evaluator, _ = service((input_record,))

    result = evaluator.evaluate(scenario((OutputDomain.CAPACITY,)))

    assert result.state is ResultState.REJECTED
    assert [item.code for item in result.issues] == ["OUTPUT_DOMAIN_UNAVAILABLE"]
    assert result.sections == ()


def test_missing_input_fails_closed_without_creating_zero_value() -> None:
    evaluator, _ = service(())

    result = evaluator.evaluate(scenario((OutputDomain.FOUNDATION,)))

    assert result.state is ResultState.INPUT_REQUIRED
    assert [item.code for item in result.issues] == ["INPUT_RECORD_REQUIRED"]
    assert result.sections == ()
