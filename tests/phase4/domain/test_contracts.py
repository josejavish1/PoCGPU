import pytest
from dataclasses import FrozenInstanceError
from decimal import Decimal
import re # For re.escape

from src.pocgpu.domain.economics.contracts import (
    EconomicBoundary,
    VolumeMeasure,
    CostAllocation,
    UtilizationScenario,
    MarginPolicy,
    UnitEconomicsResult,
    PricingResult,
    ServiceId, WorkloadId, CapacityResultId, TcoResultId, CurrencyCode, PeriodIdentifier,
    CostPoolId, AllocationPolicyId, DimensionIdentifier, WorkloadReference, ProvenanceIdentifier,
    DriverIdentifier, PolicyReference, ScenarioId, SourceClassification, MarginPolicyId,
    ApplicableScope, RoundingMode, ApprovalReference, FormulaVersionKey, FormulaVersionValue,
    BlockerMessage, InformationalUnitCostKey
)

# Helper function to create a default EconomicBoundary for tests
def create_default_economic_boundary(
    service_id: ServiceId = "service-123",
    workload_id: WorkloadId = "workload-abc",
    capacity_result_id: CapacityResultId = "cap-res-456",
    tco_result_id: TcoResultId = "tco-res-789",
    currency: CurrencyCode = "USD",
    period: PeriodIdentifier = "MONTHLY",
    cost_pool_id: CostPoolId = "pool-xyz",
    allocation_policy_id: AllocationPolicyId = "alloc-pol-def"
) -> EconomicBoundary:
    return EconomicBoundary(
        service_id=service_id,
        workload_id=workload_id,
        capacity_result_id=capacity_result_id,
        tco_result_id=tco_result_id,
        currency=currency,
        period=period,
        cost_pool_id=cost_pool_id,
        allocation_policy_id=allocation_policy_id
    )

# Helper function to create a default VolumeMeasure for tests
def create_default_volume_measure(
    dimension: DimensionIdentifier = "CPU_HOURS",
    period: PeriodIdentifier = "MONTHLY",
    governed_value: Decimal = Decimal("1000000"),
    workload_reference: WorkloadReference = "workload-abc",
    provenance: ProvenanceIdentifier = "system-a"
) -> VolumeMeasure:
    return VolumeMeasure(
        dimension=dimension,
        period=period,
        governed_value=governed_value,
        workload_reference=workload_reference,
        provenance=provenance
    )

# Helper function to create a default CostAllocation for tests
def create_default_cost_allocation(
    cost_pool_id: CostPoolId = "pool-xyz",
    driver: DriverIdentifier = "CPU_USAGE",
    denominator: Decimal = Decimal("1000000"),
    allocated_amount: Decimal = Decimal("1000.00"),
    residual_amount: Decimal = Decimal("50.00"),
    policy_reference: PolicyReference = "policy-ref-1"
) -> CostAllocation:
    return CostAllocation(
        cost_pool_id=cost_pool_id,
        driver=driver,
        denominator=denominator,
        allocated_amount=allocated_amount,
        residual_amount=residual_amount,
        policy_reference=policy_reference
    )

# Helper function to create a default UtilizationScenario for tests
def create_default_utilization_scenario(
    scenario_id: ScenarioId = "base-utilization",
    utilization_ratio: Decimal = Decimal("0.75"),
    demand_tokens: Decimal = Decimal("1000000"),
    source_classification: SourceClassification = "actual"
) -> UtilizationScenario:
    return UtilizationScenario(
        scenario_id=scenario_id,
        utilization_ratio=utilization_ratio,
        demand_tokens=demand_tokens,
        source_classification=source_classification
    )

# Helper function to create a default MarginPolicy for tests
def create_default_margin_policy(
    policy_id: MarginPolicyId = "standard-margin",
    target_gross_margin: Decimal = Decimal("0.30"),
    applicable_scope: ApplicableScope = "GLOBAL",
    price_precision: int = 2,
    rounding_mode: RoundingMode = "HALF_UP",
    approval_reference: ApprovalReference = "doc-123"
) -> MarginPolicy:
    return MarginPolicy(
        policy_id=policy_id,
        target_gross_margin=target_gross_margin,
        applicable_scope=applicable_scope,
        price_precision=price_precision,
        rounding_mode=rounding_mode,
        approval_reference=approval_reference
    )


class TestDomainContracts:

    def test_economic_boundary_instantiation_and_immutability(self) -> None:
        boundary = create_default_economic_boundary()
        assert boundary.service_id == "service-123"
        assert boundary.currency == "USD"

        with pytest.raises(FrozenInstanceError):
            # noinspection PyDataclass
            boundary.service_id = "new-service" # type: ignore [misc]

    def test_volume_measure_instantiation_and_immutability(self) -> None:
        volume = create_default_volume_measure()
        assert volume.dimension == "CPU_HOURS"
        assert volume.governed_value == Decimal("1000000")

        with pytest.raises(FrozenInstanceError):
            # noinspection PyDataclass
            volume.governed_value = Decimal("2000000") # type: ignore [misc]

    def test_cost_allocation_instantiation_and_immutability(self) -> None:
        allocation = create_default_cost_allocation()
        assert allocation.cost_pool_id == "pool-xyz"
        assert allocation.allocated_amount == Decimal("1000.00")

        with pytest.raises(FrozenInstanceError):
            # noinspection PyDataclass
            allocation.allocated_amount = Decimal("1200.00") # type: ignore [misc]

    def test_utilization_scenario_instantiation_and_immutability(self) -> None:
        scenario = create_default_utilization_scenario()
        assert scenario.scenario_id == "base-utilization"
        assert scenario.utilization_ratio == Decimal("0.75")

        with pytest.raises(FrozenInstanceError):
            # noinspection PyDataclass
            scenario.utilization_ratio = Decimal("0.80") # type: ignore [misc]

    def test_margin_policy_instantiation_and_immutability(self) -> None:
        policy = create_default_margin_policy()
        assert policy.policy_id == "standard-margin"
        assert policy.target_gross_margin == Decimal("0.30")

        with pytest.raises(FrozenInstanceError):
            # noinspection PyDataclass
            policy.target_gross_margin = Decimal("0.35") # type: ignore [misc]

    def test_unit_economics_result_instantiation_and_immutability(self) -> None:
        boundary = create_default_economic_boundary()
        volume = create_default_volume_measure()
        allocation = create_default_cost_allocation()
        scenario = create_default_utilization_scenario()

        result = UnitEconomicsResult(
            boundary=boundary,
            denominators=[volume],
            allocations=[allocation],
            blended_cost_per_million=Decimal("0.005"),
            informational_unit_costs={"CPU_HOUR": Decimal("0.000005")},
            utilization_sensitivity=[scenario],
            reconciliation_delta=Decimal("0.00"),
            formula_versions={"cost_model": "v1.0"},
            blockers=[]
        )

        assert result.boundary == boundary
        assert result.blended_cost_per_million == Decimal("0.005")
        assert result.denominators[0].governed_value == Decimal("1000000")

        with pytest.raises(FrozenInstanceError):
            # noinspection PyDataclass
            result.blended_cost_per_million = Decimal("0.006") # type: ignore [misc]

    def test_pricing_result_instantiation_and_immutability(self) -> None:
        boundary = create_default_economic_boundary()

        result = PricingResult(
            boundary=boundary,
            cost_basis=Decimal("0.005"),
            target_gross_margin=Decimal("0.30"),
            unrounded_target_price=Decimal("0.007142857"),
            rounded_target_price=Decimal("0.0071"),
            rounding_delta=Decimal("0.000042857"),
            implied_markup=Decimal("0.42857"),
            currency="USD",
            formula_versions={"pricing_model": "v1.0"},
            blockers=[]
        )

        assert result.boundary == boundary
        assert result.cost_basis == Decimal("0.005")
        assert result.target_gross_margin == Decimal("0.30")
        assert result.implied_markup == Decimal("0.42857")
        assert result.currency == "USD"

        with pytest.raises(FrozenInstanceError):
            # noinspection PyDataclass
            result.cost_basis = Decimal("0.006") # type: ignore [misc]

    def test_pricing_result_currency_mismatch_validation(self) -> None:
        boundary_usd = create_default_economic_boundary(currency="USD")

        # Valid case: currency matches boundary
        PricingResult(
            boundary=boundary_usd,
            cost_basis=Decimal("1.0"),
            target_gross_margin=Decimal("0.2"),
            unrounded_target_price=Decimal("1.25"),
            rounded_target_price=Decimal("1.25"),
            rounding_delta=Decimal("0.0"),
            implied_markup=Decimal("0.25"),
            currency="USD",
            formula_versions={},
            blockers=[]
        )

        # Invalid case: currency mismatch
        expected_error_message = (
            r"PricingResult currency 'EUR' must match EconomicBoundary currency 'USD'."
        )
        with pytest.raises(ValueError, match=re.escape(expected_error_message)):
            PricingResult(
                boundary=boundary_usd,
                cost_basis=Decimal("1.0"),
                target_gross_margin=Decimal("0.2"),
                unrounded_target_price=Decimal("1.25"),
                rounded_target_price=Decimal("1.25"),
                rounding_delta=Decimal("0.0"),
                implied_markup=Decimal("0.25"),
                currency="EUR", # Mismatch here
                formula_versions={},
                blockers=[]
            )

    def test_pricing_result_gross_margin_and_markup_distinct_fields(self) -> None:
        # This test primarily checks the existence of distinct fields,
        # which is a structural invariant enforced by the dataclass definition itself.
        # We can assert their types and names.
        boundary = create_default_economic_boundary()
        result = PricingResult(
            boundary=boundary,
            cost_basis=Decimal("1.0"),
            target_gross_margin=Decimal("0.2"),
            unrounded_target_price=Decimal("1.25"),
            rounded_target_price=Decimal("1.25"),
            rounding_delta=Decimal("0.0"),
            implied_markup=Decimal("0.25"),
            currency="USD",
            formula_versions={},
            blockers=[]
        )

        assert hasattr(result, 'target_gross_margin')
        assert isinstance(result.target_gross_margin, Decimal)
        assert hasattr(result, 'implied_markup')
        assert isinstance(result.implied_markup, Decimal)
        assert result.target_gross_margin != result.implied_markup # They are distinct values too

    def test_no_default_values_for_utilization_volume_margin(self) -> None:
        # This is a design-time check. We ensure the dataclass definitions
        # do not have default values for the fields of VolumeMeasure, UtilizationScenario,
        # and MarginPolicy. This is implicitly handled by not providing defaults in the
        # dataclass field definitions and using kw_only=True.

        # VolumeMeasure
        with pytest.raises(TypeError, match=re.escape(
            "VolumeMeasure.__init__() missing 5 required keyword-only arguments: 'dimension', 'period', 'governed_value', 'workload_reference', and 'provenance'"
        )):
            # noinspection PyArgumentList
            VolumeMeasure() # type: ignore [call-arg]

        # UtilizationScenario
        with pytest.raises(TypeError, match=re.escape(
            "UtilizationScenario.__init__() missing 4 required keyword-only arguments: 'scenario_id', 'utilization_ratio', 'demand_tokens', and 'source_classification'"
        )):
            # noinspection PyArgumentList
            UtilizationScenario() # type: ignore [call-arg]

        # MarginPolicy
        with pytest.raises(TypeError, match=re.escape(
            "MarginPolicy.__init__() missing 6 required keyword-only arguments: 'policy_id', 'target_gross_margin', 'applicable_scope', 'price_precision', 'rounding_mode', and 'approval_reference'"
        )):
            # noinspection PyArgumentList
            MarginPolicy() # type: ignore [call-arg]
