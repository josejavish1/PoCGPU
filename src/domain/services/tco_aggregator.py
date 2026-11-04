"""GAAP/IFRS On-Premise, Cloud, and Hybrid TCO Aggregator Service."""

from __future__ import annotations

from decimal import Decimal

from src.domain.models.assessment import ArchetypeRecommendationResult
from src.domain.models.financial import ComputedTcoBreakdown, MonetaryAmount
from src.domain.models.hardware import (
    CloudInstancePricingSpec,
    DatacenterFacilitySpec,
    ServerChassisSpec,
)
from src.domain.models.validation import assert_strict_decimal, decimal_ceil_div
from src.domain.models.workload import LlmWorkloadProfile, RooflineSimulationResult
from src.domain.ports.hybrid_tco import HybridTcoAggregatorPort


class HybridTcoAggregator(HybridTcoAggregatorPort):
    """Deterministic TCO engine implementing GAAP/IFRS CapEx depreciation and OpEx synthesis."""

    def __init__(
        self,
        default_hours_per_month: Decimal = Decimal("730.00"),
        reserved_3yr_cutoff_months: int = 36,
        reserved_1yr_cutoff_months: int = 12,
        months_per_year: Decimal = Decimal("12.00"),
        hybrid_on_prem_majority_threshold: Decimal = Decimal("0.5000"),
    ) -> None:
        assert_strict_decimal(default_hours_per_month, "default_hours_per_month")
        assert_strict_decimal(months_per_year, "months_per_year")
        assert_strict_decimal(hybrid_on_prem_majority_threshold, "hybrid_on_prem_majority_threshold")

        if default_hours_per_month <= Decimal("0"):
            raise ValueError("default_hours_per_month must be strictly positive.")
        if months_per_year <= Decimal("0"):
            raise ValueError("months_per_year must be strictly positive.")
        if not (Decimal("0") <= hybrid_on_prem_majority_threshold <= Decimal("1.0")):
            raise ValueError("hybrid_on_prem_majority_threshold must be in range [0, 1].")

        if (
            isinstance(reserved_1yr_cutoff_months, bool)
            or not isinstance(reserved_1yr_cutoff_months, int)
            or reserved_1yr_cutoff_months <= 0
        ):
            raise ValueError(f"reserved_1yr_cutoff_months must be a positive integer, got {reserved_1yr_cutoff_months}.")
        if (
            isinstance(reserved_3yr_cutoff_months, bool)
            or not isinstance(reserved_3yr_cutoff_months, int)
            or reserved_3yr_cutoff_months <= reserved_1yr_cutoff_months
        ):
            raise ValueError(
                f"reserved_3yr_cutoff_months ({reserved_3yr_cutoff_months}) must be > reserved_1yr_cutoff_months ({reserved_1yr_cutoff_months})."
            )

        self._default_hours_per_month = default_hours_per_month
        self._reserved_3yr_cutoff_months = reserved_3yr_cutoff_months
        self._reserved_1yr_cutoff_months = reserved_1yr_cutoff_months
        self._months_per_year = months_per_year
        self._hybrid_on_prem_majority_threshold = hybrid_on_prem_majority_threshold

    def compute_on_premise_tco(
        self,
        chassis: ServerChassisSpec,
        facility: DatacenterFacilitySpec,
        roofline: RooflineSimulationResult,
        amortization_months: int,
        chassis_per_rack: int,
        management_plane_monthly: MonetaryAmount,
        persistent_storage_monthly: MonetaryAmount,
        network_egress_monthly: MonetaryAmount,
        hours_per_month: Decimal | None = None,
    ) -> ComputedTcoBreakdown:
        """Computes amortized CapEx (net of salvage) and facility OpEx for on-premise clusters."""
        if isinstance(amortization_months, bool) or not isinstance(amortization_months, int) or amortization_months <= 0:
            raise ValueError(f"amortization_months must be a positive integer, got {amortization_months}.")
        if isinstance(chassis_per_rack, bool) or not isinstance(chassis_per_rack, int) or chassis_per_rack <= 0:
            raise ValueError(f"chassis_per_rack must be a positive integer, got {chassis_per_rack}.")

        effective_hours_month = hours_per_month or self._default_hours_per_month
        assert_strict_decimal(effective_hours_month, "hours_per_month")
        if effective_hours_month <= Decimal("0"):
            raise ValueError("hours_per_month must be strictly positive.")

        # Ensure currency uniformity across on-prem inputs
        target_currency = chassis.capex_unit_price.currency
        for item, name in [
            (management_plane_monthly, "management_plane_monthly"),
            (persistent_storage_monthly, "persistent_storage_monthly"),
            (network_egress_monthly, "network_egress_monthly"),
            (facility.electricity_rate_per_kwh, "facility.electricity_rate_per_kwh"),
            (facility.colocation_rack_monthly_fee, "facility.colocation_rack_monthly_fee"),
        ]:
            if item.currency != target_currency:
                raise ValueError(
                    f"Currency mismatch in on-premise TCO: '{name}' has '{item.currency}' but chassis has '{target_currency}'."
                )

        total_nodes = roofline.required_cluster_nodes_baseline
        total_chassis_capex = chassis.capex_unit_price.multiply(Decimal(total_nodes))

        salvage_pct = chassis.get_salvage_value_pct(amortization_months)
        net_depreciable_capex = total_chassis_capex.multiply(Decimal("1.0000") - salvage_pct)
        hardware_compute_monthly = net_depreciable_capex.divide(Decimal(amortization_months))

        total_facility_power_kw = (
            chassis.total_chassis_tdp_kw * Decimal(total_nodes) * facility.pue_rating
        )
        monthly_kwh_consumption = total_facility_power_kw * effective_hours_month
        facility_power_cooling_monthly = facility.electricity_rate_per_kwh.multiply(monthly_kwh_consumption)

        racks_required = max(1, decimal_ceil_div(Decimal(total_nodes), Decimal(chassis_per_rack)))
        datacenter_rack_colocation_monthly = facility.colocation_rack_monthly_fee.multiply(Decimal(racks_required))

        oem_support_contract_monthly = total_chassis_capex.multiply(
            chassis.oem_warranty_annual_pct
        ).divide(self._months_per_year)

        total_monthly_nominal_tco = (
            hardware_compute_monthly
            .add(management_plane_monthly)
            .add(persistent_storage_monthly)
            .add(facility_power_cooling_monthly)
            .add(datacenter_rack_colocation_monthly)
            .add(oem_support_contract_monthly)
            .add(network_egress_monthly)
        )

        return ComputedTcoBreakdown(
            hardware_compute_monthly=hardware_compute_monthly,
            management_plane_monthly=management_plane_monthly,
            persistent_storage_monthly=persistent_storage_monthly,
            facility_power_cooling_monthly=facility_power_cooling_monthly,
            datacenter_rack_colocation_monthly=datacenter_rack_colocation_monthly,
            oem_support_contract_monthly=oem_support_contract_monthly,
            network_egress_monthly=network_egress_monthly,
            total_monthly_nominal_tco=total_monthly_nominal_tco,
            amortization_period_months=amortization_months,
            is_on_premise=True,
        )

    def compute_cloud_tco(
        self,
        cloud_spec: CloudInstancePricingSpec,
        workload: LlmWorkloadProfile,
        roofline: RooflineSimulationResult,
        amortization_months: int,
        spot_allocation_ratio: Decimal,
        reserved_allocation_ratio: Decimal,
        persistent_storage_gb: Decimal,
        monthly_egress_gb: Decimal,
        management_plane_monthly: MonetaryAmount,
        hours_per_month: Decimal,
    ) -> ComputedTcoBreakdown:
        """Computes elastic Cloud OpEx blending On-Demand, Reserved, and Spot allocations."""
        if isinstance(amortization_months, bool) or not isinstance(amortization_months, int) or amortization_months <= 0:
            raise ValueError(f"amortization_months must be a positive integer, got {amortization_months}.")

        assert_strict_decimal(spot_allocation_ratio, "spot_allocation_ratio")
        assert_strict_decimal(reserved_allocation_ratio, "reserved_allocation_ratio")
        assert_strict_decimal(persistent_storage_gb, "persistent_storage_gb")
        assert_strict_decimal(monthly_egress_gb, "monthly_egress_gb")
        assert_strict_decimal(hours_per_month, "hours_per_month")

        if hours_per_month <= Decimal("0"):
            raise ValueError(f"hours_per_month must be strictly positive, got {hours_per_month}.")
        if persistent_storage_gb < Decimal("0") or monthly_egress_gb < Decimal("0"):
            raise ValueError("Storage and egress volumes cannot be negative.")

        if not (Decimal("0") <= spot_allocation_ratio <= Decimal("1.0")):
            raise ValueError(f"spot_allocation_ratio must be in [0, 1], got {spot_allocation_ratio}.")
        if not (Decimal("0") <= reserved_allocation_ratio <= Decimal("1.0")):
            raise ValueError(f"reserved_allocation_ratio must be in [0, 1], got {reserved_allocation_ratio}.")
        if spot_allocation_ratio + reserved_allocation_ratio > Decimal("1.0"):
            raise ValueError(
                f"Sum of spot ({spot_allocation_ratio}) and reserved ({reserved_allocation_ratio}) "
                "cannot exceed 1.0."
            )

        target_currency = cloud_spec.on_demand_hourly.currency
        if management_plane_monthly.currency != target_currency:
            raise ValueError(
                f"Currency mismatch in cloud TCO: management_plane_monthly has '{management_plane_monthly.currency}' "
                f"but cloud_spec has '{target_currency}'."
            )

        on_demand_ratio = Decimal("1.0000") - spot_allocation_ratio - reserved_allocation_ratio

        # Determine reserved tier using configured cutoffs
        if amortization_months >= self._reserved_3yr_cutoff_months:
            reserved_rate = cloud_spec.reserved_3yr_hourly
        else:
            reserved_rate = cloud_spec.reserved_1yr_hourly

        blended_hourly_rate = (
            cloud_spec.spot_hourly_mean.multiply(spot_allocation_ratio)
            .add(reserved_rate.multiply(reserved_allocation_ratio))
            .add(cloud_spec.on_demand_hourly.multiply(on_demand_ratio))
        )

        total_instances = roofline.required_cluster_nodes_baseline
        hardware_compute_monthly = blended_hourly_rate.multiply(Decimal(total_instances)).multiply(hours_per_month)

        persistent_storage_monthly = cloud_spec.storage_gb_monthly.multiply(persistent_storage_gb)
        network_egress_monthly = cloud_spec.egress_gb_price.multiply(monthly_egress_gb)

        zero_facility = MonetaryAmount(Decimal("0.0000"), target_currency)

        total_monthly_nominal_tco = (
            hardware_compute_monthly
            .add(management_plane_monthly)
            .add(persistent_storage_monthly)
            .add(zero_facility)
            .add(zero_facility)
            .add(zero_facility)
            .add(network_egress_monthly)
        )

        return ComputedTcoBreakdown(
            hardware_compute_monthly=hardware_compute_monthly,
            management_plane_monthly=management_plane_monthly,
            persistent_storage_monthly=persistent_storage_monthly,
            facility_power_cooling_monthly=zero_facility,
            datacenter_rack_colocation_monthly=zero_facility,
            oem_support_contract_monthly=zero_facility,
            network_egress_monthly=network_egress_monthly,
            total_monthly_nominal_tco=total_monthly_nominal_tco,
            amortization_period_months=amortization_months,
            is_on_premise=False,
        )

    def compute_hybrid_tco(
        self,
        on_prem_tco: ComputedTcoBreakdown,
        cloud_tco: ComputedTcoBreakdown,
        recommendation: ArchetypeRecommendationResult,
    ) -> ComputedTcoBreakdown:
        """Aggregates weighted Hybrid TCO from base on-premise and burst cloud allocations."""
        base_split = recommendation.recommended_base_load_split_pct
        burst_split = recommendation.recommended_burst_load_split_pct

        if base_split + burst_split != Decimal("1.0000"):
            raise ValueError(f"Hybrid splits must sum to 1.0000, got base={base_split}, burst={burst_split}.")

        if on_prem_tco.total_monthly_nominal_tco.currency != cloud_tco.total_monthly_nominal_tco.currency:
            raise ValueError(
                f"Cannot synthesize hybrid TCO across distinct currencies: "
                f"'{on_prem_tco.total_monthly_nominal_tco.currency}' vs '{cloud_tco.total_monthly_nominal_tco.currency}'."
            )

        synthesized_compute = on_prem_tco.hardware_compute_monthly.multiply(base_split).add(
            cloud_tco.hardware_compute_monthly.multiply(burst_split)
        )
        synthesized_storage = on_prem_tco.persistent_storage_monthly.multiply(base_split).add(
            cloud_tco.persistent_storage_monthly.multiply(burst_split)
        )
        synthesized_egress = on_prem_tco.network_egress_monthly.multiply(base_split).add(
            cloud_tco.network_egress_monthly.multiply(burst_split)
        )

        # Proportional blending of both management planes
        synthesized_management = on_prem_tco.management_plane_monthly.multiply(base_split).add(
            cloud_tco.management_plane_monthly.multiply(burst_split)
        )

        synthesized_power = on_prem_tco.facility_power_cooling_monthly.multiply(base_split)
        synthesized_rack = on_prem_tco.datacenter_rack_colocation_monthly.multiply(base_split)
        synthesized_oem = on_prem_tco.oem_support_contract_monthly.multiply(base_split)

        total_monthly_nominal_tco = (
            synthesized_compute
            .add(synthesized_management)
            .add(synthesized_storage)
            .add(synthesized_power)
            .add(synthesized_rack)
            .add(synthesized_oem)
            .add(synthesized_egress)
        )

        return ComputedTcoBreakdown(
            hardware_compute_monthly=synthesized_compute,
            management_plane_monthly=synthesized_management,
            persistent_storage_monthly=synthesized_storage,
            facility_power_cooling_monthly=synthesized_power,
            datacenter_rack_colocation_monthly=synthesized_rack,
            oem_support_contract_monthly=synthesized_oem,
            network_egress_monthly=synthesized_egress,
            total_monthly_nominal_tco=total_monthly_nominal_tco,
            amortization_period_months=on_prem_tco.amortization_period_months,
            is_on_premise=base_split >= self._hybrid_on_prem_majority_threshold,
        )
