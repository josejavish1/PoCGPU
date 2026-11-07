import datetime
import pytest
from decimal import Decimal
from uuid import UUID, uuid4

from src.pocgpu.domain.tco.reconciliation import (
    CostAmount,
    CostCategory,
    CostRecord,
    CurrencyCode,
    TcoReconciliationService,
    TcoResult,
    UtcInstant,
)

# Helper for creating timezone-aware datetimes
def create_utc_instant(
    year: int, month: int, day: int, hour: int = 0, minute: int = 0, second: int = 0
) -> UtcInstant:
    return UtcInstant(datetime.datetime(year, month, day, hour, minute, second, tzinfo=datetime.timezone.utc))

# Test CostRecord
def test_cost_record_creation_valid():
    record = CostRecord(
        category=CostCategory.DEPRECIATION,
        amount=CostAmount(Decimal("100.50")),
        currency=CurrencyCode("USD"),
        effective_date=create_utc_instant(2023, 1, 15),
        description="Monthly depreciation"
    )
    assert isinstance(record.record_id, UUID)
    assert isinstance(record.source_id, UUID)
    assert record.category == CostCategory.DEPRECIATION
    assert record.amount == Decimal("100.50")
    assert record.currency == "USD"
    assert record.effective_date.year == 2023
    assert record.effective_date.tzinfo is not None
    assert record.description == "Monthly depreciation"
    assert not record.is_allocated
    assert record.original_record_id is None

def test_cost_record_creation_with_defaults():
    record = CostRecord(
        category=CostCategory.FIXED_OPEX,
        amount=CostAmount(Decimal("500")),
        currency=CurrencyCode("EUR"),
        effective_date=create_utc_instant(2023, 2, 1),
        description="Fixed Opex"
    )
    assert isinstance(record.record_id, UUID)
    assert isinstance(record.source_id, UUID)
    assert not record.is_allocated
    assert record.original_record_id is None

def test_cost_record_non_negative_amount_enforcement():
    with pytest.raises(ValueError, match="Cost amount for category DEPRECIATION must be non-negative"):
        CostRecord(
            category=CostCategory.DEPRECIATION,
            amount=CostAmount(Decimal("-10.00")),
            currency=CurrencyCode("USD"),
            effective_date=create_utc_instant(2023, 1, 1),
            description="Invalid depreciation"
        )

def test_cost_record_negative_amount_allowed_for_risk_adjustment():
    record = CostRecord(
        category=CostCategory.RISK_ADJUSTMENT,
        amount=CostAmount(Decimal("-25.00")),
        currency=CurrencyCode("USD"),
        effective_date=create_utc_instant(2023, 1, 1),
        description="Negative risk adjustment"
    )
    assert record.amount == Decimal("-25.00")

def test_cost_record_non_timezone_aware_date_raises_error():
    with pytest.raises(ValueError, match="effective_date must be timezone-aware"):
        CostRecord(
            category=CostCategory.DEPRECIATION,
            amount=CostAmount(Decimal("100")),
            currency=CurrencyCode("USD"),
            effective_date=UtcInstant(datetime.datetime(2023, 1, 1)), # Not timezone-aware
            description="Invalid date"
        )

def test_cost_record_allocated_requires_original_record_id():
    with pytest.raises(ValueError, match="Allocated records must specify an original_record_id"):
        CostRecord(
            category=CostCategory.ONE_OFF_ALLOCATION,
            amount=CostAmount(Decimal("10")),
            currency=CurrencyCode("USD"),
            effective_date=create_utc_instant(2023, 1, 1),
            description="Allocated cost",
            is_allocated=True,
            original_record_id=None # Missing
        )

def test_cost_record_non_allocated_no_original_record_id():
    with pytest.raises(ValueError, match="Non-allocated records must not specify an original_record_id"):
        CostRecord(
            category=CostCategory.DEPRECIATION,
            amount=CostAmount(Decimal("100")),
            currency=CurrencyCode("USD"),
            effective_date=create_utc_instant(2023, 1, 1),
            description="Depreciation",
            is_allocated=False,
            original_record_id=uuid4() # Present but shouldn't be
        )

def test_cost_record_allocated_valid():
    original_id = uuid4()
    record = CostRecord(
        category=CostCategory.ONE_OFF_ALLOCATION,
        amount=CostAmount(Decimal("10")),
        currency=CurrencyCode("USD"),
        effective_date=create_utc_instant(2023, 1, 1),
        description="Allocated cost",
        is_allocated=True,
        original_record_id=original_id
    )
    assert record.is_allocated
    assert record.original_record_id == original_id

# Test TcoReconciliationService validation
def test_service_rejects_duplicate_record_id():
    common_record_id = uuid4()
    record1 = CostRecord(
        record_id=common_record_id,
        category=CostCategory.DEPRECIATION,
        amount=CostAmount(Decimal("100")),
        currency=CurrencyCode("USD"),
        effective_date=create_utc_instant(2023, 1, 1),
        description="Depreciation 1"
    )
    record2 = CostRecord(
        record_id=common_record_id, # Duplicate
        category=CostCategory.FIXED_OPEX,
        amount=CostAmount(Decimal("50")),
        currency=CurrencyCode("USD"),
        effective_date=create_utc_instant(2023, 1, 1),
        description="Fixed Opex 1"
    )
    with pytest.raises(ValueError, match=f"Duplicate record_id found: {common_record_id}"):
        TcoReconciliationService([record1, record2])

def test_service_rejects_duplicate_source_id():
    common_source_id = uuid4()
    record1 = CostRecord(
        source_id=common_source_id,
        category=CostCategory.DEPRECIATION,
        amount=CostAmount(Decimal("100")),
        currency=CurrencyCode("USD"),
        effective_date=create_utc_instant(2023, 1, 1),
        description="Depreciation 1"
    )
    record2 = CostRecord(
        source_id=common_source_id, # Duplicate
        category=CostCategory.FIXED_OPEX,
        amount=CostAmount(Decimal("50")),
        currency=CurrencyCode("USD"),
        effective_date=create_utc_instant(2023, 1, 1),
        description="Fixed Opex 1"
    )
    with pytest.raises(ValueError, match=f"Duplicate source_id found: {common_source_id}. Each source must have a unique ID across all records to prevent duplicate attribution."):
        TcoReconciliationService([record1, record2])

def test_service_allows_different_source_ids_for_different_categories():
    record1 = CostRecord(
        source_id=uuid4(),
        category=CostCategory.DEPRECIATION,
        amount=CostAmount(Decimal("100")),
        currency=CurrencyCode("USD"),
        effective_date=create_utc_instant(2023, 1, 1),
        description="Depreciation 1"
    )
    record2 = CostRecord(
        source_id=uuid4(), # Different source ID
        category=CostCategory.FIXED_OPEX,
        amount=CostAmount(Decimal("50")),
        currency=CurrencyCode("USD"),
        effective_date=create_utc_instant(2023, 1, 1),
        description="Fixed Opex 1"
    )
    service = TcoReconciliationService([record1, record2])
    assert service is not None # No error raised

def test_service_allows_allocated_records_with_unique_source_id_and_original_id():
    original_cost_id = uuid4()
    original_record = CostRecord(
        record_id=original_cost_id,
        source_id=uuid4(),
        category=CostCategory.ONE_OFF_ALLOCATION,
        amount=CostAmount(Decimal("1200")),
        currency=CurrencyCode("USD"),
        effective_date=create_utc_instant(2022, 12, 1),
        description="Annual software license"
    )
    allocated_record_1 = CostRecord(
        source_id=uuid4(), # Unique source ID for allocation
        category=CostCategory.ONE_OFF_ALLOCATION,
        amount=CostAmount(Decimal("100")),
        currency=CurrencyCode("USD"),
        effective_date=create_utc_instant(2023, 1, 1),
        description="Jan allocation",
        is_allocated=True,
        original_record_id=original_cost_id
    )
    allocated_record_2 = CostRecord(
        source_id=uuid4(), # Unique source ID for allocation
        category=CostCategory.ONE_OFF_ALLOCATION,
        amount=CostAmount(Decimal("100")),
        currency=CurrencyCode("USD"),
        effective_date=create_utc_instant(2023, 2, 1),
        description="Feb allocation",
        is_allocated=True,
        original_record_id=original_cost_id
    )
    service = TcoReconciliationService([original_record, allocated_record_1, allocated_record_2])
    assert service is not None # No error raised

# Test TCO calculation logic
def test_tco_calculation_basic_single_currency():
    records = [
        CostRecord(category=CostCategory.DEPRECIATION, amount=CostAmount(Decimal("100")), currency=CurrencyCode("USD"), effective_date=create_utc_instant(2023, 1, 1), description="Depreciation"),
        CostRecord(category=CostCategory.CAPITAL_CHARGE, amount=CostAmount(Decimal("50")), currency=CurrencyCode("USD"), effective_date=create_utc_instant(2023, 1, 1), description="Capital Charge"),
        CostRecord(category=CostCategory.FIXED_OPEX, amount=CostAmount(Decimal("200")), currency=CurrencyCode("USD"), effective_date=create_utc_instant(2023, 1, 1), description="Fixed Opex"),
        CostRecord(category=CostCategory.VARIABLE_OPEX, amount=CostAmount(Decimal("75")), currency=CurrencyCode("USD"), effective_date=create_utc_instant(2023, 1, 1), description="Variable Opex"),
        CostRecord(category=CostCategory.ONE_OFF_ALLOCATION, amount=CostAmount(Decimal("25")), currency=CurrencyCode("USD"), effective_date=create_utc_instant(2023, 1, 1), description="One-off Allocation"),
        CostRecord(category=CostCategory.RISK_ADJUSTMENT, amount=CostAmount(Decimal("10")), currency=CurrencyCode("USD"), effective_date=create_utc_instant(2023, 1, 1), description="Positive Risk Adjustment"),
        CostRecord(category=CostCategory.CASH_OUTFLOW, amount=CostAmount(Decimal("300")), currency=CurrencyCode("USD"), effective_date=create_utc_instant(2023, 1, 1), description="Cash Outflow"),
    ]
    service = TcoReconciliationService(records)
    result = service.calculate_tco()

    # Nominal TCO = 100 + 50 + 200 + 75 + 25 = 450
    assert result.nominal_tco == {CurrencyCode("USD"): CostAmount(Decimal("450"))}

    # Risk-Adjusted TCO = Nominal TCO + Risk Adjustment = 450 + 10 = 460
    assert result.risk_adjusted_tco == {CurrencyCode("USD"): CostAmount(Decimal("460"))}

    # Accounting Expense View = Depreciation + Fixed Opex + Variable Opex + One-off Allocation = 100 + 200 + 75 + 25 = 400
    assert result.accounting_expense_view == {CurrencyCode("USD"): CostAmount(Decimal("400"))}

    # Cash Outflow View = 300
    assert result.cash_outflow_view == {CurrencyCode("USD"): CostAmount(Decimal("300"))}

    # Detailed Breakdown checks
    assert result.detailed_breakdown[CostCategory.DEPRECIATION] == {CurrencyCode("USD"): CostAmount(Decimal("100"))}
    assert result.detailed_breakdown[CostCategory.CAPITAL_CHARGE] == {CurrencyCode("USD"): CostAmount(Decimal("50"))}
    assert result.detailed_breakdown[CostCategory.FIXED_OPEX] == {CurrencyCode("USD"): CostAmount(Decimal("200"))}
    assert result.detailed_breakdown[CostCategory.VARIABLE_OPEX] == {CurrencyCode("USD"): CostAmount(Decimal("75"))}
    assert result.detailed_breakdown[CostCategory.ONE_OFF_ALLOCATION] == {CurrencyCode("USD"): CostAmount(Decimal("25"))}
    assert result.detailed_breakdown[CostCategory.RISK_ADJUSTMENT] == {CurrencyCode("USD"): CostAmount(Decimal("10"))}
    assert result.detailed_breakdown[CostCategory.CASH_OUTFLOW] == {CurrencyCode("USD"): CostAmount(Decimal("300"))}
    assert len(result.reconciliation_ledger) == 7

def test_tco_calculation_with_negative_risk_adjustment():
    records = [
        CostRecord(category=CostCategory.DEPRECIATION, amount=CostAmount(Decimal("100")), currency=CurrencyCode("USD"), effective_date=create_utc_instant(2023, 1, 1), description="Depreciation"),
        CostRecord(category=CostCategory.FIXED_OPEX, amount=CostAmount(Decimal("200")), currency=CurrencyCode("USD"), effective_date=create_utc_instant(2023, 1, 1), description="Fixed Opex"),
        CostRecord(category=CostCategory.RISK_ADJUSTMENT, amount=CostAmount(Decimal("-30")), currency=CurrencyCode("USD"), effective_date=create_utc_instant(2023, 1, 1), description="Negative Risk Adjustment"),
    ]
    service = TcoReconciliationService(records)
    result = service.calculate_tco()

    # Nominal TCO = 100 + 200 = 300
    assert result.nominal_tco == {CurrencyCode("USD"): CostAmount(Decimal("300"))}

    # Risk-Adjusted TCO = Nominal TCO + Risk Adjustment = 300 - 30 = 270
    assert result.risk_adjusted_tco == {CurrencyCode("USD"): CostAmount(Decimal("270"))}

    # Accounting Expense View = 100 + 200 = 300
    assert result.accounting_expense_view == {CurrencyCode("USD"): CostAmount(Decimal("300"))}

    assert result.detailed_breakdown[CostCategory.RISK_ADJUSTMENT] == {CurrencyCode("USD"): CostAmount(Decimal("-30"))}

def test_tco_calculation_multiple_currencies():
    records = [
        CostRecord(category=CostCategory.DEPRECIATION, amount=CostAmount(Decimal("100")), currency=CurrencyCode("USD"), effective_date=create_utc_instant(2023, 1, 1), description="Depreciation USD"),
        CostRecord(category=CostCategory.FIXED_OPEX, amount=CostAmount(Decimal("200")), currency=CurrencyCode("USD"), effective_date=create_utc_instant(2023, 1, 1), description="Fixed Opex USD"),
        CostRecord(category=CostCategory.DEPRECIATION, amount=CostAmount(Decimal("50")), currency=CurrencyCode("EUR"), effective_date=create_utc_instant(2023, 1, 1), description="Depreciation EUR"),
        CostRecord(category=CostCategory.VARIABLE_OPEX, amount=CostAmount(Decimal("75")), currency=CurrencyCode("EUR"), effective_date=create_utc_instant(2023, 1, 1), description="Variable Opex EUR"),
        CostRecord(category=CostCategory.RISK_ADJUSTMENT, amount=CostAmount(Decimal("10")), currency=CurrencyCode("USD"), effective_date=create_utc_instant(2023, 1, 1), description="Risk Adj USD"),
        CostRecord(category=CostCategory.RISK_ADJUSTMENT, amount=CostAmount(Decimal("-5")), currency=CurrencyCode("EUR"), effective_date=create_utc_instant(2023, 1, 1), description="Risk Adj EUR"),
        CostRecord(category=CostCategory.CASH_OUTFLOW, amount=CostAmount(Decimal("150")), currency=CurrencyCode("USD"), effective_date=create_utc_instant(2023, 1, 1), description="Cash Outflow USD"),
        CostRecord(category=CostCategory.CASH_OUTFLOW, amount=CostAmount(Decimal("80")), currency=CurrencyCode("EUR"), effective_date=create_utc_instant(2023, 1, 1), description="Cash Outflow EUR"),
    ]
    service = TcoReconciliationService(records)
    result = service.calculate_tco()

    # Nominal TCO USD = 100 (Dep) + 200 (Fixed Opex) = 300
    # Nominal TCO EUR = 50 (Dep) + 75 (Var Opex) = 125
    assert result.nominal_tco == {
        CurrencyCode("USD"): CostAmount(Decimal("300")),
        CurrencyCode("EUR"): CostAmount(Decimal("125")),
    }

    # Risk-Adjusted TCO USD = 300 + 10 = 310
    # Risk-Adjusted TCO EUR = 125 - 5 = 120
    assert result.risk_adjusted_tco == {
        CurrencyCode("USD"): CostAmount(Decimal("310")),
        CurrencyCode("EUR"): CostAmount(Decimal("120")),
    }

    # Accounting Expense View USD = 100 (Dep) + 200 (Fixed Opex) = 300
    # Accounting Expense View EUR = 50 (Dep) + 75 (Var Opex) = 125
    assert result.accounting_expense_view == {
        CurrencyCode("USD"): CostAmount(Decimal("300")),
        CurrencyCode("EUR"): CostAmount(Decimal("125")),
    }

    # Cash Outflow View USD = 150
    # Cash Outflow View EUR = 80
    assert result.cash_outflow_view == {
        CurrencyCode("USD"): CostAmount(Decimal("150")),
        CurrencyCode("EUR"): CostAmount(Decimal("80")),
    }

    assert result.detailed_breakdown[CostCategory.DEPRECIATION] == {
        CurrencyCode("USD"): CostAmount(Decimal("100")),
        CurrencyCode("EUR"): CostAmount(Decimal("50")),
    }
    assert result.detailed_breakdown[CostCategory.RISK_ADJUSTMENT] == {
        CurrencyCode("USD"): CostAmount(Decimal("10")),
        CurrencyCode("EUR"): CostAmount(Decimal("-5")),
    }

def test_tco_calculation_empty_records():
    service = TcoReconciliationService([])
    result = service.calculate_tco()

    assert result.nominal_tco == {}
    assert result.risk_adjusted_tco == {}
    assert result.accounting_expense_view == {}
    assert result.cash_outflow_view == {}
    assert result.detailed_breakdown == {category: {} for category in CostCategory}
    assert result.reconciliation_ledger == []

def test_tco_result_reconciliation_ledger_order_invariance():
    record1 = CostRecord(category=CostCategory.DEPRECIATION, amount=CostAmount(Decimal("100")), currency=CurrencyCode("USD"), effective_date=create_utc_instant(2023, 1, 15), description="Depreciation 1")
    record2 = CostRecord(category=CostCategory.FIXED_OPEX, amount=CostAmount(Decimal("50")), currency=CurrencyCode("USD"), effective_date=create_utc_instant(2023, 1, 1), description="Fixed Opex 1")
    record3 = CostRecord(category=CostCategory.VARIABLE_OPEX, amount=CostAmount(Decimal("25")), currency=CurrencyCode("USD"), effective_date=create_utc_instant(2023, 1, 20), description="Variable Opex 1")

    # Pass records in a specific order
    service = TcoReconciliationService([record1, record2, record3])
    result = service.calculate_tco()

    # The ledger should be sorted by effective_date
    expected_ledger_order = [record2, record1, record3]
    assert result.reconciliation_ledger == expected_ledger_order

    # Pass records in a different order
    service_reordered = TcoReconciliationService([record3, record1, record2])
    result_reordered = service_reordered.calculate_tco()
    assert result_reordered.reconciliation_ledger == expected_ledger_order

def test_tco_result_type_coercion():
    # Test that TcoResult ensures all amounts are CostAmount (Decimal)
    records = [
        CostRecord(category=CostCategory.DEPRECIATION, amount=CostAmount(Decimal("100")), currency=CurrencyCode("USD"), effective_date=create_utc_instant(2023, 1, 1), description="Depreciation"),
    ]
    service = TcoReconciliationService(records)
    result = service.calculate_tco()

    assert isinstance(result.nominal_tco[CurrencyCode("USD")], Decimal)
    assert isinstance(result.risk_adjusted_tco[CurrencyCode("USD")], Decimal)
    assert isinstance(result.accounting_expense_view[CurrencyCode("USD")], Decimal)
    assert isinstance(result.cash_outflow_view[CurrencyCode("USD")], Decimal)
    assert isinstance(result.detailed_breakdown[CostCategory.DEPRECIATION][CurrencyCode("USD")], Decimal)
