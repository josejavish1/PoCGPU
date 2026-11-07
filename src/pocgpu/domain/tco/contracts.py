import datetime
import enum
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Literal, Mapping, NewType, Self, TypeAlias

# Type aliases for clarity and domain purity
CurrencyCode: TypeAlias = str
UtcInstant: TypeAlias = datetime.datetime

# --- Enums ---

class CostClass(enum.Enum):
    """
    Defines the canonical categories for Total Cost of Ownership (TCO) components.
    """
    ASSET_DEPRECIATION = "ASSET_DEPRECIATION"
    CAPITAL_CHARGE = "CAPITAL_CHARGE"
    FACILITY = "FACILITY"
    COLOCATION = "COLOCATION"
    ENERGY = "ENERGY"
    COOLING = "COOLING"
    NETWORK = "NETWORK"
    STORAGE = "STORAGE"
    SOFTWARE = "SOFTWARE"
    SUPPORT = "SUPPORT"
    MAINTENANCE = "MAINTENANCE"
    LABOR = "LABOR"
    SECURITY = "SECURITY"
    COMPLIANCE = "COMPLIANCE"
    INSURANCE = "INSURANCE"
    DECOMMISSIONING = "DECOMMISSIONING"

class CostDisposition(enum.Enum):
    """
    Specifies how a CostClass is treated within a CostBoundary.
    """
    INCLUDED = "INCLUDED"
    EXCLUDED = "EXCLUDED"
    NOT_APPLICABLE = "NOT_APPLICABLE"

# --- Exceptions ---

class PolicyViolationError(ValueError):
    """
    Raised when a defined policy is violated, indicating a configuration or data integrity issue.
    """
    pass

# --- Domain Models ---

@dataclass(frozen=True, kw_only=True)
class CostBoundary:
    """
    Defines the explicit disposition for every canonical CostClass, ensuring strict boundary completeness.
    """
    dispositions: Mapping[CostClass, tuple[CostDisposition, str | None]]

    def __post_init__(self) -> None:
        """
        Enforces strict boundary completeness and rationale requirements.
        """
        # Ensure every canonical CostClass has an explicit disposition
        defined_classes = set(self.dispositions.keys())
        all_cost_classes = set(CostClass)

        missing_classes = all_cost_classes - defined_classes
        if missing_classes:
            raise PolicyViolationError(
                f"POLICY_REQUIRED: CostBoundary is incomplete. Missing dispositions for: "
                f"{", ".join(c.value for c in sorted(list(missing_classes), key=lambda x: x.value))}"
            )

        # Ensure no extra classes are defined (e.g., invalid CostClass enum members)
        extra_classes = defined_classes - all_cost_classes
        if extra_classes:
            raise PolicyViolationError(
                f"POLICY_REQUIRED: CostBoundary contains undefined CostClasses: "
                f"{", ".join(c.value for c in sorted(list(extra_classes), key=lambda x: x.value))}"
            )

        # Enforce rationale for EXCLUDED classes and prevent rationale for others
        for cost_class, (disposition, rationale) in self.dispositions.items():
            if disposition is CostDisposition.EXCLUDED and not rationale:
                raise PolicyViolationError(
                    f"POLICY_REQUIRED: CostClass '{cost_class.value}' is EXCLUDED but requires a non-empty rationale."
                )
            if disposition is not CostDisposition.EXCLUDED and rationale:
                raise PolicyViolationError(
                    f"POLICY_REQUIRED: CostClass '{cost_class.value}' has a rationale but is not EXCLUDED. "
                    f"Rationale should only be provided for EXCLUDED dispositions."
                )

@dataclass(frozen=True, kw_only=True)
class CostRecord:
    """
    Represents a single record of a cost incurred.
    """
    amount: Decimal
    currency: CurrencyCode
    cost_class: CostClass
    timestamp: UtcInstant
    description: str

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            raise TypeError("Amount must be a Decimal.")
        if self.amount < Decimal('0'):
            raise ValueError("Amount cannot be negative.")
        if not self.currency:
            raise ValueError("Currency cannot be empty.")
        if not isinstance(self.timestamp, datetime.datetime) or self.timestamp.tzinfo is None:
            raise ValueError("Timestamp must be a timezone-aware UtcInstant.")
        if not self.description:
            raise ValueError("Description cannot be empty.")

@dataclass(frozen=True, kw_only=True)
class AssetRecord:
    """
    Represents a record of an asset, including its acquisition and depreciation details.
    """
    asset_id: str
    description: str
    acquisition_cost: Decimal
    acquisition_currency: CurrencyCode
    acquisition_date: UtcInstant
    useful_life_years: int
    depreciation_method: str # e.g., "Straight-line", "Declining balance"

    def __post_init__(self) -> None:
        if not self.asset_id:
            raise ValueError("Asset ID cannot be empty.")
        if not self.description:
            raise ValueError("Description cannot be empty.")
        if not isinstance(self.acquisition_cost, Decimal):
            raise TypeError("Acquisition cost must be a Decimal.")
        if self.acquisition_cost < Decimal('0'):
            raise ValueError("Acquisition cost cannot be negative.")
        if not self.acquisition_currency:
            raise ValueError("Acquisition currency cannot be empty.")
        if not isinstance(self.acquisition_date, datetime.datetime) or self.acquisition_date.tzinfo is None:
            raise ValueError("Acquisition date must be a timezone-aware UtcInstant.")
        if self.useful_life_years <= 0:
            raise ValueError("Useful life years must be positive.")
        if not self.depreciation_method:
            raise ValueError("Depreciation method cannot be empty.")

@dataclass(frozen=True, kw_only=True)
class PowerObservation:
    """
    Represents an observation of power consumption or generation.
    """
    timestamp: UtcInstant
    power_value: Decimal # e.g., in kW
    unit: str # e.g., "kW", "kWh"

    def __post_init__(self) -> None:
        if not isinstance(self.timestamp, datetime.datetime) or self.timestamp.tzinfo is None:
            raise ValueError("Timestamp must be a timezone-aware UtcInstant.")
        if not isinstance(self.power_value, Decimal):
            raise TypeError("Power value must be a Decimal.")
        if self.power_value < Decimal('0'):
            raise ValueError("Power value cannot be negative.")
        if not self.unit:
            raise ValueError("Unit cannot be empty.")

@dataclass(frozen=True, kw_only=True)
class FacilityPolicy:
    """
    Defines policies specific to a physical facility or data center.
    """
    policy_id: str
    name: str
    description: str
    effective_date: UtcInstant
    details: Mapping[str, Any]

    def __post_init__(self) -> None:
        if not self.policy_id:
            raise ValueError("Policy ID cannot be empty.")
        if not self.name:
            raise ValueError("Name cannot be empty.")
        if not self.description:
            raise ValueError("Description cannot be empty.")
        if not isinstance(self.effective_date, datetime.datetime) or self.effective_date.tzinfo is None:
            raise ValueError("Effective date must be a timezone-aware UtcInstant.")

@dataclass(frozen=True, kw_only=True)
class AllocationPolicy:
    """
    Defines rules for allocating costs across different entities or departments.
    """
    policy_id: str
    name: str
    description: str
    effective_date: UtcInstant
    details: Mapping[str, Any]

    def __post_init__(self) -> None:
        if not self.policy_id:
            raise ValueError("Policy ID cannot be empty.")
        if not self.name:
            raise ValueError("Name cannot be empty.")
        if not self.description:
            raise ValueError("Description cannot be empty.")
        if not isinstance(self.effective_date, datetime.datetime) or self.effective_date.tzinfo is None:
            raise ValueError("Effective date must be a timezone-aware UtcInstant.")

@dataclass(frozen=True, kw_only=True)
class AccountingPolicy:
    """
    Defines accounting principles and rules applicable to TCO calculations.
    """
    policy_id: str
    name: str
    description: str
    effective_date: UtcInstant
    details: Mapping[str, Any]

    def __post_init__(self) -> None:
        if not self.policy_id:
            raise ValueError("Policy ID cannot be empty.")
        if not self.name:
            raise ValueError("Name cannot be empty.")
        if not self.description:
            raise ValueError("Description cannot be empty.")
        if not isinstance(self.effective_date, datetime.datetime) or self.effective_date.tzinfo is None:
            raise ValueError("Effective date must be a timezone-aware UtcInstant.")

@dataclass(frozen=True, kw_only=True)
class FxObservation:
    """
    Represents a foreign exchange rate observation at a specific point in time.
    """
    source_currency: CurrencyCode
    target_currency: CurrencyCode
    rate: Decimal # e.g., 1 USD = 0.9 EUR, so rate is 0.9
    observation_timestamp: UtcInstant

    def __post_init__(self) -> None:
        if not self.source_currency:
            raise ValueError("Source currency cannot be empty.")
        if not self.target_currency:
            raise ValueError("Target currency cannot be empty.")
        if self.source_currency == self.target_currency:
            raise ValueError("Source and target currencies cannot be the same for an FX observation.")
        if not isinstance(self.rate, Decimal):
            raise TypeError("Rate must be a Decimal.")
        if self.rate <= Decimal('0'):
            raise ValueError("FX rate must be positive.")
        if not isinstance(self.observation_timestamp, datetime.datetime) or self.observation_timestamp.tzinfo is None:
            raise ValueError("Observation timestamp must be a timezone-aware UtcInstant.")

@dataclass(frozen=True, kw_only=True)
class ConvertedAmount:
    """
    Represents a monetary amount converted from one currency to another,
    preserving original details and FX observation provenance.
    """
    original_amount: Decimal
    original_currency: CurrencyCode
    converted_amount: Decimal
    converted_currency: CurrencyCode
    fx_observation_provenance: FxObservation

    def __post_init__(self) -> None:
        if not isinstance(self.original_amount, Decimal):
            raise TypeError("Original amount must be a Decimal.")
        if not self.original_currency:
            raise ValueError("Original currency cannot be empty.")
        if not isinstance(self.converted_amount, Decimal):
            raise TypeError("Converted amount must be a Decimal.")
        if not self.converted_currency:
            raise ValueError("Converted currency cannot be empty.")
        if not isinstance(self.fx_observation_provenance, FxObservation):
            raise TypeError("FX observation provenance must be an FxObservation instance.")
        if self.original_currency == self.converted_currency:
            raise ValueError("Original and converted currencies cannot be the same for a ConvertedAmount.")
        if self.original_currency != self.fx_observation_provenance.source_currency:
            raise ValueError(
                f"Original currency '{self.original_currency}' does not match FX observation source currency "
                f"'{self.fx_observation_provenance.source_currency}'."
            )
        if self.converted_currency != self.fx_observation_provenance.target_currency:
            raise ValueError(
                f"Converted currency '{self.converted_currency}' does not match FX observation target currency "
                f"'{self.fx_observation_provenance.target_currency}'."
            )

    @classmethod
    def from_amount_and_fx(
        cls,
        amount: Decimal,
        currency: CurrencyCode,
        fx_observation: FxObservation,
        target_currency: CurrencyCode | None = None,
        stale_threshold_seconds: int | None = None,
    ) -> Self:
        """
        Performs a deterministic currency conversion using the provided FX observation.

        Fails closed on missing or stale FX observations.
        If target_currency is not provided, it defaults to the fx_observation's target_currency.
        """
        if not isinstance(amount, Decimal):
            raise TypeError("Amount must be a Decimal.")
        if amount < Decimal('0'):
            raise ValueError("Amount cannot be negative.")
        if not currency:
            raise ValueError("Currency cannot be empty.")
        if not isinstance(fx_observation, FxObservation):
            raise TypeError("FX observation must be an FxObservation instance.")

        if currency != fx_observation.source_currency:
            raise PolicyViolationError(
                f"FX observation source currency '{fx_observation.source_currency}' does not match "
                f"the amount's currency '{currency}'."
            )

        effective_target_currency = target_currency if target_currency is not None else fx_observation.target_currency
        if effective_target_currency != fx_observation.target_currency:
            raise PolicyViolationError(
                f"Requested target currency '{effective_target_currency}' does not match "
                f"FX observation target currency '{fx_observation.target_currency}'."
            )

        if stale_threshold_seconds is not None:
            if not isinstance(stale_threshold_seconds, int) or stale_threshold_seconds < 0:
                raise ValueError("Stale threshold seconds must be a non-negative integer or None.")
            now_utc = datetime.datetime.now(datetime.timezone.utc)
            time_since_observation = now_utc - fx_observation.observation_timestamp
            if int(time_since_observation.total_seconds()) > stale_threshold_seconds:
                raise PolicyViolationError(
                    f"FX observation is stale. Observed {fx_observation.observation_timestamp} "
                    f"is older than {stale_threshold_seconds} seconds from {now_utc}."
                )

        converted_value = amount * fx_observation.rate

        return cls(
            original_amount=amount,
            original_currency=currency,
            converted_amount=converted_value,
            converted_currency=effective_target_currency,
            fx_observation_provenance=fx_observation,
        )
