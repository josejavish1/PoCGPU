from dataclasses import dataclass
from decimal import Decimal
from typing import TypeAlias

# Type aliases for clarity
MonthlyTokens: TypeAlias = Decimal
MonthlyTCO: TypeAlias = Decimal
UtilizationRatio: TypeAlias = Decimal

class UnitEconomicsError(Exception):
    """Base exception for unit economics calculations."""
    pass

class InvalidTokenDemandError(UnitEconomicsError):
    """Raised when total token demand is zero or negative."""
    pass

class InvalidTCOError(UnitEconomicsError):
    """Raised when Total Cost of Ownership (TCO) is negative."""
    pass

class InvalidCapacityError(UnitEconomicsError):
    """Raised when useful monthly token capacity is zero or negative."""
    pass

class InvalidUtilizationRatioError(UnitEconomicsError):
    """Raised when a utilization ratio is outside the valid range (0 < ratio <= 1)."""
    pass

@dataclass(frozen=True)
class UnitEconomicsResult:
    """
    Represents the blended unit economics result based on ECO-001.
    """
    total_million_tokens: Decimal
    blended_cost_per_million: Decimal

@dataclass(frozen=True)
class UtilizationScenario:
    """
    Represents a single point in the utilization sensitivity analysis based on ECO-002.
    """
    utilization_ratio: UtilizationRatio
    tokens_at_utilization: MonthlyTokens
    cost_per_million_at_utilization: Decimal

@dataclass(frozen=True)
class UtilizationSensitivityResult:
    """
    Represents the collection of utilization sensitivity scenarios based on ECO-002.
    """
    scenarios: list[UtilizationScenario]

class UnitEconomicsCalculator:
    """
    Provides methods for calculating unit economics metrics based on canonical formulas.
    """

    def calculate_blended_unit_economics(
        self,
        monthly_input_tokens: MonthlyTokens,
        monthly_output_tokens: MonthlyTokens,
        allocated_monthly_tco: MonthlyTCO,
    ) -> UnitEconomicsResult:
        """
        Computes the blended unit economics (cost per million tokens) based on ECO-001.

        Args:
            monthly_input_tokens: The total monthly input tokens.
            monthly_output_tokens: The total monthly output tokens.
            allocated_monthly_tco: The total monthly cost of ownership allocated to this demand.

        Returns:
            A UnitEconomicsResult containing total million tokens and blended cost per million.

        Raises:
            InvalidTokenDemandError: If the total token demand is zero or negative.
            InvalidTCOError: If the allocated monthly TCO is negative.
        """
        if allocated_monthly_tco < Decimal('0'):
            raise InvalidTCOError("Allocated monthly TCO cannot be negative.")

        total_tokens = monthly_input_tokens + monthly_output_tokens
        if total_tokens <= Decimal('0'):
            raise InvalidTokenDemandError(
                "Total token demand (monthly_input_tokens + monthly_output_tokens) must be positive."
            )

        total_million_tokens = total_tokens / Decimal('1000000')
        blended_cost_per_million = allocated_monthly_tco / total_million_tokens

        return UnitEconomicsResult(
            total_million_tokens=total_million_tokens,
            blended_cost_per_million=blended_cost_per_million,
        )

    def evaluate_utilization_sensitivity(
        self,
        monthly_tco: MonthlyTCO,
        useful_monthly_token_capacity: MonthlyTokens,
        utilization_ratios: list[UtilizationRatio],
    ) -> UtilizationSensitivityResult:
        """
        Evaluates the cost per million tokens across a sequence of utilization scenarios
        based on ECO-002.

        Args:
            monthly_tco: The total monthly cost of ownership for the capacity.
            useful_monthly_token_capacity: The total useful monthly token capacity of the system.
            utilization_ratios: A list of utilization ratios (0 < ratio <= 1) to evaluate.

        Returns:
            A UtilizationSensitivityResult containing a list of UtilizationScenario objects.

        Raises:
            InvalidTCOError: If the monthly TCO is negative.
            InvalidCapacityError: If the useful monthly token capacity is zero or negative.
            InvalidUtilizationRatioError: If any utilization ratio is outside the valid range (0 < ratio <= 1).
        """
        if monthly_tco < Decimal('0'):
            raise InvalidTCOError("Monthly TCO cannot be negative.")

        if useful_monthly_token_capacity <= Decimal('0'):
            raise InvalidCapacityError("Useful monthly token capacity must be positive.")

        scenarios: list[UtilizationScenario] = []
        for ratio in utilization_ratios:
            if not (Decimal('0') < ratio <= Decimal('1')):
                raise InvalidUtilizationRatioError(
                    f"Utilization ratio must be between 0 (exclusive) and 1 (inclusive), but got {ratio}."
                )

            tokens_at_utilization = useful_monthly_token_capacity * ratio
            # Denominator for cost_per_million_at_utilization
            million_tokens_at_utilization = tokens_at_utilization / Decimal('1000000')

            # If monthly_tco is 0, cost_per_million_at_utilization will be 0, which is correct.
            cost_per_million_at_utilization = monthly_tco / million_tokens_at_utilization

            scenarios.append(
                UtilizationScenario(
                    utilization_ratio=ratio,
                    tokens_at_utilization=tokens_at_utilization,
                    cost_per_million_at_utilization=cost_per_million_at_utilization,
                )
            )
        return UtilizationSensitivityResult(scenarios=scenarios)
