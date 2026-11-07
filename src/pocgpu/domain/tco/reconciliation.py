import datetime
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Dict, List, NewType, Optional, Set
from uuid import UUID, uuid4

# Type Aliases
UtcInstant = NewType("UtcInstant", datetime.datetime)
CurrencyCode = NewType("CurrencyCode", str)
CostAmount = NewType("CostAmount", Decimal)


class CostCategory(Enum):
    """Defines the distinct categories for TCO cost components."""
    DEPRECIATION = "DEPRECIATION"
    CAPITAL_CHARGE = "CAPITAL_CHARGE"
    FIXED_OPEX = "FIXED_OPEX"
    VARIABLE_OPEX = "VARIABLE_OPEX"
    ONE_OFF_ALLOCATION = "ONE_OFF_ALLOCATION"
    RISK_ADJUSTMENT = "RISK_ADJUSTMENT"
    CASH_OUTFLOW = "CASH_OUTFLOW"


CostCategory.NOMINAL_COMPONENTS = {
    CostCategory.DEPRECIATION,
    CostCategory.CAPITAL_CHARGE,
    CostCategory.FIXED_OPEX,
    CostCategory.VARIABLE_OPEX,
    CostCategory.ONE_OFF_ALLOCATION,
}

CostCategory.ACCOUNTING_EXPENSE_COMPONENTS = {
    CostCategory.DEPRECIATION,
    CostCategory.FIXED_OPEX,
    CostCategory.VARIABLE_OPEX,
    CostCategory.ONE_OFF_ALLOCATION,
}


@dataclass(frozen=True, init=False)
class CostRecord:
    """
    Represents a single, immutable cost entry for TCO reconciliation.
    Enforces positive cost monotonicity for core components.
    """
    category: CostCategory
    amount: CostAmount
    currency: CurrencyCode
    effective_date: UtcInstant
    description: str
    record_id: UUID
    source_id: UUID
    is_allocated: bool
    original_record_id: Optional[UUID]

    def __init__(
        self,
        category: CostCategory,
        amount: CostAmount,
        currency: CurrencyCode,
        effective_date: UtcInstant,
        description: str,
        record_id: Optional[UUID] = None,
        source_id: Optional[UUID] = None,
        is_allocated: bool = False,
        original_record_id: Optional[UUID] = None,
    ) -> None:
        resolved_amount = amount if isinstance(amount, Decimal) else Decimal(str(amount))
        resolved_currency = currency if isinstance(currency, str) else str(currency)
        resolved_record_id = uuid4() if record_id is None else record_id
        resolved_source_id = uuid4() if source_id is None else source_id

        object.__setattr__(self, "category", category)
        object.__setattr__(self, "amount", CostAmount(resolved_amount))
        object.__setattr__(self, "currency", CurrencyCode(resolved_currency))
        object.__setattr__(self, "effective_date", effective_date)
        object.__setattr__(self, "description", description)
        object.__setattr__(self, "record_id", resolved_record_id)
        object.__setattr__(self, "source_id", resolved_source_id)
        object.__setattr__(self, "is_allocated", is_allocated)
        object.__setattr__(self, "original_record_id", original_record_id)
        self.__post_init__()

    def __post_init__(self) -> None:
        if not isinstance(self.effective_date, datetime.datetime):
            raise TypeError("effective_date must be a datetime.datetime object.")
        if self.effective_date.tzinfo is None or self.effective_date.tzinfo.utcoffset(self.effective_date) is None:
            raise ValueError("effective_date must be timezone-aware.")

        if self.category != CostCategory.RISK_ADJUSTMENT and self.amount < 0:
            raise ValueError(
                f"Cost amount for category {self.category.name} must be non-negative. Received: {self.amount}"
            )

        if self.is_allocated and self.original_record_id is None:
            raise ValueError("Allocated records must specify an original_record_id.")
        if not self.is_allocated and self.original_record_id is not None:
            raise ValueError("Non-allocated records must not specify an original_record_id.")


@dataclass(frozen=True)
class TcoResult:
    """
    Aggregated TCO views and detailed breakdown for a specific period.
    All amounts are reconciled to the original currencies.
    """
    nominal_tco: Dict[CurrencyCode, CostAmount]
    risk_adjusted_tco: Dict[CurrencyCode, CostAmount]
    accounting_expense_view: Dict[CurrencyCode, CostAmount]
    cash_outflow_view: Dict[CurrencyCode, CostAmount]
    detailed_breakdown: Dict[CostCategory, Dict[CurrencyCode, CostAmount]]
    reconciliation_ledger: List[CostRecord]


class TcoReconciliationService:
    """
    Service for calculating and reconciling Total Cost of Ownership (TCO)
    based on a collection of cost records.
    Enforces strict prevention of duplicate source record attribution across cost classes.
    """

    def __init__(self, records: List[CostRecord]) -> None:
        """
        Initializes the service with a list of cost records.
        Performs initial validation for duplicate record and source attribution.
        """
        self._records = records
        self._validate_records()

    def _validate_records(self) -> None:
        """
        Validates the input records for duplicate record_id and source_id.
        Duplicate source record attribution is strictly prevented across cost classes
        by enforcing unique source_id for all records.
        """
        seen_record_ids: Set[UUID] = set()
        seen_source_ids: Set[UUID] = set()

        for record in self._records:
            if record.record_id in seen_record_ids:
                raise ValueError(
                    f"Duplicate record_id found: {record.record_id}. Each record must have a unique ID."
                )
            seen_record_ids.add(record.record_id)

            if record.source_id in seen_source_ids:
                raise ValueError(
                    f"Duplicate source_id found: {record.source_id}. Each source must have a unique ID across all records to prevent duplicate attribution."
                )
            seen_source_ids.add(record.source_id)

    def calculate_tco(self) -> TcoResult:
        """
        Calculates the various TCO views and provides a detailed breakdown.
        Ensures exact Decimal ledger reconciliation across components and currencies.
        """
        nominal_tco: Dict[CurrencyCode, CostAmount] = {}
        risk_adjusted_tco: Dict[CurrencyCode, CostAmount] = {}
        accounting_expense_view: Dict[CurrencyCode, CostAmount] = {}
        cash_outflow_view: Dict[CurrencyCode, CostAmount] = {}
        detailed_breakdown: Dict[CostCategory, Dict[CurrencyCode, CostAmount]] = {
            category: {} for category in CostCategory
        }

        for record in self._records:
            currency = record.currency
            amount = record.amount
            category = record.category

            nominal_tco.setdefault(currency, CostAmount(Decimal("0")))
            accounting_expense_view.setdefault(currency, CostAmount(Decimal("0")))
            cash_outflow_view.setdefault(currency, CostAmount(Decimal("0")))

            detailed_breakdown[category].setdefault(currency, CostAmount(Decimal("0")))
            detailed_breakdown[category][currency] = CostAmount(
                detailed_breakdown[category][currency] + amount
            )

            if category in CostCategory.NOMINAL_COMPONENTS:
                nominal_tco[currency] = CostAmount(nominal_tco[currency] + amount)

            if category in CostCategory.ACCOUNTING_EXPENSE_COMPONENTS:
                accounting_expense_view[currency] = CostAmount(
                    accounting_expense_view[currency] + amount
                )

            if category == CostCategory.CASH_OUTFLOW:
                cash_outflow_view[currency] = CostAmount(
                    cash_outflow_view[currency] + amount
                )

        risk_adjustments_by_currency: Dict[CurrencyCode, CostAmount] = (
            detailed_breakdown.get(CostCategory.RISK_ADJUSTMENT, {})
        )

        risk_adjusted_tco = nominal_tco.copy()
        for currency, adjustment_amount in risk_adjustments_by_currency.items():
            risk_adjusted_tco.setdefault(currency, CostAmount(Decimal("0")))
            risk_adjusted_tco[currency] = CostAmount(
                risk_adjusted_tco[currency] + adjustment_amount
            )

        for currency_dict in [
            nominal_tco,
            risk_adjusted_tco,
            accounting_expense_view,
            cash_outflow_view,
        ]:
            for k, v in currency_dict.items():
                currency_dict[k] = CostAmount(v)

        for category_dict in detailed_breakdown.values():
            for k, v in category_dict.items():
                category_dict[k] = CostAmount(v)

        return TcoResult(
            nominal_tco=nominal_tco,
            risk_adjusted_tco=risk_adjusted_tco,
            accounting_expense_view=accounting_expense_view,
            cash_outflow_view=cash_outflow_view,
            detailed_breakdown=detailed_breakdown,
            reconciliation_ledger=sorted(
                self._records, key=lambda r: r.effective_date
            ),
        )
