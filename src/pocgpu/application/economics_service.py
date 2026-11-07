from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Protocol, Dict, Optional


class BlockerCode(Enum):
    """Enumeration of specific blocker codes for service failures."""
    POLICY_REQUIRED = "POLICY_REQUIRED"
    INPUT_REQUIRED = "INPUT_REQUIRED"
    BOUNDARY_MISMATCH = "BOUNDARY_MISMATCH"
    ZERO_VOLUME = "ZERO_VOLUME"


@dataclass(frozen=True)
class EconomicsServiceError(Exception):
    """Custom exception for economics service failures, including a blocker code."""
    message: str
    blocker_code: BlockerCode


# --- Domain Models (Phase 2, 3, Policies, Results) ---

@dataclass(frozen=True)
class CapacityResult:
    """Represents the outcome of Phase 2 capacity calculations."""
    tenant_id: str
    gpu_type: str
    region: str
    volume: Decimal
    total_capacity_cost: Decimal


@dataclass(frozen=True)
class TcoResult:
    """Represents the outcome of Phase 3 Total Cost of Ownership calculations."""
    tenant_id: str
    gpu_type: str
    region: str
    volume: Decimal
    total_cost_of_ownership: Decimal


@dataclass(frozen=True)
class AllocationPolicy:
    """Defines a policy for cost allocation."""
    tenant_id: str
    gpu_type: str
    region: str
    allocation_rate: Decimal  # e.g., 0.10 for 10% overhead allocation


@dataclass(frozen=True)
class MarginPolicy:
    """Defines a policy for profit margin."""
    tenant_id: str
    gpu_type: str
    region: str
    margin_rate: Decimal  # e.g., 0.20 for 20% profit margin


@dataclass(frozen=True)
class UnitEconomicsResult:
    """Canonical object for unit economics calculations."""
    tenant_id: str
    gpu_type: str
    region: str
    volume: Decimal
    total_cost_of_ownership: Decimal
    allocated_overhead_cost: Decimal
    unit_cost: Decimal


@dataclass(frozen=True)
class PricingResult:
    """Canonical object for pricing calculations."""
    tenant_id: str
    gpu_type: str
    region: str
    volume: Decimal
    unit_cost: Decimal
    unit_price_before_margin: Decimal
    unit_price_with_margin: Decimal


# --- Policy Repository Ports ---

class AllocationPolicyPort(Protocol):
    """Port for retrieving allocation policies."""
    def get_policy(self, tenant_id: str, gpu_type: str, region: str) -> Optional[AllocationPolicy]:
        """Retrieves an allocation policy for a given tenant, GPU type, and region."""
        ...


class MarginPolicyPort(Protocol):
    """Port for retrieving margin policies."""
    def get_policy(self, tenant_id: str, gpu_type: str, region: str) -> Optional[MarginPolicy]:
        """Retrieves a margin policy for a given tenant, GPU type, and region."""
        ...


# --- In-memory Governed Adapters ---

class InMemoryAllocationPolicyAdapter(AllocationPolicyPort):
    """In-memory adapter for AllocationPolicyPort, enforcing tenant scope."""
    def __init__(self):
        self._policies: Dict[str, AllocationPolicy] = {}

    def _generate_key(self, tenant_id: str, gpu_type: str, region: str) -> str:
        """Generates a unique key for policy storage, including tenant_id."""
        return f"{tenant_id}|{gpu_type}|{region}"

    def add_policy(self, policy: AllocationPolicy) -> None:
        """Adds an allocation policy to the in-memory store."""
        key = self._generate_key(policy.tenant_id, policy.gpu_type, policy.region)
        self._policies[key] = policy

    def get_policy(self, tenant_id: str, gpu_type: str, region: str) -> Optional[AllocationPolicy]:
        """Retrieves an allocation policy, ensuring tenant scope."""
        key = self._generate_key(tenant_id, gpu_type, region)
        return self._policies.get(key)


class InMemoryMarginPolicyAdapter(MarginPolicyPort):
    """In-memory adapter for MarginPolicyPort, enforcing tenant scope."""
    def __init__(self):
        self._policies: Dict[str, MarginPolicy] = {}

    def _generate_key(self, tenant_id: str, gpu_type: str, region: str) -> str:
        """Generates a unique key for policy storage, including tenant_id."""
        return f"{tenant_id}|{gpu_type}|{region}"

    def add_policy(self, policy: MarginPolicy) -> None:
        """Adds a margin policy to the in-memory store."""
        key = self._generate_key(policy.tenant_id, policy.gpu_type, policy.region)
        self._policies[key] = policy

    def get_policy(self, tenant_id: str, gpu_type: str, region: str) -> Optional[MarginPolicy]:
        """Retrieves a margin policy, ensuring tenant scope."""
        key = self._generate_key(tenant_id, gpu_type, region)
        return self._policies.get(key)


# --- Phase 4 Application Service ---

class EconomicsService:
    """Phase 4 application service for orchestrating economic and pricing calculations.

    Enforces tenant scope checks at every repository and service boundary.
    Orchestrates the resolution of immutable Phase 2 CapacityResult, Phase 3 TcoResult,
    AllocationPolicy, and MarginPolicy records without duplicating Phase 2 or Phase 3 formulas.
    Executes boundary compatibility verification, cost allocation, ECO-001, ECO-002, PRC-001,
    and PRC-002 to assemble canonical UnitEconomicsResult and PricingResult objects.
    Ensures any missing fact, incompatible boundary, zero volume, or unapproved policy
    fails closed with explicit blocker codes and prevents certification.
    """

    def __init__(
        self, allocation_policy_port: AllocationPolicyPort, margin_policy_port: MarginPolicyPort
    ):
        """Initializes the EconomicsService with required policy ports."""
        self._allocation_policy_port = allocation_policy_port
        self._margin_policy_port = margin_policy_port

    def certify_economics(
        self, tenant_id: str, capacity_result: CapacityResult, tco_result: TcoResult
    ) -> tuple[UnitEconomicsResult, PricingResult]:
        """Certifies the economics and pricing for a given tenant and results.

        Args:
            tenant_id: The identifier of the tenant for whom to certify economics.
            capacity_result: The Phase 2 CapacityResult record.
            tco_result: The Phase 3 TcoResult record.

        Returns:
            A tuple containing UnitEconomicsResult and PricingResult.

        Raises:
            EconomicsServiceError: If any required input is missing, boundaries are incompatible,
                                   volume is zero, or policies are unapproved/missing.
        """
        # Tenant scope checks at service boundary
        if capacity_result.tenant_id != tenant_id:
            raise EconomicsServiceError(
                f"CapacityResult tenant ID '{capacity_result.tenant_id}' does not match requested tenant ID '{tenant_id}'.",
                BlockerCode.INPUT_REQUIRED,
            )
        if tco_result.tenant_id != tenant_id:
            raise EconomicsServiceError(
                f"TcoResult tenant ID '{tco_result.tenant_id}' does not match requested tenant ID '{tenant_id}'.",
                BlockerCode.INPUT_REQUIRED,
            )

        # Zero volume check (moved up to prioritize over boundary mismatch for volume)
        if tco_result.volume <= Decimal('0'):
            raise EconomicsServiceError(
                f"Cannot certify economics for zero or negative volume: {tco_result.volume}.",
                BlockerCode.ZERO_VOLUME,
            )

        # Boundary compatibility verification
        if capacity_result.gpu_type != tco_result.gpu_type:
            raise EconomicsServiceError(
                f"GPU type mismatch: CapacityResult '{capacity_result.gpu_type}' vs TcoResult '{tco_result.gpu_type}'.",
                BlockerCode.BOUNDARY_MISMATCH,
            )
        if capacity_result.region != tco_result.region:
            raise EconomicsServiceError(
                f"Region mismatch: CapacityResult '{capacity_result.region}' vs TcoResult '{tco_result.region}'.",
                BlockerCode.BOUNDARY_MISMATCH,
            )
        if capacity_result.volume != tco_result.volume:
            # While not explicitly stated, volume should match for consistent results
            raise EconomicsServiceError(
                f"Volume mismatch: CapacityResult '{capacity_result.volume}' vs TcoResult '{tco_result.volume}'.",
                BlockerCode.BOUNDARY_MISMATCH,
            )

        # Policy resolution (tenant scope enforced by adapters)
        allocation_policy = self._allocation_policy_port.get_policy(
            tenant_id, tco_result.gpu_type, tco_result.region
        )
        if allocation_policy is None:
            raise EconomicsServiceError(
                f"Allocation policy required for tenant '{tenant_id}', GPU type '{tco_result.gpu_type}', region '{tco_result.region}'.",
                BlockerCode.POLICY_REQUIRED,
            )

        margin_policy = self._margin_policy_port.get_policy(
            tenant_id, tco_result.gpu_type, tco_result.region
        )
        if margin_policy is None:
            raise EconomicsServiceError(
                f"Margin policy required for tenant '{tenant_id}', GPU type '{tco_result.gpu_type}', region '{tco_result.region}'.",
                BlockerCode.POLICY_REQUIRED,
            )

        # ECO-001: Cost allocation
        # Allocated overhead cost is a portion of the total cost of ownership
        allocated_overhead_cost = tco_result.total_cost_of_ownership * allocation_policy.allocation_rate

        # ECO-002: Unit cost calculation
        # Total cost including allocated overhead, divided by volume
        total_cost_for_unit_economics = tco_result.total_cost_of_ownership + allocated_overhead_cost
        unit_cost = total_cost_for_unit_economics / tco_result.volume

        unit_economics_result = UnitEconomicsResult(
            tenant_id=tenant_id,
            gpu_type=tco_result.gpu_type,
            region=tco_result.region,
            volume=tco_result.volume,
            total_cost_of_ownership=tco_result.total_cost_of_ownership,
            allocated_overhead_cost=allocated_overhead_cost,
            unit_cost=unit_cost,
        )

        # PRC-001: Unit price before margin
        # For this phase, it's the calculated unit cost
        unit_price_before_margin = unit_cost

        # PRC-002: Unit price with margin
        unit_price_with_margin = unit_price_before_margin * (Decimal('1') + margin_policy.margin_rate)

        pricing_result = PricingResult(
            tenant_id=tenant_id,
            gpu_type=tco_result.gpu_type,
            region=tco_result.region,
            volume=tco_result.volume,
            unit_cost=unit_cost,
            unit_price_before_margin=unit_price_before_margin,
            unit_price_with_margin=unit_price_with_margin,
        )

        return unit_economics_result, pricing_result
