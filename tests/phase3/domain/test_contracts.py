import datetime
import pytest
from decimal import Decimal
from typing import Any, Mapping

from src.pocgpu.domain.tco.contracts import (
    AllocationPolicy,
    AccountingPolicy,
    AssetRecord,
    ConvertedAmount,
    CostBoundary,
    CostClass,
    CostDisposition,
    CostRecord,
    FacilityPolicy,
    FxObservation,
    PolicyViolationError,
    PowerObservation,
    CurrencyCode,
    UtcInstant,
)

# Helper for timezone-aware UTC datetime
def utc_now() -> UtcInstant:
    return datetime.datetime.now(datetime.timezone.utc)

def utc_past(seconds_ago: int) -> UtcInstant:
    return datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=seconds_ago)

def utc_future(seconds_from_now: int) -> UtcInstant:
    return datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=seconds_from_now)

# --- Test CostClass Enum ---
def test_cost_class_enum_values():
    assert CostClass.ASSET_DEPRECIATION.value == "ASSET_DEPRECIATION"
    assert CostClass.CAPITAL_CHARGE.value == "CAPITAL_CHARGE"
    assert CostClass.FACILITY.value == "FACILITY"
    assert CostClass.COLOCATION.value == "COLOCATION"
    assert CostClass.ENERGY.value == "ENERGY"
    assert CostClass.COOLING.value == "COOLING"
    assert CostClass.NETWORK.value == "NETWORK"
    assert CostClass.STORAGE.value == "STORAGE"
    assert CostClass.SOFTWARE.value == "SOFTWARE"
    assert CostClass.SUPPORT.value == "SUPPORT"
    assert CostClass.MAINTENANCE.value == "MAINTENANCE"
    assert CostClass.LABOR.value == "LABOR"
    assert CostClass.SECURITY.value == "SECURITY"
    assert CostClass.COMPLIANCE.value == "COMPLIANCE"
    assert CostClass.INSURANCE.value == "INSURANCE"
    assert CostClass.DECOMMISSIONING.value == "DECOMMISSIONING"
    assert len(CostClass) == 16 # Ensure all specified classes are present

# --- Test CostDisposition Enum ---
def test_cost_disposition_enum_values():
    assert CostDisposition.INCLUDED.value == "INCLUDED"
    assert CostDisposition.EXCLUDED.value == "EXCLUDED"
    assert CostDisposition.NOT_APPLICABLE.value == "NOT_APPLICABLE"
    assert len(CostDisposition) == 3

# --- Test CostBoundary ---
def test_cost_boundary_complete_and_valid():
    dispositions = {
        CostClass.ASSET_DEPRECIATION: (CostDisposition.INCLUDED, None),
        CostClass.CAPITAL_CHARGE: (CostDisposition.INCLUDED, None),
        CostClass.FACILITY: (CostDisposition.INCLUDED, None),
        CostClass.COLOCATION: (CostDisposition.NOT_APPLICABLE, None),
        CostClass.ENERGY: (CostDisposition.INCLUDED, None),
        CostClass.COOLING: (CostDisposition.EXCLUDED, "Cooling costs are managed by a separate budget."),
        CostClass.NETWORK: (CostDisposition.INCLUDED, None),
        CostClass.STORAGE: (CostDisposition.INCLUDED, None),
        CostClass.SOFTWARE: (CostDisposition.INCLUDED, None),
        CostClass.SUPPORT: (CostDisposition.INCLUDED, None),
        CostClass.MAINTENANCE: (CostDisposition.INCLUDED, None),
        CostClass.LABOR: (CostDisposition.INCLUDED, None),
        CostClass.SECURITY: (CostDisposition.INCLUDED, None),
        CostClass.COMPLIANCE: (CostDisposition.INCLUDED, None),
        CostClass.INSURANCE: (CostDisposition.INCLUDED, None),
        CostClass.DECOMMISSIONING: (CostDisposition.NOT_APPLICABLE, None),
    }
    boundary = CostBoundary(dispositions=dispositions)
    assert boundary is not None
    assert boundary.dispositions == dispositions

def test_cost_boundary_missing_cost_class_fails():
    dispositions = {
        CostClass.ASSET_DEPRECIATION: (CostDisposition.INCLUDED, None),
        # Missing CAPITAL_CHARGE
        CostClass.FACILITY: (CostDisposition.INCLUDED, None),
        CostClass.COLOCATION: (CostDisposition.NOT_APPLICABLE, None),
        CostClass.ENERGY: (CostDisposition.INCLUDED, None),
        CostClass.COOLING: (CostDisposition.EXCLUDED, "Cooling costs are managed by a separate budget."),
        CostClass.NETWORK: (CostDisposition.INCLUDED, None),
        CostClass.STORAGE: (CostDisposition.INCLUDED, None),
        CostClass.SOFTWARE: (CostDisposition.INCLUDED, None),
        CostClass.SUPPORT: (CostDisposition.INCLUDED, None),
        CostClass.MAINTENANCE: (CostDisposition.INCLUDED, None),
        CostClass.LABOR: (CostDisposition.INCLUDED, None),
        CostClass.SECURITY: (CostDisposition.INCLUDED, None),
        CostClass.COMPLIANCE: (CostDisposition.INCLUDED, None),
        CostClass.INSURANCE: (CostDisposition.INCLUDED, None),
        CostClass.DECOMMISSIONING: (CostDisposition.NOT_APPLICABLE, None),
    }
    with pytest.raises(PolicyViolationError, match=r"POLICY_REQUIRED: CostBoundary is incomplete\. Missing dispositions for: CAPITAL_CHARGE"):
        CostBoundary(dispositions=dispositions)

def test_cost_boundary_excluded_without_rationale_fails():
    dispositions = {
        CostClass.ASSET_DEPRECIATION: (CostDisposition.INCLUDED, None),
        CostClass.CAPITAL_CHARGE: (CostDisposition.INCLUDED, None),
        CostClass.FACILITY: (CostDisposition.INCLUDED, None),
        CostClass.COLOCATION: (CostDisposition.NOT_APPLICABLE, None),
        CostClass.ENERGY: (CostDisposition.INCLUDED, None),
        CostClass.COOLING: (CostDisposition.EXCLUDED, None), # Missing rationale
        CostClass.NETWORK: (CostDisposition.INCLUDED, None),
        CostClass.STORAGE: (CostDisposition.INCLUDED, None),
        CostClass.SOFTWARE: (CostDisposition.INCLUDED, None),
        CostClass.SUPPORT: (CostDisposition.INCLUDED, None),
        CostClass.MAINTENANCE: (CostDisposition.INCLUDED, None),
        CostClass.LABOR: (CostDisposition.INCLUDED, None),
        CostClass.SECURITY: (CostDisposition.INCLUDED, None),
        CostClass.COMPLIANCE: (CostDisposition.INCLUDED, None),
        CostClass.INSURANCE: (CostDisposition.INCLUDED, None),
        CostClass.DECOMMISSIONING: (CostDisposition.NOT_APPLICABLE, None),
    }
    with pytest.raises(PolicyViolationError, match=r"POLICY_REQUIRED: CostClass 'COOLING' is EXCLUDED but requires a non-empty rationale\."):
        CostBoundary(dispositions=dispositions)

def test_cost_boundary_included_with_rationale_fails():
    dispositions = {
        CostClass.ASSET_DEPRECIATION: (CostDisposition.INCLUDED, None),
        CostClass.CAPITAL_CHARGE: (CostDisposition.INCLUDED, None),
        CostClass.FACILITY: (CostDisposition.INCLUDED, "This is a rationale that should not be here."), # Rationale for INCLUDED
        CostClass.COLOCATION: (CostDisposition.NOT_APPLICABLE, None),
        CostClass.ENERGY: (CostDisposition.INCLUDED, None),
        CostClass.COOLING: (CostDisposition.EXCLUDED, "Cooling costs are managed by a separate budget."),
        CostClass.NETWORK: (CostDisposition.INCLUDED, None),
        CostClass.STORAGE: (CostDisposition.INCLUDED, None),
        CostClass.SOFTWARE: (CostDisposition.INCLUDED, None),
        CostClass.SUPPORT: (CostDisposition.INCLUDED, None),
        CostClass.MAINTENANCE: (CostDisposition.INCLUDED, None),
        CostClass.LABOR: (CostDisposition.INCLUDED, None),
        CostClass.SECURITY: (CostDisposition.INCLUDED, None),
        CostClass.COMPLIANCE: (CostDisposition.INCLUDED, None),
        CostClass.INSURANCE: (CostDisposition.INCLUDED, None),
        CostClass.DECOMMISSIONING: (CostDisposition.NOT_APPLICABLE, None),
    }
    with pytest.raises(PolicyViolationError, match=r"POLICY_REQUIRED: CostClass 'FACILITY' has a rationale but is not EXCLUDED\. Rationale should only be provided for EXCLUDED dispositions\."):
        CostBoundary(dispositions=dispositions)

def test_cost_boundary_not_applicable_with_rationale_fails():
    dispositions = {
        CostClass.ASSET_DEPRECIATION: (CostDisposition.INCLUDED, None),
        CostClass.CAPITAL_CHARGE: (CostDisposition.INCLUDED, None),
        CostClass.FACILITY: (CostDisposition.INCLUDED, None),
        CostClass.COLOCATION: (CostDisposition.NOT_APPLICABLE, "This is a rationale that should not be here."), # Rationale for NOT_APPLICABLE
        CostClass.ENERGY: (CostDisposition.INCLUDED, None),
        CostClass.COOLING: (CostDisposition.EXCLUDED, "Cooling costs are managed by a separate budget."),
        CostClass.NETWORK: (CostDisposition.INCLUDED, None),
        CostClass.STORAGE: (CostDisposition.INCLUDED, None),
        CostClass.SOFTWARE: (CostDisposition.INCLUDED, None),
        CostClass.SUPPORT: (CostDisposition.INCLUDED, None),
        CostClass.MAINTENANCE: (CostDisposition.INCLUDED, None),
        CostClass.LABOR: (CostDisposition.INCLUDED, None),
        CostClass.SECURITY: (CostDisposition.INCLUDED, None),
        CostClass.COMPLIANCE: (CostDisposition.INCLUDED, None),
        CostClass.INSURANCE: (CostDisposition.INCLUDED, None),
        CostClass.DECOMMISSIONING: (CostDisposition.NOT_APPLICABLE, None),
    }
    with pytest.raises(PolicyViolationError, match=r"POLICY_REQUIRED: CostClass 'COLOCATION' has a rationale but is not EXCLUDED\. Rationale should only be provided for EXCLUDED dispositions\."):
        CostBoundary(dispositions=dispositions)

# --- Test CostRecord ---
def test_cost_record_creation():
    record = CostRecord(
        amount=Decimal('123.45'),
        currency="USD",
        cost_class=CostClass.ENERGY,
        timestamp=utc_now(),
        description="Monthly energy bill"
    )
    assert record.amount == Decimal('123.45')
    assert record.currency == "USD"
    assert record.cost_class == CostClass.ENERGY
    assert record.description == "Monthly energy bill"
    assert record.timestamp.tzinfo is not None

def test_cost_record_invalid_amount_type_fails():
    with pytest.raises(TypeError, match="Amount must be a Decimal."):
        CostRecord(amount=123.45, currency="USD", cost_class=CostClass.ENERGY, timestamp=utc_now(), description="Test")

def test_cost_record_negative_amount_fails():
    with pytest.raises(ValueError, match="Amount cannot be negative."):
        CostRecord(amount=Decimal('-10.00'), currency="USD", cost_class=CostClass.ENERGY, timestamp=utc_now(), description="Test")

def test_cost_record_empty_currency_fails():
    with pytest.raises(ValueError, match="Currency cannot be empty."):
        CostRecord(amount=Decimal('10.00'), currency="", cost_class=CostClass.ENERGY, timestamp=utc_now(), description="Test")

def test_cost_record_naive_timestamp_fails():
    with pytest.raises(ValueError, match="Timestamp must be a timezone-aware UtcInstant."):
        CostRecord(amount=Decimal('10.00'), currency="USD", cost_class=CostClass.ENERGY, timestamp=datetime.datetime.now(), description="Test")

def test_cost_record_empty_description_fails():
    with pytest.raises(ValueError, match="Description cannot be empty."):
        CostRecord(amount=Decimal('10.00'), currency="USD", cost_class=CostClass.ENERGY, timestamp=utc_now(), description="")

# --- Test AssetRecord ---
def test_asset_record_creation():
    record = AssetRecord(
        asset_id="GPU-001",
        description="NVIDIA A100 GPU",
        acquisition_cost=Decimal('10000.00'),
        acquisition_currency="USD",
        acquisition_date=utc_past(365),
        useful_life_years=5,
        depreciation_method="Straight-line"
    )
    assert record.asset_id == "GPU-001"
    assert record.description == "NVIDIA A100 GPU"
    assert record.acquisition_cost == Decimal('10000.00')
    assert record.acquisition_currency == "USD"
    assert record.acquisition_date.tzinfo is not None
    assert record.useful_life_years == 5
    assert record.depreciation_method == "Straight-line"

def test_asset_record_invalid_acquisition_cost_type_fails():
    with pytest.raises(TypeError, match="Acquisition cost must be a Decimal."):
        AssetRecord(asset_id="GPU-001", description="Desc", acquisition_cost=10000.00, acquisition_currency="USD", acquisition_date=utc_now(), useful_life_years=5, depreciation_method="SL")

def test_asset_record_negative_acquisition_cost_fails():
    with pytest.raises(ValueError, match="Acquisition cost cannot be negative."):
        AssetRecord(asset_id="GPU-001", description="Desc", acquisition_cost=Decimal('-100.00'), acquisition_currency="USD", acquisition_date=utc_now(), useful_life_years=5, depreciation_method="SL")

def test_asset_record_empty_asset_id_fails():
    with pytest.raises(ValueError, match="Asset ID cannot be empty."):
        AssetRecord(asset_id="", description="Desc", acquisition_cost=Decimal('100.00'), acquisition_currency="USD", acquisition_date=utc_now(), useful_life_years=5, depreciation_method="SL")

def test_asset_record_empty_description_fails():
    with pytest.raises(ValueError, match="Description cannot be empty."):
        AssetRecord(asset_id="GPU-001", description="", acquisition_cost=Decimal('100.00'), acquisition_currency="USD", acquisition_date=utc_now(), useful_life_years=5, depreciation_method="SL")

def test_asset_record_empty_acquisition_currency_fails():
    with pytest.raises(ValueError, match="Acquisition currency cannot be empty."):
        AssetRecord(asset_id="GPU-001", description="Desc", acquisition_cost=Decimal('100.00'), acquisition_currency="", acquisition_date=utc_now(), useful_life_years=5, depreciation_method="SL")

def test_asset_record_naive_acquisition_date_fails():
    with pytest.raises(ValueError, match="Acquisition date must be a timezone-aware UtcInstant."):
        AssetRecord(asset_id="GPU-001", description="Desc", acquisition_cost=Decimal('100.00'), acquisition_currency="USD", acquisition_date=datetime.datetime.now(), useful_life_years=5, depreciation_method="SL")

def test_asset_record_non_positive_useful_life_fails():
    with pytest.raises(ValueError, match="Useful life years must be positive."):
        AssetRecord(asset_id="GPU-001", description="Desc", acquisition_cost=Decimal('100.00'), acquisition_currency="USD", acquisition_date=utc_now(), useful_life_years=0, depreciation_method="SL")
    with pytest.raises(ValueError, match="Useful life years must be positive."):
        AssetRecord(asset_id="GPU-001", description="Desc", acquisition_cost=Decimal('100.00'), acquisition_currency="USD", acquisition_date=utc_now(), useful_life_years=-1, depreciation_method="SL")

def test_asset_record_empty_depreciation_method_fails():
    with pytest.raises(ValueError, match="Depreciation method cannot be empty."):
        AssetRecord(asset_id="GPU-001", description="Desc", acquisition_cost=Decimal('100.00'), acquisition_currency="USD", acquisition_date=utc_now(), useful_life_years=5, depreciation_method="")

# --- Test PowerObservation ---
def test_power_observation_creation():
    obs = PowerObservation(
        timestamp=utc_now(),
        power_value=Decimal('150.75'),
        unit="kW"
    )
    assert obs.timestamp.tzinfo is not None
    assert obs.power_value == Decimal('150.75')
    assert obs.unit == "kW"

def test_power_observation_naive_timestamp_fails():
    with pytest.raises(ValueError, match="Timestamp must be a timezone-aware UtcInstant."):
        PowerObservation(timestamp=datetime.datetime.now(), power_value=Decimal('100'), unit="kW")

def test_power_observation_invalid_power_value_type_fails():
    with pytest.raises(TypeError, match="Power value must be a Decimal."):
        PowerObservation(timestamp=utc_now(), power_value=100.0, unit="kW")

def test_power_observation_negative_power_value_fails():
    with pytest.raises(ValueError, match="Power value cannot be negative."):
        PowerObservation(timestamp=utc_now(), power_value=Decimal('-10'), unit="kW")

def test_power_observation_empty_unit_fails():
    with pytest.raises(ValueError, match="Unit cannot be empty."):
        PowerObservation(timestamp=utc_now(), power_value=Decimal('100'), unit="")

# --- Test FacilityPolicy ---
def test_facility_policy_creation():
    policy = FacilityPolicy(
        policy_id="FP-001",
        name="Data Center Energy Efficiency Policy",
        description="Policy for optimizing energy consumption in DC-West.",
        effective_date=utc_past(30),
        details={"target_pue": Decimal('1.2'), "reporting_frequency": "monthly"}
    )
    assert policy.policy_id == "FP-001"
    assert policy.name == "Data Center Energy Efficiency Policy"
    assert policy.description == "Policy for optimizing energy consumption in DC-West."
    assert policy.effective_date.tzinfo is not None
    assert policy.details == {"target_pue": Decimal('1.2'), "reporting_frequency": "monthly"}

def test_facility_policy_empty_policy_id_fails():
    with pytest.raises(ValueError, match="Policy ID cannot be empty."):
        FacilityPolicy(policy_id="", name="Name", description="Desc", effective_date=utc_now(), details={})

def test_facility_policy_empty_name_fails():
    with pytest.raises(ValueError, match="Name cannot be empty."):
        FacilityPolicy(policy_id="FP-001", name="", description="Desc", effective_date=utc_now(), details={})

def test_facility_policy_empty_description_fails():
    with pytest.raises(ValueError, match="Description cannot be empty."):
        FacilityPolicy(policy_id="FP-001", name="Name", description="", effective_date=utc_now(), details={})

def test_facility_policy_naive_effective_date_fails():
    with pytest.raises(ValueError, match="Effective date must be a timezone-aware UtcInstant."):
        FacilityPolicy(policy_id="FP-001", name="Name", description="Desc", effective_date=datetime.datetime.now(), details={})

# --- Test AllocationPolicy ---
def test_allocation_policy_creation():
    policy = AllocationPolicy(
        policy_id="AP-001",
        name="Shared Infrastructure Cost Allocation",
        description="Policy for allocating shared network and storage costs.",
        effective_date=utc_past(60),
        details={"method": "pro-rata", "basis": "cpu_usage"}
    )
    assert policy.policy_id == "AP-001"
    assert policy.name == "Shared Infrastructure Cost Allocation"
    assert policy.description == "Policy for allocating shared network and storage costs."
    assert policy.effective_date.tzinfo is not None
    assert policy.details == {"method": "pro-rata", "basis": "cpu_usage"}

def test_allocation_policy_empty_policy_id_fails():
    with pytest.raises(ValueError, match="Policy ID cannot be empty."):
        AllocationPolicy(policy_id="", name="Name", description="Desc", effective_date=utc_now(), details={})

def test_allocation_policy_empty_name_fails():
    with pytest.raises(ValueError, match="Name cannot be empty."):
        AllocationPolicy(policy_id="AP-001", name="", description="Desc", effective_date=utc_now(), details={})

def test_allocation_policy_empty_description_fails():
    with pytest.raises(ValueError, match="Description cannot be empty."):
        AllocationPolicy(policy_id="AP-001", name="Name", description="", effective_date=utc_now(), details={})

def test_allocation_policy_naive_effective_date_fails():
    with pytest.raises(ValueError, match="Effective date must be a timezone-aware UtcInstant."):
        AllocationPolicy(policy_id="AP-001", name="Name", description="Desc", effective_date=datetime.datetime.now(), details={})

# --- Test AccountingPolicy ---
def test_accounting_policy_creation():
    policy = AccountingPolicy(
        policy_id="ACP-001",
        name="GPU Depreciation Policy",
        description="Policy for depreciation of GPU assets.",
        effective_date=utc_past(90),
        details={"asset_class": "GPU", "depreciation_period": "5 years", "method": "straight-line"}
    )
    assert policy.policy_id == "ACP-001"
    assert policy.name == "GPU Depreciation Policy"
    assert policy.description == "Policy for depreciation of GPU assets."
    assert policy.effective_date.tzinfo is not None
    assert policy.details == {"asset_class": "GPU", "depreciation_period": "5 years", "method": "straight-line"}

def test_accounting_policy_empty_policy_id_fails():
    with pytest.raises(ValueError, match="Policy ID cannot be empty."):
        AccountingPolicy(policy_id="", name="Name", description="Desc", effective_date=utc_now(), details={})

def test_accounting_policy_empty_name_fails():
    with pytest.raises(ValueError, match="Name cannot be empty."):
        AccountingPolicy(policy_id="ACP-001", name="", description="Desc", effective_date=utc_now(), details={})

def test_accounting_policy_empty_description_fails():
    with pytest.raises(ValueError, match="Description cannot be empty."):
        AccountingPolicy(policy_id="ACP-001", name="Name", description="", effective_date=utc_now(), details={})

def test_accounting_policy_naive_effective_date_fails():
    with pytest.raises(ValueError, match="Effective date must be a timezone-aware UtcInstant."):
        AccountingPolicy(policy_id="ACP-001", name="Name", description="Desc", effective_date=datetime.datetime.now(), details={})

# --- Test FxObservation ---
def test_fx_observation_creation():
    fx_obs = FxObservation(
        source_currency="USD",
        target_currency="EUR",
        rate=Decimal('0.92'),
        observation_timestamp=utc_now()
    )
    assert fx_obs.source_currency == "USD"
    assert fx_obs.target_currency == "EUR"
    assert fx_obs.rate == Decimal('0.92')
    assert fx_obs.observation_timestamp.tzinfo is not None

def test_fx_observation_empty_source_currency_fails():
    with pytest.raises(ValueError, match="Source currency cannot be empty."):
        FxObservation(source_currency="", target_currency="EUR", rate=Decimal('0.9'), observation_timestamp=utc_now())

def test_fx_observation_empty_target_currency_fails():
    with pytest.raises(ValueError, match="Target currency cannot be empty."):
        FxObservation(source_currency="USD", target_currency="", rate=Decimal('0.9'), observation_timestamp=utc_now())

def test_fx_observation_same_source_target_currency_fails():
    with pytest.raises(ValueError, match="Source and target currencies cannot be the same for an FX observation."):
        FxObservation(source_currency="USD", target_currency="USD", rate=Decimal('1.0'), observation_timestamp=utc_now())

def test_fx_observation_invalid_rate_type_fails():
    with pytest.raises(TypeError, match="Rate must be a Decimal."):
        FxObservation(source_currency="USD", target_currency="EUR", rate=0.9, observation_timestamp=utc_now())

def test_fx_observation_non_positive_rate_fails():
    with pytest.raises(ValueError, match="FX rate must be positive."):
        FxObservation(source_currency="USD", target_currency="EUR", rate=Decimal('0'), observation_timestamp=utc_now())
    with pytest.raises(ValueError, match="FX rate must be positive."):
        FxObservation(source_currency="USD", target_currency="EUR", rate=Decimal('-0.5'), observation_timestamp=utc_now())

def test_fx_observation_naive_timestamp_fails():
    with pytest.raises(ValueError, match="Observation timestamp must be a timezone-aware UtcInstant."):
        FxObservation(source_currency="USD", target_currency="EUR", rate=Decimal('0.9'), observation_timestamp=datetime.datetime.now())

# --- Test ConvertedAmount ---
def test_converted_amount_creation():
    fx_obs = FxObservation(source_currency="USD", target_currency="EUR", rate=Decimal('0.92'), observation_timestamp=utc_now())
    converted = ConvertedAmount(
        original_amount=Decimal('100.00'),
        original_currency="USD",
        converted_amount=Decimal('92.00'),
        converted_currency="EUR",
        fx_observation_provenance=fx_obs
    )
    assert converted.original_amount == Decimal('100.00')
    assert converted.original_currency == "USD"
    assert converted.converted_amount == Decimal('92.00')
    assert converted.converted_currency == "EUR"
    assert converted.fx_observation_provenance == fx_obs

def test_converted_amount_invalid_original_amount_type_fails():
    fx_obs = FxObservation(source_currency="USD", target_currency="EUR", rate=Decimal('0.92'), observation_timestamp=utc_now())
    with pytest.raises(TypeError, match="Original amount must be a Decimal."):
        ConvertedAmount(original_amount=100.00, original_currency="USD", converted_amount=Decimal('92.00'), converted_currency="EUR", fx_observation_provenance=fx_obs)

def test_converted_amount_empty_original_currency_fails():
    fx_obs = FxObservation(source_currency="USD", target_currency="EUR", rate=Decimal('0.92'), observation_timestamp=utc_now())
    with pytest.raises(ValueError, match="Original currency cannot be empty."):
        ConvertedAmount(original_amount=Decimal('100.00'), original_currency="", converted_amount=Decimal('92.00'), converted_currency="EUR", fx_observation_provenance=fx_obs)

def test_converted_amount_invalid_converted_amount_type_fails():
    fx_obs = FxObservation(source_currency="USD", target_currency="EUR", rate=Decimal('0.92'), observation_timestamp=utc_now())
    with pytest.raises(TypeError, match="Converted amount must be a Decimal."):
        ConvertedAmount(original_amount=Decimal('100.00'), original_currency="USD", converted_amount=92.00, converted_currency="EUR", fx_observation_provenance=fx_obs)

def test_converted_amount_empty_converted_currency_fails():
    fx_obs = FxObservation(source_currency="USD", target_currency="EUR", rate=Decimal('0.92'), observation_timestamp=utc_now())
    with pytest.raises(ValueError, match="Converted currency cannot be empty."):
        ConvertedAmount(original_amount=Decimal('100.00'), original_currency="USD", converted_amount=Decimal('92.00'), converted_currency="", fx_observation_provenance=fx_obs)

def test_converted_amount_invalid_fx_provenance_type_fails():
    with pytest.raises(TypeError, match="FX observation provenance must be an FxObservation instance."):
        ConvertedAmount(original_amount=Decimal('100.00'), original_currency="USD", converted_amount=Decimal('92.00'), converted_currency="EUR", fx_observation_provenance="not an fx obs") # type: ignore

def test_converted_amount_same_original_converted_currency_fails():
    fx_obs = FxObservation(source_currency="USD", target_currency="EUR", rate=Decimal('0.92'), observation_timestamp=utc_now())
    with pytest.raises(ValueError, match="Original and converted currencies cannot be the same for a ConvertedAmount."):
        ConvertedAmount(original_amount=Decimal('100.00'), original_currency="USD", converted_amount=Decimal('100.00'), converted_currency="USD", fx_observation_provenance=fx_obs)

def test_converted_amount_mismatched_original_currency_with_fx_fails():
    fx_obs = FxObservation(source_currency="GBP", target_currency="EUR", rate=Decimal('1.15'), observation_timestamp=utc_now())
    with pytest.raises(ValueError, match=r"Original currency 'USD' does not match FX observation source currency 'GBP'\."):
        ConvertedAmount(original_amount=Decimal('100.00'), original_currency="USD", converted_amount=Decimal('115.00'), converted_currency="EUR", fx_observation_provenance=fx_obs)

def test_converted_amount_mismatched_converted_currency_with_fx_fails():
    fx_obs = FxObservation(source_currency="USD", target_currency="GBP", rate=Decimal('0.8'), observation_timestamp=utc_now())
    with pytest.raises(ValueError, match=r"Converted currency 'EUR' does not match FX observation target currency 'GBP'\."):
        ConvertedAmount(original_amount=Decimal('100.00'), original_currency="USD", converted_amount=Decimal('80.00'), converted_currency="EUR", fx_observation_provenance=fx_obs)

# --- Test ConvertedAmount.from_amount_and_fx ---
def test_from_amount_and_fx_successful_conversion():
    fx_obs = FxObservation(source_currency="USD", target_currency="EUR", rate=Decimal('0.925'), observation_timestamp=utc_past(10))
    amount_usd = Decimal('100.00')
    converted = ConvertedAmount.from_amount_and_fx(amount=amount_usd, currency="USD", fx_observation=fx_obs)

    assert converted.original_amount == amount_usd
    assert converted.original_currency == "USD"
    assert converted.converted_amount == Decimal('92.50')
    assert converted.converted_currency == "EUR"
    assert converted.fx_observation_provenance == fx_obs

def test_from_amount_and_fx_with_explicit_target_currency():
    fx_obs = FxObservation(source_currency="USD", target_currency="EUR", rate=Decimal('0.925'), observation_timestamp=utc_past(10))
    amount_usd = Decimal('100.00')
    converted = ConvertedAmount.from_amount_and_fx(amount=amount_usd, currency="USD", fx_observation=fx_obs, target_currency="EUR")

    assert converted.original_amount == amount_usd
    assert converted.original_currency == "USD"
    assert converted.converted_amount == Decimal('92.50')
    assert converted.converted_currency == "EUR"
    assert converted.fx_observation_provenance == fx_obs

def test_from_amount_and_fx_invalid_amount_type_fails():
    fx_obs = FxObservation(source_currency="USD", target_currency="EUR", rate=Decimal('0.92'), observation_timestamp=utc_now())
    with pytest.raises(TypeError, match="Amount must be a Decimal."):
        ConvertedAmount.from_amount_and_fx(amount=100.0, currency="USD", fx_observation=fx_obs)

def test_from_amount_and_fx_negative_amount_fails():
    fx_obs = FxObservation(source_currency="USD", target_currency="EUR", rate=Decimal('0.92'), observation_timestamp=utc_now())
    with pytest.raises(ValueError, match="Amount cannot be negative."):
        ConvertedAmount.from_amount_and_fx(amount=Decimal('-10.00'), currency="USD", fx_observation=fx_obs)

def test_from_amount_and_fx_empty_currency_fails():
    fx_obs = FxObservation(source_currency="USD", target_currency="EUR", rate=Decimal('0.92'), observation_timestamp=utc_now())
    with pytest.raises(ValueError, match="Currency cannot be empty."):
        ConvertedAmount.from_amount_and_fx(amount=Decimal('100.00'), currency="", fx_observation=fx_obs)

def test_from_amount_and_fx_invalid_fx_observation_type_fails():
    with pytest.raises(TypeError, match="FX observation must be an FxObservation instance."):
        ConvertedAmount.from_amount_and_fx(amount=Decimal('100.00'), currency="USD", fx_observation="not an fx obs") # type: ignore

def test_from_amount_and_fx_mismatched_currency_with_fx_source_fails():
    fx_obs = FxObservation(source_currency="GBP", target_currency="EUR", rate=Decimal('1.15'), observation_timestamp=utc_now())
    with pytest.raises(PolicyViolationError, match=r"FX observation source currency 'GBP' does not match the amount's currency 'USD'\."):
        ConvertedAmount.from_amount_and_fx(amount=Decimal('100.00'), currency="USD", fx_observation=fx_obs)

def test_from_amount_and_fx_mismatched_target_currency_with_fx_target_fails():
    fx_obs = FxObservation(source_currency="USD", target_currency="EUR", rate=Decimal('0.92'), observation_timestamp=utc_now())
    with pytest.raises(PolicyViolationError, match=r"Requested target currency 'GBP' does not match FX observation target currency 'EUR'\."):
        ConvertedAmount.from_amount_and_fx(amount=Decimal('100.00'), currency="USD", fx_observation=fx_obs, target_currency="GBP")

def test_from_amount_and_fx_stale_observation_fails():
    fx_obs = FxObservation(source_currency="USD", target_currency="EUR", rate=Decimal('0.92'), observation_timestamp=utc_past(60)) # 60 seconds ago
    with pytest.raises(PolicyViolationError, match=r"FX observation is stale\. Observed .* is older than 30 seconds from .*"):
        ConvertedAmount.from_amount_and_fx(amount=Decimal('100.00'), currency="USD", fx_observation=fx_obs, stale_threshold_seconds=30)

def test_from_amount_and_fx_observation_not_stale_passes():
    fx_obs = FxObservation(source_currency="USD", target_currency="EUR", rate=Decimal('0.92'), observation_timestamp=utc_past(10)) # 10 seconds ago
    converted = ConvertedAmount.from_amount_and_fx(amount=Decimal('100.00'), currency="USD", fx_observation=fx_obs, stale_threshold_seconds=30)
    assert converted.converted_amount == Decimal('92.00')

def test_from_amount_and_fx_stale_threshold_zero_passes_for_current_obs():
    fx_obs = FxObservation(source_currency="USD", target_currency="EUR", rate=Decimal('0.92'), observation_timestamp=utc_now())
    converted = ConvertedAmount.from_amount_and_fx(amount=Decimal('100.00'), currency="USD", fx_observation=fx_obs, stale_threshold_seconds=0)
    assert converted.converted_amount == Decimal('92.00')

def test_from_amount_and_fx_stale_threshold_zero_fails_for_past_obs():
    fx_obs = FxObservation(source_currency="USD", target_currency="EUR", rate=Decimal('0.92'), observation_timestamp=utc_past(1))
    with pytest.raises(PolicyViolationError, match=r"FX observation is stale\. Observed .* is older than 0 seconds from .*"):
        ConvertedAmount.from_amount_and_fx(amount=Decimal('100.00'), currency="USD", fx_observation=fx_obs, stale_threshold_seconds=0)

def test_from_amount_and_fx_invalid_stale_threshold_seconds_fails():
    fx_obs = FxObservation(source_currency="USD", target_currency="EUR", rate=Decimal('0.92'), observation_timestamp=utc_now())
    with pytest.raises(ValueError, match="Stale threshold seconds must be a non-negative integer or None."):
        ConvertedAmount.from_amount_and_fx(amount=Decimal('100.00'), currency="USD", fx_observation=fx_obs, stale_threshold_seconds=-1)
    with pytest.raises(ValueError, match="Stale threshold seconds must be a non-negative integer or None."):
        ConvertedAmount.from_amount_and_fx(amount=Decimal('100.00'), currency="USD", fx_observation=fx_obs, stale_threshold_seconds="not an int") # type: ignore
