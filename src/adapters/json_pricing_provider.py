"""JSON-backed Cloud Pricing and FX Currency Conversion Adapter."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from types import MappingProxyType
from typing import Mapping, Optional, Sequence

from src.domain.exceptions import DomainLookupError
from src.domain.models.financial import CurrencyCode, MonetaryAmount
from src.domain.models.hardware import CloudInstancePricingSpec
from src.domain.ports.hardware_registry import HardwareRegistryPort
from src.domain.ports.pricing_provider import PricingProviderPort


class JsonPricingProviderAdapter(PricingProviderPort):
    """Loads cloud instance rates and performs foreign exchange currency conversion."""

    def __init__(
        self,
        pricing_catalog_path: Path,
        hardware_registry: HardwareRegistryPort,
    ) -> None:
        self._pricing_path = pricing_catalog_path
        self._hardware_registry = hardware_registry
        self._fx_rates: dict[CurrencyCode, Decimal] = {}
        self._cloud_instances: dict[str, CloudInstancePricingSpec] = {}
        self._load_pricing()

    def _load_pricing(self) -> None:
        if not self._pricing_path.is_file():
            raise FileNotFoundError(f"Pricing catalog file not found at: {self._pricing_path}")

        raw_data = json.loads(self._pricing_path.read_text(encoding="utf-8"))

        for currency_str, rate_str in raw_data.get("fx_rates_to_usd", {}).items():
            self._fx_rates[CurrencyCode(currency_str)] = Decimal(rate_str)

        for instance_id, inst_data in raw_data.get("cloud_instances", {}).items():
            accel_sku_id = inst_data["accelerator_sku_id"]
            accel_spec = self._hardware_registry.get_accelerator_spec(accel_sku_id)
            curr = CurrencyCode(inst_data.get("currency", "USD"))

            self._cloud_instances[instance_id] = CloudInstancePricingSpec(
                provider_id=inst_data["provider_id"],
                region=inst_data["region"],
                instance_type=inst_data["instance_type"],
                accelerator_sku=accel_spec,
                accelerators_per_instance=int(inst_data["accelerators_per_instance"]),
                on_demand_hourly=MonetaryAmount(Decimal(inst_data["on_demand_hourly"]), curr),
                reserved_1yr_hourly=MonetaryAmount(Decimal(inst_data["reserved_1yr_hourly"]), curr),
                reserved_3yr_hourly=MonetaryAmount(Decimal(inst_data["reserved_3yr_hourly"]), curr),
                spot_hourly_mean=MonetaryAmount(Decimal(inst_data["spot_hourly_mean"]), curr),
                spot_preemption_probability_daily=Decimal(inst_data["spot_preemption_probability_daily"]),
                cold_boot_rebuild_seconds=Decimal(inst_data["cold_boot_rebuild_seconds"]),
                storage_gb_monthly=MonetaryAmount(Decimal(inst_data["storage_gb_monthly"]), curr),
                egress_gb_price=MonetaryAmount(Decimal(inst_data["egress_gb_price"]), curr),
            )

    def convert_currency(
        self,
        amount: MonetaryAmount,
        target_currency: CurrencyCode,
    ) -> MonetaryAmount:
        """Converts monetary amounts using dynamic FX rates from the catalog."""
        if amount.currency == target_currency:
            return amount

        if amount.currency not in self._fx_rates:
            raise DomainLookupError(f"FX rate not available for source currency '{amount.currency}'.")
        if target_currency not in self._fx_rates:
            raise DomainLookupError(f"FX rate not available for target currency '{target_currency}'.")

        # Convert amount from source currency to USD, then from USD to target currency
        rate_source_to_usd = self._fx_rates[amount.currency]
        rate_target_to_usd = self._fx_rates[target_currency]

        amount_usd = amount.amount / rate_source_to_usd
        converted_amount = amount_usd * rate_target_to_usd

        return MonetaryAmount(
            converted_amount,
            target_currency,
            precision_places=amount.precision_places,
        )

    def get_cloud_pricing(
        self,
        sku_id: str,
        region: Optional[str],
        target_currency: CurrencyCode,
    ) -> Sequence[CloudInstancePricingSpec]:
        """Fetches live cloud instance pricing specs for a given accelerator converted to target currency."""
        matching: list[CloudInstancePricingSpec] = []
        for instance in self._cloud_instances.values():
            if instance.accelerator_sku.sku_id == sku_id:
                if region is None or instance.region == region:
                    converted_spec = CloudInstancePricingSpec(
                        provider_id=instance.provider_id,
                        region=instance.region,
                        instance_type=instance.instance_type,
                        accelerator_sku=instance.accelerator_sku,
                        accelerators_per_instance=instance.accelerators_per_instance,
                        on_demand_hourly=self.convert_currency(instance.on_demand_hourly, target_currency),
                        reserved_1yr_hourly=self.convert_currency(instance.reserved_1yr_hourly, target_currency),
                        reserved_3yr_hourly=self.convert_currency(instance.reserved_3yr_hourly, target_currency),
                        spot_hourly_mean=self.convert_currency(instance.spot_hourly_mean, target_currency),
                        spot_preemption_probability_daily=instance.spot_preemption_probability_daily,
                        cold_boot_rebuild_seconds=instance.cold_boot_rebuild_seconds,
                        storage_gb_monthly=self.convert_currency(instance.storage_gb_monthly, target_currency),
                        egress_gb_price=self.convert_currency(instance.egress_gb_price, target_currency),
                    )
                    matching.append(converted_spec)
        return tuple(matching)

    @property
    def available_cloud_instances(self) -> Mapping[str, CloudInstancePricingSpec]:
        return MappingProxyType(self._cloud_instances)
