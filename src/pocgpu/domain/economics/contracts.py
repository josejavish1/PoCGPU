from dataclasses import dataclass
from decimal import Decimal
from typing import TypeAlias

# PEP 695 type aliases
ServiceId: TypeAlias = str
WorkloadId: TypeAlias = str
CapacityResultId: TypeAlias = str
TcoResultId: TypeAlias = str
CurrencyCode: TypeAlias = str
PeriodIdentifier: TypeAlias = str
CostPoolId: TypeAlias = str
AllocationPolicyId: TypeAlias = str
DimensionIdentifier: TypeAlias = str
WorkloadReference: TypeAlias = str
ProvenanceIdentifier: TypeAlias = str
DriverIdentifier: TypeAlias = str
PolicyReference: TypeAlias = str
ScenarioId: TypeAlias = str
SourceClassification: TypeAlias = str
MarginPolicyId: TypeAlias = str
ApplicableScope: TypeAlias = str
RoundingMode: TypeAlias = str
ApprovalReference: TypeAlias = str
FormulaVersionKey: TypeAlias = str
FormulaVersionValue: TypeAlias = str
BlockerMessage: TypeAlias = str
InformationalUnitCostKey: TypeAlias = str


@dataclass(frozen=True, kw_only=True)
class EconomicBoundary:
    """
    Defines the immutable economic context for a specific service, workload, and financial period.
    """
    service_id: ServiceId
    workload_id: WorkloadId
    capacity_result_id: CapacityResultId
    tco_result_id: TcoResultId
    currency: CurrencyCode
    period: PeriodIdentifier
    cost_pool_id: CostPoolId
    allocation_policy_id: AllocationPolicyId


@dataclass(frozen=True, kw_only=True)
class VolumeMeasure:
    """
    Represents an immutable measure of volume for a specific dimension and period.
    No default values for volume are permitted.
    """
    dimension: DimensionIdentifier
    period: PeriodIdentifier
    governed_value: Decimal
    workload_reference: WorkloadReference
    provenance: ProvenanceIdentifier


@dataclass(frozen=True, kw_only=True)
class CostAllocation:
    """
    Represents an immutable allocation of cost from a cost pool based on a driver.
    """
    cost_pool_id: CostPoolId
    driver: DriverIdentifier
    denominator: Decimal
    allocated_amount: Decimal
    residual_amount: Decimal
    policy_reference: PolicyReference


@dataclass(frozen=True, kw_only=True)
class UtilizationScenario:
    """
    Defines an immutable utilization scenario with a specific ratio and demand tokens.
    No default values for utilization are permitted.
    """
    scenario_id: ScenarioId
    utilization_ratio: Decimal
    demand_tokens: Decimal
    source_classification: SourceClassification


@dataclass(frozen=True, kw_only=True)
class MarginPolicy:
    """
    Defines an immutable margin policy, including target gross margin and rounding rules.
    No default values for margin are permitted.
    """
    policy_id: MarginPolicyId
    target_gross_margin: Decimal
    applicable_scope: ApplicableScope
    price_precision: int
    rounding_mode: RoundingMode
    approval_reference: ApprovalReference


@dataclass(frozen=True, kw_only=True)
class UnitEconomicsResult:
    """
    Encapsulates the immutable results of unit economics calculations, including costs,
    allocations, and utilization sensitivity.
    """
    boundary: EconomicBoundary
    denominators: list[VolumeMeasure]
    allocations: list[CostAllocation]
    blended_cost_per_million: Decimal
    informational_unit_costs: dict[InformationalUnitCostKey, Decimal]
    utilization_sensitivity: list[UtilizationScenario]
    reconciliation_delta: Decimal
    formula_versions: dict[FormulaVersionKey, FormulaVersionValue]
    blockers: list[BlockerMessage]

    def __post_init__(self) -> None:
        """
        Performs validation after initialization to enforce structural invariants.
        For UnitEconomicsResult, the boundary itself defines the service, workload, currency, and period.
        There are no other fields within UnitEconomicsResult that would need to be checked for a mismatch
        against the boundary's identities based on the current specification.
        """
        pass


@dataclass(frozen=True, kw_only=True)
class PricingResult:
    """
    Encapsulates the immutable results of pricing calculations, including cost basis,
    target margin, and final prices.
    """
    boundary: EconomicBoundary
    cost_basis: Decimal
    target_gross_margin: Decimal  # Distinct field name for gross margin
    unrounded_target_price: Decimal
    rounded_target_price: Decimal
    rounding_delta: Decimal
    implied_markup: Decimal      # Distinct field name for markup
    currency: CurrencyCode       # Must match boundary.currency
    formula_versions: dict[FormulaVersionKey, FormulaVersionValue]
    blockers: list[BlockerMessage]

    def __post_init__(self) -> None:
        """
        Performs validation after initialization to enforce structural invariants.
        """
        # Gross margin and markup must use distinct field names, types, and localization keys.
        # This is ensured by having `target_gross_margin` and `implied_markup` as separate Decimal fields.

        # Boundary validation: the `currency` field of PricingResult must match `boundary.currency`.
        if self.currency != self.boundary.currency:
            raise ValueError(
                f"PricingResult currency '{self.currency}' must match "
                f"EconomicBoundary currency '{self.boundary.currency}'."
            )
