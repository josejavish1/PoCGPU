import pytest
from decimal import Decimal
from datetime import datetime, timezone
from dataclasses import dataclass
from src.pocgpu.domain.economics.allocation import (
    CostVolumeIdentity,
    CostInput,
    VolumeInput,
    AllocationResult,
    BlendedInfrastructurePolicy,
    TokenBasedAllocationPolicy,
    AllocationPolicy,
    CostPoolAllocator,
    IdentityMismatchError,
    PolicyRequiredError,
    AllocationConservationError,
    AllocationError,
    UtcInstant
)

# --- Fixtures ---
@pytest.fixture
def utc_now() -> UtcInstant:
    """Provides a timezone-aware UtcInstant."""
    return datetime.now(timezone.utc).replace(microsecond=0)

@pytest.fixture
def common_identity(utc_now: UtcInstant) -> CostVolumeIdentity:
    """Provides a common CostVolumeIdentity for compatible inputs."""
    return CostVolumeIdentity(
        service_id="service-alpha",
        workload_id="workload-123",
        currency="USD",
        period=utc_now
    )

@pytest.fixture
def mismatched_identity(utc_now: UtcInstant) -> CostVolumeIdentity:
    """Provides a CostVolumeIdentity with a mismatched workload_id."""
    return CostVolumeIdentity(
        service_id="service-alpha",
        workload_id="workload-456", # Mismatched
        currency="USD",
        period=utc_now
    )

@pytest.fixture
def cost_input_fixture(common_identity: CostVolumeIdentity) -> CostInput:
    """Provides a standard CostInput."""
    return CostInput(
        identity=common_identity,
        total_tco_amount=Decimal("1000.00")
    )

@pytest.fixture
def volume_input_fixture(common_identity: CostVolumeIdentity) -> VolumeInput:
    """Provides a standard VolumeInput."""
    return VolumeInput(
        identity=common_identity,
        input_tokens=10000,
        output_tokens=20000,
        requests=500,
        capacity_units=100
    )

@pytest.fixture
def mismatched_cost_input_fixture(mismatched_identity: CostVolumeIdentity) -> CostInput:
    """Provides a CostInput with a mismatched identity."""
    return CostInput(
        identity=mismatched_identity,
        total_tco_amount=Decimal("1000.00")
    )

@pytest.fixture
def blended_policy_fixture() -> BlendedInfrastructurePolicy:
    """Provides a BlendedInfrastructurePolicy instance."""
    return BlendedInfrastructurePolicy()

@pytest.fixture
def token_based_policy_fixture() -> TokenBasedAllocationPolicy:
    """Provides a TokenBasedAllocationPolicy instance."""
    return TokenBasedAllocationPolicy(
        input_token_cost_rate=Decimal("0.001"),
        output_token_cost_rate=Decimal("0.0005")
    )

@pytest.fixture
def cost_pool_allocator_fixture() -> CostPoolAllocator:
    """Provides a CostPoolAllocator instance."""
    return CostPoolAllocator()

# --- Tests for Domain Models ---
class TestCostVolumeIdentity:
    def test_equality_and_hash(self, utc_now: UtcInstant):
        id1 = CostVolumeIdentity("s1", "w1", "USD", utc_now)
        id2 = CostVolumeIdentity("s1", "w1", "USD", utc_now)
        id3 = CostVolumeIdentity("s2", "w1", "USD", utc_now)

        assert id1 == id2
        assert id1 != id3
        assert hash(id1) == hash(id2)
        assert hash(id1) != hash(id3)

    def test_invalid_period_raises_value_error(self):
        with pytest.raises(ValueError, match="Period must be a timezone-aware UtcInstant."):
            CostVolumeIdentity("s1", "w1", "USD", datetime.now()) # Naive datetime

class TestCostInput:
    def test_valid_cost_input(self, common_identity: CostVolumeIdentity):
        cost_input = CostInput(common_identity, Decimal("123.45"))
        assert cost_input.total_tco_amount == Decimal("123.45")

    def test_invalid_total_tco_amount_type_raises_type_error(self, common_identity: CostVolumeIdentity):
        with pytest.raises(TypeError, match="total_tco_amount must be a Decimal."):
            CostInput(common_identity, 100.00) # float instead of Decimal

    def test_negative_total_tco_amount_raises_value_error(self, common_identity: CostVolumeIdentity):
        with pytest.raises(ValueError, match="total_tco_amount cannot be negative."):
            CostInput(common_identity, Decimal("-10.00"))

class TestVolumeInput:
    def test_valid_volume_input(self, common_identity: CostVolumeIdentity):
        volume_input = VolumeInput(common_identity, 100, 200, 10, 5)
        assert volume_input.input_tokens == 100

    @pytest.mark.parametrize(
        "input_tokens, output_tokens, requests, capacity_units",
        [
            (-1, 100, 10, 5),
            (100, -1, 10, 5),
            (100, 100, -1, 5),
            (100, 100, 10, -1),
            (100, 100, 10, 5.5), # float
            ("100", 100, 10, 5) # string
        ]
    )
    def test_invalid_volume_metrics_raises_value_error(self, common_identity: CostVolumeIdentity,
                                                       input_tokens, output_tokens, requests, capacity_units):
        with pytest.raises(ValueError, match="All volume metrics must be non-negative integers."):
            VolumeInput(common_identity, input_tokens, output_tokens, requests, capacity_units)

class TestAllocationResult:
    def test_valid_allocation_result(self):
        allocated = {"cost_pool_a": Decimal("50.00"), "cost_pool_b": Decimal("30.00")}
        result = AllocationResult(allocated, Decimal("20.00"), Decimal("100.00"))
        assert result.residual_amount == Decimal("20.00")

    def test_allocation_conservation_violation_raises_error(self):
        allocated = {"cost_pool_a": Decimal("50.00"), "cost_pool_b": Decimal("30.00")}
        # Sum is 80, residual is 10, total is 100. Mismatch.
        with pytest.raises(AllocationConservationError, match=r"Conservation of value invariant violated."):
            AllocationResult(allocated, Decimal("10.00"), Decimal("100.00"))

    def test_allocation_conservation_exact_match(self):
        allocated = {"cost_pool_a": Decimal("50.00"), "cost_pool_b": Decimal("30.00")}
        result = AllocationResult(allocated, Decimal("20.00"), Decimal("100.00"))
        assert result.residual_amount == Decimal("20.00") # No error raised

    def test_allocation_conservation_with_zero_residual(self):
        allocated = {"cost_pool_a": Decimal("50.00"), "cost_pool_b": Decimal("50.00")}
        result = AllocationResult(allocated, Decimal("0.00"), Decimal("100.00"))
        assert result.residual_amount == Decimal("0.00") # No error raised

    def test_allocation_conservation_with_negative_residual_raises_error(self):
        allocated = {"cost_pool_a": Decimal("60.00"), "cost_pool_b": Decimal("50.00")}
        # Total 100, allocated 110, residual 0. Mismatch. (110 + 0 != 100)
        with pytest.raises(AllocationConservationError, match=r"Conservation of value invariant violated."):
            AllocationResult(allocated, Decimal("0.00"), Decimal("100.00"))

# --- Tests for Allocation Policies ---
class TestBlendedInfrastructurePolicy:
    def test_can_separate_token_costs(self, blended_policy_fixture: BlendedInfrastructurePolicy):
        assert not blended_policy_fixture.can_separate_token_costs

    def test_allocation(self, blended_policy_fixture: BlendedInfrastructurePolicy,
                        cost_input_fixture: CostInput, volume_input_fixture: VolumeInput):
        result = blended_policy_fixture.allocate(cost_input_fixture.total_tco_amount, volume_input_fixture)
        assert result.allocated_amounts == {"blended_cost": Decimal("1000.00")}
        assert result.residual_amount == Decimal("0.00")
        assert result.total_cost_pool_amount == Decimal("1000.00")

class TestTokenBasedAllocationPolicy:
    def test_can_separate_token_costs(self, token_based_policy_fixture: TokenBasedAllocationPolicy):
        assert token_based_policy_fixture.can_separate_token_costs

    def test_valid_rates(self):
        policy = TokenBasedAllocationPolicy(input_token_cost_rate=Decimal("0.01"), output_token_cost_rate=Decimal("0.005"))
        assert policy.input_token_cost_rate == Decimal("0.01")

    @pytest.mark.parametrize(
        "input_rate, output_rate",
        [
            (Decimal("-0.01"), Decimal("0.005")),
            (Decimal("0.01"), Decimal("-0.005")),
            (0.01, Decimal("0.005")), # float
            (Decimal("0.01"), "0.005") # string
        ]
    )
    def test_invalid_rates_raises_value_error(self, input_rate, output_rate):
        with pytest.raises((ValueError, TypeError), match=r"cost_rate must be a non-negative Decimal."):
            TokenBasedAllocationPolicy(input_token_cost_rate=input_rate, output_token_cost_rate=output_rate)

    def test_allocation_with_residual(self, token_based_policy_fixture: TokenBasedAllocationPolicy,
                                     cost_input_fixture: CostInput, volume_input_fixture: VolumeInput):
        # total_tco_amount = 1000.00
        # input_tokens = 10000, rate = 0.001 -> 10.00
        # output_tokens = 20000, rate = 0.0005 -> 10.00
        # Total allocated = 20.00
        # Residual = 1000.00 - 20.00 = 980.00
        result = token_based_policy_fixture.allocate(cost_input_fixture.total_tco_amount, volume_input_fixture)

        assert result.allocated_amounts == {
            "input_tokens_cost": Decimal("10.00"),
            "output_tokens_cost": Decimal("10.00")
        }
        assert result.residual_amount == Decimal("980.00")
        assert result.total_cost_pool_amount == Decimal("1000.00")

    def test_allocation_exact_fit(self, common_identity: CostVolumeIdentity):
        policy = TokenBasedAllocationPolicy(input_token_cost_rate=Decimal("0.05"), output_token_cost_rate=Decimal("0.025"))
        cost_input = CostInput(common_identity, Decimal("1000.00"))
        volume_input = VolumeInput(common_identity, input_tokens=10000, output_tokens=20000, requests=0, capacity_units=0)
        # input_cost = 10000 * 0.05 = 500.00
        # output_cost = 20000 * 0.025 = 500.00
        # Total allocated = 1000.00
        # Residual = 0.00
        result = policy.allocate(cost_input.total_tco_amount, volume_input)
        assert result.allocated_amounts == {
            "input_tokens_cost": Decimal("500.00"),
            "output_tokens_cost": Decimal("500.00")
        }
        assert result.residual_amount == Decimal("0.00")
        assert result.total_cost_pool_amount == Decimal("1000.00")

    def test_allocation_over_allocation_results_in_negative_residual_but_conserves_value(self, common_identity: CostVolumeIdentity):
        # Policy attempts to allocate more than total_tco_amount, resulting in a negative residual.
        # However, the AllocationResult's __post_init__ will confirm conservation.
        policy = TokenBasedAllocationPolicy(input_token_cost_rate=Decimal("0.1"), output_token_cost_rate=Decimal("0.1"))
        cost_input = CostInput(common_identity, Decimal("100.00"))
        volume_input = VolumeInput(common_identity, input_tokens=1000, output_tokens=1000, requests=0, capacity_units=0)
        # input_cost = 1000 * 0.1 = 100.00
        # output_cost = 1000 * 0.1 = 100.00
        # Total allocated by policy = 200.00
        # Residual calculated by policy = 100.00 - 200.00 = -100.00
        # AllocationResult will be (allocated=200, residual=-100, total=100) which conserves value.

        # No pytest.raises expected here, as conservation is maintained.
        result = policy.allocate(cost_input.total_tco_amount, volume_input)

        assert result.allocated_amounts == {
            "input_tokens_cost": Decimal("100.00"),
            "output_tokens_cost": Decimal("100.00")
        }
        assert result.residual_amount == Decimal("-100.00")
        assert result.total_cost_pool_amount == Decimal("100.00")

# --- Tests for CostPoolAllocator ---
class TestCostPoolAllocator:
    def test_allocate_tco_success_blended_policy(self, cost_pool_allocator_fixture: CostPoolAllocator,
                                                 cost_input_fixture: CostInput, volume_input_fixture: VolumeInput,
                                                 blended_policy_fixture: BlendedInfrastructurePolicy):
        result = cost_pool_allocator_fixture.allocate_tco(
            cost_input=cost_input_fixture,
            volume_input=volume_input_fixture,
            policy=blended_policy_fixture,
            require_separate_token_costs=False
        )
        assert result.allocated_amounts == {"blended_cost": Decimal("1000.00")}
        assert result.residual_amount == Decimal("0.00")
        assert result.total_cost_pool_amount == Decimal("1000.00")

    def test_allocate_tco_success_token_based_policy(self, cost_pool_allocator_fixture: CostPoolAllocator,
                                                    cost_input_fixture: CostInput, volume_input_fixture: VolumeInput,
                                                    token_based_policy_fixture: TokenBasedAllocationPolicy):
        result = cost_pool_allocator_fixture.allocate_tco(
            cost_input=cost_input_fixture,
            volume_input=volume_input_fixture,
            policy=token_based_policy_fixture,
            require_separate_token_costs=True
        )
        assert result.allocated_amounts == {
            "input_tokens_cost": Decimal("10.00"),
            "output_tokens_cost": Decimal("10.00")
        }
        assert result.residual_amount == Decimal("980.00")
        assert result.total_cost_pool_amount == Decimal("1000.00")

    def test_allocate_tco_identity_mismatch_fails_closed(self, cost_pool_allocator_fixture: CostPoolAllocator,
                                                         mismatched_cost_input_fixture: CostInput,
                                                         volume_input_fixture: VolumeInput,
                                                         blended_policy_fixture: BlendedInfrastructurePolicy):
        with pytest.raises(IdentityMismatchError, match=r"Cost and volume input identities mismatch."):
            cost_pool_allocator_fixture.allocate_tco(
                cost_input=mismatched_cost_input_fixture,
                volume_input=volume_input_fixture,
                policy=blended_policy_fixture,
                require_separate_token_costs=False
            )

    def test_allocate_tco_policy_required_error_for_token_separation(self, cost_pool_allocator_fixture: CostPoolAllocator,
                                                                     cost_input_fixture: CostInput,
                                                                     volume_input_fixture: VolumeInput,
                                                                     blended_policy_fixture: BlendedInfrastructurePolicy):
        with pytest.raises(PolicyRequiredError, match=r"An explicit causal allocation policy is required to infer separate input and output token costs from blended infrastructure cost."):
            cost_pool_allocator_fixture.allocate_tco(
                cost_input=cost_input_fixture,
                volume_input=volume_input_fixture,
                policy=blended_policy_fixture,
                require_separate_token_costs=True # Requesting token separation with a blended policy
            )

    def test_allocate_tco_conservation_error_from_policy(self, cost_pool_allocator_fixture: CostPoolAllocator,
                                                         common_identity: CostVolumeIdentity):
        # Create a mock policy that returns an AllocationResult violating conservation
        @dataclass(frozen=True)
        class FaultyPolicy:
            @property
            def can_separate_token_costs(self) -> bool:
                return True # Doesn't matter for this test

            def allocate(self, total_tco_amount: Decimal, volume_data: VolumeInput) -> AllocationResult:
                # This result will violate conservation: 50+30+10 != 100
                return AllocationResult(
                    allocated_amounts={"faulty_pool_a": Decimal("50.00"), "faulty_pool_b": Decimal("30.00")},
                    residual_amount=Decimal("10.00"),
                    total_cost_pool_amount=Decimal("100.00")
                )

        faulty_policy = FaultyPolicy()
        cost_input = CostInput(common_identity, Decimal("100.00"))
        volume_input = VolumeInput(common_identity, 1, 1, 1, 1)

        with pytest.raises(AllocationConservationError, match=r"Conservation of value invariant violated."):
            cost_pool_allocator_fixture.allocate_tco(
                cost_input=cost_input,
                volume_input=volume_input,
                policy=faulty_policy,
                require_separate_token_costs=False
            )

    def test_allocate_tco_token_based_policy_not_requiring_separation(self, cost_pool_allocator_fixture: CostPoolAllocator,
                                                                      cost_input_fixture: CostInput,
                                                                      volume_input_fixture: VolumeInput,
                                                                      token_based_policy_fixture: TokenBasedAllocationPolicy):
        # A token-based policy can be used even if separation is not explicitly required,
        # as long as it provides a valid AllocationResult.
        result = cost_pool_allocator_fixture.allocate_tco(
            cost_input=cost_input_fixture,
            volume_input=volume_input_fixture,
            policy=token_based_policy_fixture,
            require_separate_token_costs=False # Not explicitly requiring, but policy provides it
        )
        assert result.allocated_amounts == {
            "input_tokens_cost": Decimal("10.00"),
            "output_tokens_cost": Decimal("10.00")
        }
        assert result.residual_amount == Decimal("980.00")
        assert result.total_cost_pool_amount == Decimal("1000.00")
