import datetime
import json
import pytest
from uuid import UUID, uuid4

from src.pocgpu.application.tco_service import (
    TcoCalculationService,
    InMemoryEvidenceRepository,
    InMemoryPolicyRepository,
    InMemoryCapacityReferenceRepository,
    EvidenceBlock,
    Policy,
    CapacityReference,
    TcoCertificationStatus,
    TenantId,
    UtcInstant,
    TcoResult,
)

# --- Fixtures ---
@pytest.fixture
def tenant_id() -> TenantId:
    """Provides a consistent tenant ID for tests."""
    return uuid4()

@pytest.fixture
def other_tenant_id() -> TenantId:
    """Provides a different tenant ID for scope tests."""
    return uuid4()

@pytest.fixture
def utc_now() -> UtcInstant:
    """Provides a consistent UTC timestamp for tests."""
    return datetime.datetime.now(datetime.timezone.utc)

@pytest.fixture
def evidence_repo() -> InMemoryEvidenceRepository:
    """Provides an in-memory evidence repository."""
    return InMemoryEvidenceRepository()

@pytest.fixture
def policy_repo() -> InMemoryPolicyRepository:
    """Provides an in-memory policy repository."""
    return InMemoryPolicyRepository()

@pytest.fixture
def capacity_ref_repo() -> InMemoryCapacityReferenceRepository:
    """Provides an in-memory capacity reference repository."""
    return InMemoryCapacityReferenceRepository()

@pytest.fixture
def tco_service(
    evidence_repo: InMemoryEvidenceRepository,
    policy_repo: InMemoryPolicyRepository,
    capacity_ref_repo: InMemoryCapacityReferenceRepository,
) -> TcoCalculationService:
    """Provides a TcoCalculationService instance with in-memory repositories."""
    return TcoCalculationService(evidence_repo, policy_repo, capacity_ref_repo)

# --- Helper Functions for Test Data ---
def create_evidence_block(
    tenant_id: TenantId,
    is_stale: bool = False,
    cost_factor: float = 10.0,
    captured_at: UtcInstant | None = None,
    id: UUID | None = None,
) -> EvidenceBlock:
    return EvidenceBlock(
        id=id if id else uuid4(),
        tenant_id=tenant_id,
        data={"description": "Test evidence", "cost_factor": cost_factor},
        version="1.0",
        is_stale=is_stale,
        captured_at=captured_at if captured_at else datetime.datetime.now(datetime.timezone.utc),
    )

def create_policy(
    tenant_id: TenantId,
    is_resolved: bool = True,
    policy_impact: float = 5.0,
    id: UUID | None = None,
) -> Policy:
    return Policy(
        id=id if id else uuid4(),
        tenant_id=tenant_id,
        name="Test Policy",
        definition={"rule": "some_rule", "policy_impact": policy_impact},
        version="1.0",
        is_resolved=is_resolved,
    )

def create_capacity_reference(
    tenant_id: TenantId,
    capacity_cost: float = 20.0,
    id: UUID | None = None,
) -> CapacityReference:
    return CapacityReference(
        id=id if id else uuid4(),
        tenant_id=tenant_id,
        reference_data={"type": "GPU", "capacity_cost": capacity_cost},
        version="1.0",
    )

# --- Test Cases ---

class TestTcoCalculationService:

    def test_successful_certification(
        self,
        tco_service: TcoCalculationService,
        evidence_repo: InMemoryEvidenceRepository,
        policy_repo: InMemoryPolicyRepository,
        capacity_ref_repo: InMemoryCapacityReferenceRepository,
        tenant_id: TenantId,
        utc_now: UtcInstant,
    ) -> None:
        """
        Tests a scenario where all inputs are valid and TCO is certified.
        """
        evidence = create_evidence_block(tenant_id, captured_at=utc_now)
        policy = create_policy(tenant_id)
        capacity_ref = create_capacity_reference(tenant_id)

        evidence_repo.add_evidence_block(evidence)
        policy_repo.add_policy(policy)
        capacity_ref_repo.add_capacity_reference(capacity_ref)

        result = tco_service.calculate_tco(
            tenant_id=tenant_id,
            evidence_ids=[evidence.id],
            policy_ids=[policy.id],
            capacity_ref_ids=[capacity_ref.id],
            assumed_power_cost_present=False,
            critical_facts_required=True,
        )

        assert result.certification_status == TcoCertificationStatus.CERTIFIED
        assert result.calculated_value > 0.0
        assert isinstance(result.provenance_hash, str)
        assert len(result.provenance_hash) == 64
        assert isinstance(result.json_bytes, bytes)
        assert json.loads(result.json_bytes.decode("utf-8")) is not None

    def test_input_required_due_to_missing_critical_facts(
        self,
        tco_service: TcoCalculationService,
        policy_repo: InMemoryPolicyRepository,
        capacity_ref_repo: InMemoryCapacityReferenceRepository,
        tenant_id: TenantId,
    ) -> None:
        """
        Tests that INPUT_REQUIRED status is returned when critical facts are missing.
        """
        policy = create_policy(tenant_id)
        capacity_ref = create_capacity_reference(tenant_id)
        policy_repo.add_policy(policy)
        capacity_ref_repo.add_capacity_reference(capacity_ref)

        result = tco_service.calculate_tco(
            tenant_id=tenant_id,
            evidence_ids=[],
            policy_ids=[policy.id],
            capacity_ref_ids=[capacity_ref.id],
            critical_facts_required=True,
        )

        assert result.certification_status == TcoCertificationStatus.INPUT_REQUIRED
        assert result.calculated_value == 0.0

    def test_input_required_can_be_bypassed_if_not_required(
        self,
        tco_service: TcoCalculationService,
        policy_repo: InMemoryPolicyRepository,
        capacity_ref_repo: InMemoryCapacityReferenceRepository,
        tenant_id: TenantId,
    ) -> None:
        """
        Tests that INPUT_REQUIRED status is not returned if critical facts are not required.
        """
        policy = create_policy(tenant_id)
        capacity_ref = create_capacity_reference(tenant_id)
        policy_repo.add_policy(policy)
        capacity_ref_repo.add_capacity_reference(capacity_ref)

        result = tco_service.calculate_tco(
            tenant_id=tenant_id,
            evidence_ids=[],
            policy_ids=[policy.id],
            capacity_ref_ids=[capacity_ref.id],
            critical_facts_required=False,
        )

        assert result.certification_status == TcoCertificationStatus.CERTIFIED
        assert result.calculated_value > 0.0

    def test_policy_required_due_to_unresolved_policies(
        self,
        tco_service: TcoCalculationService,
        evidence_repo: InMemoryEvidenceRepository,
        policy_repo: InMemoryPolicyRepository,
        capacity_ref_repo: InMemoryCapacityReferenceRepository,
        tenant_id: TenantId,
        utc_now: UtcInstant,
    ) -> None:
        """
        Tests that POLICY_REQUIRED status is returned when policies are unresolved.
        """
        evidence = create_evidence_block(tenant_id, captured_at=utc_now)
        unresolved_policy = create_policy(tenant_id, is_resolved=False)
        capacity_ref = create_capacity_reference(tenant_id)

        evidence_repo.add_evidence_block(evidence)
        policy_repo.add_policy(unresolved_policy)
        capacity_ref_repo.add_capacity_reference(capacity_ref)

        result = tco_service.calculate_tco(
            tenant_id=tenant_id,
            evidence_ids=[evidence.id],
            policy_ids=[unresolved_policy.id],
            capacity_ref_ids=[capacity_ref.id],
        )

        assert result.certification_status == TcoCertificationStatus.POLICY_REQUIRED
        assert result.calculated_value == 0.0

    def test_stale_evidence_blocks_certification(
        self,
        tco_service: TcoCalculationService,
        evidence_repo: InMemoryEvidenceRepository,
        policy_repo: InMemoryPolicyRepository,
        capacity_ref_repo: InMemoryCapacityReferenceRepository,
        tenant_id: TenantId,
        utc_now: UtcInstant,
    ) -> None:
        """
        Tests that STALE_EVIDENCE status is returned when evidence blocks are stale.
        """
        stale_evidence = create_evidence_block(tenant_id, is_stale=True, captured_at=utc_now)
        policy = create_policy(tenant_id)
        capacity_ref = create_capacity_reference(tenant_id)

        evidence_repo.add_evidence_block(stale_evidence)
        policy_repo.add_policy(policy)
        capacity_ref_repo.add_capacity_reference(capacity_ref)

        result = tco_service.calculate_tco(
            tenant_id=tenant_id,
            evidence_ids=[stale_evidence.id],
            policy_ids=[policy.id],
            capacity_ref_ids=[capacity_ref.id],
        )

        assert result.certification_status == TcoCertificationStatus.STALE_EVIDENCE
        assert result.calculated_value > 0.0

    def test_assumption_based_status(
        self,
        tco_service: TcoCalculationService,
        evidence_repo: InMemoryEvidenceRepository,
        policy_repo: InMemoryPolicyRepository,
        capacity_ref_repo: InMemoryCapacityReferenceRepository,
        tenant_id: TenantId,
        utc_now: UtcInstant,
    ) -> None:
        """
        Tests that ASSUMPTION_BASED status is returned when assumed power/cost inputs are present.
        """
        evidence = create_evidence_block(tenant_id, captured_at=utc_now)
        policy = create_policy(tenant_id)
        capacity_ref = create_capacity_reference(tenant_id)

        evidence_repo.add_evidence_block(evidence)
        policy_repo.add_policy(policy)
        capacity_ref_repo.add_capacity_reference(capacity_ref)

        result = tco_service.calculate_tco(
            tenant_id=tenant_id,
            evidence_ids=[evidence.id],
            policy_ids=[policy.id],
            capacity_ref_ids=[capacity_ref.id],
            assumed_power_cost_present=True,
        )

        assert result.certification_status == TcoCertificationStatus.ASSUMPTION_BASED
        assert result.calculated_value > 0.0

    def test_tenant_scope_enforcement(
        self,
        tco_service: TcoCalculationService,
        evidence_repo: InMemoryEvidenceRepository,
        policy_repo: InMemoryPolicyRepository,
        capacity_ref_repo: InMemoryCapacityReferenceRepository,
        tenant_id: TenantId,
        other_tenant_id: TenantId,
        utc_now: UtcInstant,
    ) -> None:
        """
        Tests that the service correctly enforces tenant scope, preventing access to other tenants' data.
        """
        evidence_t1 = create_evidence_block(tenant_id, captured_at=utc_now)
        policy_t1 = create_policy(tenant_id)
        capacity_ref_t1 = create_capacity_reference(tenant_id)
        evidence_repo.add_evidence_block(evidence_t1)
        policy_repo.add_policy(policy_t1)
        capacity_ref_repo.add_capacity_reference(capacity_ref_t1)

        evidence_t2 = create_evidence_block(other_tenant_id, captured_at=utc_now)
        policy_t2 = create_policy(other_tenant_id)
        capacity_ref_t2 = create_capacity_reference(other_tenant_id)
        evidence_repo.add_evidence_block(evidence_t2)
        policy_repo.add_policy(policy_t2)
        capacity_ref_repo.add_capacity_reference(capacity_ref_t2)

        result = tco_service.calculate_tco(
            tenant_id=tenant_id,
            evidence_ids=[evidence_t1.id, evidence_t2.id],
            policy_ids=[policy_t1.id, policy_t2.id],
            capacity_ref_ids=[capacity_ref_t1.id, capacity_ref_t2.id],
            critical_facts_required=True,
        )

        assert result.certification_status == TcoCertificationStatus.CERTIFIED
        assert result.calculated_value == round(100.0 + 10.0 + 5.0 + 20.0, 2)

        result_only_other_tenant_data = tco_service.calculate_tco(
            tenant_id=tenant_id,
            evidence_ids=[evidence_t2.id],
            policy_ids=[policy_t2.id],
            capacity_ref_ids=[capacity_ref_t2.id],
            critical_facts_required=True,
        )
        assert result_only_other_tenant_data.certification_status == TcoCertificationStatus.INPUT_REQUIRED
        assert result_only_other_tenant_data.calculated_value == 0.0

    def test_deterministic_output_identical_inputs(
        self,
        tco_service: TcoCalculationService,
        evidence_repo: InMemoryEvidenceRepository,
        policy_repo: InMemoryPolicyRepository,
        capacity_ref_repo: InMemoryCapacityReferenceRepository,
        tenant_id: TenantId,
        utc_now: UtcInstant,
    ) -> None:
        """
        Tests that identical immutable inputs and policy versions produce identical
        canonical TcoResult structures, deterministic JSON serialization bytes,
        and SHA-256 provenance hashes.
        """
        evidence_id = uuid4()
        policy_id = uuid4()
        capacity_ref_id = uuid4()

        evidence_data = create_evidence_block(tenant_id, id=evidence_id, captured_at=utc_now)
        policy_data = create_policy(tenant_id, id=policy_id)
        capacity_ref_data = create_capacity_reference(tenant_id, id=capacity_ref_id)

        evidence_repo.add_evidence_block(evidence_data)
        policy_repo.add_policy(policy_data)
        capacity_ref_repo.add_capacity_reference(capacity_ref_data)

        result1 = tco_service.calculate_tco(
            tenant_id=tenant_id,
            evidence_ids=[evidence_id],
            policy_ids=[policy_id],
            capacity_ref_ids=[capacity_ref_id],
            assumed_power_cost_present=False,
            critical_facts_required=True,
        )

        result2 = tco_service.calculate_tco(
            tenant_id=tenant_id,
            evidence_ids=[evidence_id],
            policy_ids=[policy_id],
            capacity_ref_ids=[capacity_ref_id],
            assumed_power_cost_present=False,
            critical_facts_required=True,
        )

        assert result1.calculated_value == result2.calculated_value
        assert result1.certification_status == result2.certification_status
        assert result1.provenance_hash == result2.provenance_hash
        assert result1.json_bytes == result2.json_bytes

        json1 = json.loads(result1.json_bytes.decode("utf-8"))
        json2 = json.loads(result2.json_bytes.decode("utf-8"))
        assert json1 == json2

        different_evidence_id = uuid4()
        different_evidence_data = create_evidence_block(tenant_id, id=different_evidence_id, cost_factor=11.0, captured_at=utc_now)
        evidence_repo.add_evidence_block(different_evidence_data)

        result3 = tco_service.calculate_tco(
            tenant_id=tenant_id,
            evidence_ids=[different_evidence_id],
            policy_ids=[policy_id],
            capacity_ref_ids=[capacity_ref_id],
            assumed_power_cost_present=False,
            critical_facts_required=True,
        )

        assert result1.provenance_hash != result3.provenance_hash
        assert result1.json_bytes != result3.json_bytes
        assert result1.calculated_value != result3.calculated_value

    def test_multiple_certification_issues_priority(
        self,
        tco_service: TcoCalculationService,
        evidence_repo: InMemoryEvidenceRepository,
        policy_repo: InMemoryPolicyRepository,
        capacity_ref_repo: InMemoryCapacityReferenceRepository,
        tenant_id: TenantId,
        utc_now: UtcInstant,
    ) -> None:
        """
        Tests the priority of certification statuses.
        INPUT_REQUIRED > POLICY_REQUIRED > STALE_EVIDENCE > ASSUMPTION_BASED > CERTIFIED
        """
        unresolved_policy = create_policy(tenant_id, is_resolved=False)
        stale_evidence = create_evidence_block(tenant_id, is_stale=True, captured_at=utc_now)
        capacity_ref = create_capacity_reference(tenant_id)

        policy_repo.add_policy(unresolved_policy)
        evidence_repo.add_evidence_block(stale_evidence)
        capacity_ref_repo.add_capacity_reference(capacity_ref)

        result = tco_service.calculate_tco(
            tenant_id=tenant_id,
            evidence_ids=[],
            policy_ids=[unresolved_policy.id],
            capacity_ref_ids=[capacity_ref.id],
            assumed_power_cost_present=True,
            critical_facts_required=True,
        )
        assert result.certification_status == TcoCertificationStatus.INPUT_REQUIRED
        assert result.calculated_value == 0.0

        evidence = create_evidence_block(tenant_id, captured_at=utc_now)
        evidence_repo.add_evidence_block(evidence)

        result = tco_service.calculate_tco(
            tenant_id=tenant_id,
            evidence_ids=[evidence.id, stale_evidence.id],
            policy_ids=[unresolved_policy.id],
            capacity_ref_ids=[capacity_ref.id],
            assumed_power_cost_present=True,
            critical_facts_required=True,
        )
        assert result.certification_status == TcoCertificationStatus.POLICY_REQUIRED
        assert result.calculated_value == 0.0

        resolved_policy = create_policy(tenant_id, is_resolved=True)
        policy_repo.add_policy(resolved_policy)

        result = tco_service.calculate_tco(
            tenant_id=tenant_id,
            evidence_ids=[evidence.id, stale_evidence.id],
            policy_ids=[resolved_policy.id],
            capacity_ref_ids=[capacity_ref.id],
            assumed_power_cost_present=True,
            critical_facts_required=True,
        )
        assert result.certification_status == TcoCertificationStatus.STALE_EVIDENCE
        assert result.calculated_value > 0.0

        non_stale_evidence = create_evidence_block(tenant_id, is_stale=False, captured_at=utc_now)
        evidence_repo.add_evidence_block(non_stale_evidence)

        result = tco_service.calculate_tco(
            tenant_id=tenant_id,
            evidence_ids=[non_stale_evidence.id],
            policy_ids=[resolved_policy.id],
            capacity_ref_ids=[capacity_ref.id],
            assumed_power_cost_present=True,
            critical_facts_required=True,
        )
        assert result.certification_status == TcoCertificationStatus.ASSUMPTION_BASED
        assert result.calculated_value > 0.0

        result = tco_service.calculate_tco(
            tenant_id=tenant_id,
            evidence_ids=[non_stale_evidence.id],
            policy_ids=[resolved_policy.id],
            capacity_ref_ids=[capacity_ref.id],
            assumed_power_cost_present=False,
            critical_facts_required=True,
        )
        assert result.certification_status == TcoCertificationStatus.CERTIFIED
        assert result.calculated_value > 0.0
