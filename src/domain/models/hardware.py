"""Hardware and Datacenter Value Objects for Universal Hybrid FinOps Advisor."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from types import MappingProxyType
from typing import Mapping

from src.domain.exceptions import DomainLookupError
from src.domain.models.financial import MonetaryAmount
from src.domain.models.validation import assert_strict_decimal

WATTS_PER_KILOWATT: Decimal = Decimal("1000")


class InterconnectType(str, Enum):
    PCIE_GEN4 = "PCIE_GEN4"
    PCIE_GEN5 = "PCIE_GEN5"
    NVLINK_SXM4 = "NVLINK_SXM4"
    NVLINK_SXM5 = "NVLINK_SXM5"
    NVLINK_SXM6 = "NVLINK_SXM6"
    INFINIBAND_NDR = "INFINIBAND_NDR"
    INFINIBAND_XDR = "INFINIBAND_XDR"
    ROCE_V2 = "ROCE_V2"
    CUSTOM_FABRIC = "CUSTOM_FABRIC"


class CoolingTopology(str, Enum):
    AIR_COOLED = "AIR_COOLED"
    DIRECT_LIQUID_COOLED = "DIRECT_LIQUID_COOLED"
    IMMERSION = "IMMERSION"


@dataclass(frozen=True)
class HardwareAcceleratorSpec:
    """Immutable physics specification of a physical AI accelerator silicon."""

    sku_id: str
    vendor: str
    architecture: str
    fp16_tflops: Decimal
    fp8_tflops: Decimal
    int8_tops: Decimal
    vram_gb: Decimal
    memory_bandwidth_gbps: Decimal
    interconnect: InterconnectType
    interconnect_bandwidth_gbps: Decimal
    tensor_parallel_efficiency_factor: Decimal  # Declared from catalog (e.g. 0.94 for NVLink, 0.70 for PCIe)
    tdp_watts: Decimal
    annualized_failure_rate_pct: Decimal        # Silicon AFR (e.g. 0.035 for 3.5%)
    mttr_replacement_hours: Decimal             # Physical replacement MTTR for RMA

    def __post_init__(self) -> None:
        assert_strict_decimal(self.fp16_tflops, "fp16_tflops")
        assert_strict_decimal(self.fp8_tflops, "fp8_tflops")
        assert_strict_decimal(self.int8_tops, "int8_tops")
        assert_strict_decimal(self.vram_gb, "vram_gb")
        assert_strict_decimal(self.memory_bandwidth_gbps, "memory_bandwidth_gbps")
        assert_strict_decimal(self.interconnect_bandwidth_gbps, "interconnect_bandwidth_gbps")
        assert_strict_decimal(self.tensor_parallel_efficiency_factor, "tensor_parallel_efficiency_factor")
        assert_strict_decimal(self.tdp_watts, "tdp_watts")
        assert_strict_decimal(self.annualized_failure_rate_pct, "annualized_failure_rate_pct")
        assert_strict_decimal(self.mttr_replacement_hours, "mttr_replacement_hours")

        if (
            self.vram_gb <= Decimal("0")
            or self.memory_bandwidth_gbps <= Decimal("0")
            or self.tdp_watts <= Decimal("0")
            or self.mttr_replacement_hours <= Decimal("0")
            or self.fp16_tflops <= Decimal("0")
            or self.interconnect_bandwidth_gbps <= Decimal("0")
        ):
            raise ValueError(f"Hardware accelerator '{self.sku_id}' physical parameters must be strictly positive.")

        if self.fp8_tflops < Decimal("0") or self.int8_tops < Decimal("0"):
            raise ValueError(f"Accelerator '{self.sku_id}' compute rates cannot be negative.")

        if not (Decimal("0") < self.tensor_parallel_efficiency_factor <= Decimal("1.0")):
            raise ValueError(
                f"Accelerator '{self.sku_id}' tensor_parallel_efficiency_factor must be in range (0.0, 1.0], "
                f"got {self.tensor_parallel_efficiency_factor}."
            )

        if not (Decimal("0") <= self.annualized_failure_rate_pct <= Decimal("1.0")):
            raise ValueError(
                f"Accelerator '{self.sku_id}' annualized_failure_rate_pct must be in range [0.0, 1.0], "
                f"got {self.annualized_failure_rate_pct}."
            )


@dataclass(frozen=True)
class ServerChassisSpec:
    """Bare-metal on-premise server Bill of Materials (BOM) specification."""

    chassis_id: str
    oem_vendor: str
    model_name: str
    accelerator_sku: HardwareAcceleratorSpec
    accelerators_per_chassis: int
    base_system_power_watts: Decimal                        # CPU, host RAM, NVMe, fans, NICs
    rack_units_u: int
    capex_unit_price: MonetaryAmount
    oem_warranty_annual_pct: Decimal                        # 24/7 Mission-Critical Care Pack % of CapEx
    salvage_value_by_horizon_months: Mapping[int, Decimal]   # Dynamic depreciation salvage schedule

    def __post_init__(self) -> None:
        if isinstance(self.accelerators_per_chassis, bool) or not isinstance(self.accelerators_per_chassis, int) or self.accelerators_per_chassis <= 0:
            raise ValueError(f"Server chassis '{self.chassis_id}' accelerators_per_chassis must be a positive integer.")
        if isinstance(self.rack_units_u, bool) or not isinstance(self.rack_units_u, int) or self.rack_units_u <= 0:
            raise ValueError(f"Server chassis '{self.chassis_id}' rack_units_u must be a positive integer.")

        assert_strict_decimal(self.base_system_power_watts, "base_system_power_watts")
        assert_strict_decimal(self.oem_warranty_annual_pct, "oem_warranty_annual_pct")

        if self.base_system_power_watts < Decimal("0") or self.oem_warranty_annual_pct < Decimal("0"):
            raise ValueError(f"Server chassis '{self.chassis_id}' power and warranty percentage cannot be negative.")

        if not self.salvage_value_by_horizon_months:
            raise ValueError(f"Server chassis '{self.chassis_id}' must define a non-empty salvage value schedule.")

        for horizon, salvage_ratio in self.salvage_value_by_horizon_months.items():
            if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon <= 0:
                raise ValueError(f"Chassis '{self.chassis_id}' horizon months must be positive integer, got {horizon}.")
            assert_strict_decimal(salvage_ratio, f"salvage_ratio_{horizon}m")
            if not (Decimal("0") <= salvage_ratio <= Decimal("1.0")):
                raise ValueError(
                    f"Chassis '{self.chassis_id}' salvage ratio for {horizon}m must be in range [0.0, 1.0], "
                    f"got {salvage_ratio}."
                )

        # Guarantee true deep immutability using MappingProxyType
        object.__setattr__(
            self,
            "salvage_value_by_horizon_months",
            MappingProxyType(dict(self.salvage_value_by_horizon_months)),
        )

    @property
    def total_chassis_tdp_kw(self) -> Decimal:
        accel_total = self.accelerator_sku.tdp_watts * Decimal(self.accelerators_per_chassis)
        return (accel_total + self.base_system_power_watts) / WATTS_PER_KILOWATT

    def get_salvage_value_pct(self, horizon_months: int) -> Decimal:
        """Retrieves salvage value percentage with deterministic tie-breaking toward longer horizon."""
        if not self.salvage_value_by_horizon_months:
            raise DomainLookupError(f"No salvage value schedule defined for chassis '{self.chassis_id}'.")
        if horizon_months in self.salvage_value_by_horizon_months:
            return self.salvage_value_by_horizon_months[horizon_months]
        # Closest horizon fallback; ties broken deterministically toward the longer (more conservative) horizon
        closest_horizon = min(
            self.salvage_value_by_horizon_months.keys(),
            key=lambda h: (abs(h - horizon_months), -h),
        )
        return self.salvage_value_by_horizon_months[closest_horizon]


@dataclass(frozen=True)
class CloudInstancePricingSpec:
    """Cloud VM instance specification with Spot and On-Demand pricing."""

    instance_id: str
    provider_id: str
    region: str
    instance_type: str
    accelerator_sku: HardwareAcceleratorSpec
    accelerators_per_instance: int
    on_demand_hourly: MonetaryAmount
    reserved_1yr_hourly: MonetaryAmount
    reserved_3yr_hourly: MonetaryAmount
    spot_hourly_mean: MonetaryAmount
    spot_preemption_probability_daily: Decimal  # Open FAIR LEF input (e.g. 0.03)
    cold_boot_rebuild_seconds: Decimal          # Image pull + weight load MTTR
    storage_gb_monthly: MonetaryAmount
    egress_gb_price: MonetaryAmount

    def __post_init__(self) -> None:
        if isinstance(self.accelerators_per_instance, bool) or not isinstance(self.accelerators_per_instance, int) or self.accelerators_per_instance <= 0:
            raise ValueError(f"Cloud instance '{self.instance_type}' accelerator count must be strictly positive integer.")
        assert_strict_decimal(self.spot_preemption_probability_daily, "spot_preemption_probability_daily")
        assert_strict_decimal(self.cold_boot_rebuild_seconds, "cold_boot_rebuild_seconds")

        if not (Decimal("0") <= self.spot_preemption_probability_daily <= Decimal("1.0")):
            raise ValueError(
                f"Cloud instance '{self.instance_type}' spot preemption probability must be in range [0.0, 1.0], "
                f"got {self.spot_preemption_probability_daily}."
            )
        if self.cold_boot_rebuild_seconds < Decimal("0"):
            raise ValueError(f"Cloud instance '{self.instance_type}' cold boot rebuild seconds cannot be negative.")

        # Ensure currency uniformity across all pricing components
        target_currency = self.on_demand_hourly.currency
        for item, name in [
            (self.reserved_1yr_hourly, "reserved_1yr_hourly"),
            (self.reserved_3yr_hourly, "reserved_3yr_hourly"),
            (self.spot_hourly_mean, "spot_hourly_mean"),
            (self.storage_gb_monthly, "storage_gb_monthly"),
            (self.egress_gb_price, "egress_gb_price"),
        ]:
            if item.currency != target_currency:
                raise ValueError(
                    f"Currency mismatch in CloudInstancePricingSpec for '{name}': '{item.currency}' vs expected '{target_currency}'."
                )


@dataclass(frozen=True)
class DatacenterFacilitySpec:
    """On-premise enterprise facility physical and economic constraints."""

    facility_id: str
    pue_rating: Decimal
    max_rack_power_density_kw: Decimal
    electricity_rate_per_kwh: MonetaryAmount
    colocation_rack_monthly_fee: MonetaryAmount
    cooling_topology: CoolingTopology
    max_rack_units_u: int = 42

    def __post_init__(self) -> None:
        assert_strict_decimal(self.pue_rating, "pue_rating")
        assert_strict_decimal(self.max_rack_power_density_kw, "max_rack_power_density_kw")

        if isinstance(self.max_rack_units_u, bool) or not isinstance(self.max_rack_units_u, int) or self.max_rack_units_u <= 0:
            raise ValueError(f"max_rack_units_u must be a positive integer, got {self.max_rack_units_u}.")

        if self.max_rack_power_density_kw <= Decimal("0") or self.pue_rating < Decimal("1.0"):
            raise ValueError(
                f"Datacenter facility '{self.facility_id}' max power must be positive and PUE >= 1.0, "
                f"got power={self.max_rack_power_density_kw}, PUE={self.pue_rating}."
            )

        if self.electricity_rate_per_kwh.currency != self.colocation_rack_monthly_fee.currency:
            raise ValueError(
                f"Currency mismatch in DatacenterFacilitySpec: electricity_rate_per_kwh '{self.electricity_rate_per_kwh.currency}' "
                f"vs colocation_rack_monthly_fee '{self.colocation_rack_monthly_fee.currency}'."
            )
