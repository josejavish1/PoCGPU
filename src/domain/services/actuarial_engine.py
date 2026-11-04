"""Open FAIR Actuarial Risk Modeling Engine for Hardware RMA and Cloud Spot Preemption."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_EVEN
from typing import Optional

from src.domain.models.financial import ActuarialRiskMetrics, MonetaryAmount
from src.domain.models.hardware import CloudInstancePricingSpec, ServerChassisSpec
from src.domain.models.validation import assert_strict_decimal
from src.domain.models.workload import RooflineSimulationResult
from src.domain.ports.actuarial_risk import ActuarialRiskPort

BITS_PER_BYTE: Decimal = Decimal("8.0")


class OpenFairActuarialEngine(ActuarialRiskPort):
    """Deterministic Open FAIR engine quantifying Annualized Loss Expectancy (ALE) for AI clusters."""

    def __init__(
        self,
        hours_per_year: Decimal = Decimal("8760"),
        days_per_year: Decimal = Decimal("365"),
        months_per_year: Decimal = Decimal("12"),
        seconds_per_hour: Decimal = Decimal("3600"),
        min_lef_floor: Decimal = Decimal("0.0001"),
        hot_spare_failover_mttr_hours: Decimal = Decimal("0.2500"),
        cloud_weight_streaming_gbps: Decimal = Decimal("25.0"),
    ) -> None:
        assert_strict_decimal(hours_per_year, "hours_per_year")
        assert_strict_decimal(days_per_year, "days_per_year")
        assert_strict_decimal(months_per_year, "months_per_year")
        assert_strict_decimal(seconds_per_hour, "seconds_per_hour")
        assert_strict_decimal(min_lef_floor, "min_lef_floor")
        assert_strict_decimal(hot_spare_failover_mttr_hours, "hot_spare_failover_mttr_hours")
        assert_strict_decimal(cloud_weight_streaming_gbps, "cloud_weight_streaming_gbps")

        if (
            hours_per_year <= Decimal("0")
            or days_per_year <= Decimal("0")
            or months_per_year <= Decimal("0")
            or seconds_per_hour <= Decimal("0")
            or min_lef_floor <= Decimal("0")
            or hot_spare_failover_mttr_hours <= Decimal("0")
            or cloud_weight_streaming_gbps <= Decimal("0")
        ):
            raise ValueError("Temporal and actuarial floor parameters must be strictly positive.")

        self._hours_per_year = hours_per_year
        self._days_per_year = days_per_year
        self._months_per_year = months_per_year
        self._seconds_per_hour = seconds_per_hour
        self._min_lef_floor = min_lef_floor
        self._hot_spare_failover_mttr_hours = hot_spare_failover_mttr_hours
        self._cloud_weight_streaming_gbyte_per_sec = (cloud_weight_streaming_gbps / BITS_PER_BYTE).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_EVEN
        )

    def evaluate_on_premise_hardware_risk(
        self,
        chassis: ServerChassisSpec,
        cluster_node_count: int,
        hourly_sla_penalty: MonetaryAmount,
        spare_chassis_count: int = 0,
        nominal_monthly_tco: Optional[MonetaryAmount] = None,
    ) -> ActuarialRiskMetrics:
        """Evaluates hardware silicon failure rate (AFR), MTBF, and RMA replacement ALE with hot-spare mitigation."""
        if isinstance(cluster_node_count, bool) or not isinstance(cluster_node_count, int) or cluster_node_count <= 0:
            raise ValueError(f"Cluster node count must be a positive integer, got {cluster_node_count}.")
        if isinstance(spare_chassis_count, bool) or not isinstance(spare_chassis_count, int) or spare_chassis_count < 0:
            raise ValueError(f"Spare chassis count must be a non-negative integer, got {spare_chassis_count}.")
        if hourly_sla_penalty.amount < Decimal("0"):
            raise ValueError("Hourly SLA penalty cannot be negative.")

        total_accelerators = cluster_node_count * chassis.accelerators_per_chassis
        raw_lef_annual = (
            chassis.accelerator_sku.annualized_failure_rate_pct * Decimal(total_accelerators)
        ).quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN)

        expected_mtbf_hours = (
            self._hours_per_year / max(self._min_lef_floor, raw_lef_annual)
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)

        full_rma_mttr = chassis.accelerator_sku.mttr_replacement_hours.quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_EVEN
        )

        # Open FAIR Two-Tier Mitigation Modeling (Failover MTTR vs Physical RMA MTTR)
        if spare_chassis_count > 0:
            spare_accelerators = Decimal(spare_chassis_count * chassis.accelerators_per_chassis)
            mitigated_events = min(raw_lef_annual, spare_accelerators)
            unmitigated_events = max(Decimal("0.0000"), raw_lef_annual - spare_accelerators)

            ale_mitigated = hourly_sla_penalty.multiply(self._hot_spare_failover_mttr_hours).multiply(mitigated_events)
            ale_unmitigated = hourly_sla_penalty.multiply(full_rma_mttr).multiply(unmitigated_events)
            ale = ale_mitigated.add(ale_unmitigated)

            effective_mttr_hours = (
                (mitigated_events * self._hot_spare_failover_mttr_hours + unmitigated_events * full_rma_mttr)
                / max(Decimal("0.0001"), raw_lef_annual)
            ).quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN)
            sle = hourly_sla_penalty.multiply(effective_mttr_hours)
        else:
            effective_mttr_hours = full_rma_mttr
            sle = hourly_sla_penalty.multiply(effective_mttr_hours)
            ale = sle.multiply(raw_lef_annual)

        monthly_reserve = ale.divide(self._months_per_year)
        total_risk_adjusted = nominal_monthly_tco.add(monthly_reserve) if nominal_monthly_tco else monthly_reserve

        return ActuarialRiskMetrics(
            loss_event_frequency_annual=raw_lef_annual,
            single_loss_expectancy=sle,
            annualized_loss_expectancy=ale,
            monthly_risk_adjusted_reserve=monthly_reserve,
            expected_hardware_mtbf_hours=expected_mtbf_hours,
            expected_recovery_mttr_hours=effective_mttr_hours,
            total_monthly_risk_adjusted_tco=total_risk_adjusted,
        )

    def evaluate_cloud_spot_preemption_risk(
        self,
        cloud_spec: CloudInstancePricingSpec,
        cluster_instance_count: int,
        hourly_sla_penalty: MonetaryAmount,
        roofline: RooflineSimulationResult,
        nominal_monthly_tco: Optional[MonetaryAmount] = None,
    ) -> ActuarialRiskMetrics:
        """Evaluates Cloud Spot preemption probability, cold rebuild streaming MTTR, and eviction ALE."""
        if isinstance(cluster_instance_count, bool) or not isinstance(cluster_instance_count, int) or cluster_instance_count <= 0:
            raise ValueError(f"Cluster instance count must be a positive integer, got {cluster_instance_count}.")
        if hourly_sla_penalty.amount < Decimal("0"):
            raise ValueError("Hourly SLA penalty cannot be negative.")

        lef_annual = (
            self._days_per_year * cloud_spec.spot_preemption_probability_daily * Decimal(cluster_instance_count)
        ).quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN)

        expected_mtbf_hours = (
            self._hours_per_year / max(self._min_lef_floor, lef_annual)
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)

        # Direct access to typed roofline weights footprint
        weight_vram = roofline.model_weights_vram_gb
        if weight_vram > Decimal("0"):
            weight_streaming_seconds = (
                weight_vram / max(Decimal("0.1"), self._cloud_weight_streaming_gbyte_per_sec)
            )
        else:
            weight_streaming_seconds = Decimal("0.0000")

        total_rebuild_seconds = cloud_spec.cold_boot_rebuild_seconds + weight_streaming_seconds

        recovery_mttr_hours = (
            total_rebuild_seconds / self._seconds_per_hour
        ).quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN)

        sle = hourly_sla_penalty.multiply(recovery_mttr_hours)
        ale = sle.multiply(lef_annual)
        monthly_reserve = ale.divide(self._months_per_year)
        total_risk_adjusted = nominal_monthly_tco.add(monthly_reserve) if nominal_monthly_tco else monthly_reserve

        return ActuarialRiskMetrics(
            loss_event_frequency_annual=lef_annual,
            single_loss_expectancy=sle,
            annualized_loss_expectancy=ale,
            monthly_risk_adjusted_reserve=monthly_reserve,
            expected_hardware_mtbf_hours=expected_mtbf_hours,
            expected_recovery_mttr_hours=recovery_mttr_hours,
            total_monthly_risk_adjusted_tco=total_risk_adjusted,
        )
