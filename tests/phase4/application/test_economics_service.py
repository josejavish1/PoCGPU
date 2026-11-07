import pytest
from decimal import Decimal

from src.pocgpu.application.economics_service import (
    AllocationPolicy,
    CapacityResult,
    EconomicsService,
    EconomicsServiceError,
    InMemoryAllocationPolicyAdapter,
    InMemoryMarginPolicyAdapter,
    MarginPolicy,
    TcoResult,
    BlockerCode,
)


@pytest.fixture
def sample_tenant_id() -> str:
    """Provides a sample tenant ID."""
    return "tenant-123"


@pytest.fixture
def sample_gpu_type() -> str:
    """Provides a sample GPU type."""
    return "NVIDIA-A100"


@pytest.fixture
def sample_region() -> str:
    """Provides a sample region."""
    return "us-east-1"


@pytest.fixture
def sample_capacity_result(
    sample_tenant_id: str, sample_gpu_type: str, sample_region: str
) -> CapacityResult:
    """Provides a sample CapacityResult."""
    return CapacityResult(
        tenant_id=sample_tenant_id,
        gpu_type=sample_gpu_type,
        region=sample_region,
        volume=Decimal("10"),
        total_capacity_cost=Decimal("10000.00"),
    )


@pytest.fixture
def sample_tco_result(
    sample_tenant_id: str, sample_gpu_type: str, sample_region: str
) -> TcoResult:
    """Provides a sample TcoResult."""
    return TcoResult(
        tenant_id=sample_tenant_id,
        gpu_type=sample_gpu_type,
        region=sample_region,
        volume=Decimal("10"),
        total_cost_of_ownership=Decimal("5000.00"),
    )


@pytest.fixture
def sample_allocation_policy(
    sample_tenant_id: str, sample_gpu_type: str, sample_region: str
) -> AllocationPolicy:
    """Provides a sample AllocationPolicy."""
    return AllocationPolicy(
        tenant_id=sample_tenant_id,
        gpu_type=sample_gpu_type,
        region=sample_region,
        allocation_rate=Decimal("0.10"),  # 10% overhead
    )


@pytest.fixture
def sample_margin_policy(
    sample_tenant_id: str, sample_gpu_type: str, sample_region: str
) -> MarginPolicy:
    """Provides a sample MarginPolicy."""
    return MarginPolicy(
        tenant_id=sample_tenant_id,
        gpu_type=sample_gpu_type,
        region=sample_region,
        margin_rate=Decimal("0.20"),  # 20% margin
    )


@pytest.fixture
def allocation_policy_adapter() -> InMemoryAllocationPolicyAdapter:
    """Provides an in-memory allocation policy adapter."""
    return InMemoryAllocationPolicyAdapter()


@pytest.fixture
def margin_policy_adapter() -> InMemoryMarginPolicyAdapter:
    """Provides an in-memory margin policy adapter."""
    return InMemoryMarginPolicyAdapter()


@pytest.fixture
def economics_service(
    allocation_policy_adapter: InMemoryAllocationPolicyAdapter,
    margin_policy_adapter: InMemoryMarginPolicyAdapter,
) -> EconomicsService:
    """Provides an EconomicsService instance with in-memory adapters."""
    return EconomicsService(allocation_policy_port=allocation_policy_adapter, margin_policy_port=margin_policy_adapter)


class TestEconomicsService:
    """Test suite for the EconomicsService."""

    def test_certify_economics_success(
        self,
        economics_service: EconomicsService,
        allocation_policy_adapter: InMemoryAllocationPolicyAdapter,
        margin_policy_adapter: InMemoryMarginPolicyAdapter,
        sample_tenant_id: str,
        sample_gpu_type: str,
        sample_region: str,
        sample_capacity_result: CapacityResult,
        sample_tco_result: TcoResult,
        sample_allocation_policy: AllocationPolicy,
        sample_margin_policy: MarginPolicy,
    ) -> None:
        """Tests successful certification of economics and pricing."""
        allocation_policy_adapter.add_policy(sample_allocation_policy)
        margin_policy_adapter.add_policy(sample_margin_policy)

        unit_economics, pricing = economics_service.certify_economics(
            sample_tenant_id, sample_capacity_result, sample_tco_result
        )

        # Expected calculations
        expected_allocated_overhead_cost = sample_tco_result.total_cost_of_ownership * sample_allocation_policy.allocation_rate
        expected_total_cost_for_unit_economics = sample_tco_result.total_cost_of_ownership + expected_allocated_overhead_cost
        expected_unit_cost = expected_total_cost_for_unit_economics / sample_tco_result.volume
        expected_unit_price_before_margin = expected_unit_cost
        expected_unit_price_with_margin = expected_unit_price_before_margin * (Decimal('1') + sample_margin_policy.margin_rate)

        # Assert UnitEconomicsResult
        assert unit_economics.tenant_id == sample_tenant_id
        assert unit_economics.gpu_type == sample_gpu_type
        assert unit_economics.region == sample_region
        assert unit_economics.volume == sample_tco_result.volume
        assert unit_economics.total_cost_of_ownership == sample_tco_result.total_cost_of_ownership
        assert unit_economics.allocated_overhead_cost == expected_allocated_overhead_cost
        assert unit_economics.unit_cost == expected_unit_cost

        # Assert PricingResult
        assert pricing.tenant_id == sample_tenant_id
        assert pricing.gpu_type == sample_gpu_type
        assert pricing.region == sample_region
        assert pricing.volume == sample_tco_result.volume
        assert pricing.unit_cost == expected_unit_cost
        assert pricing.unit_price_before_margin == expected_unit_price_before_margin
        assert pricing.unit_price_with_margin == expected_unit_price_with_margin

    def test_certify_economics_missing_allocation_policy(
        self,
        economics_service: EconomicsService,
        margin_policy_adapter: InMemoryMarginPolicyAdapter,
        sample_tenant_id: str,
        sample_capacity_result: CapacityResult,
        sample_tco_result: TcoResult,
        sample_margin_policy: MarginPolicy,
    ) -> None:
        """Tests that certification fails if allocation policy is missing."""
        margin_policy_adapter.add_policy(sample_margin_policy)

        with pytest.raises(EconomicsServiceError) as exc_info:
            economics_service.certify_economics(sample_tenant_id, sample_capacity_result, sample_tco_result)

        assert exc_info.value.blocker_code == BlockerCode.POLICY_REQUIRED
        assert "Allocation policy required" in exc_info.value.message

    def test_certify_economics_missing_margin_policy(
        self,
        economics_service: EconomicsService,
        allocation_policy_adapter: InMemoryAllocationPolicyAdapter,
        sample_tenant_id: str,
        sample_capacity_result: CapacityResult,
        sample_tco_result: TcoResult,
        sample_allocation_policy: AllocationPolicy,
    ) -> None:
        """Tests that certification fails if margin policy is missing."""
        allocation_policy_adapter.add_policy(sample_allocation_policy)

        with pytest.raises(EconomicsServiceError) as exc_info:
            economics_service.certify_economics(sample_tenant_id, sample_capacity_result, sample_tco_result)

        assert exc_info.value.blocker_code == BlockerCode.POLICY_REQUIRED
        assert "Margin policy required" in exc_info.value.message

    def test_certify_economics_boundary_mismatch_gpu_type(
        self,
        economics_service: EconomicsService,
        allocation_policy_adapter: InMemoryAllocationPolicyAdapter,
        margin_policy_adapter: InMemoryMarginPolicyAdapter,
        sample_tenant_id: str,
        sample_capacity_result: CapacityResult,
        sample_tco_result: TcoResult,
        sample_allocation_policy: AllocationPolicy,
        sample_margin_policy: MarginPolicy,
    ) -> None:
        """Tests that certification fails on GPU type mismatch between results."""
        allocation_policy_adapter.add_policy(sample_allocation_policy)
        margin_policy_adapter.add_policy(sample_margin_policy)

        mismatched_tco_result = TcoResult(
            tenant_id=sample_tco_result.tenant_id,
            gpu_type="NVIDIA-V100",  # Mismatched GPU type
            region=sample_tco_result.region,
            volume=sample_tco_result.volume,
            total_cost_of_ownership=sample_tco_result.total_cost_of_ownership,
        )

        with pytest.raises(EconomicsServiceError) as exc_info:
            economics_service.certify_economics(sample_tenant_id, sample_capacity_result, mismatched_tco_result)

        assert exc_info.value.blocker_code == BlockerCode.BOUNDARY_MISMATCH
        assert "GPU type mismatch" in exc_info.value.message

    def test_certify_economics_boundary_mismatch_region(
        self,
        economics_service: EconomicsService,
        allocation_policy_adapter: InMemoryAllocationPolicyAdapter,
        margin_policy_adapter: InMemoryMarginPolicyAdapter,
        sample_tenant_id: str,
        sample_capacity_result: CapacityResult,
        sample_tco_result: TcoResult,
        sample_allocation_policy: AllocationPolicy,
        sample_margin_policy: MarginPolicy,
    ) -> None:
        """Tests that certification fails on region mismatch between results."""
        allocation_policy_adapter.add_policy(sample_allocation_policy)
        margin_policy_adapter.add_policy(sample_margin_policy)

        mismatched_tco_result = TcoResult(
            tenant_id=sample_tco_result.tenant_id,
            gpu_type=sample_tco_result.gpu_type,
            region="eu-west-1",  # Mismatched region
            volume=sample_tco_result.volume,
            total_cost_of_ownership=sample_tco_result.total_cost_of_ownership,
        )

        with pytest.raises(EconomicsServiceError) as exc_info:
            economics_service.certify_economics(sample_tenant_id, sample_capacity_result, mismatched_tco_result)

        assert exc_info.value.blocker_code == BlockerCode.BOUNDARY_MISMATCH
        assert "Region mismatch" in exc_info.value.message

    def test_certify_economics_boundary_mismatch_volume(
        self,
        economics_service: EconomicsService,
        allocation_policy_adapter: InMemoryAllocationPolicyAdapter,
        margin_policy_adapter: InMemoryMarginPolicyAdapter,
        sample_tenant_id: str,
        sample_capacity_result: CapacityResult,
        sample_tco_result: TcoResult,
        sample_allocation_policy: AllocationPolicy,
        sample_margin_policy: MarginPolicy,
    ) -> None:
        """Tests that certification fails on volume mismatch between results."""
        allocation_policy_adapter.add_policy(sample_allocation_policy)
        margin_policy_adapter.add_policy(sample_margin_policy)

        mismatched_tco_result = TcoResult(
            tenant_id=sample_tco_result.tenant_id,
            gpu_type=sample_tco_result.gpu_type,
            region=sample_tco_result.region,
            volume=Decimal("5"),  # Mismatched volume
            total_cost_of_ownership=sample_tco_result.total_cost_of_ownership,
        )

        with pytest.raises(EconomicsServiceError) as exc_info:
            economics_service.certify_economics(sample_tenant_id, sample_capacity_result, mismatched_tco_result)

        assert exc_info.value.blocker_code == BlockerCode.BOUNDARY_MISMATCH
        assert "Volume mismatch" in exc_info.value.message

    def test_certify_economics_zero_volume(
        self,
        economics_service: EconomicsService,
        allocation_policy_adapter: InMemoryAllocationPolicyAdapter,
        margin_policy_adapter: InMemoryMarginPolicyAdapter,
        sample_tenant_id: str,
        sample_capacity_result: CapacityResult,
        sample_tco_result: TcoResult,
        sample_allocation_policy: AllocationPolicy,
        sample_margin_policy: MarginPolicy,
    ) -> None:
        """Tests that certification fails if TCO result has zero volume."""
        allocation_policy_adapter.add_policy(sample_allocation_policy)
        margin_policy_adapter.add_policy(sample_margin_policy)

        zero_volume_tco_result = TcoResult(
            tenant_id=sample_tco_result.tenant_id,
            gpu_type=sample_tco_result.gpu_type,
            region=sample_tco_result.region,
            volume=Decimal("0"),  # Zero volume
            total_cost_of_ownership=sample_tco_result.total_cost_of_ownership,
        )

        # To ensure ZERO_VOLUME is raised, capacity_result's volume must match
        # or the check order must prioritize ZERO_VOLUME.
        # The service code has been updated to prioritize ZERO_VOLUME.
        matching_capacity_result = CapacityResult(
            tenant_id=sample_capacity_result.tenant_id,
            gpu_type=sample_capacity_result.gpu_type,
            region=sample_capacity_result.region,
            volume=Decimal("0"), # Match volume for this specific test case
            total_capacity_cost=sample_capacity_result.total_capacity_cost
        )

        with pytest.raises(EconomicsServiceError) as exc_info:
            economics_service.certify_economics(sample_tenant_id, matching_capacity_result, zero_volume_tco_result)

        assert exc_info.value.blocker_code == BlockerCode.ZERO_VOLUME
        assert "Cannot certify economics for zero or negative volume" in exc_info.value.message

    def test_certify_economics_negative_volume(
        self,
        economics_service: EconomicsService,
        allocation_policy_adapter: InMemoryAllocationPolicyAdapter,
        margin_policy_adapter: InMemoryMarginPolicyAdapter,
        sample_tenant_id: str,
        sample_capacity_result: CapacityResult,
        sample_tco_result: TcoResult,
        sample_allocation_policy: AllocationPolicy,
        sample_margin_policy: MarginPolicy,
    ) -> None:
        """Tests that certification fails if TCO result has negative volume."""
        allocation_policy_adapter.add_policy(sample_allocation_policy)
        margin_policy_adapter.add_policy(sample_margin_policy)

        negative_volume_tco_result = TcoResult(
            tenant_id=sample_tco_result.tenant_id,
            gpu_type=sample_tco_result.gpu_type,
            region=sample_tco_result.region,
            volume=Decimal("-1"),  # Negative volume
            total_cost_of_ownership=sample_tco_result.total_cost_of_ownership,
        )

        # To ensure ZERO_VOLUME is raised, capacity_result's volume must match
        # or the check order must prioritize ZERO_VOLUME.
        # The service code has been updated to prioritize ZERO_VOLUME.
        matching_capacity_result = CapacityResult(
            tenant_id=sample_capacity_result.tenant_id,
            gpu_type=sample_capacity_result.gpu_type,
            region=sample_capacity_result.region,
            volume=Decimal("-1"), # Match volume for this specific test case
            total_capacity_cost=sample_capacity_result.total_capacity_cost
        )

        with pytest.raises(EconomicsServiceError) as exc_info:
            economics_service.certify_economics(sample_tenant_id, matching_capacity_result, negative_volume_tco_result)

        assert exc_info.value.blocker_code == BlockerCode.ZERO_VOLUME
        assert "Cannot certify economics for zero or negative volume" in exc_info.value.message

    def test_certify_economics_input_required_different_tenant_id_capacity_result(
        self,
        economics_service: EconomicsService,
        allocation_policy_adapter: InMemoryAllocationPolicyAdapter,
        margin_policy_adapter: InMemoryMarginPolicyAdapter,
        sample_tenant_id: str,
        sample_capacity_result: CapacityResult,
        sample_tco_result: TcoResult,
        sample_allocation_policy: AllocationPolicy,
        sample_margin_policy: MarginPolicy,
    ) -> None:
        """Tests that certification fails if CapacityResult has a different tenant ID."""
        allocation_policy_adapter.add_policy(sample_allocation_policy)
        margin_policy_adapter.add_policy(sample_margin_policy)

        mismatched_capacity_result = CapacityResult(
            tenant_id="another-tenant",
            gpu_type=sample_capacity_result.gpu_type,
            region=sample_capacity_result.region,
            volume=sample_capacity_result.volume,
            total_capacity_cost=sample_capacity_result.total_capacity_cost,
        )

        with pytest.raises(EconomicsServiceError) as exc_info:
            economics_service.certify_economics(sample_tenant_id, mismatched_capacity_result, sample_tco_result)

        assert exc_info.value.blocker_code == BlockerCode.INPUT_REQUIRED
        assert "CapacityResult tenant ID 'another-tenant' does not match requested tenant ID" in exc_info.value.message

    def test_certify_economics_input_required_different_tenant_id_tco_result(
        self,
        economics_service: EconomicsService,
        allocation_policy_adapter: InMemoryAllocationPolicyAdapter,
        margin_policy_adapter: InMemoryMarginPolicyAdapter,
        sample_tenant_id: str,
        sample_capacity_result: CapacityResult,
        sample_tco_result: TcoResult,
        sample_allocation_policy: AllocationPolicy,
        sample_margin_policy: MarginPolicy,
    ) -> None:
        """Tests that certification fails if TcoResult has a different tenant ID."""
        allocation_policy_adapter.add_policy(sample_allocation_policy)
        margin_policy_adapter.add_policy(sample_margin_policy)

        mismatched_tco_result = TcoResult(
            tenant_id="another-tenant",
            gpu_type=sample_tco_result.gpu_type,
            region=sample_tco_result.region,
            volume=sample_tco_result.volume,
            total_cost_of_ownership=sample_tco_result.total_cost_of_ownership,
        )

        with pytest.raises(EconomicsServiceError) as exc_info:
            economics_service.certify_economics(sample_tenant_id, sample_capacity_result, mismatched_tco_result)

        assert exc_info.value.blocker_code == BlockerCode.INPUT_REQUIRED
        assert "TcoResult tenant ID 'another-tenant' does not match requested tenant ID" in exc_info.value.message


class TestInMemoryAdapters:
    """Test suite for in-memory policy adapters, focusing on tenant scope."""

    def test_in_memory_allocation_policy_adapter_tenant_scope(
        self, allocation_policy_adapter: InMemoryAllocationPolicyAdapter
    ) -> None:
        """Tests that the allocation policy adapter respects tenant scope."""
        policy_tenant_a = AllocationPolicy(
            tenant_id="tenant-A", gpu_type="GPU-X", region="region-1", allocation_rate=Decimal("0.1")
        )
        policy_tenant_b = AllocationPolicy(
            tenant_id="tenant-B", gpu_type="GPU-X", region="region-1", allocation_rate=Decimal("0.2")
        )

        allocation_policy_adapter.add_policy(policy_tenant_a)
        # Do NOT add policy_tenant_b yet, to test isolation properly

        # Retrieve for tenant-A (should succeed)
        retrieved_policy_a = allocation_policy_adapter.get_policy("tenant-A", "GPU-X", "region-1")
        assert retrieved_policy_a == policy_tenant_a

        # Attempt to retrieve tenant-A's policy parameters using tenant-B's ID (should fail, as tenant-B has no policy for these params)
        retrieved_policy_a_wrong_tenant_id_lookup = allocation_policy_adapter.get_policy("tenant-B", "GPU-X", "region-1")
        assert retrieved_policy_a_wrong_tenant_id_lookup is None

        # Now add policy for tenant-B
        allocation_policy_adapter.add_policy(policy_tenant_b)

        # Retrieve for tenant-B (should succeed)
        retrieved_policy_b = allocation_policy_adapter.get_policy("tenant-B", "GPU-X", "region-1")
        assert retrieved_policy_b == policy_tenant_b

        # Verify tenant-A's policy is still only accessible by tenant-A
        assert allocation_policy_adapter.get_policy("tenant-A", "GPU-X", "region-1") == policy_tenant_a

        # Attempt to retrieve non-existent policy
        non_existent_policy = allocation_policy_adapter.get_policy("tenant-C", "GPU-X", "region-1")
        assert non_existent_policy is None

    def test_in_memory_margin_policy_adapter_tenant_scope(
        self, margin_policy_adapter: InMemoryMarginPolicyAdapter
    ) -> None:
        """Tests that the margin policy adapter respects tenant scope."""
        policy_tenant_a = MarginPolicy(
            tenant_id="tenant-A", gpu_type="GPU-X", region="region-1", margin_rate=Decimal("0.15")
        )
        policy_tenant_b = MarginPolicy(
            tenant_id="tenant-B", gpu_type="GPU-X", region="region-1", margin_rate=Decimal("0.25")
        )

        margin_policy_adapter.add_policy(policy_tenant_a)
        # Do NOT add policy_tenant_b yet, to test isolation properly

        # Retrieve for tenant-A (should succeed)
        retrieved_policy_a = margin_policy_adapter.get_policy("tenant-A", "GPU-X", "region-1")
        assert retrieved_policy_a == policy_tenant_a

        # Attempt to retrieve tenant-A's policy parameters using tenant-B's ID (should fail, as tenant-B has no policy for these params)
        retrieved_policy_a_wrong_tenant_id_lookup = margin_policy_adapter.get_policy("tenant-B", "GPU-X", "region-1")
        assert retrieved_policy_a_wrong_tenant_id_lookup is None

        # Now add policy for tenant-B
        margin_policy_adapter.add_policy(policy_tenant_b)

        # Retrieve for tenant-B (should succeed)
        retrieved_policy_b = margin_policy_adapter.get_policy("tenant-B", "GPU-X", "region-1")
        assert retrieved_policy_b == policy_tenant_b

        # Verify tenant-A's policy is still only accessible by tenant-A
        assert margin_policy_adapter.get_policy("tenant-A", "GPU-X", "region-1") == policy_tenant_a

        # Attempt to retrieve non-existent policy
        non_existent_policy = margin_policy_adapter.get_policy("tenant-C", "GPU-X", "region-1")
        assert non_existent_policy is None
