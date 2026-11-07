import dataclasses
from enum import Enum
from typing import Self, TypeAlias, Sequence

# --- Type Aliases (PEP 695) ---
Kilowatt: TypeAlias = float
Hours: TypeAlias = float
Quantity: TypeAlias = int
PricePerKWH: TypeAlias = float
PUEValue: TypeAlias = float
KilowattHour: TypeAlias = float

# --- Enums ---
class CalculationStatus(Enum):
    """
    Represents the status of an energy cost calculation.
    """
    MEASURED_DATA = "MEASURED_DATA"
    ASSUMPTION_BASED = "ASSUMPTION_BASED"

# --- Exceptions ---
class EnergyCalculationError(Exception):
    """Base exception for energy cost calculation errors."""
    pass

class InvalidPUEError(EnergyCalculationError):
    """Raised when PUE is less than 1.0."""
    pass

class CoolingDoubleCountingError(EnergyCalculationError):
    """Raised when cooling costs are double-counted due to PUE inclusion."""
    pass

# --- Input Dataclasses ---
@dataclasses.dataclass(frozen=True)
class ITPowerRecord:
    """
    Represents the power consumption of a single IT component or group.
    """
    average_it_kw: Kilowatt
    quantity: Quantity
    active_hours: Hours
    is_tdp_assumption: bool

    def __init__(
        self,
        average_it_kw: Kilowatt,
        quantity: Quantity,
        active_hours: Hours,
        is_tdp_assumption: bool = False,
    ) -> None:
        object.__setattr__(self, "average_it_kw", average_it_kw)
        object.__setattr__(self, "quantity", quantity)
        object.__setattr__(self, "active_hours", active_hours)
        object.__setattr__(self, "is_tdp_assumption", is_tdp_assumption)
        self.__post_init__()

    def __post_init__(self: Self) -> None:
        if isinstance(self.average_it_kw, bool) or not isinstance(self.average_it_kw, (int, float)) or self.average_it_kw < 0:
            raise ValueError("average_it_kw must be a non-negative number.")
        if isinstance(self.quantity, bool) or not isinstance(self.quantity, int) or self.quantity <= 0:
            raise ValueError("quantity must be a positive integer.")
        if isinstance(self.active_hours, bool) or not isinstance(self.active_hours, (int, float)) or self.active_hours < 0:
            raise ValueError("active_hours must be a non-negative number.")

@dataclasses.dataclass(frozen=True)
class FacilityPolicy:
    """
    Defines facility-level policies relevant to energy calculation.
    """
    pue: PUEValue
    pue_includes_cooling: bool

    def __post_init__(self: Self) -> None:
        if isinstance(self.pue, bool) or not isinstance(self.pue, (int, float)) or self.pue < 1.0:
            raise InvalidPUEError("PUE (Power Usage Effectiveness) must be 1.0 or greater.")
        if not isinstance(self.pue_includes_cooling, bool):
            raise ValueError("pue_includes_cooling must be a boolean.")

@dataclasses.dataclass(frozen=True)
class ElectricityPrice:
    """
    Represents the cost of electricity per kilowatt-hour.
    """
    price_per_kwh: PricePerKWH

    def __post_init__(self: Self) -> None:
        if isinstance(self.price_per_kwh, bool) or not isinstance(self.price_per_kwh, (int, float)) or self.price_per_kwh < 0:
            raise ValueError("price_per_kwh must be a non-negative number.")

@dataclasses.dataclass(frozen=True)
class CoolingCostRecord:
    """
    Represents a separate record of cooling energy consumption and cost.
    Used to detect potential double-counting.
    """
    cooling_kwh: KilowattHour
    cooling_cost: float
    is_explicitly_excluded_from_pue: bool

    def __init__(
        self,
        cooling_kwh: KilowattHour,
        cooling_cost: float,
        is_explicitly_excluded_from_pue: bool = False,
    ) -> None:
        object.__setattr__(self, "cooling_kwh", cooling_kwh)
        object.__setattr__(self, "cooling_cost", cooling_cost)
        object.__setattr__(self, "is_explicitly_excluded_from_pue", is_explicitly_excluded_from_pue)
        self.__post_init__()

    def __post_init__(self: Self) -> None:
        if isinstance(self.cooling_kwh, bool) or not isinstance(self.cooling_kwh, (int, float)) or self.cooling_kwh < 0:
            raise ValueError("cooling_kwh must be a non-negative number.")
        if isinstance(self.cooling_cost, bool) or not isinstance(self.cooling_cost, (int, float)) or self.cooling_cost < 0:
            raise ValueError("cooling_cost must be a non-negative number.")
        if not isinstance(self.is_explicitly_excluded_from_pue, bool):
            raise ValueError("is_explicitly_excluded_from_pue must be a boolean.")

# --- Output Dataclass ---
@dataclasses.dataclass(frozen=True)
class EnergyCostCalculationResult:
    """
    The result of an energy cost calculation.
    """
    monthly_facility_kwh: KilowattHour
    monthly_energy_cost: float
    status: CalculationStatus
    warnings: list[str]

    def __init__(
        self,
        monthly_facility_kwh: KilowattHour,
        monthly_energy_cost: float,
        status: CalculationStatus,
        warnings: list[str] | None = None,
    ) -> None:
        object.__setattr__(self, "monthly_facility_kwh", monthly_facility_kwh)
        object.__setattr__(self, "monthly_energy_cost", monthly_energy_cost)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "warnings", [] if warnings is None else warnings)
        self.__post_init__()

    def __post_init__(self: Self) -> None:
        if isinstance(self.monthly_facility_kwh, bool) or not isinstance(self.monthly_facility_kwh, (int, float)) or self.monthly_facility_kwh < 0:
            raise ValueError("monthly_facility_kwh must be a non-negative number.")
        if isinstance(self.monthly_energy_cost, bool) or not isinstance(self.monthly_energy_cost, (int, float)) or self.monthly_energy_cost < 0:
            raise ValueError("monthly_energy_cost must be a non-negative number.")
        if not isinstance(self.status, CalculationStatus):
            raise ValueError("status must be a CalculationStatus enum member.")
        if not isinstance(self.warnings, list):
            raise ValueError("warnings must be a list of strings.")
        if not all(isinstance(w, str) for w in self.warnings):
            raise ValueError("All warnings must be strings.")


# --- Calculator Logic ---
class EnergyCostCalculator:
    """
    Calculates monthly energy consumption and cost based on IT power records,
    facility policy, and electricity pricing.
    Enforces dimensional compatibility and prevents cooling double-counting.
    """

    @staticmethod
    def calculate_monthly_energy_cost(
        it_power_records: Sequence[ITPowerRecord],
        facility_policy: FacilityPolicy,
        electricity_price: ElectricityPrice,
        cooling_cost_record: CoolingCostRecord | None = None,
    ) -> EnergyCostCalculationResult:
        """
        Calculates the monthly facility energy consumption and cost.

        Args:
            it_power_records: A sequence of ITPowerRecord instances.
            facility_policy: FacilityPolicy instance containing PUE and cooling inclusion info.
            electricity_price: ElectricityPrice instance.
            cooling_cost_record: Optional CoolingCostRecord for separate cooling costs.

        Returns:
            An EnergyCostCalculationResult instance.

        Raises:
            InvalidPUEError: If the PUE in facility_policy is less than 1.0.
            CoolingDoubleCountingError: If cooling costs are double-counted (RSK-009).
            ValueError: For invalid input data types or values.
        """
        if not isinstance(it_power_records, Sequence):
            raise ValueError("it_power_records must be a sequence.")
        if not all(isinstance(rec, ITPowerRecord) for rec in it_power_records):
            raise ValueError("All items in it_power_records must be ITPowerRecord instances.")
        if not isinstance(facility_policy, FacilityPolicy):
            raise ValueError("facility_policy must be a FacilityPolicy instance.")
        if not isinstance(electricity_price, ElectricityPrice):
            raise ValueError("electricity_price must be an ElectricityPrice instance.")
        if cooling_cost_record is not None and not isinstance(cooling_cost_record, CoolingCostRecord):
            raise ValueError("cooling_cost_record must be a CoolingCostRecord instance or None.")

        total_it_kwh_raw = 0.0
        calculation_status = CalculationStatus.MEASURED_DATA
        warnings: list[str] = []

        # Calculate sum(average_it_kw_i * quantity_i * active_hours_i)
        for record in it_power_records:
            if record.is_tdp_assumption:
                calculation_status = CalculationStatus.ASSUMPTION_BASED
                warnings.append("Calculation includes TDP (Thermal Design Power) as an assumption for IT power.")
            total_it_kwh_raw += record.average_it_kw * record.quantity * record.active_hours

        # Formula TCO-002: monthly_facility_kwh = sum(...) * pue
        monthly_facility_kwh = total_it_kwh_raw * facility_policy.pue

        # Formula TCO-002: monthly_energy_cost = monthly_facility_kwh * electricity_price_per_kwh
        monthly_energy_cost = monthly_facility_kwh * electricity_price.price_per_kwh

        # RSK-009: Prevent cooling double-counting
        if facility_policy.pue_includes_cooling:
            if cooling_cost_record and not cooling_cost_record.is_explicitly_excluded_from_pue:
                raise CoolingDoubleCountingError(
                    "RSK-009: Cooling costs are potentially double-counted. "
                    "Facility PUE includes cooling overhead, but a separate CoolingCostRecord "
                    "is provided without explicit proof of exclusion from PUE observation."
                )
            elif cooling_cost_record and cooling_cost_record.is_explicitly_excluded_from_pue:
                monthly_facility_kwh += cooling_cost_record.cooling_kwh
                monthly_energy_cost += cooling_cost_record.cooling_cost
                warnings.append(
                    "RSK-009: Separate cooling costs added, explicitly excluded from PUE observation, "
                    "even though Facility PUE generally includes cooling overhead."
                )
        else:
            if cooling_cost_record:
                monthly_facility_kwh += cooling_cost_record.cooling_kwh
                monthly_energy_cost += cooling_cost_record.cooling_cost
                warnings.append(
                    "Separate cooling costs added as Facility PUE does not include cooling overhead."
                )

        return EnergyCostCalculationResult(
            monthly_facility_kwh=monthly_facility_kwh,
            monthly_energy_cost=monthly_energy_cost,
            status=calculation_status,
            warnings=warnings,
        )
