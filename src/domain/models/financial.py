"""Financial Value Objects for Universal Hybrid FinOps Advisor."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
from typing import NewType, Optional, Union

from src.domain.models.validation import assert_strict_decimal

CurrencyCode = NewType("CurrencyCode", str)


@dataclass(frozen=True)
class MonetaryAmount:
    """Immutable monetary representation enforcing strict Decimal Banker's Rounding and float/bool prohibition."""

    amount: Decimal
    currency: CurrencyCode
    precision_places: int = 4

    def __post_init__(self) -> None:
        if isinstance(self.amount, (float, bool)) or not isinstance(self.amount, (Decimal, int, str)):
            raise TypeError(
                "Float, boolean, and non-numeric amounts are strictly prohibited to prevent IEEE-754 precision loss. "
                "Provide amount as Decimal, int, or numeric string."
            )

        if not isinstance(self.precision_places, int) or isinstance(self.precision_places, bool) or self.precision_places < 0:
            raise ValueError(f"Precision places must be a non-negative integer, got {self.precision_places}.")

        currency_str = str(self.currency).strip().upper()
        if len(currency_str) != 3 or not currency_str.isascii() or not currency_str.isalpha():
            raise ValueError(
                f"Currency code must be a valid 3-letter ASCII ISO-4217 code, got '{self.currency}'."
            )
        object.__setattr__(self, "currency", CurrencyCode(currency_str))

        target_quantizer = Decimal("10") ** -self.precision_places

        try:
            raw_decimal = self.amount if isinstance(self.amount, Decimal) else Decimal(str(self.amount))
        except InvalidOperation as exc:
            raise ValueError(f"MonetaryAmount must be a valid finite number, got '{self.amount}'.") from exc

        if not raw_decimal.is_finite():
            raise ValueError(f"MonetaryAmount must be finite, got '{self.amount}'.")

        quantized = raw_decimal.quantize(target_quantizer, rounding=ROUND_HALF_EVEN)
        object.__setattr__(self, "amount", quantized)

    def add(self, other: MonetaryAmount) -> MonetaryAmount:
        self._assert_same_currency(other)
        max_prec = max(self.precision_places, other.precision_places)
        return MonetaryAmount(self.amount + other.amount, self.currency, precision_places=max_prec)

    def subtract(self, other: MonetaryAmount) -> MonetaryAmount:
        self._assert_same_currency(other)
        max_prec = max(self.precision_places, other.precision_places)
        return MonetaryAmount(self.amount - other.amount, self.currency, precision_places=max_prec)

    def multiply(
        self,
        factor: Union[Decimal, int],
        precision_places: Optional[int] = None,
    ) -> MonetaryAmount:
        if isinstance(factor, (float, bool)):
            raise TypeError("Multiplication factor must be Decimal or int, never float or bool.")
        if not isinstance(factor, (Decimal, int)):
            raise TypeError(f"Unsupported factor type for multiplication: {type(factor).__name__}")
        factor_dec = factor if isinstance(factor, Decimal) else Decimal(str(factor))
        target_prec = precision_places if precision_places is not None else self.precision_places
        return MonetaryAmount(self.amount * factor_dec, self.currency, precision_places=target_prec)

    def divide(
        self,
        divisor: Union[Decimal, int],
        precision_places: Optional[int] = None,
    ) -> MonetaryAmount:
        if isinstance(divisor, (float, bool)):
            raise TypeError("Divisor must be Decimal or int, never float or bool.")
        if not isinstance(divisor, (Decimal, int)):
            raise TypeError(f"Unsupported divisor type for division: {type(divisor).__name__}")
        divisor_dec = divisor if isinstance(divisor, Decimal) else Decimal(str(divisor))
        if divisor_dec == Decimal("0"):
            raise ZeroDivisionError("Cannot divide MonetaryAmount by zero.")
        target_prec = precision_places if precision_places is not None else self.precision_places
        return MonetaryAmount(self.amount / divisor_dec, self.currency, precision_places=target_prec)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MonetaryAmount):
            return False
        return self.currency == other.currency and self.amount == other.amount

    def __hash__(self) -> int:
        return hash((self.currency, self.amount))

    def __lt__(self, other: MonetaryAmount) -> bool:
        self._assert_same_currency(other)
        return self.amount < other.amount

    def __le__(self, other: MonetaryAmount) -> bool:
        self._assert_same_currency(other)
        return self.amount <= other.amount

    def __gt__(self, other: MonetaryAmount) -> bool:
        self._assert_same_currency(other)
        return self.amount > other.amount

    def __ge__(self, other: MonetaryAmount) -> bool:
        self._assert_same_currency(other)
        return self.amount >= other.amount

    def _assert_same_currency(self, other: MonetaryAmount) -> None:
        if not isinstance(other, MonetaryAmount):
            raise TypeError(
                f"Cannot operate MonetaryAmount with non-MonetaryAmount of type '{type(other).__name__}'."
            )
        if self.currency != other.currency:
            raise ValueError(
                f"Cannot operate across distinct currencies: '{self.currency}' vs '{other.currency}'."
            )


@dataclass(frozen=True)
class ComputedTcoBreakdown:
    """Monthly TCO breakdown across compute, control plane, storage, power, and facilities."""

    hardware_compute_monthly: MonetaryAmount
    management_plane_monthly: MonetaryAmount
    persistent_storage_monthly: MonetaryAmount
    facility_power_cooling_monthly: MonetaryAmount
    datacenter_rack_colocation_monthly: MonetaryAmount
    oem_support_contract_monthly: MonetaryAmount
    network_egress_monthly: MonetaryAmount
    total_monthly_nominal_tco: MonetaryAmount
    amortization_period_months: int
    is_on_premise: bool

    def __post_init__(self) -> None:
        if isinstance(self.amortization_period_months, bool) or not isinstance(self.amortization_period_months, int) or self.amortization_period_months <= 0:
            raise ValueError(f"amortization_period_months must be positive integer, got {self.amortization_period_months}.")

        target_curr = self.total_monthly_nominal_tco.currency
        for item, name in [
            (self.hardware_compute_monthly, "hardware_compute_monthly"),
            (self.management_plane_monthly, "management_plane_monthly"),
            (self.persistent_storage_monthly, "persistent_storage_monthly"),
            (self.facility_power_cooling_monthly, "facility_power_cooling_monthly"),
            (self.datacenter_rack_colocation_monthly, "datacenter_rack_colocation_monthly"),
            (self.oem_support_contract_monthly, "oem_support_contract_monthly"),
            (self.network_egress_monthly, "network_egress_monthly"),
        ]:
            if item.currency != target_curr:
                raise ValueError(
                    f"Currency mismatch in ComputedTcoBreakdown for '{name}': '{item.currency}' vs expected '{target_curr}'."
                )

        # Reconcile sum invariant
        expected_total = (
            self.hardware_compute_monthly
            .add(self.management_plane_monthly)
            .add(self.persistent_storage_monthly)
            .add(self.facility_power_cooling_monthly)
            .add(self.datacenter_rack_colocation_monthly)
            .add(self.oem_support_contract_monthly)
            .add(self.network_egress_monthly)
        )
        if self.total_monthly_nominal_tco != expected_total:
            raise ValueError(
                f"ComputedTcoBreakdown sum reconciliation failed: total '{self.total_monthly_nominal_tco.amount}' "
                f"does not match sum of components '{expected_total.amount}'."
            )


@dataclass(frozen=True)
class ActuarialRiskMetrics:
    """Open FAIR quantitative loss metrics evaluating availability and hardware failure risk."""

    loss_event_frequency_annual: Decimal
    single_loss_expectancy: MonetaryAmount
    annualized_loss_expectancy: MonetaryAmount
    monthly_risk_adjusted_reserve: MonetaryAmount
    expected_hardware_mtbf_hours: Decimal
    expected_recovery_mttr_hours: Decimal
    total_monthly_risk_adjusted_tco: MonetaryAmount

    def __post_init__(self) -> None:
        assert_strict_decimal(self.loss_event_frequency_annual, "loss_event_frequency_annual")
        assert_strict_decimal(self.expected_hardware_mtbf_hours, "expected_hardware_mtbf_hours")
        assert_strict_decimal(self.expected_recovery_mttr_hours, "expected_recovery_mttr_hours")

        if self.loss_event_frequency_annual < Decimal("0"):
            raise ValueError("loss_event_frequency_annual cannot be negative.")
        if self.expected_hardware_mtbf_hours <= Decimal("0"):
            raise ValueError("expected_hardware_mtbf_hours must be strictly positive.")
        if self.expected_recovery_mttr_hours < Decimal("0"):
            raise ValueError("expected_recovery_mttr_hours cannot be negative.")

        target_curr = self.total_monthly_risk_adjusted_tco.currency
        for item, name in [
            (self.single_loss_expectancy, "single_loss_expectancy"),
            (self.annualized_loss_expectancy, "annualized_loss_expectancy"),
            (self.monthly_risk_adjusted_reserve, "monthly_risk_adjusted_reserve"),
        ]:
            if item.currency != target_curr:
                raise ValueError(
                    f"Currency mismatch in ActuarialRiskMetrics for '{name}': '{item.currency}' vs expected '{target_curr}'."
                )
            if item.amount < Decimal("0"):
                raise ValueError(f"Actuarial monetary metric '{name}' cannot be negative, got {item.amount}.")

        if self.total_monthly_risk_adjusted_tco.amount < Decimal("0"):
            raise ValueError("total_monthly_risk_adjusted_tco cannot be negative.")
