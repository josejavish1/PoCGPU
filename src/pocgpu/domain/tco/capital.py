import dataclasses
from datetime import datetime, timezone, timedelta
from typing import NewType, Self, Any

# --- Type Aliases (PEP 695) ---
# UtcInstant is a NewType for datetime, specifically for UTC timezone-aware datetimes.
UtcInstant = NewType('UtcInstant', datetime)

# Helper function to create UtcInstant
def create_utc_instant(dt: datetime) -> UtcInstant:
    """Ensures a datetime object is timezone-aware UTC."""
    if dt.tzinfo is None:
        raise InputRequiredError("Datetime must be timezone-aware.")
    if dt.tzinfo != timezone.utc:
        dt = dt.astimezone(timezone.utc)
    return UtcInstant(dt)

# --- Custom Exceptions ---
class CapitalAccountingError(Exception):
    """Base exception for capital accounting domain errors."""
    pass

class InputRequiredError(CapitalAccountingError):
    """Raised when required input data is missing or invalid."""
    pass

class PolicyRequiredError(CapitalAccountingError):
    """Raised when an accounting policy violation occurs."""
    pass

# --- Monetary Value Representation ---
@dataclasses.dataclass(frozen=True)
class MonetaryValue:
    """
    Represents a monetary amount with its currency and original invoice provenance.
    Enforces non-negative amounts.
    """
    amount: float
    currency_code: str
    invoice_id: str | None = None

    def __post_init__(self):
        if not isinstance(self.amount, (int, float)):
            raise InputRequiredError("Monetary amount must be a number.")
        if self.amount < 0:
            raise InputRequiredError("Monetary amount cannot be negative.")
        if not self.currency_code:
            raise InputRequiredError("Currency code is required.")
        if not isinstance(self.currency_code, str):
            raise InputRequiredError("Currency code must be a string.")
        if self.invoice_id is not None and not isinstance(self.invoice_id, str):
            raise InputRequiredError("Invoice ID must be a string or None.")

    def _check_currency(self, other: Self):
        if self.currency_code != other.currency_code:
            raise PolicyRequiredError(
                f"Cannot perform operation on monetary values of different currencies: "
                f"'{self.currency_code}' vs '{other.currency_code}'."
            )

    def __add__(self, other: Self) -> Self:
        if not isinstance(other, MonetaryValue):
            return NotImplemented
        self._check_currency(other)
        # When adding, if one has an invoice_id and the other doesn't, prefer the one that exists.
        # If both have, it implies a combined value, so invoice_id might become None or a list.
        # For simplicity, we'll just take the first non-None.
        new_invoice_id = self.invoice_id if self.invoice_id else other.invoice_id
        return MonetaryValue(self.amount + other.amount, self.currency_code, new_invoice_id)

    def __sub__(self, other: Self) -> Self:
        if not isinstance(other, MonetaryValue):
            return NotImplemented
        self._check_currency(other)
        new_invoice_id = self.invoice_id if self.invoice_id else other.invoice_id
        return MonetaryValue(self.amount - other.amount, self.currency_code, new_invoice_id)

    def __mul__(self, scalar: float) -> Self:
        if not isinstance(scalar, (int, float)):
            return NotImplemented
        return MonetaryValue(self.amount * scalar, self.currency_code, self.invoice_id)

    def __truediv__(self, scalar: float) -> Self:
        if not isinstance(scalar, (int, float)):
            return NotImplemented
        if scalar == 0:
            raise InputRequiredError("Cannot divide monetary value by zero.")
        return MonetaryValue(self.amount / scalar, self.currency_code, self.invoice_id)

    def __ge__(self, other: Self) -> bool:
        if not isinstance(other, MonetaryValue):
            return NotImplemented
        self._check_currency(other)
        return self.amount >= other.amount

    def __le__(self, other: Self) -> bool:
        if not isinstance(other, MonetaryValue):
            return NotImplemented
        self._check_currency(other)
        return self.amount <= other.amount

    def __lt__(self, other: Self) -> bool:
        if not isinstance(other, MonetaryValue):
            return NotImplemented
        self._check_currency(other)
        return self.amount < other.amount

    def __gt__(self, other: Self) -> bool:
        if not isinstance(other, MonetaryValue):
            return NotImplemented
        self._check_currency(other)
        return self.amount > other.amount

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MonetaryValue):
            return NotImplemented
        return self.amount == other.amount and self.currency_code == other.currency_code

    def __hash__(self) -> int:
        return hash((self.amount, self.currency_code))

# --- Accounting Policy ---
@dataclasses.dataclass(frozen=True)
class AccountingPolicy:
    """
    Defines policies for capital accounting, including rates for economic capital charge
    and partial-period conventions.
    """
    economic_capital_rate_nominal: float
    economic_capital_rate_real: float
    partial_period_convention: str # e.g., "full_month", "half_month", "actual_days"

    def __post_init__(self):
        if not isinstance(self.economic_capital_rate_nominal, (int, float)):
            raise InputRequiredError("Nominal economic capital rate must be a number.")
        if not (0 <= self.economic_capital_rate_nominal <= 1):
            raise PolicyRequiredError("Nominal economic capital rate must be between 0 and 1 (inclusive).")
        if not isinstance(self.economic_capital_rate_real, (int, float)):
            raise InputRequiredError("Real economic capital rate must be a number.")
        if not (0 <= self.economic_capital_rate_real <= 1):
            raise PolicyRequiredError("Real economic capital rate must be between 0 and 1 (inclusive).")
        if not isinstance(self.partial_period_convention, str):
            raise InputRequiredError("Partial period convention must be a string.")
        if self.partial_period_convention not in ["full_month", "half_month", "actual_days"]:
            raise PolicyRequiredError(f"Invalid partial period convention: '{self.partial_period_convention}'. "
                                      "Supported conventions are 'full_month', 'half_month', 'actual_days'.")

# --- Asset Record ---
@dataclasses.dataclass(frozen=True)
class AssetRecord:
    """
    Represents an asset for capital accounting, storing its acquisition, installation,
    and other relevant financial details.
    """
    asset_id: str
    acquisition_cost: MonetaryValue
    installation_cost: MonetaryValue
    topology_quantity: float # Represents "Phase 2 immutable topology quantities"
    residual_value: MonetaryValue
    useful_life_months: int
    acquisition_date: UtcInstant # For partial period conventions, if needed later

    def __post_init__(self):
        if not isinstance(self.asset_id, str):
            raise InputRequiredError("Asset ID must be a string.")
        if not self.asset_id:
            raise InputRequiredError("Asset ID is required.")
        if not isinstance(self.topology_quantity, (int, float)):
            raise InputRequiredError("Topology quantity must be a number.")
        if self.topology_quantity <= 0:
            raise InputRequiredError("Topology quantity must be positive.")
        if not isinstance(self.useful_life_months, int):
            raise InputRequiredError("Useful life in months must be an integer.")
        if self.useful_life_months <= 0:
            raise InputRequiredError("Useful life in months must be positive.")
        if not isinstance(self.acquisition_date, datetime) or self.acquisition_date.tzinfo != timezone.utc:
            raise InputRequiredError("Acquisition date must be a timezone-aware UTC datetime.")

        # Ensure currency consistency for costs
        if self.acquisition_cost.currency_code != self.installation_cost.currency_code:
            raise PolicyRequiredError("Acquisition and installation costs must be in the same currency.")
        if self.acquisition_cost.currency_code != self.residual_value.currency_code:
            raise PolicyRequiredError("Acquisition cost and residual value must be in the same currency.")

    def calculate_capitalized_cost(self) -> MonetaryValue:
        """
        Computes the capitalized cost from acquisition and installation components
        scaled by Phase 2 immutable topology quantities.
        Enforces capitalized_cost >= 0.
        """
        combined_cost = self.acquisition_cost + self.installation_cost
        capitalized_cost = combined_cost * self.topology_quantity

        # The MonetaryValue.__post_init__ already ensures amount >= 0.
        # If topology_quantity is positive, and combined_cost is positive, capitalized_cost will be positive.
        # Given topology_quantity is validated to be > 0, this check is mostly for robustness.
        if capitalized_cost.amount < 0:
            raise PolicyRequiredError("Calculated capitalized cost cannot be negative.")
        return capitalized_cost

    def calculate_monthly_depreciation(self) -> MonetaryValue:
        """
        Calculates monthly depreciation: (capitalized_cost - residual_value) / useful_life_months.
        Enforces domain invariants: residual_value <= capitalized_cost.
        """
        capitalized_cost = self.calculate_capitalized_cost()

        if self.residual_value > capitalized_cost:
            raise PolicyRequiredError("Residual value cannot exceed capitalized cost.")

        depreciable_base = capitalized_cost - self.residual_value
        # depreciable_base.amount should be >= 0 due to the check above.
        if depreciable_base.amount < 0: # Redundant but safe check
            raise PolicyRequiredError("Depreciable base cannot be negative after subtracting residual value.")

        # useful_life_months is already validated to be > 0 in __post_init__
        monthly_depreciation = depreciable_base / float(self.useful_life_months)

        return monthly_depreciation

    def calculate_economic_capital_charge(self, policy: AccountingPolicy, use_real_rate: bool = False) -> MonetaryValue:
        """
        Computes economic capital charge using governed nominal or real rates from AccountingPolicy.
        This is a completely separate view from accounting depreciation.
        """
        capitalized_cost = self.calculate_capitalized_cost()
        rate = policy.economic_capital_rate_real if use_real_rate else policy.economic_capital_rate_nominal
        economic_charge_amount = capitalized_cost.amount * rate
        # The economic charge should also carry the currency and provenance of the capitalized cost.
        return MonetaryValue(economic_charge_amount, capitalized_cost.currency_code, capitalized_cost.invoice_id)

    def calculate_partial_period_depreciation(self, policy: AccountingPolicy, period_start: UtcInstant, period_end: UtcInstant) -> MonetaryValue:
        """
        Computes depreciation for a partial period based on the provided policy.
        This is a placeholder and would require detailed implementation based on
        the 'partial_period_convention' from AccountingPolicy.
        """
        if not isinstance(period_start, datetime) or period_start.tzinfo != timezone.utc:
            raise InputRequiredError("Period start date must be a timezone-aware UTC datetime.")
        if not isinstance(period_end, datetime) or period_end.tzinfo != timezone.utc:
            raise InputRequiredError("Period end date must be a timezone-aware UTC datetime.")
        if period_start >= period_end:
            raise InputRequiredError("Period start date must be before period end date.")

        monthly_depreciation = self.calculate_monthly_depreciation()

        if policy.partial_period_convention == "full_month":
            # This convention typically means if an asset is active for any part of the month,
            # a full month's depreciation is taken. For this simplified method, we'll assume
            # the period_start/end implies a full month's eligibility.
            return monthly_depreciation
        elif policy.partial_period_convention == "half_month":
            # This convention typically means half a month's depreciation for partial months.
            # For simplicity, we'll just return half the monthly depreciation.
            return monthly_depreciation / 2.0
        elif policy.partial_period_convention == "actual_days":
            # This requires calculating the number of days in the period relative to days in a typical month.
            # For a robust implementation, we'd need to know the specific month.
            # Let's assume a standard month length for calculation for now, e.g., 30 days.
            # This is a simplification and would need more context for a real-world scenario.
            days_in_period = (period_end - period_start).days
            # A common simplification for "actual_days" is to use 30 or 31 days as the denominator,
            # or the actual days in the specific month. Let's use 30 for now.
            days_in_average_month = 30.0
            if days_in_average_month <= 0: # Defensive check
                raise PolicyRequiredError("Days in average month must be positive for depreciation calculation.")
            return monthly_depreciation * (days_in_period / days_in_average_month)
        else:
            # This case should ideally be caught by AccountingPolicy.__post_init__
            raise PolicyRequiredError(f"Unsupported partial period convention: '{policy.partial_period_convention}'.")
