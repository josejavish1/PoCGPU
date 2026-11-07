import dataclasses
from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_EVEN, ROUND_CEILING, ROUND_FLOOR, ROUND_UP, ROUND_DOWN, ROUND_HALF_DOWN, ROUND_05UP, localcontext
from typing import Literal, TypeAlias, Optional

# Type alias for Decimal.rounding constants
RoundingMode: TypeAlias = Literal[
    ROUND_CEILING,
    ROUND_DOWN,
    ROUND_FLOOR,
    ROUND_HALF_DOWN,
    ROUND_HALF_EVEN,
    ROUND_HALF_UP,
    ROUND_UP,
    ROUND_05UP,
]

# --- Constants ---
POLICY_REQUIRED: str = "POLICY_REQUIRED"

# --- Exceptions ---
class PricingDomainError(Exception):
    """Base exception for pricing domain errors."""
    pass

class InvalidMarginPolicyError(PricingDomainError):
    """Raised when a MarginPolicy has invalid domain values."""
    pass

# --- Domain Models ---
@dataclasses.dataclass(frozen=True)
class MarginPolicy:
    """
    Defines the policy for calculating target gross margin and price rounding.

    Attributes:
        target_gross_margin: The desired gross margin as a Decimal,
                             must be 0 <= target_gross_margin < 1.
        approval_reference: A string reference indicating policy approval,
                            can be empty if not yet approved.
        price_precision: The number of decimal places for rounding the price.
        rounding_mode: The rounding strategy to apply (e.g., ROUND_HALF_UP).
    """
    target_gross_margin: Decimal
    approval_reference: str
    price_precision: int
    rounding_mode: RoundingMode

    def __post_init__(self) -> None:
        """
        Validates the domain constraints for MarginPolicy attributes.
        """
        if not (Decimal('0') <= self.target_gross_margin < Decimal('1')):
            raise InvalidMarginPolicyError(
                f"Target gross margin must be between 0 (inclusive) and 1 (exclusive), "
                f"but received {self.target_gross_margin}."
            )
        # The approval_reference validation is moved to PricingService to allow for 'unapproved' policies.
        if not isinstance(self.price_precision, int) or self.price_precision < 0:
            raise InvalidMarginPolicyError(
                f"Price precision must be a non-negative integer, but received {self.price_precision}."
            )

@dataclasses.dataclass(frozen=True)
class PricingResult:
    """
    Encapsulates the results of a pricing calculation.

    Attributes:
        unrounded_target_price: The calculated target price before any rounding.
        rounded_target_price: The target price after applying rounding rules.
        rounding_delta: The difference between the rounded and unrounded target prices.
        implied_markup: The implied markup based on the unrounded target price and cost basis,
                        or None if cost_basis is zero.
    """
    unrounded_target_price: Decimal
    rounded_target_price: Decimal
    rounding_delta: Decimal
    implied_markup: Optional[Decimal]

# --- Services ---
class PricingService:
    """
    Provides pricing calculation services based on defined policies.
    Implements canonical formulas PRC-001 and PRC-002 (version 0.1.0).
    """

    def compute_target_price(
        self, cost_basis: Decimal, policy: Optional[MarginPolicy]
    ) -> PricingResult | Literal["POLICY_REQUIRED"]:
        """
        Computes the target price based on cost basis and a margin policy.

        Args:
            cost_basis: The base cost of the item.
            policy: The MarginPolicy to apply, or None if no policy is available.

        Returns:
            A PricingResult object containing the calculated prices and markup,
            or the string "POLICY_REQUIRED" if the policy is missing or unapproved.

        Raises:
            InvalidMarginPolicyError: If the provided policy has invalid domain values.
            PricingDomainError: For other internal domain calculation errors.
        """
        if policy is None or not policy.approval_reference:
            return POLICY_REQUIRED

        with localcontext() as ctx:
            ctx.prec = 50  # Set a high precision for internal calculations to maintain "exact Decimal precision"

            # PRC-001: Compute unrounded_target_price
            # Denominator must be > 0 due to MarginPolicy validation (target_gross_margin < 1)
            denominator = Decimal('1') - policy.target_gross_margin
            if denominator == Decimal('0'):  # Should be caught by MarginPolicy validation, but as a safeguard
                raise PricingDomainError("Internal error: Target gross margin of 1.0 would lead to division by zero.")

            unrounded_target_price = cost_basis / denominator
            gross_profit = unrounded_target_price - cost_basis

            # PRC-001: Apply rounding strictly once at the declared billing/presentation boundary
            quantized_precision = Decimal('10') ** -policy.price_precision
            rounded_target_price = unrounded_target_price.quantize(quantized_precision, rounding=policy.rounding_mode)

            # PRC-001: Explicitly record rounding_delta
            rounding_delta = rounded_target_price - unrounded_target_price

            # PRC-002: Compute implied_markup
            implied_markup: Optional[Decimal]
            if cost_basis > Decimal('0'):
                implied_markup = gross_profit / cost_basis
            else:  # cost_basis == 0
                implied_markup = None  # Explicitly undefined

        # PRC-001: Verify invariant: recomputing gross margin from unrounded_target_price
        # and cost_basis equals target_gross_margin within exact Decimal precision.
        # This invariant is only meaningful when unrounded_target_price is not zero.
        if unrounded_target_price != Decimal('0'):
            recomputed_gross_margin = gross_profit / unrounded_target_price
            if recomputed_gross_margin != policy.target_gross_margin:
                raise PricingDomainError(
                    f"Gross margin invariant violated: Recomputed {recomputed_gross_margin} "
                    f"does not match target {policy.target_gross_margin} for unrounded price."
                )
        elif cost_basis != Decimal('0'):
            raise PricingDomainError(
                f"Internal error: Unrounded target price is zero for non-zero cost basis {cost_basis}."
            )

        return PricingResult(
            unrounded_target_price=unrounded_target_price,
            rounded_target_price=rounded_target_price,
            rounding_delta=rounding_delta,
            implied_markup=implied_markup,
        )
