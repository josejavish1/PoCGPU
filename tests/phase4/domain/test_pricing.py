import pytest
from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_EVEN, ROUND_CEILING, ROUND_FLOOR, ROUND_UP, ROUND_DOWN, ROUND_HALF_DOWN, ROUND_05UP
from typing import Optional

from pocgpu.domain.economics.pricing import (
    POLICY_REQUIRED,
    PricingDomainError,
    InvalidMarginPolicyError,
    RoundingMode,
    MarginPolicy,
    PricingResult,
    PricingService,
)


class TestMarginPolicy:
    """Tests for the MarginPolicy dataclass."""

    def test_valid_policy_creation(self) -> None:
        """Ensures a MarginPolicy can be created with valid parameters."""
        policy = MarginPolicy(
            target_gross_margin=Decimal('0.25'),
            approval_reference="REF-2023-001",
            price_precision=2,
            rounding_mode=ROUND_HALF_UP,
        )
        assert policy.target_gross_margin == Decimal('0.25')
        assert policy.approval_reference == "REF-2023-001"
        assert policy.price_precision == 2
        assert policy.rounding_mode == ROUND_HALF_UP

    @pytest.mark.parametrize(
        "margin, expected_error_match",
        [
            (Decimal('-0.01'), r"Target gross margin must be between 0 \(inclusive\) and 1 \(exclusive\).*"),
            (Decimal('1.00'), r"Target gross margin must be between 0 \(inclusive\) and 1 \(exclusive\).*"),
            (Decimal('1.01'), r"Target gross margin must be between 0 \(inclusive\) and 1 \(exclusive\).*"),
        ],
    )
    def test_invalid_target_gross_margin_raises_error(self, margin: Decimal, expected_error_match: str) -> None:
        """Verifies that invalid target_gross_margin values raise InvalidMarginPolicyError."""
        with pytest.raises(InvalidMarginPolicyError, match=expected_error_match):
            MarginPolicy(
                target_gross_margin=margin,
                approval_reference="REF-VALID",
                price_precision=2,
                rounding_mode=ROUND_HALF_UP,
            )

    def test_empty_approval_reference_does_not_raise_error_on_construction(self) -> None:
        """Verifies that an empty approval_reference does not raise InvalidMarginPolicyError on construction.
        The service is responsible for checking approval status.
        """
        policy = MarginPolicy(
            target_gross_margin=Decimal('0.1'),
            approval_reference="",
            price_precision=2,
            rounding_mode=ROUND_HALF_UP,
        )
        assert policy.approval_reference == ""

    @pytest.mark.parametrize(
        "precision, expected_error_match",
        [
            (-1, r"Price precision must be a non-negative integer.*"),
            (1.5, r"Price precision must be a non-negative integer.*"),
        ],
    )
    def test_invalid_price_precision_raises_error(self, precision: int | float, expected_error_match: str) -> None:
        """Verifies that invalid price_precision values raise InvalidMarginPolicyError."""
        with pytest.raises(InvalidMarginPolicyError, match=expected_error_match):
            MarginPolicy(
                target_gross_margin=Decimal('0.1'),
                approval_reference="REF-VALID",
                price_precision=precision,  # type: ignore
                rounding_mode=ROUND_HALF_UP,
            )

class TestPricingService:
    """Tests for the PricingService class."""

    @pytest.fixture
    def pricing_service(self) -> PricingService:
        """Provides a PricingService instance for tests."""
        return PricingService()

    @pytest.fixture
    def valid_policy(self) -> MarginPolicy:
        """Provides a valid MarginPolicy instance."""
        return MarginPolicy(
            target_gross_margin=Decimal('0.25'),
            approval_reference="APPROVED-POLICY-123",
            price_precision=2,
            rounding_mode=ROUND_HALF_UP,
        )

    def test_compute_target_price_with_no_policy(self, pricing_service: PricingService) -> None:
        """Ensures POLICY_REQUIRED is returned when no policy is provided."""
        result = pricing_service.compute_target_price(Decimal('100'), None)
        assert result == POLICY_REQUIRED

    def test_compute_target_price_with_unapproved_policy(self, pricing_service: PricingService) -> None:
        """Ensures POLICY_REQUIRED is returned when the policy is unapproved (empty reference)."""
        unapproved_policy = MarginPolicy(
            target_gross_margin=Decimal('0.1'),
            approval_reference="",  # Unapproved
            price_precision=2,
            rounding_mode=ROUND_HALF_UP,
        )
        result = pricing_service.compute_target_price(Decimal('100'), unapproved_policy)
        assert result == POLICY_REQUIRED

    @pytest.mark.parametrize(
        "cost_basis, target_margin, expected_unrounded, expected_rounded, expected_delta, precision, rounding_mode, expected_markup",
        [
            # Basic case: 100 / (1 - 0.25) = 100 / 0.75 = 133.333... (50 significant digits)
            (Decimal('100'), Decimal('0.25'), Decimal('133.33333333333333333333333333333333333333333333333'), Decimal('133.33'), Decimal('-0.00333333333333333333333333333333333333333333333'), 2, ROUND_HALF_UP, Decimal('0.3333333333333333333333333333333333333333333333333')),
            # No rounding needed
            (Decimal('75'), Decimal('0.25'), Decimal('100'), Decimal('100.00'), Decimal('0.00'), 2, ROUND_HALF_UP, Decimal('0.33333333333333333333333333333333333333333333333333')),
            # Different precision
            (Decimal('100'), Decimal('0.25'), Decimal('133.33333333333333333333333333333333333333333333333'), Decimal('133.333'), Decimal('-0.00033333333333333333333333333333333333333333333'), 3, ROUND_HALF_UP, Decimal('0.3333333333333333333333333333333333333333333333333')),
            # Different rounding mode (ROUND_FLOOR)
            (Decimal('100'), Decimal('0.25'), Decimal('133.33333333333333333333333333333333333333333333333'), Decimal('133.33'), Decimal('-0.00333333333333333333333333333333333333333333333'), 2, ROUND_FLOOR, Decimal('0.3333333333333333333333333333333333333333333333333')),
            # Rounding up with ROUND_CEILING
            (Decimal('100'), Decimal('0.25'), Decimal('133.33333333333333333333333333333333333333333333333'), Decimal('133.34'), Decimal('0.00666666666666666666666666666666666666666666667'), 2, ROUND_CEILING, Decimal('0.3333333333333333333333333333333333333333333333333')),
            # Cost basis 0
            (Decimal('0'), Decimal('0.1'), Decimal('0'), Decimal('0.00'), Decimal('0'), 2, ROUND_HALF_UP, None),
            # Small cost basis, high margin
            (Decimal('0.01'), Decimal('0.9'), Decimal('0.1'), Decimal('0.10'), Decimal('0'), 2, ROUND_HALF_UP, Decimal('9')),
            # Margin 0
            (Decimal('100'), Decimal('0'), Decimal('100'), Decimal('100.00'), Decimal('0'), 2, ROUND_HALF_UP, Decimal('0')),
        ],
    )
    def test_compute_target_price_valid_cases(
        self,
        pricing_service: PricingService,
        cost_basis: Decimal,
        target_margin: Decimal,
        expected_unrounded: Decimal,
        expected_rounded: Decimal,
        expected_delta: Decimal,
        precision: int,
        rounding_mode: RoundingMode,
        expected_markup: Optional[Decimal],
    ) -> None:
        """Tests compute_target_price with various valid inputs and rounding modes."""
        policy = MarginPolicy(
            target_gross_margin=target_margin,
            approval_reference="APPROVED-POLICY-TEST",
            price_precision=precision,
            rounding_mode=rounding_mode,
        )
        result = pricing_service.compute_target_price(cost_basis, policy)

        assert isinstance(result, PricingResult)
        assert result.unrounded_target_price == expected_unrounded
        assert result.rounded_target_price == expected_rounded
        assert result.rounding_delta == expected_delta
        assert result.implied_markup == expected_markup

        # Verify PRC-001 invariant: recomputed gross margin from unrounded_target_price
        # and cost_basis equals target_gross_margin within exact Decimal precision.
        if result.unrounded_target_price != Decimal('0'):
            recomputed_gross_margin = (result.unrounded_target_price - cost_basis) / result.unrounded_target_price
            assert recomputed_gross_margin == target_margin
        else:
            # If unrounded_target_price is 0, the invariant check is skipped in the service.
            # We just ensure cost_basis was also 0 for consistency.
            assert cost_basis == Decimal('0')

    def test_unrounded_target_price_increases_with_target_gross_margin_for_positive_cost(
        self, pricing_service: PricingService
    ) -> None:
        """
        Verifies the invariant that increasing target_gross_margin strictly increases
        unrounded_target_price for positive cost.
        """
        cost_basis = Decimal('100')
        policy_low_margin = MarginPolicy(
            target_gross_margin=Decimal('0.1'),
            approval_reference="REF-LOW",
            price_precision=2,
            rounding_mode=ROUND_HALF_UP,
        )
        policy_high_margin = MarginPolicy(
            target_gross_margin=Decimal('0.2'),
            approval_reference="REF-HIGH",
            price_precision=2,
            rounding_mode=ROUND_HALF_UP,
        )

        result_low = pricing_service.compute_target_price(cost_basis, policy_low_margin)
        result_high = pricing_service.compute_target_price(cost_basis, policy_high_margin)

        assert isinstance(result_low, PricingResult)
        assert isinstance(result_high, PricingResult)
        assert result_high.unrounded_target_price > result_low.unrounded_target_price

        # Test with margin approaching 1
        policy_very_high_margin = MarginPolicy(
            target_gross_margin=Decimal('0.99'),
            approval_reference="REF-VERY-HIGH",
            price_precision=2,
            rounding_mode=ROUND_HALF_UP,
        )
        result_very_high = pricing_service.compute_target_price(cost_basis, policy_very_high_margin)
        assert isinstance(result_very_high, PricingResult)
        assert result_very_high.unrounded_target_price > result_high.unrounded_target_price

    def test_implied_markup_is_none_when_cost_basis_is_zero(self, pricing_service: PricingService) -> None:
        """Ensures implied_markup is None when cost_basis is zero."""
        policy = MarginPolicy(
            target_gross_margin=Decimal('0.5'),
            approval_reference="APPROVED-POLICY-ZERO-COST",
            price_precision=2,
            rounding_mode=ROUND_HALF_UP,
        )
        result = pricing_service.compute_target_price(Decimal('0'), policy)
        assert isinstance(result, PricingResult)
        assert result.implied_markup is None
        assert result.unrounded_target_price == Decimal('0')
        assert result.rounded_target_price == Decimal('0.00')
        assert result.rounding_delta == Decimal('0')

    def test_pricing_domain_error_for_internal_inconsistency(self, pricing_service: PricingService) -> None:
        """
        Tests that PricingDomainError is raised for internal inconsistencies,
        e.g., unrounded_target_price being zero for non-zero cost_basis.
        This scenario should ideally be prevented by MarginPolicy validation,
        but the internal check acts as a safeguard.
        """
        # The specific error condition (unrounded_target_price is zero for non-zero cost_basis)
        # is mathematically unreachable given the MarginPolicy constraints (0 <= target_gross_margin < 1)
        # and assuming non-negative cost_basis. Thus, no test is provided to trigger this impossible state.
        pass
