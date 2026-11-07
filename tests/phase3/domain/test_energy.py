import pytest
import dataclasses
import re

from src.pocgpu.domain.tco.energy import (
    ITPowerRecord,
    FacilityPolicy,
    ElectricityPrice,
    CoolingCostRecord,
    EnergyCostCalculationResult,
    EnergyCostCalculator,
    CalculationStatus,
    InvalidPUEError,
    CoolingDoubleCountingError,
)

# --- Fixtures for common objects ---
@pytest.fixture
def default_it_record() -> ITPowerRecord:
    return ITPowerRecord(average_it_kw=1.0, quantity=10, active_hours=720) # 10kW * 720h = 7200 kWh

@pytest.fixture
def default_facility_policy() -> FacilityPolicy:
    return FacilityPolicy(pue=1.5, pue_includes_cooling=True)

@pytest.fixture
def default_electricity_price() -> ElectricityPrice:
    return ElectricityPrice(price_per_kwh=0.10)

@pytest.fixture
def default_cooling_record() -> CoolingCostRecord:
    return CoolingCostRecord(cooling_kwh=1000.0, cooling_cost=100.0)

# --- Test ITPowerRecord ---
class TestITPowerRecord:
    def test_valid_creation(self, default_it_record: ITPowerRecord) -> None:
        assert default_it_record.average_it_kw == 1.0
        assert default_it_record.quantity == 10
        assert default_it_record.active_hours == 720
        assert not default_it_record.is_tdp_assumption

    @pytest.mark.parametrize(
        "kw, qty, hours, expected_error_match",
        [
            (-1.0, 10, 720, "average_it_kw must be a non-negative number."),
            (1.0, 0, 720, "quantity must be a positive integer."),
            (1.0, -1, 720, "quantity must be a positive integer."),
            (1.0, 10, -1.0, "active_hours must be a non-negative number."),
            ("abc", 10, 720, "average_it_kw must be a non-negative number."),
            (1.0, 10.5, 720, "quantity must be a positive integer."),
            (1.0, 10, "def", "active_hours must be a non-negative number."),
        ],
    )
    def test_invalid_creation(self, kw, qty, hours, expected_error_match: str) -> None:
        with pytest.raises(ValueError, match=re.escape(expected_error_match)):
            ITPowerRecord(average_it_kw=kw, quantity=qty, active_hours=hours)

# --- Test FacilityPolicy ---
class TestFacilityPolicy:
    def test_valid_creation(self, default_facility_policy: FacilityPolicy) -> None:
        assert default_facility_policy.pue == 1.5
        assert default_facility_policy.pue_includes_cooling is True

    @pytest.mark.parametrize(
        "pue, includes_cooling, expected_error_type, expected_error_match",
        [
            (0.9, True, InvalidPUEError, "PUE (Power Usage Effectiveness) must be 1.0 or greater."),
            (1.0, True, None, None), # Valid
            (1.5, "not_bool", ValueError, "pue_includes_cooling must be a boolean."),
            ("abc", True, InvalidPUEError, "PUE (Power Usage Effectiveness) must be 1.0 or greater."),
        ],
    )
    def test_invalid_creation(self, pue, includes_cooling, expected_error_type, expected_error_match: str | None) -> None:
        if expected_error_type:
            with pytest.raises(expected_error_type, match=re.escape(expected_error_match)):
                FacilityPolicy(pue=pue, pue_includes_cooling=includes_cooling)
        else:
            # Test valid case
            policy = FacilityPolicy(pue=pue, pue_includes_cooling=includes_cooling)
            assert policy.pue == pue
            assert policy.pue_includes_cooling == includes_cooling

# --- Test ElectricityPrice ---
class TestElectricityPrice:
    def test_valid_creation(self, default_electricity_price: ElectricityPrice) -> None:
        assert default_electricity_price.price_per_kwh == 0.10

    @pytest.mark.parametrize(
        "price, expected_error_match",
        [
            (-0.01, "price_per_kwh must be a non-negative number."),
            ("abc", "price_per_kwh must be a non-negative number."),
        ],
    )
    def test_invalid_creation(self, price, expected_error_match: str) -> None:
        with pytest.raises(ValueError, match=re.escape(expected_error_match)):
            ElectricityPrice(price_per_kwh=price)

# --- Test CoolingCostRecord ---
class TestCoolingCostRecord:
    def test_valid_creation(self, default_cooling_record: CoolingCostRecord) -> None:
        assert default_cooling_record.cooling_kwh == 1000.0
        assert default_cooling_record.cooling_cost == 100.0
        assert not default_cooling_record.is_explicitly_excluded_from_pue

    @pytest.mark.parametrize(
        "kwh, cost, excluded, expected_error_match",
        [
            (-1.0, 100.0, False, "cooling_kwh must be a non-negative number."),
            (1000.0, -1.0, False, "cooling_cost must be a non-negative number."),
            (1000.0, 100.0, "not_bool", "is_explicitly_excluded_from_pue must be a boolean."),
            ("abc", 100.0, False, "cooling_kwh must be a non-negative number."),
            (1000.0, "def", False, "cooling_cost must be a non-negative number."),
        ],
    )
    def test_invalid_creation(self, kwh, cost, excluded, expected_error_match: str) -> None:
        with pytest.raises(ValueError, match=re.escape(expected_error_match)):
            CoolingCostRecord(cooling_kwh=kwh, cooling_cost=cost, is_explicitly_excluded_from_pue=excluded)

# --- Test EnergyCostCalculationResult ---
class TestEnergyCostCalculationResult:
    def test_valid_creation(self) -> None:
        result = EnergyCostCalculationResult(
            monthly_facility_kwh=10000.0,
            monthly_energy_cost=1000.0,
            status=CalculationStatus.MEASURED_DATA,
            warnings=["Test warning"],
        )
        assert result.monthly_facility_kwh == 10000.0
        assert result.monthly_energy_cost == 1000.0
        assert result.status == CalculationStatus.MEASURED_DATA
        assert result.warnings == ["Test warning"]

    @pytest.mark.parametrize(
        "kwh, cost, status, warnings, expected_error_match",
        [
            (-1.0, 1000.0, CalculationStatus.MEASURED_DATA, [], "monthly_facility_kwh must be a non-negative number."),
            (10000.0, -1.0, CalculationStatus.MEASURED_DATA, [], "monthly_energy_cost must be a non-negative number."),
            (10000.0, 1000.0, "INVALID_STATUS", [], "status must be a CalculationStatus enum member."),
            (10000.0, 1000.0, CalculationStatus.MEASURED_DATA, "not_list", "warnings must be a list of strings."),
            (10000.0, 1000.0, CalculationStatus.MEASURED_DATA, [123], "All warnings must be strings."),
        ],
    )
    def test_invalid_creation(self, kwh, cost, status, warnings, expected_error_match: str) -> None:
        with pytest.raises(ValueError, match=re.escape(expected_error_match)):
            EnergyCostCalculationResult(
                monthly_facility_kwh=kwh,
                monthly_energy_cost=cost,
                status=status,
                warnings=warnings,
            )

# --- Test EnergyCostCalculator ---
class TestEnergyCostCalculator:
    def test_basic_calculation(
        self,
        default_it_record: ITPowerRecord,
        default_facility_policy: FacilityPolicy,
        default_electricity_price: ElectricityPrice,
    ) -> None:
        # 1.0kW * 10 qty * 720 hours = 7200 kWh IT raw
        # monthly_facility_kwh = 7200 kWh * 1.5 PUE = 10800 kWh
        # monthly_energy_cost = 10800 kWh * $0.10/kWh = $1080.0
        
        # Adjust default_facility_policy to not include cooling for basic test
        policy_no_cooling = dataclasses.replace(default_facility_policy, pue_includes_cooling=False)

        result = EnergyCostCalculator.calculate_monthly_energy_cost(
            it_power_records=[default_it_record],
            facility_policy=policy_no_cooling,
            electricity_price=default_electricity_price,
        )

        assert result.monthly_facility_kwh == 10800.0
        assert result.monthly_energy_cost == 1080.0
        assert result.status == CalculationStatus.MEASURED_DATA
        assert not result.warnings

    def test_multiple_it_records(
        self,
        default_facility_policy: FacilityPolicy,
        default_electricity_price: ElectricityPrice,
    ) -> None:
        record1 = ITPowerRecord(average_it_kw=5.0, quantity=2, active_hours=720) # 7200 kWh
        record2 = ITPowerRecord(average_it_kw=2.0, quantity=5, active_hours=360) # 3600 kWh
        # Total IT raw = 7200 + 3600 = 10800 kWh
        # monthly_facility_kwh = 10800 kWh * 1.5 PUE = 16200 kWh
        # monthly_energy_cost = 16200 kWh * $0.10/kWh = $1620.0

        policy_no_cooling = dataclasses.replace(default_facility_policy, pue_includes_cooling=False)

        result = EnergyCostCalculator.calculate_monthly_energy_cost(
            it_power_records=[record1, record2],
            facility_policy=policy_no_cooling,
            electricity_price=default_electricity_price,
        )

        assert result.monthly_facility_kwh == 16200.0
        assert result.monthly_energy_cost == 1620.0
        assert result.status == CalculationStatus.MEASURED_DATA
        assert not result.warnings

    def test_pue_less_than_one_raises_error(
        self,
        default_it_record: ITPowerRecord,
        default_electricity_price: ElectricityPrice,
    ) -> None:
        with pytest.raises(InvalidPUEError, match=re.escape("PUE (Power Usage Effectiveness) must be 1.0 or greater.")):
            FacilityPolicy(pue=0.9, pue_includes_cooling=False)

    def test_tdp_assumption_flags_status_and_adds_warning(
        self,
        default_it_record: ITPowerRecord,
        default_facility_policy: FacilityPolicy,
        default_electricity_price: ElectricityPrice,
    ) -> None:
        tdp_record = dataclasses.replace(default_it_record, is_tdp_assumption=True)
        policy_no_cooling = dataclasses.replace(default_facility_policy, pue_includes_cooling=False)

        result = EnergyCostCalculator.calculate_monthly_energy_cost(
            it_power_records=[tdp_record],
            facility_policy=policy_no_cooling,
            electricity_price=default_electricity_price,
        )

        assert result.status == CalculationStatus.ASSUMPTION_BASED
        assert "Calculation includes TDP (Thermal Design Power) as an assumption for IT power." in result.warnings

    # --- RSK-009 Cooling Double-Counting Tests ---
    def test_rsk009_double_counting_error(
        self,
        default_it_record: ITPowerRecord,
        default_facility_policy: FacilityPolicy, # pue_includes_cooling=True
        default_electricity_price: ElectricityPrice,
        default_cooling_record: CoolingCostRecord, # is_explicitly_excluded_from_pue=False
    ) -> None:
        with pytest.raises(CoolingDoubleCountingError, match=re.escape(
            "RSK-009: Cooling costs are potentially double-counted. "
            "Facility PUE includes cooling overhead, but a separate CoolingCostRecord "
            "is provided without explicit proof of exclusion from PUE observation."
        )):
            EnergyCostCalculator.calculate_monthly_energy_cost(
                it_power_records=[default_it_record],
                facility_policy=default_facility_policy,
                electricity_price=default_electricity_price,
                cooling_cost_record=default_cooling_record,
            )

    def test_rsk009_cooling_explicitly_excluded_from_pue_added(
        self,
        default_it_record: ITPowerRecord,
        default_facility_policy: FacilityPolicy, # pue_includes_cooling=True
        default_electricity_price: ElectricityPrice,
        default_cooling_record: CoolingCostRecord,
    ) -> None:
        excluded_cooling_record = dataclasses.replace(default_cooling_record, is_explicitly_excluded_from_pue=True)

        result = EnergyCostCalculator.calculate_monthly_energy_cost(
            it_power_records=[default_it_record],
            facility_policy=default_facility_policy,
            electricity_price=default_electricity_price,
            cooling_cost_record=excluded_cooling_record,
        )

        assert result.monthly_facility_kwh == 11800.0
        assert result.monthly_energy_cost == 1180.0
        assert CalculationStatus.MEASURED_DATA == result.status
        assert "RSK-009: Separate cooling costs added, explicitly excluded from PUE observation, " \
               "even though Facility PUE generally includes cooling overhead." in result.warnings

    def test_rsk009_pue_does_not_include_cooling_separate_cooling_added(
        self,
        default_it_record: ITPowerRecord,
        default_electricity_price: ElectricityPrice,
        default_cooling_record: CoolingCostRecord,
    ) -> None:
        policy_no_cooling = FacilityPolicy(pue=1.5, pue_includes_cooling=False)

        result = EnergyCostCalculator.calculate_monthly_energy_cost(
            it_power_records=[default_it_record],
            facility_policy=policy_no_cooling,
            electricity_price=default_electricity_price,
            cooling_cost_record=default_cooling_record,
        )

        assert result.monthly_facility_kwh == 11800.0
        assert result.monthly_energy_cost == 1180.0
        assert CalculationStatus.MEASURED_DATA == result.status
        assert "Separate cooling costs added as Facility PUE does not include cooling overhead." in result.warnings

    def test_rsk009_no_cooling_record_no_impact(
        self,
        default_it_record: ITPowerRecord,
        default_facility_policy: FacilityPolicy,
        default_electricity_price: ElectricityPrice,
    ) -> None:
        policy_no_cooling = dataclasses.replace(default_facility_policy, pue_includes_cooling=False)

        result = EnergyCostCalculator.calculate_monthly_energy_cost(
            it_power_records=[default_it_record],
            facility_policy=policy_no_cooling,
            electricity_price=default_electricity_price,
            cooling_cost_record=None,
        )

        assert result.monthly_facility_kwh == 10800.0
        assert result.monthly_energy_cost == 1080.0
        assert CalculationStatus.MEASURED_DATA == result.status
        assert not result.warnings

    # --- Input Validation for Calculator Method ---
    @pytest.mark.parametrize(
        "it_records, policy, price, cooling_record, expected_error_match",
        [
            ("not_list", FacilityPolicy(pue=1.0, pue_includes_cooling=False), ElectricityPrice(0.1), None, "All items in it_power_records must be ITPowerRecord instances."),
            ([ITPowerRecord(1,1,1), "not_record"], FacilityPolicy(pue=1.0, pue_includes_cooling=False), ElectricityPrice(0.1), None, "All items in it_power_records must be ITPowerRecord instances."),
            ([ITPowerRecord(1,1,1)], "not_policy", ElectricityPrice(0.1), None, "facility_policy must be a FacilityPolicy instance."),
            ([ITPowerRecord(1,1,1)], FacilityPolicy(pue=1.0, pue_includes_cooling=False), "not_price", None, "electricity_price must be an ElectricityPrice instance."),
            ([ITPowerRecord(1,1,1)], FacilityPolicy(pue=1.0, pue_includes_cooling=False), ElectricityPrice(0.1), "not_cooling", "cooling_cost_record must be a CoolingCostRecord instance or None."),
        ],
    )
    def test_calculator_input_validation(
        self, it_records, policy, price, cooling_record, expected_error_match: str
    ) -> None:
        with pytest.raises(ValueError, match=re.escape(expected_error_match)):
            EnergyCostCalculator.calculate_monthly_energy_cost(
                it_power_records=it_records,
                facility_policy=policy,
                electricity_price=price,
                cooling_cost_record=cooling_record,
            )

    def test_zero_values_calculation(self) -> None:
        it_record_zero_power = ITPowerRecord(average_it_kw=0.0, quantity=10, active_hours=720)
        it_record_zero_hours = ITPowerRecord(average_it_kw=1.0, quantity=10, active_hours=0)

        policy = FacilityPolicy(pue=1.0, pue_includes_cooling=False)
        price_zero = ElectricityPrice(price_per_kwh=0.0)
        price_non_zero = ElectricityPrice(price_per_kwh=0.1)

        # Test with zero power
        result_zero_power = EnergyCostCalculator.calculate_monthly_energy_cost(
            it_power_records=[it_record_zero_power],
            facility_policy=policy,
            electricity_price=price_non_zero,
        )
        assert result_zero_power.monthly_facility_kwh == 0.0
        assert result_zero_power.monthly_energy_cost == 0.0

        # Test with zero hours
        result_zero_hours = EnergyCostCalculator.calculate_monthly_energy_cost(
            it_power_records=[it_record_zero_hours],
            facility_policy=policy,
            electricity_price=price_non_zero,
        )
        assert result_zero_hours.monthly_facility_kwh == 0.0
        assert result_zero_hours.monthly_energy_cost == 0.0

        # Test with zero price
        result_zero_price = EnergyCostCalculator.calculate_monthly_energy_cost(
            it_power_records=[ITPowerRecord(average_it_kw=1.0, quantity=1, active_hours=1)],
            facility_policy=policy,
            electricity_price=price_zero,
        )
        assert result_zero_price.monthly_facility_kwh == 1.0 # 1kW * 1qty * 1hr * 1.0 PUE
        assert result_zero_price.monthly_energy_cost == 0.0
