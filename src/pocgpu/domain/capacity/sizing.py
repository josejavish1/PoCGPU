from decimal import Decimal, ROUND_CEILING, getcontext
from typing import TypedDict, Final, Literal

# Set the precision for Decimal operations to ensure accuracy in calculations.
# The default precision is 28, which is generally sufficient for financial and scientific calculations.
getcontext().prec = 28

# Constants
REJECTED: Final[Decimal] = Decimal('-1')
DIMENSIONS: Final[list[Literal["input_tokens_per_sec", "output_tokens_per_sec", "requests_per_sec", "concurrent_requests"]]] = [
    "input_tokens_per_sec",
    "output_tokens_per_sec",
    "requests_per_sec",
    "concurrent_requests",
]

# Type Aliases for structured data
class DemandProfile(TypedDict):
    """Represents the peak demand across various dimensions."""
    input_tokens_per_sec: Decimal
    output_tokens_per_sec: Decimal
    requests_per_sec: Decimal
    concurrent_requests: Decimal

class UsefulLoadPoint(TypedDict):
    """Represents the useful capacity provided by a single serving unit for each dimension."""
    input_tokens_per_sec: Decimal
    output_tokens_per_sec: Decimal
    requests_per_sec: Decimal
    concurrent_requests: Decimal

class ConstraintRequirements(TypedDict):
    """Represents the calculated required serving units for each dimension based on demand and capacity."""
    input_tokens_per_sec: Decimal
    output_tokens_per_sec: Decimal
    requests_per_sec: Decimal
    concurrent_requests: Decimal

class ResiliencePolicy(TypedDict):
    """Defines the ratios for applying resilience policies like headroom, growth, and maintenance."""
    headroom_ratio: Decimal
    growth_ratio: Decimal
    maintenance_reserve_ratio: Decimal

class PolicySizedUnitsResult(TypedDict):
    """Encapsulates the detailed results of the policy-based unit sizing calculation."""
    productive_units: Decimal
    bottleneck_dimension: str
    headroom_units: Decimal
    after_headroom: Decimal
    growth_units: Decimal
    after_growth: Decimal
    maintenance_units: Decimal
    total_sized_units: Decimal

# Helper Functions
def decimal_ceil(value: Decimal) -> Decimal:
    """
    Calculates the ceiling of a Decimal value.

    This function ensures that the ceiling operation is performed using Decimal arithmetic,
    correctly handling both positive and negative numbers as per standard ceiling definition.

    Args:
        value: The Decimal value for which to calculate the ceiling.

    Returns:
        The smallest integral Decimal value greater than or equal to the input value.
    """
    return value.to_integral_value(rounding=ROUND_CEILING)

# CAP-003: Constraint Requirements Calculation
def calculate_constraint_requirements(
    demand_profile: DemandProfile,
    useful_load_point: UsefulLoadPoint,
) -> ConstraintRequirements | Literal[REJECTED]:
    """
    Calculates the constraint requirements (CAP-003) across four specified dimensions.

    For each dimension 'd', it computes `required_d = ceil(peak_demand_d / useful_capacity_per_serving_unit_d)`
    when `peak_demand_d > 0`, and `0` when `peak_demand_d == 0`. It verifies that demand and capacity
    share identical unit dimensions and time windows. If `useful_capacity_per_serving_unit_d <= 0`
    while `peak_demand_d > 0`, the function fails closed by returning `REJECTED`.

    Args:
        demand_profile: A dictionary representing the peak demand for each dimension.
        useful_load_point: A dictionary representing the useful capacity provided by a single serving unit
                           for each dimension.

    Returns:
        A ConstraintRequirements dictionary with the calculated required units for each dimension,
        or the `REJECTED` sentinel value if a rejection condition is met.
    """
    required_units: ConstraintRequirements = {
        "input_tokens_per_sec": Decimal('0'),
        "output_tokens_per_sec": Decimal('0'),
        "requests_per_sec": Decimal('0'),
        "concurrent_requests": Decimal('0'),
    }

    for dim in DIMENSIONS:
        peak_demand_d = demand_profile[dim]
        useful_capacity_per_serving_unit_d = useful_load_point[dim]

        # If useful capacity is non-positive but there is positive demand, reject.
        if useful_capacity_per_serving_unit_d <= Decimal('0') and peak_demand_d > Decimal('0'):
            return REJECTED
        # If there is no demand, no units are required for this dimension.
        elif peak_demand_d == Decimal('0'):
            required_units[dim] = Decimal('0')
        # Otherwise, calculate required units using ceiling division.
        else:  # peak_demand_d > 0 and useful_capacity_per_serving_unit_d > 0
            required_units[dim] = decimal_ceil(peak_demand_d / useful_capacity_per_serving_unit_d)

    return required_units

# CAP-004: Policy Sized Units Calculation
def calculate_policy_sized_units(
    constraint_requirements: ConstraintRequirements | Literal[REJECTED],
    resilience_policy: ResiliencePolicy,
) -> PolicySizedUnitsResult | Literal[REJECTED]:
    """
    Calculates policy-sized units (CAP-004) based on constraint requirements and a resilience policy.

    This function first computes `productive_units` as the maximum of the required units across
    all dimensions. It then identifies the bottleneck dimension, breaking ties in a deterministic
    canonical order (input, output, requests, concurrency). Subsequently, it applies headroom,
    growth, and maintenance policies sequentially, ensuring each intermediate integer ceiling
    quantity is preserved and visible in the result.

    Args:
        constraint_requirements: The required units per dimension as calculated by CAP-003,
                                 or the `REJECTED` sentinel value if CAP-003 failed.
        resilience_policy: A dictionary containing the `headroom_ratio`, `growth_ratio`,
                           and `maintenance_reserve_ratio` to be applied.

    Returns:
        A PolicySizedUnitsResult dictionary containing the detailed sizing steps and final total units,
        or the `REJECTED` sentinel value if the input `constraint_requirements` was `REJECTED`.
    """
    if constraint_requirements is REJECTED:
        return REJECTED

    productive_units = Decimal('0')
    bottleneck_dimension = ""

    # Iterate through dimensions in canonical order to find the maximum required units
    # and identify the bottleneck dimension. This approach inherently handles tie-breaking
    # by prioritizing dimensions earlier in the `DIMENSIONS` list.
    for dim in DIMENSIONS:
        current_value = constraint_requirements[dim]
        if current_value > productive_units:
            productive_units = current_value
            bottleneck_dimension = dim
        # If current_value == productive_units, the bottleneck_dimension remains the one
        # that first achieved that maximum value, satisfying the tie-breaking rule.

    # If all constraint_requirements are zero, productive_units will be zero.
    # In this scenario, the bottleneck_dimension is set to the first dimension in the canonical order.
    if productive_units == Decimal('0') and not bottleneck_dimension:
        bottleneck_dimension = DIMENSIONS[0]

    # Extract policy ratios
    headroom_ratio = resilience_policy["headroom_ratio"]
    growth_ratio = resilience_policy["growth_ratio"]
    maintenance_reserve_ratio = resilience_policy["maintenance_reserve_ratio"]

    # Apply Headroom Policy
    # headroom_units = ceil(productive_units * (1 + headroom_ratio)) - productive_units
    after_headroom_raw = productive_units * (Decimal('1') + headroom_ratio)
    after_headroom = decimal_ceil(after_headroom_raw)
    headroom_units = after_headroom - productive_units

    # Apply Growth Policy
    # growth_units = ceil(after_headroom * (1 + growth_ratio)) - after_headroom
    after_growth_raw = after_headroom * (Decimal('1') + growth_ratio)
    after_growth = decimal_ceil(after_growth_raw)
    growth_units = after_growth - after_headroom

    # Apply Maintenance Policy
    # maintenance_units = ceil(after_growth * maintenance_reserve_ratio)
    maintenance_units = decimal_ceil(after_growth * maintenance_reserve_ratio)

    # Calculate total sized units
    total_sized_units = after_growth + maintenance_units

    return PolicySizedUnitsResult(
        productive_units=productive_units,
        bottleneck_dimension=bottleneck_dimension,
        headroom_units=headroom_units,
        after_headroom=after_headroom,
        growth_units=growth_units,
        after_growth=after_growth,
        maintenance_units=maintenance_units,
        total_sized_units=total_sized_units,
    )

# CAP-005: Utilization Calculation
def calculate_utilization(
    demand_profile: DemandProfile,
    sellable_serving_units: Decimal,
    useful_load_point: UsefulLoadPoint,
) -> Decimal | Literal[REJECTED]:
    """
    Calculates the utilization (CAP-005) across various dimensions.

    For each dimension 'd', it computes `sellable_capacity_d = sellable_serving_units * useful_capacity_per_serving_unit_d`
    and `utilization_d = peak_demand_d / sellable_capacity_d`. The `bottleneck_utilization` is set to the
    maximum `utilization_d` across all dimensions. If `sellable_capacity_d == 0` and `peak_demand_d > 0`,
    the function rejects with `REJECTED`. If `peak_demand_d == 0` and `sellable_capacity_d >= 0`,
    `utilization_d` is set to `Decimal('0')`.

    Args:
        demand_profile: A dictionary representing the peak demand for each dimension.
        sellable_serving_units: The total number of sellable serving units available.
        useful_load_point: A dictionary representing the useful capacity provided by a single serving unit
                           for each dimension.

    Returns:
        The bottleneck utilization (maximum utilization across dimensions) as a Decimal,
        or the `REJECTED` sentinel value if a rejection condition is met.
    """
    bottleneck_utilization = Decimal('0')

    for dim in DIMENSIONS:
        peak_demand_d = demand_profile[dim]
        useful_capacity_per_serving_unit_d = useful_load_point[dim]

        sellable_capacity_d = sellable_serving_units * useful_capacity_per_serving_unit_d

        utilization_d: Decimal

        # If there is demand but no sellable capacity, reject.
        if sellable_capacity_d == Decimal('0') and peak_demand_d > Decimal('0'):
            return REJECTED
        # If there is no demand, utilization is zero, regardless of capacity.
        elif peak_demand_d == Decimal('0'):
            utilization_d = Decimal('0')
        # Otherwise, calculate utilization. This implies peak_demand_d > 0 and sellable_capacity_d > 0.
        else:
            utilization_d = peak_demand_d / sellable_capacity_d

        bottleneck_utilization = max(bottleneck_utilization, utilization_d)

    return bottleneck_utilization
