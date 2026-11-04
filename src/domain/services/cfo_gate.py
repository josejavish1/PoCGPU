"""Pre-Flight CFO Constitutional Audit Gate enforcing mathematical and physical invariants."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_EVEN

from src.domain.exceptions import (
    ConstitutionalGateViolationError,
    DomainLookupError,
)
from src.domain.models.financial import ComputedTcoBreakdown
from src.domain.models.hardware import (
    CoolingTopology,
    DatacenterFacilitySpec,
    ServerChassisSpec,
)
from src.domain.models.validation import assert_strict_decimal
from src.domain.models.workload import RooflineSimulationResult
from src.domain.ports.constitutional_gate import (
    ConstitutionalGatePolicy,
    ConstitutionalGatePort,
)


class CfoActuarialGate(ConstitutionalGatePort):
    """Constitutional gatekeeper enforcing strict physical, thermodynamic, silicon, and financial invariants."""

    def validate_physical_invariants(
        self,
        chassis: ServerChassisSpec,
        facility: DatacenterFacilitySpec,
        chassis_count_per_rack: int,
        policy: ConstitutionalGatePolicy,
    ) -> None:
        """Validates rack power density, cooling topology, and physical rack U-height capacity limits."""
        if isinstance(chassis_count_per_rack, bool) or not isinstance(chassis_count_per_rack, int) or chassis_count_per_rack <= 0:
            raise ValueError(f"chassis_count_per_rack must be a positive integer, got {chassis_count_per_rack}.")

        # 1. Physical Rack Space Overflow (GATE-PHY-004)
        total_rack_u = chassis_count_per_rack * chassis.rack_units_u
        effective_max_u = min(facility.max_rack_units_u, policy.max_rack_units_u)
        if total_rack_u > effective_max_u:
            raise ConstitutionalGateViolationError(
                rule_code="GATE-PHY-004",
                i18n_key="gate.phy.004.violation",
                i18n_params={
                    "actual_u": total_rack_u,
                    "limit_u": effective_max_u,
                },
            )

        # 2. Structural Rack Power Density Limit (GATE-PHY-001) - Evaluated on unrounded physical power
        total_rack_power_kw = chassis.total_chassis_tdp_kw * Decimal(chassis_count_per_rack)
        effective_power_limit = min(facility.max_rack_power_density_kw, policy.max_rack_power_kw)
        if total_rack_power_kw > effective_power_limit:
            raise ConstitutionalGateViolationError(
                rule_code="GATE-PHY-001",
                i18n_key="gate.phy.001.violation",
                i18n_params={
                    "actual_kw": total_rack_power_kw.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN),
                    "limit_kw": effective_power_limit.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN),
                },
            )

        # 3. Cooling Topology Thermal Ceilings (GATE-PHY-002) - Strict Lookup without Fallback
        if facility.cooling_topology not in policy.max_power_kw_by_cooling_topology:
            raise DomainLookupError(
                f"Cooling topology '{facility.cooling_topology.value}' is absent from constitutional policy limit registry."
            )
        cooling_limit_kw = policy.max_power_kw_by_cooling_topology[facility.cooling_topology]

        if total_rack_power_kw > cooling_limit_kw:
            raise ConstitutionalGateViolationError(
                rule_code="GATE-PHY-002",
                i18n_key="gate.phy.002.violation",
                i18n_params={
                    "actual_kw": total_rack_power_kw.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN),
                    "limit_kw": cooling_limit_kw.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN),
                    "cooling_type": facility.cooling_topology.value,
                },
            )

        # 4. Carnot Thermodynamic Floor (GATE-PHY-003)
        if facility.pue_rating < policy.min_carnot_pue:
            raise ConstitutionalGateViolationError(
                rule_code="GATE-PHY-003",
                i18n_key="gate.phy.003.violation",
                i18n_params={
                    "actual_pue": facility.pue_rating,
                    "min_pue": policy.min_carnot_pue,
                },
            )

    def validate_silicon_invariants(
        self,
        roofline: RooflineSimulationResult,
        policy: ConstitutionalGatePolicy,
    ) -> None:
        """Validates 10% VRAM safety headroom and HBM memory bus saturation ceilings."""
        # 1. VRAM Runtime Safety Ceiling (GATE-SIL-001)
        if roofline.vram_utilization_ratio > policy.max_vram_utilization_ratio:
            utilization_pct = (roofline.vram_utilization_ratio * Decimal("100")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_EVEN
            )
            max_pct = (policy.max_vram_utilization_ratio * Decimal("100")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_EVEN
            )
            reserve_pct = (Decimal("100") - max_pct).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
            raise ConstitutionalGateViolationError(
                rule_code="GATE-SIL-001",
                i18n_key="gate.sil.001.violation",
                i18n_params={
                    "utilization_pct": utilization_pct,
                    "max_utilization_pct": max_pct,
                    "reserve_pct": reserve_pct,
                },
            )

        # 2. HBM Memory Bus Saturation Ceiling (GATE-SIL-002)
        if roofline.memory_bus_utilization_ratio > policy.max_memory_bus_utilization_ratio:
            bus_util_pct = (roofline.memory_bus_utilization_ratio * Decimal("100")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_EVEN
            )
            max_bus_pct = (policy.max_memory_bus_utilization_ratio * Decimal("100")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_EVEN
            )
            raise ConstitutionalGateViolationError(
                rule_code="GATE-SIL-002",
                i18n_key="gate.sil.002.violation",
                i18n_params={
                    "bus_utilization_pct": bus_util_pct,
                    "max_bus_utilization_pct": max_bus_pct,
                },
            )

    def validate_financial_invariants(
        self,
        tco: ComputedTcoBreakdown,
        salvage_value_pct: Decimal,
        policy: ConstitutionalGatePolicy,
    ) -> None:
        """Validates positive TCO floor, amortization bounds, and salvage value limits."""
        assert_strict_decimal(salvage_value_pct, "salvage_value_pct")

        # 1. Strict Positive Economic Floor (GATE-FIN-001)
        if tco.total_monthly_nominal_tco.amount <= Decimal("0"):
            raise ConstitutionalGateViolationError(
                rule_code="GATE-FIN-001",
                i18n_key="gate.fin.001.violation",
                i18n_params={
                    "horizon_months": tco.amortization_period_months,
                    "tco_amount": tco.total_monthly_nominal_tco.amount,
                },
            )

        # 2. GAAP/IFRS Accounting Horizons and Residual Salvage Bounds (GATE-FIN-002)
        is_amortization_valid = (
            policy.min_amortization_months <= tco.amortization_period_months <= policy.max_amortization_months
        )
        is_salvage_valid = Decimal("0") <= salvage_value_pct <= policy.max_salvage_value_ratio

        if not is_amortization_valid or not is_salvage_valid:
            salvage_pct_formatted = (salvage_value_pct * Decimal("100")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_EVEN
            )
            max_salvage_formatted = (policy.max_salvage_value_ratio * Decimal("100")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_EVEN
            )
            raise ConstitutionalGateViolationError(
                rule_code="GATE-FIN-002",
                i18n_key="gate.fin.002.violation",
                i18n_params={
                    "months": tco.amortization_period_months,
                    "min_months": policy.min_amortization_months,
                    "max_months": policy.max_amortization_months,
                    "salvage_pct": salvage_pct_formatted,
                    "max_salvage_pct": max_salvage_formatted,
                },
            )
