"""JSON-backed Hardware Registry Adapter implementing HardwareRegistryPort."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from types import MappingProxyType
from typing import Mapping, Sequence

from src.domain.exceptions import DomainLookupError
from src.domain.models.financial import CurrencyCode, MonetaryAmount
from src.domain.models.hardware import (
    HardwareAcceleratorSpec,
    InterconnectType,
    ServerChassisSpec,
)
from src.domain.ports.hardware_registry import HardwareRegistryPort


class JsonHardwareRegistryAdapter(HardwareRegistryPort):
    """Loads declarative hardware accelerator physics and server chassis BOMs from JSON catalog."""

    def __init__(self, catalog_path: Path) -> None:
        self._catalog_path = catalog_path
        self._accelerators: dict[str, HardwareAcceleratorSpec] = {}
        self._chassis: dict[str, ServerChassisSpec] = {}
        self._load_catalog()

    def _load_catalog(self) -> None:
        if not self._catalog_path.is_file():
            raise FileNotFoundError(f"Hardware catalog file not found at: {self._catalog_path}")

        raw_data = json.loads(self._catalog_path.read_text(encoding="utf-8"))

        for sku_id, spec_data in raw_data.get("accelerators", {}).items():
            self._accelerators[sku_id] = HardwareAcceleratorSpec(
                sku_id=sku_id,
                vendor=spec_data["vendor"],
                architecture=spec_data["architecture"],
                fp16_tflops=Decimal(spec_data["fp16_tflops"]),
                fp8_tflops=Decimal(spec_data["fp8_tflops"]),
                int8_tops=Decimal(spec_data["int8_tops"]),
                vram_gb=Decimal(spec_data["vram_gb"]),
                memory_bandwidth_gbps=Decimal(spec_data["memory_bandwidth_gbps"]),
                interconnect=InterconnectType[spec_data["interconnect"]],
                interconnect_bandwidth_gbps=Decimal(spec_data["interconnect_bandwidth_gbps"]),
                tensor_parallel_efficiency_factor=Decimal(spec_data["tensor_parallel_efficiency_factor"]),
                tdp_watts=Decimal(spec_data["tdp_watts"]),
                annualized_failure_rate_pct=Decimal(spec_data["annualized_failure_rate_pct"]),
                mttr_replacement_hours=Decimal(spec_data["mttr_replacement_hours"]),
            )

        for chassis_id, c_data in raw_data.get("chassis", {}).items():
            accel_sku_id = c_data["accelerator_sku_id"]
            if accel_sku_id not in self._accelerators:
                raise DomainLookupError(
                    f"Chassis '{chassis_id}' references unknown accelerator SKU '{accel_sku_id}'."
                )

            salvage_map = {
                int(months): Decimal(pct)
                for months, pct in c_data.get("salvage_value_by_horizon_months", {}).items()
            }

            self._chassis[chassis_id] = ServerChassisSpec(
                chassis_id=chassis_id,
                oem_vendor=c_data["oem_vendor"],
                model_name=c_data["model_name"],
                accelerator_sku=self._accelerators[accel_sku_id],
                accelerators_per_chassis=int(c_data["accelerators_per_chassis"]),
                base_system_power_watts=Decimal(c_data["base_system_power_watts"]),
                rack_units_u=int(c_data["rack_units_u"]),
                capex_unit_price=MonetaryAmount(
                    amount=Decimal(c_data["capex_unit_price"]["amount"]),
                    currency=CurrencyCode(c_data["capex_unit_price"]["currency"]),
                ),
                oem_warranty_annual_pct=Decimal(c_data["oem_warranty_annual_pct"]),
                salvage_value_by_horizon_months=salvage_map,
            )

    def get_accelerator_spec(self, sku_id: str) -> HardwareAcceleratorSpec:
        """Dynamically resolves silicon physics specification. Raises DomainLookupError if absent."""
        if sku_id not in self._accelerators:
            raise DomainLookupError(f"Accelerator SKU '{sku_id}' not found in hardware catalog.")
        return self._accelerators[sku_id]

    def list_compatible_chassis(
        self,
        min_vram_gb: Decimal,
        max_rack_kw: Decimal,
    ) -> Sequence[ServerChassisSpec]:
        """Queries on-premise server chassis meeting thermal and capacity limits."""
        compatible: list[ServerChassisSpec] = []
        for chassis in self._chassis.values():
            total_vram = chassis.accelerator_sku.vram_gb * Decimal(chassis.accelerators_per_chassis)
            if total_vram >= min_vram_gb and chassis.total_chassis_tdp_kw <= max_rack_kw:
                compatible.append(chassis)
        return tuple(compatible)

    @property
    def available_accelerators(self) -> Mapping[str, HardwareAcceleratorSpec]:
        return MappingProxyType(self._accelerators)

    @property
    def available_chassis(self) -> Mapping[str, ServerChassisSpec]:
        return MappingProxyType(self._chassis)
