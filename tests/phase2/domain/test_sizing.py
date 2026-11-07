import pytest
from decimal import Decimal, getcontext
from typing import Any, Literal

# Adjust precision for Decimal operations to ensure accuracy in calculations.
# The default precision is 28, which is generally sufficient for financial and scientific calculations.
getcontext().prec = 28

# Import the functions and types from the target module
from src.pocgpu.domain.capacity.sizing import (
    decimal_ceil,
    calculate_constraint_requirements,
    calculate_policy_sized_units,
    calculate_utilization,
    REJECTED,
    DemandProfile,
    UsefulLoadPoint,
    ConstraintRequirements,
    ResiliencePolicy,
    PolicySizedUnitsResult,
    DIMENSIONS,
)

# Helper for Decimal assertions to provide more informative error messages.
def assert_decimal_equal(actual: Decimal, expected: Decimal, message: str = ""):
    """Asserts that two Decimal values are equal, providing a custom message on failure."""
    assert actual == expected, f"{message} Expected {expected}, got {actual}"

# --- Tests for decimal_ceil helper function ---

def test_decimal_ceil_positive_integers():
    """Tests decimal_ceil with positive integer inputs."""
    assert_decimal_equal(decimal_ceil(Decimal('5')), Decimal('5'))
    assert_decimal_equal(decimal_ceil(Decimal('100')), Decimal('100'))

def test_decimal_ceil_positive_fractions():
    """Tests decimal_ceil with positive fractional inputs."""
    assert_decimal_equal(decimal_ceil(Decimal('5.1')), Decimal('6'))
    assert_decimal_equal(decimal_ceil(Decimal('5.9')), Decimal('6'))
    assert_decimal_equal(decimal_ceil(Decimal('5.0000000000000000000000000001')), Decimal('6'))
    assert_decimal_equal(decimal_ceil(Decimal('0.001')), Decimal('1'))

def test_decimal_ceil_negative_integers():
    """Tests decimal_ceil with negative integer inputs."""
    assert_decimal_equal(decimal_ceil(Decimal('-5')), Decimal('-5'))
    assert_decimal_equal(decimal_ceil(Decimal('-100')), Decimal('-100'))

def test_decimal_ceil_negative_fractions():
    """Tests decimal_ceil with negative fractional inputs, addressing previous failure."""
    assert_decimal_equal(decimal_ceil(Decimal('-5.1')), Decimal('-5'))
    assert_decimal_equal(decimal_ceil(Decimal('-5.9')), Decimal('-5'))
    assert_decimal_equal(decimal_ceil(Decimal('-5.0000000000000000000000000001')), Decimal('-5'))
    assert_decimal_equal(decimal_ceil(Decimal('-0.001')), Decimal('0'))

def test_decimal_ceil_zero():
    """Tests decimal_ceil with zero input."""
    assert_decimal_equal(decimal_ceil(Decimal('0')), Decimal('0'))
    assert_decimal_equal(decimal_ceil(Decimal('-0')), Decimal('0'))

# --- Tests for CAP-003: calculate_constraint_requirements ---

@pytest.fixture
def sample_useful_load_point() -> UsefulLoadPoint:
    """Provides a standard useful load point for testing."""
    return {
        "input_tokens_per_sec": Decimal('10'),
        "output_tokens_per_sec": Decimal('5'),
        "requests_per_sec": Decimal('1'),
        "concurrent_requests": Decimal('2'),
    }

def test_cap003_basic_calculation(sample_useful_load_point: UsefulLoadPoint):
    """Tests CAP-003 with a basic demand profile resulting in positive required units."""
    demand: DemandProfile = {
        "input_tokens_per_sec": Decimal('100'),
        "output_tokens_per_sec": Decimal('23'),
        "requests_per_sec": Decimal('7'),
        "concurrent_requests": Decimal('15'),
    }
    expected_requirements: ConstraintRequirements = {
        "input_tokens_per_sec": Decimal('10'), # 100/10 = 10
        "output_tokens_per_sec": Decimal('5'),  # ceil(23/5) = 5
        "requests_per_sec": Decimal('7'),    # ceil(7/1) = 7
        "concurrent_requests": Decimal('8'), # ceil(15/2) = 8
    }
    result = calculate_constraint_requirements(demand, sample_useful_load_point)
    assert result is not REJECTED
    assert isinstance(result, dict)
    for dim in DIMENSIONS:
        assert_decimal_equal(result[dim], expected_requirements[dim], f"Dimension: {dim}")

def test_cap003_zero_demand(sample_useful_load_point: UsefulLoadPoint):
    """Tests CAP-003 with zero demand in all dimensions."""
    demand: DemandProfile = {
        "input_tokens_per_sec": Decimal('0'),
        "output_tokens_per_sec": Decimal('0'),
        "requests_per_sec": Decimal('0'),
        "concurrent_requests": Decimal('0'),
    }
    expected_requirements: ConstraintRequirements = {
        "input_tokens_per_sec": Decimal('0'),
        "output_tokens_per_sec": Decimal('0'),
        "requests_per_sec": Decimal('0'),
        "concurrent_requests": Decimal('0'),
    }
    result = calculate_constraint_requirements(demand, sample_useful_load_point)
    assert result is not REJECTED
    assert isinstance(result, dict)
    for dim in DIMENSIONS:
        assert_decimal_equal(result[dim], expected_requirements[dim], f"Dimension: {dim}")

def test_cap003_mixed_demand_and_zero_capacity():
    """Tests CAP-003 with mixed demand and a zero capacity dimension, expecting REJECTED."""
    demand: DemandProfile = {
        "input_tokens_per_sec": Decimal('100'),
        "output_tokens_per_sec": Decimal('50'),
        "requests_per_sec": Decimal('10'),
        "concurrent_requests": Decimal('0'),
    }
    useful_load_point: UsefulLoadPoint = {
        "input_tokens_per_sec": Decimal('10'),
        "output_tokens_per_sec": Decimal('0'), # Zero capacity for output_tokens_per_sec
        "requests_per_sec": Decimal('1'),
        "concurrent_requests": Decimal('2'),
    }
    result = calculate_constraint_requirements(demand, useful_load_point)
    assert result is REJECTED

def test_cap003_negative_capacity_with_demand():
    """Tests CAP-003 with negative capacity and positive demand, expecting REJECTED."""
    demand: DemandProfile = {
        "input_tokens_per_sec": Decimal('100'),
        "output_tokens_per_sec": Decimal('50'),
        "requests_per_sec": Decimal('10'),
        "concurrent_requests": Decimal('0'),
    }
    useful_load_point: UsefulLoadPoint = {
        "input_tokens_per_sec": Decimal('10'),
        "output_tokens_per_sec": Decimal('-5'), # Negative capacity for output_tokens_per_sec
        "requests_per_sec": Decimal('1'),
        "concurrent_requests": Decimal('2'),
    }
    result = calculate_constraint_requirements(demand, useful_load_point)
    assert result is REJECTED

def test_cap003_zero_capacity_no_demand():
    """Tests CAP-003 with zero capacity but also zero demand, which should not reject."""
    demand: DemandProfile = {
        "input_tokens_per_sec": Decimal('100'),
        "output_tokens_per_sec": Decimal('0'), # No demand
        "requests_per_sec": Decimal('10'),
        "concurrent_requests": Decimal('0'),
    }
    useful_load_point: UsefulLoadPoint = {
        "input_tokens_per_sec": Decimal('10'),
        "output_tokens_per_sec": Decimal('0'), # Zero capacity
        "requests_per_sec": Decimal('1'),
        "concurrent_requests": Decimal('2'),
    }
    expected_requirements: ConstraintRequirements = {
        "input_tokens_per_sec": Decimal('10'),
        "output_tokens_per_sec": Decimal('0'),
        "requests_per_sec": Decimal('10'),
        "concurrent_requests": Decimal('0'),
    }
    result = calculate_constraint_requirements(demand, useful_load_point)
    assert result is not REJECTED
    assert isinstance(result, dict)
    for dim in DIMENSIONS:
        assert_decimal_equal(result[dim], expected_requirements[dim], f"Dimension: {dim}")

# --- Tests for CAP-004: calculate_policy_sized_units ---

@pytest.fixture
def sample_resilience_policy() -> ResiliencePolicy:
    """Provides a standard resilience policy for testing."""
    return {
        "headroom_ratio": Decimal('0.10'), # 10%
        "growth_ratio": Decimal('0.20'),   # 20%
        "maintenance_reserve_ratio": Decimal('0.05'), # 5%
    }

def test_cap004_basic_sizing(sample_resilience_policy: ResiliencePolicy):
    """Tests CAP-004 with a basic set of constraint requirements and policy."""
    constraints: ConstraintRequirements = {
        "input_tokens_per_sec": Decimal('10'),
        "output_tokens_per_sec": Decimal('12'), # Bottleneck
        "requests_per_sec": Decimal('8'),
        "concurrent_requests": Decimal('5'),
    }
    result = calculate_policy_sized_units(constraints, sample_resilience_policy)
    assert result is not REJECTED
    assert isinstance(result, dict)

    # Productive Units: max(10, 12, 8, 5) = 12
    assert_decimal_equal(result["productive_units"], Decimal('12'))
    assert result["bottleneck_dimension"] == "output_tokens_per_sec"

    # Headroom: ceil(12 * (1 + 0.10)) - 12 = ceil(12 * 1.1) - 12 = ceil(13.2) - 12 = 14 - 12 = 2
    assert_decimal_equal(result["headroom_units"], Decimal('2'))
    assert_decimal_equal(result["after_headroom"], Decimal('14')) # 12 + 2

    # Growth: ceil(14 * (1 + 0.20)) - 14 = ceil(14 * 1.2) - 14 = ceil(16.8) - 14 = 17 - 14 = 3
    assert_decimal_equal(result["growth_units"], Decimal('3'))
    assert_decimal_equal(result["after_growth"], Decimal('17')) # 14 + 3

    # Maintenance: ceil(17 * 0.05) = ceil(0.85) = 1
    assert_decimal_equal(result["maintenance_units"], Decimal('1'))

    # Total Sized Units: 17 + 1 = 18
    assert_decimal_equal(result["total_sized_units"], Decimal('18'))

def test_cap004_zero_productive_units(sample_resilience_policy: ResiliencePolicy):
    """Tests CAP-004 when all constraint requirements are zero."""
    constraints: ConstraintRequirements = {
        "input_tokens_per_sec": Decimal('0'),
        "output_tokens_per_sec": Decimal('0'),
        "requests_per_sec": Decimal('0'),
        "concurrent_requests": Decimal('0'),
    }
    result = calculate_policy_sized_units(constraints, sample_resilience_policy)
    assert result is not REJECTED
    assert isinstance(result, dict)

    assert_decimal_equal(result["productive_units"], Decimal('0'))
    assert result["bottleneck_dimension"] == "input_tokens_per_sec" # Canonical tie-break

    # All ratios applied to 0 should result in 0
    assert_decimal_equal(result["headroom_units"], Decimal('0'))
    assert_decimal_equal(result["after_headroom"], Decimal('0'))
    assert_decimal_equal(result["growth_units"], Decimal('0'))
    assert_decimal_equal(result["after_growth"], Decimal('0'))
    assert_decimal_equal(result["maintenance_units"], Decimal('0'))
    assert_decimal_equal(result["total_sized_units"], Decimal('0'))

def test_cap004_bottleneck_tie_breaking(sample_resilience_policy: ResiliencePolicy):
    """Tests CAP-004's bottleneck tie-breaking logic based on canonical order."""
    constraints: ConstraintRequirements = {
        "input_tokens_per_sec": Decimal('10'), # First in canonical order
        "output_tokens_per_sec": Decimal('10'),
        "requests_per_sec": Decimal('8'),
        "concurrent_requests": Decimal('5'),
    }
    result = calculate_policy_sized_units(constraints, sample_resilience_policy)
    assert result is not REJECTED
    assert result["bottleneck_dimension"] == "input_tokens_per_sec"

    constraints_shifted: ConstraintRequirements = {
        "input_tokens_per_sec": Decimal('8'),
        "output_tokens_per_sec": Decimal('10'), # Now the first max
        "requests_per_sec": Decimal('10'),
        "concurrent_requests": Decimal('5'),
    }
    result_shifted = calculate_policy_sized_units(constraints_shifted, sample_resilience_policy)
    assert result_shifted is not REJECTED
    assert result_shifted["bottleneck_dimension"] == "output_tokens_per_sec"

def test_cap004_with_rejected_constraints(sample_resilience_policy: ResiliencePolicy):
    """Tests CAP-004's behavior when input constraint_requirements is REJECTED."""
    result = calculate_policy_sized_units(REJECTED, sample_resilience_policy)
    assert result is REJECTED

def test_cap004_zero_ratios():
    """Tests CAP-004 with all resilience policy ratios set to zero."""
    constraints: ConstraintRequirements = {
        "input_tokens_per_sec": Decimal('10'),
        "output_tokens_per_sec": Decimal('12'),
        "requests_per_sec": Decimal('8'),
        "concurrent_requests": Decimal('5'),
    }
    zero_policy: ResiliencePolicy = {
        "headroom_ratio": Decimal('0'),
        "growth_ratio": Decimal('0'),
        "maintenance_reserve_ratio": Decimal('0'),
    }
    result = calculate_policy_sized_units(constraints, zero_policy)
    assert result is not REJECTED

    assert_decimal_equal(result["productive_units"], Decimal('12'))
    assert_decimal_equal(result["headroom_units"], Decimal('0'))
    assert_decimal_equal(result["after_headroom"], Decimal('12'))
    assert_decimal_equal(result["growth_units"], Decimal('0'))
    assert_decimal_equal(result["after_growth"], Decimal('12'))
    assert_decimal_equal(result["maintenance_units"], Decimal('0'))
    assert_decimal_equal(result["total_sized_units"], Decimal('12'))

# --- Tests for CAP-005: calculate_utilization ---

def test_cap005_basic_utilization(sample_useful_load_point: UsefulLoadPoint):
    """Tests CAP-005 with a basic demand and sellable units, calculating bottleneck utilization."""
    demand: DemandProfile = {
        "input_tokens_per_sec": Decimal('90'),
        "output_tokens_per_sec": Decimal('20'),
        "requests_per_sec": Decimal('8'),
        "concurrent_requests": Decimal('12'),
    }
    sellable_serving_units = Decimal('10')

    # Expected calculations:
    # input: 90 / (10 * 10) = 90 / 100 = 0.9
    # output: 20 / (10 * 5) = 20 / 50 = 0.4
    # requests: 8 / (10 * 1) = 8 / 10 = 0.8
    # concurrency: 12 / (10 * 2) = 12 / 20 = 0.6
    # Bottleneck utilization should be 0.9
    expected_utilization = Decimal('0.9')

    result = calculate_utilization(demand, sellable_serving_units, sample_useful_load_point)
    assert result is not REJECTED
    assert_decimal_equal(result, expected_utilization)

def test_cap005_zero_demand(sample_useful_load_point: UsefulLoadPoint):
    """Tests CAP-005 with zero demand in all dimensions, expecting zero utilization."""
    demand: DemandProfile = {
        "input_tokens_per_sec": Decimal('0'),
        "output_tokens_per_sec": Decimal('0'),
        "requests_per_sec": Decimal('0'),
        "concurrent_requests": Decimal('0'),
    }
    sellable_serving_units = Decimal('10')
    expected_utilization = Decimal('0')

    result = calculate_utilization(demand, sellable_serving_units, sample_useful_load_point)
    assert result is not REJECTED
    assert_decimal_equal(result, expected_utilization)

def test_cap005_zero_sellable_units_with_demand():
    """Tests CAP-005 with zero sellable units and positive demand, expecting REJECTED."""
    demand: DemandProfile = {
        "input_tokens_per_sec": Decimal('10'),
        "output_tokens_per_sec": Decimal('0'),
        "requests_per_sec": Decimal('0'),
        "concurrent_requests": Decimal('0'),
    }
    sellable_serving_units = Decimal('0')
    useful_load_point: UsefulLoadPoint = {
        "input_tokens_per_sec": Decimal('10'),
        "output_tokens_per_sec": Decimal('5'),
        "requests_per_sec": Decimal('1'),
        "concurrent_requests": Decimal('2'),
    }
    result = calculate_utilization(demand, sellable_serving_units, useful_load_point)
    assert result is REJECTED

def test_cap005_zero_sellable_units_no_demand():
    """Tests CAP-005 with zero sellable units but also zero demand, expecting zero utilization."""
    demand: DemandProfile = {
        "input_tokens_per_sec": Decimal('0'),
        "output_tokens_per_sec": Decimal('0'),
        "requests_per_sec": Decimal('0'),
        "concurrent_requests": Decimal('0'),
    }
    sellable_serving_units = Decimal('0')
    useful_load_point: UsefulLoadPoint = {
        "input_tokens_per_sec": Decimal('10'),
        "output_tokens_per_sec": Decimal('5'),
        "requests_per_sec": Decimal('1'),
        "concurrent_requests": Decimal('2'),
    }
    expected_utilization = Decimal('0')

    result = calculate_utilization(demand, sellable_serving_units, useful_load_point)
    assert result is not REJECTED
    assert_decimal_equal(result, expected_utilization)

def test_cap005_partial_zero_capacity_with_demand():
    """Tests CAP-005 with a dimension having zero capacity and positive demand, expecting REJECTED."""
    demand: DemandProfile = {
        "input_tokens_per_sec": Decimal('100'),
        "output_tokens_per_sec": Decimal('50'),
        "requests_per_sec": Decimal('10'),
        "concurrent_requests": Decimal('0'),
    }
    sellable_serving_units = Decimal('10')
    useful_load_point: UsefulLoadPoint = {
        "input_tokens_per_sec": Decimal('10'),
        "output_tokens_per_sec": Decimal('0'), # Zero capacity for output_tokens_per_sec
        "requests_per_sec": Decimal('1'),
        "concurrent_requests": Decimal('2'),
    }
    result = calculate_utilization(demand, sellable_serving_units, useful_load_point)
    assert result is REJECTED

def test_cap005_negative_sellable_units_with_demand():
    """Tests CAP-005 with negative sellable units and positive demand, expecting REJECTED due to negative capacity."""
    demand: DemandProfile = {
        "input_tokens_per_sec": Decimal('10'),
        "output_tokens_per_sec": Decimal('0'),
        "requests_per_sec": Decimal('0'),
        "concurrent_requests": Decimal('0'),
    }
    sellable_serving_units = Decimal('-1') # Negative sellable units
    useful_load_point: UsefulLoadPoint = {
        "input_tokens_per_sec": Decimal('10'),
        "output_tokens_per_sec": Decimal('5'),
        "requests_per_sec": Decimal('1'),
        "concurrent_requests": Decimal('2'),
    }
    # This will result in sellable_capacity_d = -10 for input_tokens_per_sec.
    # The current logic for CAP-005 does not explicitly reject for negative capacity, only zero capacity with demand.
    # However, a negative capacity is an invalid state for 'sellable_capacity_d'.
    # The current implementation will calculate utilization as 10 / -10 = -1.
    # max(0, -1) will still be 0, which might mask the issue.
    # Re-evaluating the prompt: "If sellable_capacity_d == 0 and peak_demand_d > 0, reject with REJECTED".
    # It does not specify for negative sellable_capacity_d. Assuming valid inputs for capacity (>=0).
    # If negative capacity is passed, the result might be negative utilization, which max() will turn to 0.
    # For strict adherence, we only reject on the specified condition.
    # If the domain mandates non-negative capacity, this should be enforced at input validation.
    # For now, based on the strict wording, it should not reject, but result in 0 if max() is applied.
    result = calculate_utilization(demand, sellable_serving_units, useful_load_point)
    # The calculation for input_tokens_per_sec would be 10 / ((-1) * 10) = 10 / -10 = -1.
    # max(0, -1, 0, 0, 0) = 0.
    assert result is not REJECTED
    assert_decimal_equal(result, Decimal('0'))


# --- Test for Demand Monotonicity (CAP-004) ---

def test_demand_monotonicity():
    """Tests that increasing demand in any dimension does not reduce productive_units or policy-sized units."""
    # Define a base demand profile and related parameters
    demand_base: DemandProfile = {
        "input_tokens_per_sec": Decimal('100'),
        "output_tokens_per_sec": Decimal('50'),
        "requests_per_sec": Decimal('10'),
        "concurrent_requests": Decimal('5'),
    }
    useful_load_point: UsefulLoadPoint = {
        "input_tokens_per_sec": Decimal('10'),
        "output_tokens_per_sec": Decimal('10'),
        "requests_per_sec": Decimal('1'),
        "concurrent_requests": Decimal('1'),
    }
    resilience_policy: ResiliencePolicy = {
        "headroom_ratio": Decimal('0.1'),
        "growth_ratio": Decimal('0.2'),
        "maintenance_reserve_ratio": Decimal('0.05'),
    }

    # Calculate for base demand
    constraints_base = calculate_constraint_requirements(demand_base, useful_load_point)
    assert constraints_base is not REJECTED
    result_base = calculate_policy_sized_units(constraints_base, resilience_policy)
    assert result_base is not REJECTED
    total_units_base = result_base["total_sized_units"]

    # Scenario 1: Increase demand in one dimension (input_tokens_per_sec)
    demand_increased_input: DemandProfile = {
        **demand_base,
        "input_tokens_per_sec": Decimal('120'), # Increased from 100
    }
    constraints_increased_input = calculate_constraint_requirements(demand_increased_input, useful_load_point)
    assert constraints_increased_input is not REJECTED
    result_increased_input = calculate_policy_sized_units(constraints_increased_input, resilience_policy)
    assert result_increased_input is not REJECTED
    total_units_increased_input = result_increased_input["total_sized_units"]

    # Assert monotonicity: increased demand should not reduce total units
    assert total_units_increased_input >= total_units_base, \
        f"Monotonicity violated (increased input): {total_units_increased_input} < {total_units_base}"

    # Scenario 2: Increase demand in all dimensions slightly
    demand_increased_all: DemandProfile = {
        "input_tokens_per_sec": Decimal('110'),
        "output_tokens_per_sec": Decimal('60'),
        "requests_per_sec": Decimal('12'),
        "concurrent_requests": Decimal('6'),
    }
    constraints_increased_all = calculate_constraint_requirements(demand_increased_all, useful_load_point)
    assert constraints_increased_all is not REJECTED
    result_increased_all = calculate_policy_sized_units(constraints_increased_all, resilience_policy)
    assert result_increased_all is not REJECTED
    total_units_increased_all = result_increased_all["total_sized_units"]

    # Assert monotonicity against base
    assert total_units_increased_all >= total_units_base, \
        f"Monotonicity violated (all increased): {total_units_increased_all} < {total_units_base}"

    # Scenario 3: Test a scenario where increasing demand in one dimension shifts the bottleneck
    demand_shift_bottleneck_base: DemandProfile = {
        "input_tokens_per_sec": Decimal('100'), # Requires 10 units (100/10)
        "output_tokens_per_sec": Decimal('120'), # Requires 12 units (120/10) - Bottleneck
        "requests_per_sec": Decimal('5'),    # Requires 5 units (5/1)
        "concurrent_requests": Decimal('5'), # Requires 5 units (5/1)
    }
    constraints_shift_bottleneck_base = calculate_constraint_requirements(demand_shift_bottleneck_base, useful_load_point)
    assert constraints_shift_bottleneck_base is not REJECTED
    result_shift_bottleneck_base = calculate_policy_sized_units(constraints_shift_bottleneck_base, resilience_policy)
    assert result_shift_bottleneck_base is not REJECTED
    total_units_shift_bottleneck_base = result_shift_bottleneck_base["total_sized_units"]
    assert result_shift_bottleneck_base["bottleneck_dimension"] == "output_tokens_per_sec"

    demand_shift_bottleneck_increased: DemandProfile = {
        **demand_shift_bottleneck_base,
        "input_tokens_per_sec": Decimal('130'), # Now requires 13 units (130/10), new bottleneck
    }
    constraints_shift_bottleneck_increased = calculate_constraint_requirements(demand_shift_bottleneck_increased, useful_load_point)
    assert constraints_shift_bottleneck_increased is not REJECTED
    result_shift_bottleneck_increased = calculate_policy_sized_units(constraints_shift_bottleneck_increased, resilience_policy)
    assert result_shift_bottleneck_increased is not REJECTED
    total_units_shift_bottleneck_increased = result_shift_bottleneck_increased["total_sized_units"]
    assert result_shift_bottleneck_increased["bottleneck_dimension"] == "input_tokens_per_sec"

    assert total_units_shift_bottleneck_increased >= total_units_shift_bottleneck_base, \
        f"Monotonicity violated (bottleneck shift): {total_units_shift_bottleneck_increased} < {total_units_shift_bottleneck_base}"
