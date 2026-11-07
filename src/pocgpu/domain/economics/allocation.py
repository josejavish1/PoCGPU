from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime, timezone
from typing import Protocol, TypeAlias, Literal

# --- Type Aliases ---
UtcInstant: TypeAlias = datetime
CostPoolDimension: TypeAlias = Literal[
    "input_tokens_cost",
    "output_tokens_cost",
    "requests_cost",
    "capacity_units_cost",
    "blended_cost",
    "reserved_resilience_cost",
    "idle_capacity_cost"
]

# --- Exceptions ---
class AllocationError(Exception):
    """Base exception for allocation-related errors."""
    pass

class IdentityMismatchError(AllocationError):
    """Raised when cost and volume inputs have mismatched identities."""
    pass

class PolicyRequiredError(AllocationError):
    """
    Raised when an explicit causal allocation policy is required but missing
    or insufficient for the requested allocation.
    """
    pass

class AllocationConservationError(AllocationError):
    """
    Raised when the conservation of value invariant is violated during allocation.
    """
    pass

# --- Domain Models ---
@dataclass(frozen=True)
class CostVolumeIdentity:
    """
    Represents the unique identity for cost and volume inputs, ensuring compatibility.
    """
    service_id: str
    workload_id: str
    currency: str
    period: UtcInstant

    def __post_init__(self):
        """
        Validates that the period is a timezone-aware UtcInstant.
        """
        if not isinstance(self.period, datetime) or self.period.tzinfo is None:
            raise ValueError("Period must be a timezone-aware UtcInstant.")

@dataclass(frozen=True)
class CostInput:
    """
    Represents the total cost of ownership (TCO) for a specific identity.
    """
    identity: CostVolumeIdentity
    total_tco_amount: Decimal

    def __post_init__(self):
        """
        Validates the total_tco_amount.
        """
        if not isinstance(self.total_tco_amount, Decimal):
            raise TypeError("total_tco_amount must be a Decimal.")
        if self.total_tco_amount < Decimal("0.00"):
            raise ValueError("total_tco_amount cannot be negative.")

@dataclass(frozen=True)
class VolumeInput:
    """
    Represents the volume data and informational dimensions for a specific identity.
    """
    identity: CostVolumeIdentity
    input_tokens: int
    output_tokens: int
    requests: int
    capacity_units: int

    def __post_init__(self):
        """
        Validates that all volume metrics are non-negative integers.
        """
        if not all(isinstance(x, int) and x >= 0 for x in [self.input_tokens, self.output_tokens, self.requests, self.capacity_units]):
            raise ValueError("All volume metrics must be non-negative integers.")

@dataclass(frozen=True)
class AllocationResult:
    """
    Represents the outcome of an allocation, detailing amounts distributed
    across cost pools and any residual.
    """
    allocated_amounts: dict[str, Decimal]
    residual_amount: Decimal
    total_cost_pool_amount: Decimal # The original total amount that was to be allocated

    def __post_init__(self):
        """
        Validates types and enforces the conservation of value invariant.
        """
        if not isinstance(self.allocated_amounts, dict):
            raise TypeError("allocated_amounts must be a dictionary.")
        if not all(isinstance(k, str) and isinstance(v, Decimal) for k, v in self.allocated_amounts.items()):
            raise TypeError("allocated_amounts dictionary must have string keys and Decimal values.")
        if not isinstance(self.residual_amount, Decimal):
            raise TypeError("residual_amount must be a Decimal.")
        if not isinstance(self.total_cost_pool_amount, Decimal):
            raise TypeError("total_cost_pool_amount must be a Decimal.")

        sum_allocated = sum(self.allocated_amounts.values(), Decimal("0.00"))
        if sum_allocated + self.residual_amount != self.total_cost_pool_amount:
            raise AllocationConservationError(
                f"Conservation of value invariant violated. "
                f"Sum allocated ({sum_allocated}) + residual ({self.residual_amount}) "
                f"!= total ({self.total_cost_pool_amount}). Delta: "
                f"{self.total_cost_pool_amount - (sum_allocated + self.residual_amount)}"
            )

# --- Allocation Policy Protocol ---
class AllocationPolicy(Protocol):
    """
    Protocol for defining how total TCO is allocated across various cost pools
    and informational dimensions.
    """
    @property
    def can_separate_token_costs(self) -> bool:
        """
        Indicates if this policy is capable of explicitly allocating separate
        input and output token costs.
        """
        ...

    def allocate(self, total_tco_amount: Decimal, volume_data: VolumeInput) -> AllocationResult:
        """
        Allocates the total TCO amount based on the policy's rules and volume data.

        Args:
            total_tco_amount: The total cost of ownership to be allocated.
            volume_data: Informational dimensions and volumes for allocation.

        Returns:
            An AllocationResult detailing the distribution.
        """
        ...

# --- Concrete Allocation Policies ---
@dataclass(frozen=True)
class BlendedInfrastructurePolicy:
    """
    An allocation policy that treats all infrastructure cost as blended,
    prohibiting inference of separate input/output token costs.
    """
    @property
    def can_separate_token_costs(self) -> bool:
        """
        Returns False as this policy does not separate token costs.
        """
        return False

    def allocate(self, total_tco_amount: Decimal, volume_data: VolumeInput) -> AllocationResult:
        """
        Allocates the total TCO amount to a single 'blended_cost' pool.
        """
        allocated_amounts = {"blended_cost": total_tco_amount}
        residual_amount = Decimal("0.00") # This policy allocates everything to blended_cost
        return AllocationResult(
            allocated_amounts=allocated_amounts,
            residual_amount=residual_amount,
            total_cost_pool_amount=total_tco_amount
        )

@dataclass(frozen=True)
class TokenBasedAllocationPolicy:
    """
    An allocation policy that explicitly allocates costs based on input and output tokens,
    and a residual for other costs. This policy satisfies the requirement for
    explicit causal allocation for token costs.
    """
    input_token_cost_rate: Decimal # e.g., cost per input token
    output_token_cost_rate: Decimal # e.g., cost per output token
    # Future: Add fields for reserved resilience and idle capacity if this policy governs them.

    def __post_init__(self):
        """
        Validates that token cost rates are non-negative Decimals.
        """
        if not isinstance(self.input_token_cost_rate, Decimal) or self.input_token_cost_rate < Decimal("0.00"):
            raise ValueError("input_token_cost_rate must be a non-negative Decimal.")
        if not isinstance(self.output_token_cost_rate, Decimal) or self.output_token_cost_rate < Decimal("0.00"):
            raise ValueError("output_token_cost_rate must be a non-negative Decimal.")

    @property
    def can_separate_token_costs(self) -> bool:
        """
        Returns True as this policy explicitly separates token costs.
        """
        return True

    def allocate(self, total_tco_amount: Decimal, volume_data: VolumeInput) -> AllocationResult:
        """
        Allocates TCO based on explicit token cost rates.
        """
        input_cost = self.input_token_cost_rate * Decimal(volume_data.input_tokens)
        output_cost = self.output_token_cost_rate * Decimal(volume_data.output_tokens)

        allocated_amounts = {
            "input_tokens_cost": input_cost,
            "output_tokens_cost": output_cost
        }

        total_allocated_by_policy = input_cost + output_cost
        residual_amount = total_tco_amount - total_allocated_by_policy

        # AllocationResult's __post_init__ will enforce conservation of value.
        return AllocationResult(
            allocated_amounts=allocated_amounts,
            residual_amount=residual_amount,
            total_cost_pool_amount=total_tco_amount
        )

# --- Main Allocator ---
class CostPoolAllocator:
    """
    Orchestrates deterministic cost pool allocation and reconciliation.
    """
    def allocate_tco(
        self,
        cost_input: CostInput,
        volume_input: VolumeInput,
        policy: AllocationPolicy,
        require_separate_token_costs: bool = False
    ) -> AllocationResult:
        """
        Allocates total TCO across declared cost pools based on an approved policy.

        Verifies identity compatibility, applies the allocation policy, and
        enforces the conservation of value invariant.

        Args:
            cost_input: The total cost of ownership to be allocated.
            volume_input: The volume data and informational dimensions.
            policy: The explicit, approved allocation policy to use.
            require_separate_token_costs: If True, an explicit policy capable of
                                         separating input/output token costs is required.

        Returns:
            An AllocationResult detailing the distribution.

        Raises:
            IdentityMismatchError: If cost and volume inputs do not share identical identities.
            PolicyRequiredError: If `require_separate_token_costs` is True but the
                                 provided policy cannot separate token costs.
            AllocationConservationError: If the policy fails to conserve value
                                         (checked by AllocationResult's constructor).
        """
        # 1. Identity Verification
        if cost_input.identity != volume_input.identity:
            raise IdentityMismatchError(
                f"Cost and volume input identities mismatch. "
                f"Cost ID: {cost_input.identity}, Volume ID: {volume_input.identity}"
            )

        # 2. Policy Capability Check for Token Costs
        if require_separate_token_costs and not policy.can_separate_token_costs:
            raise PolicyRequiredError(
                "An explicit causal allocation policy is required to infer separate "
                "input and output token costs from blended infrastructure cost. "
                "The provided policy does not support this."
            )

        # 3. Policy Application
        # The AllocationResult's __post_init__ will enforce conservation of value.
        result = policy.allocate(cost_input.total_tco_amount, volume_input)

        return result
