import pytest
from datetime import datetime, timezone, timedelta
import re # For re.escape

from src.pocgpu.domain.tco.capital import (
    MonetaryValue,
    AccountingPolicy,
    AssetRecord,
    InputRequiredError,
    PolicyRequiredError,
    create_utc_instant,
    UtcInstant
)

# Helper for creating UTC datetimes
def utc_dt(year: int, month: int, day: int, hour: int = 0, minute: int = 0, second: int = 0) -> UtcInstant:
    return create_utc_instant(datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc))

# --- Test MonetaryValue ---
class TestMonetaryValue:
    def test_creation_success(self):
        mv = MonetaryValue(100.50, "USD", "INV001")
        assert mv.amount == 100.50
        assert mv.currency_code == "USD"
        assert mv.invoice_id == "INV001"

    def test_creation_negative_amount_fails(self):
        with pytest.raises(InputRequiredError, match=re.escape("Monetary amount cannot be negative.")):
            MonetaryValue(-10.0, "USD")

    def test_creation_missing_currency_fails(self):
        with pytest.raises(InputRequiredError, match=re.escape("Currency code is required.")):
            MonetaryValue(10.0, "")

    def test_creation_non_numeric_amount_fails(self):
        with pytest.raises(InputRequiredError, match=re.escape("Monetary amount must be a number.")):
            MonetaryValue("10.0", "USD") # type: ignore

    def test_creation_non_string_currency_fails(self):
        with pytest.raises(InputRequiredError, match=re.escape("Currency code must be a string.")):
            MonetaryValue(10.0, 123) # type: ignore

    def test_creation_non_string_invoice_id_fails(self):
        with pytest.raises(InputRequiredError, match=re.escape("Invoice ID must be a string or None.")):
            MonetaryValue(10.0, "USD", 123) # type: ignore

    def test_addition_same_currency(self):
        mv1 = MonetaryValue(100.0, "USD", "INV001")
        mv2 = MonetaryValue(50.0, "USD", "INV002")
        result = mv1 + mv2
        assert result == MonetaryValue(150.0, "USD", "INV001") # Prefers first invoice_id

    def test_addition_different_currency_fails(self):
        mv1 = MonetaryValue(100.0, "USD")
        mv2 = MonetaryValue(50.0, "EUR")
        with pytest.raises(PolicyRequiredError, match=re.escape("Cannot perform operation on monetary values of different currencies: 'USD' vs 'EUR'.")):
            _ = mv1 + mv2

    def test_subtraction_same_currency(self):
        mv1 = MonetaryValue(100.0, "USD", "INV001")
        mv2 = MonetaryValue(50.0, "USD", "INV002")
        result = mv1 - mv2
        assert result == MonetaryValue(50.0, "USD", "INV001")

    def test_subtraction_different_currency_fails(self):
        mv1 = MonetaryValue(100.0, "USD")
        mv2 = MonetaryValue(50.0, "EUR")
        with pytest.raises(PolicyRequiredError, match=re.escape("Cannot perform operation on monetary values of different currencies: 'USD' vs 'EUR'.")):
            _ = mv1 - mv2

    def test_multiplication(self):
        mv = MonetaryValue(100.0, "USD", "INV001")
        result = mv * 2.5
        assert result == MonetaryValue(250.0, "USD", "INV001")

    def test_division(self):
        mv = MonetaryValue(100.0, "USD", "INV001")
        result = mv / 2.0
        assert result == MonetaryValue(50.0, "USD", "INV001")

    def test_division_by_zero_fails(self):
        mv = MonetaryValue(100.0, "USD")
        with pytest.raises(InputRequiredError, match=re.escape("Cannot divide monetary value by zero.")):
            _ = mv / 0.0

    def test_comparison_greater_than(self):
        mv1 = MonetaryValue(100.0, "USD")
        mv2 = MonetaryValue(50.0, "USD")
        assert mv1 > mv2
        assert not (mv2 > mv1)

    def test_comparison_less_than(self):
        mv1 = MonetaryValue(100.0, "USD")
        mv2 = MonetaryValue(50.0, "USD")
        assert mv2 < mv1
        assert not (mv1 < mv2)

    def test_comparison_equal(self):
        mv1 = MonetaryValue(100.0, "USD")
        mv2 = MonetaryValue(100.0, "USD")
        assert mv1 == mv2

    def test_comparison_different_currency_fails(self):
        mv1 = MonetaryValue(100.0, "USD")
        mv2 = MonetaryValue(100.0, "EUR")
        with pytest.raises(PolicyRequiredError, match=re.escape("Cannot perform operation on monetary values of different currencies: 'USD' vs 'EUR'.")):
            _ = mv1 > mv2

# --- Test AccountingPolicy ---
class TestAccountingPolicy:
    def test_creation_success(self):
        policy = AccountingPolicy(0.05, 0.02, "full_month")
        assert policy.economic_capital_rate_nominal == 0.05
        assert policy.economic_capital_rate_real == 0.02
        assert policy.partial_period_convention == "full_month"

    def test_nominal_rate_out_of_range_fails(self):
        with pytest.raises(PolicyRequiredError, match=re.escape("Nominal economic capital rate must be between 0 and 1 (inclusive).")):
            AccountingPolicy(1.1, 0.02, "full_month")
        with pytest.raises(PolicyRequiredError, match=re.escape("Nominal economic capital rate must be between 0 and 1 (inclusive).")):
            AccountingPolicy(-0.1, 0.02, "full_month")

    def test_real_rate_out_of_range_fails(self):
        with pytest.raises(PolicyRequiredError, match=re.escape("Real economic capital rate must be between 0 and 1 (inclusive).")):
            AccountingPolicy(0.05, 1.1, "full_month")
        with pytest.raises(PolicyRequiredError, match=re.escape("Real economic capital rate must be between 0 and 1 (inclusive).")):
            AccountingPolicy(0.05, -0.1, "full_month")

    def test_invalid_partial_period_convention_fails(self):
        with pytest.raises(PolicyRequiredError, match=re.escape("Invalid partial period convention: 'invalid_convention'. Supported conventions are 'full_month', 'half_month', 'actual_days'.")):
            AccountingPolicy(0.05, 0.02, "invalid_convention")

    def test_non_numeric_nominal_rate_fails(self):
        with pytest.raises(InputRequiredError, match=re.escape("Nominal economic capital rate must be a number.")):
            AccountingPolicy("0.05", 0.02, "full_month") # type: ignore

    def test_non_numeric_real_rate_fails(self):
        with pytest.raises(InputRequiredError, match=re.escape("Real economic capital rate must be a number.")):
            AccountingPolicy(0.05, "0.02", "full_month") # type: ignore

    def test_non_string_convention_fails(self):
        with pytest.raises(InputRequiredError, match=re.escape("Partial period convention must be a string.")):
            AccountingPolicy(0.05, 0.02, 123) # type: ignore

# --- Test AssetRecord ---
class TestAssetRecord:
    def setup_method(self):
        self.acquisition_cost = MonetaryValue(10000.0, "USD", "INV001")
        self.installation_cost = MonetaryValue(2000.0, "USD", "INV002")
        self.residual_value = MonetaryValue(1000.0, "USD", "INV003")
        self.topology_quantity = 1.5
        self.useful_life_months = 60
        self.acquisition_date = utc_dt(2023, 1, 15)

    def test_creation_success(self):
        asset = AssetRecord(
            asset_id="ASSET001",
            acquisition_cost=self.acquisition_cost,
            installation_cost=self.installation_cost,
            topology_quantity=self.topology_quantity,
            residual_value=self.residual_value,
            useful_life_months=self.useful_life_months,
            acquisition_date=self.acquisition_date
        )
        assert asset.asset_id == "ASSET001"
        assert asset.acquisition_cost == self.acquisition_cost
        assert asset.installation_cost == self.installation_cost
        assert asset.topology_quantity == self.topology_quantity
        assert asset.residual_value == self.residual_value
        assert asset.useful_life_months == self.useful_life_months
        assert asset.acquisition_date == self.acquisition_date

    def test_creation_missing_asset_id_fails(self):
        with pytest.raises(InputRequiredError, match=re.escape("Asset ID is required.")):
            AssetRecord(
                asset_id="",
                acquisition_cost=self.acquisition_cost,
                installation_cost=self.installation_cost,
                topology_quantity=self.topology_quantity,
                residual_value=self.residual_value,
                useful_life_months=self.useful_life_months,
                acquisition_date=self.acquisition_date
            )

    def test_creation_non_string_asset_id_fails(self):
        with pytest.raises(InputRequiredError, match=re.escape("Asset ID must be a string.")):
            AssetRecord(
                asset_id=123, # type: ignore
                acquisition_cost=self.acquisition_cost,
                installation_cost=self.installation_cost,
                topology_quantity=self.topology_quantity,
                residual_value=self.residual_value,
                useful_life_months=self.useful_life_months,
                acquisition_date=self.acquisition_date
            )

    def test_creation_non_positive_topology_quantity_fails(self):
        with pytest.raises(InputRequiredError, match=re.escape("Topology quantity must be positive.")):
            AssetRecord(
                asset_id="ASSET001",
                acquisition_cost=self.acquisition_cost,
                installation_cost=self.installation_cost,
                topology_quantity=0,
                residual_value=self.residual_value,
                useful_life_months=self.useful_life_months,
                acquisition_date=self.acquisition_date
            )

    def test_creation_non_numeric_topology_quantity_fails(self):
        with pytest.raises(InputRequiredError, match=re.escape("Topology quantity must be a number.")):
            AssetRecord(
                asset_id="ASSET001",
                acquisition_cost=self.acquisition_cost,
                installation_cost=self.installation_cost,
                topology_quantity="1.5", # type: ignore
                residual_value=self.residual_value,
                useful_life_months=self.useful_life_months,
                acquisition_date=self.acquisition_date
            )

    def test_creation_non_positive_useful_life_fails(self):
        with pytest.raises(InputRequiredError, match=re.escape("Useful life in months must be positive.")):
            AssetRecord(
                asset_id="ASSET001",
                acquisition_cost=self.acquisition_cost,
                installation_cost=self.installation_cost,
                topology_quantity=self.topology_quantity,
                residual_value=self.residual_value,
                useful_life_months=0,
                acquisition_date=self.acquisition_date
            )

    def test_creation_non_integer_useful_life_fails(self):
        with pytest.raises(InputRequiredError, match=re.escape("Useful life in months must be an integer.")):
            AssetRecord(
                asset_id="ASSET001",
                acquisition_cost=self.acquisition_cost,
                installation_cost=self.installation_cost,
                topology_quantity=self.topology_quantity,
                residual_value=self.residual_value,
                useful_life_months=60.5, # type: ignore
                acquisition_date=self.acquisition_date
            )

    def test_creation_currency_mismatch_acquisition_installation_fails(self):
        installation_cost_eur = MonetaryValue(2000.0, "EUR")
        with pytest.raises(PolicyRequiredError, match=re.escape("Acquisition and installation costs must be in the same currency.")):
            AssetRecord(
                asset_id="ASSET001",
                acquisition_cost=self.acquisition_cost,
                installation_cost=installation_cost_eur,
                topology_quantity=self.topology_quantity,
                residual_value=self.residual_value,
                useful_life_months=self.useful_life_months,
                acquisition_date=self.acquisition_date
            )

    def test_creation_currency_mismatch_acquisition_residual_fails(self):
        residual_value_eur = MonetaryValue(1000.0, "EUR")
        with pytest.raises(PolicyRequiredError, match=re.escape("Acquisition cost and residual value must be in the same currency.")):
            AssetRecord(
                asset_id="ASSET001",
                acquisition_cost=self.acquisition_cost,
                installation_cost=self.installation_cost,
                topology_quantity=self.topology_quantity,
                residual_value=residual_value_eur,
                useful_life_months=self.useful_life_months,
                acquisition_date=self.acquisition_date
            )

    def test_creation_non_utc_acquisition_date_fails(self):
        # Example non-UTC timezone
        non_utc_tz = timezone(timedelta(hours=-5), "EST") # Eastern Standard Time
        non_utc_date = datetime(2023, 1, 15, 10, 0, 0, tzinfo=non_utc_tz)
        with pytest.raises(InputRequiredError, match=re.escape("Acquisition date must be a timezone-aware UTC datetime.")):
            AssetRecord(
                asset_id="ASSET001",
                acquisition_cost=self.acquisition_cost,
                installation_cost=self.installation_cost,
                topology_quantity=self.topology_quantity,
                residual_value=self.residual_value,
                useful_life_months=self.useful_life_months,
                acquisition_date=non_utc_date # type: ignore
            )
        with pytest.raises(InputRequiredError, match=re.escape("Acquisition date must be a timezone-aware UTC datetime.")):
            AssetRecord(
                asset_id="ASSET001",
                acquisition_cost=self.acquisition_cost,
                installation_cost=self.installation_cost,
                topology_quantity=self.topology_quantity,
                residual_value=self.residual_value,
                useful_life_months=self.useful_life_months,
                acquisition_date=datetime(2023, 1, 15) # Naive datetime
            )

    def test_calculate_capitalized_cost(self):
        asset = AssetRecord(
            asset_id="ASSET001",
            acquisition_cost=self.acquisition_cost,
            installation_cost=self.installation_cost,
            topology_quantity=self.topology_quantity,
            residual_value=self.residual_value,
            useful_life_months=self.useful_life_months,
            acquisition_date=self.acquisition_date
        )
        expected_capitalized_cost = (10000.0 + 2000.0) * 1.5
        assert asset.calculate_capitalized_cost() == MonetaryValue(expected_capitalized_cost, "USD", "INV001")

    def test_calculate_monthly_depreciation(self):
        asset = AssetRecord(
            asset_id="ASSET001",
            acquisition_cost=self.acquisition_cost,
            installation_cost=self.installation_cost,
            topology_quantity=self.topology_quantity,
            residual_value=self.residual_value,
            useful_life_months=self.useful_life_months,
            acquisition_date=self.acquisition_date
        )
        capitalized_cost = (10000.0 + 2000.0) * 1.5 # 18000.0
        depreciable_base = capitalized_cost - 1000.0 # 17000.0
        expected_monthly_depreciation = depreciable_base / 60.0 # 17000 / 60 = 283.333...
        assert asset.calculate_monthly_depreciation().amount == pytest.approx(expected_monthly_depreciation)
        assert asset.calculate_monthly_depreciation().currency_code == "USD"

    def test_monthly_depreciation_residual_value_exceeds_capitalized_cost_fails(self):
        high_residual_value = MonetaryValue(20000.0, "USD")
        asset = AssetRecord(
            asset_id="ASSET001",
            acquisition_cost=self.acquisition_cost,
            installation_cost=self.installation_cost,
            topology_quantity=self.topology_quantity,
            residual_value=high_residual_value,
            useful_life_months=self.useful_life_months,
            acquisition_date=self.acquisition_date
        )
        with pytest.raises(PolicyRequiredError, match=re.escape("Residual value cannot exceed capitalized cost.")):
            asset.calculate_monthly_depreciation()

    def test_calculate_economic_capital_charge_nominal(self):
        policy = AccountingPolicy(0.10, 0.05, "full_month")
        asset = AssetRecord(
            asset_id="ASSET001",
            acquisition_cost=self.acquisition_cost,
            installation_cost=self.installation_cost,
            topology_quantity=self.topology_quantity,
            residual_value=self.residual_value,
            useful_life_months=self.useful_life_months,
            acquisition_date=self.acquisition_date
        )
        capitalized_cost_amount = (10000.0 + 2000.0) * 1.5 # 18000.0
        expected_charge = capitalized_cost_amount * 0.10 # 1800.0
        charge = asset.calculate_economic_capital_charge(policy, use_real_rate=False)
        assert charge.amount == pytest.approx(expected_charge)
        assert charge.currency_code == "USD"
        assert charge.invoice_id == "INV001" # Should retain provenance

    def test_calculate_economic_capital_charge_real(self):
        policy = AccountingPolicy(0.10, 0.05, "full_month")
        asset = AssetRecord(
            asset_id="ASSET001",
            acquisition_cost=self.acquisition_cost,
            installation_cost=self.installation_cost,
            topology_quantity=self.topology_quantity,
            residual_value=self.residual_value,
            useful_life_months=self.useful_life_months,
            acquisition_date=self.acquisition_date
        )
        capitalized_cost_amount = (10000.0 + 2000.0) * 1.5 # 18000.0
        expected_charge = capitalized_cost_amount * 0.05 # 900.0
        charge = asset.calculate_economic_capital_charge(policy, use_real_rate=True)
        assert charge.amount == pytest.approx(expected_charge)
        assert charge.currency_code == "USD"
        assert charge.invoice_id == "INV001"

    def test_calculate_partial_period_depreciation_full_month(self):
        policy = AccountingPolicy(0.10, 0.05, "full_month")
        asset = AssetRecord(
            asset_id="ASSET001",
            acquisition_cost=self.acquisition_cost,
            installation_cost=self.installation_cost,
            topology_quantity=self.topology_quantity,
            residual_value=self.residual_value,
            useful_life_months=self.useful_life_months,
            acquisition_date=self.acquisition_date
        )
        monthly_depreciation = asset.calculate_monthly_depreciation()
        period_start = utc_dt(2023, 1, 1)
        period_end = utc_dt(2023, 1, 31, 23, 59, 59)
        partial_depreciation = asset.calculate_partial_period_depreciation(policy, period_start, period_end)
        assert partial_depreciation == monthly_depreciation

    def test_calculate_partial_period_depreciation_half_month(self):
        policy = AccountingPolicy(0.10, 0.05, "half_month")
        asset = AssetRecord(
            asset_id="ASSET001",
            acquisition_cost=self.acquisition_cost,
            installation_cost=self.installation_cost,
            topology_quantity=self.topology_quantity,
            residual_value=self.residual_value,
            useful_life_months=self.useful_life_months,
            acquisition_date=self.acquisition_date
        )
        monthly_depreciation = asset.calculate_monthly_depreciation()
        period_start = utc_dt(2023, 1, 1)
        period_end = utc_dt(2023, 1, 15) # Arbitrary partial period
        partial_depreciation = asset.calculate_partial_period_depreciation(policy, period_start, period_end)
        assert partial_depreciation == monthly_depreciation / 2.0

    def test_calculate_partial_period_depreciation_actual_days(self):
        policy = AccountingPolicy(0.10, 0.05, "actual_days")
        asset = AssetRecord(
            asset_id="ASSET001",
            acquisition_cost=self.acquisition_cost,
            installation_cost=self.installation_cost,
            topology_quantity=self.topology_quantity,
            residual_value=self.residual_value,
            useful_life_months=self.useful_life_months,
            acquisition_date=self.acquisition_date
        )
        monthly_depreciation = asset.calculate_monthly_depreciation()
        period_start = utc_dt(2023, 1, 1)
        period_end = utc_dt(2023, 1, 16) # 15 days
        days_in_period = 15
        days_in_average_month = 30.0
        expected_depreciation = monthly_depreciation * (days_in_period / days_in_average_month)
        partial_depreciation = asset.calculate_partial_period_depreciation(policy, period_start, period_end)
        assert partial_depreciation.amount == pytest.approx(expected_depreciation.amount)
        assert partial_depreciation.currency_code == expected_depreciation.currency_code

    def test_partial_period_depreciation_invalid_period_dates_fails(self):
        policy = AccountingPolicy(0.10, 0.05, "full_month")
        asset = AssetRecord(
            asset_id="ASSET001",
            acquisition_cost=self.acquisition_cost,
            installation_cost=self.installation_cost,
            topology_quantity=self.topology_quantity,
            residual_value=self.residual_value,
            useful_life_months=self.useful_life_months,
            acquisition_date=self.acquisition_date
        )
        # Period end before period start
        with pytest.raises(InputRequiredError, match=re.escape("Period start date must be before period end date.")):
            asset.calculate_partial_period_depreciation(policy, utc_dt(2023, 1, 31), utc_dt(2023, 1, 1))

        # Non-UTC dates
        naive_date = datetime(2023, 1, 1)
        with pytest.raises(InputRequiredError, match=re.escape("Period start date must be a timezone-aware UTC datetime.")):
            asset.calculate_partial_period_depreciation(policy, naive_date, utc_dt(2023, 1, 31)) # type: ignore
        with pytest.raises(InputRequiredError, match=re.escape("Period end date must be a timezone-aware UTC datetime.")):
            asset.calculate_partial_period_depreciation(policy, utc_dt(2023, 1, 1), naive_date) # type: ignore

# --- Test create_utc_instant helper ---
class TestCreateUtcInstant:
    def test_create_utc_instant_from_utc_datetime(self):
        dt_utc = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        instant = create_utc_instant(dt_utc)
        assert instant == dt_utc
        assert instant.tzinfo == timezone.utc

    def test_create_utc_instant_from_non_utc_datetime_converts(self):
        # Example: PST is UTC-8
        pst_offset = timezone(timedelta(hours=-8), "PST")
        dt_pst = datetime(2023, 1, 1, 12, 0, 0, tzinfo=pst_offset) # 12 PM PST
        instant = create_utc_instant(dt_pst)
        expected_utc = datetime(2023, 1, 1, 20, 0, 0, tzinfo=timezone.utc) # 8 PM UTC
        assert instant == expected_utc
        assert instant.tzinfo == timezone.utc

    def test_create_utc_instant_from_naive_datetime_fails(self):
        dt_naive = datetime(2023, 1, 1, 12, 0, 0)
        with pytest.raises(InputRequiredError, match=re.escape("Datetime must be timezone-aware.")):
            create_utc_instant(dt_naive)
