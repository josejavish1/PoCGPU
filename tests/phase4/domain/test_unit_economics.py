import pytest
from decimal import Decimal
import re # For re.escape in pytest.raises match

from src.pocgpu.domain.economics.unit_economics import (
    UnitEconomicsCalculator,
    UnitEconomicsResult,
    UtilizationScenario,
    UtilizationSensitivityResult,
    InvalidTokenDemandError,
    InvalidTCOError,
    InvalidCapacityError,
    InvalidUtilizationRatioError,
)

@pytest.fixture
def calculator() -> UnitEconomicsCalculator:
    """Provides a UnitEconomicsCalculator instance for tests."""
    return UnitEconomicsCalculator()

class TestUnitEconomicsCalculator:

    # --- Tests for calculate_blended_unit_economics (ECO-001) ---

    def test_calculate_blended_unit_economics_happy_path(self, calculator: UnitEconomicsCalculator):
        """
        Verifies correct calculation for valid positive inputs.
        """
        input_tokens = Decimal('500000')
        output_tokens = Decimal('1500000')
        allocated_tco = Decimal('2000') # $2000

        result = calculator.calculate_blended_unit_economics(
            monthly_input_tokens=input_tokens,
            monthly_output_tokens=output_tokens,
            allocated_monthly_tco=allocated_tco,
        )

        expected_total_tokens = input_tokens + output_tokens # 2000000
        expected_total_million_tokens = expected_total_tokens / Decimal('1000000') # 2
        expected_blended_cost_per_million = allocated_tco / expected_total_million_tokens # 2000 / 2 = 1000

        assert isinstance(result, UnitEconomicsResult)
        assert result.total_million_tokens == expected_total_million_tokens
        assert result.blended_cost_per_million == expected_blended_cost_per_million

    def test_calculate_blended_unit_economics_zero_tco(self, calculator: UnitEconomicsCalculator):
        """
        Verifies that zero TCO results in zero cost per million.
        """
        input_tokens = Decimal('1000000')
        output_tokens = Decimal('1000000')
        allocated_tco = Decimal('0')

        result = calculator.calculate_blended_unit_economics(
            monthly_input_tokens=input_tokens,
            monthly_output_tokens=output_tokens,
            allocated_monthly_tco=allocated_tco,
        )

        assert result.blended_cost_per_million == Decimal('0')
        assert result.total_million_tokens == Decimal('2')

    def test_calculate_blended_unit_economics_negative_tco_raises_error(self, calculator: UnitEconomicsCalculator):
        """
        Verifies that negative TCO raises an InvalidTCOError.
        """
        with pytest.raises(InvalidTCOError, match=re.escape("Allocated monthly TCO cannot be negative.")):
            calculator.calculate_blended_unit_economics(
                monthly_input_tokens=Decimal('1000000'),
                monthly_output_tokens=Decimal('1000000'),
                allocated_monthly_tco=Decimal('-100'),
            )

    @pytest.mark.parametrize(
        "input_tokens, output_tokens, expected_error_message",
        [
            (Decimal('0'), Decimal('0'), "Total token demand (monthly_input_tokens + monthly_output_tokens) must be positive."),
            (Decimal('-100'), Decimal('0'), "Total token demand (monthly_input_tokens + monthly_output_tokens) must be positive."),
            (Decimal('100'), Decimal('-200'), "Total token demand (monthly_input_tokens + monthly_output_tokens) must be positive."),
            (Decimal('-50'), Decimal('-50'), "Total token demand (monthly_input_tokens + monthly_output_tokens) must be positive."),
        ],
    )
    def test_calculate_blended_unit_economics_invalid_token_demand_raises_error(
        self, calculator: UnitEconomicsCalculator, input_tokens: Decimal, output_tokens: Decimal, expected_error_message: str
    ):
        """
        Verifies that zero or negative total token demand raises an InvalidTokenDemandError.
        """
        with pytest.raises(InvalidTokenDemandError, match=re.escape(expected_error_message)):
            calculator.calculate_blended_unit_economics(
                monthly_input_tokens=input_tokens,
                monthly_output_tokens=output_tokens,
                allocated_monthly_tco=Decimal('1000'),
            )

    def test_cost_monotonicity(self, calculator: UnitEconomicsCalculator):
        """
        Verifies that increasing positive TCO never reduces unit cost for a fixed denominator.
        """
        input_tokens = Decimal('1000000')
        output_tokens = Decimal('1000000')
        tco_values = [Decimal('100'), Decimal('200'), Decimal('200'), Decimal('300')] # Include a duplicate to test non-strict increase

        previous_cost_per_million = Decimal('-1') # Initialize with a value lower than any possible cost

        for tco in tco_values:
            result = calculator.calculate_blended_unit_economics(
                monthly_input_tokens=input_tokens,
                monthly_output_tokens=output_tokens,
                allocated_monthly_tco=tco,
            )
            current_cost_per_million = result.blended_cost_per_million
            assert current_cost_per_million >= previous_cost_per_million
            previous_cost_per_million = current_cost_per_million

    # --- Tests for evaluate_utilization_sensitivity (ECO-002) ---

    def test_evaluate_utilization_sensitivity_happy_path(self, calculator: UnitEconomicsCalculator):
        """
        Verifies correct calculation for valid utilization ratios.
        """
        monthly_tco = Decimal('10000')
        useful_capacity = Decimal('10000000') # 10 million tokens
        utilization_ratios = [Decimal('0.25'), Decimal('0.5'), Decimal('1.0')]

        result = calculator.evaluate_utilization_sensitivity(
            monthly_tco=monthly_tco,
            useful_monthly_token_capacity=useful_capacity,
            utilization_ratios=utilization_ratios,
        )

        assert isinstance(result, UtilizationSensitivityResult)
        assert len(result.scenarios) == 3

        # Scenario 1: 0.25 utilization
        scenario1 = result.scenarios[0]
        expected_tokens1 = useful_capacity * Decimal('0.25') # 2.5 million
        expected_cost1 = monthly_tco / (expected_tokens1 / Decimal('1000000')) # 10000 / 2.5 = 4000
        assert scenario1.utilization_ratio == Decimal('0.25')
        assert scenario1.tokens_at_utilization == expected_tokens1
        assert scenario1.cost_per_million_at_utilization == expected_cost1

        # Scenario 2: 0.5 utilization
        scenario2 = result.scenarios[1]
        expected_tokens2 = useful_capacity * Decimal('0.5') # 5 million
        expected_cost2 = monthly_tco / (expected_tokens2 / Decimal('1000000')) # 10000 / 5 = 2000
        assert scenario2.utilization_ratio == Decimal('0.5')
        assert scenario2.tokens_at_utilization == expected_tokens2
        assert scenario2.cost_per_million_at_utilization == expected_cost2

        # Scenario 3: 1.0 utilization
        scenario3 = result.scenarios[2]
        expected_tokens3 = useful_capacity * Decimal('1.0') # 10 million
        expected_cost3 = monthly_tco / (expected_tokens3 / Decimal('1000000')) # 10000 / 10 = 1000
        assert scenario3.utilization_ratio == Decimal('1.0')
        assert scenario3.tokens_at_utilization == expected_tokens3
        assert scenario3.cost_per_million_at_utilization == expected_cost3

    def test_evaluate_utilization_sensitivity_zero_tco(self, calculator: UnitEconomicsCalculator):
        """
        Verifies that zero TCO results in zero cost per million for all scenarios.
        """
        monthly_tco = Decimal('0')
        useful_capacity = Decimal('10000000')
        utilization_ratios = [Decimal('0.5'), Decimal('1.0')]

        result = calculator.evaluate_utilization_sensitivity(
            monthly_tco=monthly_tco,
            useful_monthly_token_capacity=useful_capacity,
            utilization_ratios=utilization_ratios,
        )

        assert all(s.cost_per_million_at_utilization == Decimal('0') for s in result.scenarios)

    def test_evaluate_utilization_sensitivity_negative_tco_raises_error(self, calculator: UnitEconomicsCalculator):
        """
        Verifies that negative TCO raises an InvalidTCOError.
        """
        with pytest.raises(InvalidTCOError, match=re.escape("Monthly TCO cannot be negative.")):
            calculator.evaluate_utilization_sensitivity(
                monthly_tco=Decimal('-100'),
                useful_monthly_token_capacity=Decimal('1000000'),
                utilization_ratios=[Decimal('0.5')],
            )

    @pytest.mark.parametrize(
        "capacity, expected_error_message",
        [
            (Decimal('0'), "Useful monthly token capacity must be positive."),
            (Decimal('-100'), "Useful monthly token capacity must be positive."),
        ],
    )
    def test_evaluate_utilization_sensitivity_invalid_capacity_raises_error(
        self, calculator: UnitEconomicsCalculator, capacity: Decimal, expected_error_message: str
    ):
        """
        Verifies that zero or negative useful monthly token capacity raises an InvalidCapacityError.
        """
        with pytest.raises(InvalidCapacityError, match=re.escape(expected_error_message)):
            calculator.evaluate_utilization_sensitivity(
                monthly_tco=Decimal('1000'),
                useful_monthly_token_capacity=capacity,
                utilization_ratios=[Decimal('0.5')],
            )

    @pytest.mark.parametrize(
        "ratio, expected_error_message",
        [
            (Decimal('0'), r"Utilization ratio must be between 0 \(exclusive\) and 1 \(inclusive\), but got 0."),
            (Decimal('-0.1'), r"Utilization ratio must be between 0 \(exclusive\) and 1 \(inclusive\), but got -0.1."),
            (Decimal('1.0000000000000000000000000001'), r"Utilization ratio must be between 0 \(exclusive\) and 1 \(inclusive\), but got 1.0000000000000000000000000001."),
            (Decimal('2'), r"Utilization ratio must be between 0 \(exclusive\) and 1 \(inclusive\), but got 2."),
        ],
    )
    def test_evaluate_utilization_sensitivity_invalid_ratio_raises_error(
        self, calculator: UnitEconomicsCalculator, ratio: Decimal, expected_error_message: str
    ):
        """
        Verifies that utilization ratios outside (0, 1] raise an InvalidUtilizationRatioError.
        """
        with pytest.raises(InvalidUtilizationRatioError, match=expected_error_message):
            calculator.evaluate_utilization_sensitivity(
                monthly_tco=Decimal('1000'),
                useful_monthly_token_capacity=Decimal('1000000'),
                utilization_ratios=[ratio],
            )

    def test_utilization_monotonicity(self, calculator: UnitEconomicsCalculator):
        """
        Verifies that increasing utilization within a fixed capacity step strictly decreases unit cost.
        """
        monthly_tco = Decimal('10000')
        useful_capacity = Decimal('10000000') # 10 million tokens
        utilization_ratios = [Decimal('0.2'), Decimal('0.4'), Decimal('0.6'), Decimal('0.8'), Decimal('1.0')]

        result = calculator.evaluate_utilization_sensitivity(
            monthly_tco=monthly_tco,
            useful_monthly_token_capacity=useful_capacity,
            utilization_ratios=utilization_ratios,
        )

        previous_cost_per_million = Decimal('inf') # Initialize with a very high value

        for scenario in result.scenarios:
            current_cost_per_million = scenario.cost_per_million_at_utilization
            assert current_cost_per_million < previous_cost_per_million # Strictly decreases
            previous_cost_per_million = current_cost_per_million

    def test_sensitivity_evaluation_does_not_mutate_baseline(self, calculator: UnitEconomicsCalculator):
        """
        Verifies that the sensitivity evaluation method does not mutate any input parameters.
        """
        original_monthly_tco = Decimal('10000')
        original_useful_capacity = Decimal('10000000')
        original_utilization_ratios = [Decimal('0.5'), Decimal('1.0')]

        # Create copies to ensure no mutation
        monthly_tco_copy = original_monthly_tco
        useful_capacity_copy = original_useful_capacity
        utilization_ratios_copy = list(original_utilization_ratios) # Shallow copy for list

        calculator.evaluate_utilization_sensitivity(
            monthly_tco=monthly_tco_copy,
            useful_monthly_token_capacity=useful_capacity_copy,
            utilization_ratios=utilization_ratios_copy,
        )

        # Assert that the original values remain unchanged
        assert monthly_tco_copy == original_monthly_tco
        assert useful_capacity_copy == original_useful_capacity
        assert utilization_ratios_copy == original_utilization_ratios
