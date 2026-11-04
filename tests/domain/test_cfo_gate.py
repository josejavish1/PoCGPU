"""Unit tests for CfoActuarialGate enforcing physical, silicon, and financial invariants."""

from __future__ import annotations

import unittest
from decimal import Decimal

from src.domain.exceptions import ConstitutionalGateViolationError
from src.domain.models.financial import ComputedTcoBreakdown, CurrencyCode, MonetaryAmount
from src.domain.models.hardware import (
    CoolingTopology,
    DatacenterFacilitySpec,
    HardwareAcceleratorSpec,
    InterconnectType,
    ServerChassisSpec,
)
from src.domain.models.workload import RooflineSimulationResult
from src.domain.ports.constitutional_gate import ConstitutionalGatePolicy
from src.domain.services.cfo_gate import CfoActuarialGate

USD = CurrencyCode("USD")


class TestCfoActuarialGate(unittest.TestCase):
    """Test suite verifying all constitutional gates (PHY, SIL, FIN)."""

    def setUp(self) -> None:
        self.gate = CfoActuarialGate()
        self.policy = ConstitutionalGatePolicy(
            max_rack_power_kw=Decimal("35.00"),
            max_power_kw_by_cooling_topology={
                CoolingTopology.AIR_COOLED: Decimal("20.00"),
                CoolingTopology.DIRECT_LIQUID_COOLED: Decimal("60.00"),
                CoolingTopology.IMMERSION: Decimal("120.00"),
            },
            min_carnot_pue=Decimal("1.0800"),
            max_vram_utilization_ratio=Decimal("0.9000"),
            max_memory_bus_utilization_ratio=Decimal("0.8500"),
            min_amortization_months=12,
            max_amortization_months=84,
            max_salvage_value_ratio=Decimal("0.3500"),
        )

        self.accelerator = HardwareAcceleratorSpec(
            sku_id="NVIDIA-H100-SXM5-80GB",
            vendor="NVIDIA",
            architecture="Hopper",
            fp16_tflops=Decimal("989.0"),
            fp8_tflops=Decimal("1979.0"),
            int8_tops=Decimal("1979.0"),
            vram_gb=Decimal("80.0"),
            memory_bandwidth_gbps=Decimal("3350.0"),
            interconnect=InterconnectType.NVLINK_SXM5,
            interconnect_bandwidth_gbps=Decimal("900.0"),
            tensor_parallel_efficiency_factor=Decimal("0.94"),
            tdp_watts=Decimal("700.0"),
            annualized_failure_rate_pct=Decimal("0.025"),
            mttr_replacement_hours=Decimal("4.0"),
        )

        # Total chassis TDP = (8 * 700W + 2400W) / 1000 = 8.00 kW
        self.chassis = ServerChassisSpec(
            chassis_id="OEM-HGX-H100-8X",
            oem_vendor="Supermicro",
            model_name="SYS-821GE-TNHR",
            accelerator_sku=self.accelerator,
            accelerators_per_chassis=8,
            base_system_power_watts=Decimal("2400.0"),
            rack_units_u=8,
            capex_unit_price=MonetaryAmount(Decimal("320000.00"), USD),
            oem_warranty_annual_pct=Decimal("0.08"),
            salvage_value_by_horizon_months={
                36: Decimal("0.20"),
                60: Decimal("0.10"),
            },
        )

        self.air_cooled_facility = DatacenterFacilitySpec(
            facility_id="DC-TIER3-AIR",
            pue_rating=Decimal("1.35"),
            max_rack_power_density_kw=Decimal("30.00"),
            electricity_rate_per_kwh=MonetaryAmount(Decimal("0.12"), USD),
            colocation_rack_monthly_fee=MonetaryAmount(Decimal("1800.00"), USD),
            cooling_topology=CoolingTopology.AIR_COOLED,
        )

    def _build_roofline(
        self,
        vram_ratio: Decimal = Decimal("0.8200"),
        bus_ratio: Decimal = Decimal("0.7500"),
    ) -> RooflineSimulationResult:
        return RooflineSimulationResult(
            chassis_or_instance_id="OEM-HGX-H100-8X",
            tensor_parallel_degree=8,
            pipeline_parallel_degree=1,
            required_cluster_nodes_baseline=2,
            model_weights_vram_gb=Decimal("140.0"),
            kv_cache_total_vram_gb=Decimal("320.0"),
            activation_buffer_vram_gb=Decimal("64.8"),
            total_required_vram_gb=Decimal("524.8"),
            cluster_total_vram_pool_gb=Decimal("640.0"),
            vram_utilization_ratio=vram_ratio,
            ttft_seconds=Decimal("0.45"),
            tpot_ms_per_token=Decimal("18.5"),
            tokens_per_second_per_user=Decimal("54.05"),
            aggregate_cluster_throughput_tok_s=Decimal("4324.0"),
            memory_bus_utilization_ratio=bus_ratio,
            model_flops_utilization_ratio=Decimal("0.42"),
            is_memory_bound=True,
        )

    def _build_tco(
        self,
        total_amount: Decimal = Decimal("25000.00"),
        amortization_months: int = 36,
    ) -> ComputedTcoBreakdown:
        zero_amt = MonetaryAmount(Decimal("0.00"), USD)
        if total_amount <= Decimal("0.00"):
            return ComputedTcoBreakdown(
                hardware_compute_monthly=zero_amt,
                management_plane_monthly=zero_amt,
                persistent_storage_monthly=zero_amt,
                facility_power_cooling_monthly=zero_amt,
                datacenter_rack_colocation_monthly=zero_amt,
                oem_support_contract_monthly=zero_amt,
                network_egress_monthly=zero_amt,
                total_monthly_nominal_tco=MonetaryAmount(total_amount, USD),
                amortization_period_months=amortization_months,
                is_on_premise=True,
            )
        base_amt = MonetaryAmount(Decimal("5000.00"), USD)
        return ComputedTcoBreakdown(
            hardware_compute_monthly=base_amt,
            management_plane_monthly=base_amt,
            persistent_storage_monthly=base_amt,
            facility_power_cooling_monthly=base_amt,
            datacenter_rack_colocation_monthly=base_amt,
            oem_support_contract_monthly=zero_amt,
            network_egress_monthly=zero_amt,
            total_monthly_nominal_tco=MonetaryAmount(total_amount, USD),
            amortization_period_months=amortization_months,
            is_on_premise=True,
        )

    def test_physical_invariants_pass_within_limits(self) -> None:
        # 2 chassis * 8.0 kW = 16.0 kW <= 20.0 kW (AIR_COOLED) and <= 30.0 kW (facility)
        self.gate.validate_physical_invariants(
            chassis=self.chassis,
            facility=self.air_cooled_facility,
            chassis_count_per_rack=2,
            policy=self.policy,
        )

    def test_gate_phy_001_rack_power_exceeds_facility_or_policy(self) -> None:
        # 4 chassis * 8.0 kW = 32.0 kW > 30.0 kW (facility max)
        with self.assertRaises(ConstitutionalGateViolationError) as ctx:
            self.gate.validate_physical_invariants(
                chassis=self.chassis,
                facility=self.air_cooled_facility,
                chassis_count_per_rack=4,
                policy=self.policy,
            )
        self.assertEqual(ctx.exception.rule_code, "GATE-PHY-001")
        self.assertEqual(ctx.exception.i18n_key, "gate.phy.001.violation")
        self.assertEqual(ctx.exception.i18n_params["actual_kw"], Decimal("32.00"))
        self.assertEqual(ctx.exception.i18n_params["limit_kw"], Decimal("30.00"))

    def test_gate_phy_002_air_cooling_limit_exceeded(self) -> None:
        # 3 chassis * 8.0 kW = 24.0 kW (<= 30.0 kW facility limit, but > 20.0 kW AIR_COOLED limit)
        with self.assertRaises(ConstitutionalGateViolationError) as ctx:
            self.gate.validate_physical_invariants(
                chassis=self.chassis,
                facility=self.air_cooled_facility,
                chassis_count_per_rack=3,
                policy=self.policy,
            )
        self.assertEqual(ctx.exception.rule_code, "GATE-PHY-002")
        self.assertEqual(ctx.exception.i18n_key, "gate.phy.002.violation")
        self.assertEqual(ctx.exception.i18n_params["actual_kw"], Decimal("24.00"))
        self.assertEqual(ctx.exception.i18n_params["limit_kw"], Decimal("20.00"))
        self.assertEqual(ctx.exception.i18n_params["cooling_type"], "AIR_COOLED")

    def test_gate_phy_003_carnot_pue_violation(self) -> None:
        unphysical_facility = DatacenterFacilitySpec(
            facility_id="DC-CARNOT-VIOLATION",
            pue_rating=Decimal("1.02"),
            max_rack_power_density_kw=Decimal("30.00"),
            electricity_rate_per_kwh=MonetaryAmount(Decimal("0.10"), USD),
            colocation_rack_monthly_fee=MonetaryAmount(Decimal("1500.00"), USD),
            cooling_topology=CoolingTopology.DIRECT_LIQUID_COOLED,
        )
        with self.assertRaises(ConstitutionalGateViolationError) as ctx:
            self.gate.validate_physical_invariants(
                chassis=self.chassis,
                facility=unphysical_facility,
                chassis_count_per_rack=2,
                policy=self.policy,
            )
        self.assertEqual(ctx.exception.rule_code, "GATE-PHY-003")
        self.assertEqual(ctx.exception.i18n_key, "gate.phy.003.violation")
        self.assertEqual(ctx.exception.i18n_params["actual_pue"], Decimal("1.02"))
        self.assertEqual(ctx.exception.i18n_params["min_pue"], Decimal("1.0800"))

    def test_silicon_invariants_pass_within_limits(self) -> None:
        roofline = self._build_roofline(
            vram_ratio=Decimal("0.8800"),
            bus_ratio=Decimal("0.8000"),
        )
        self.gate.validate_silicon_invariants(roofline=roofline, policy=self.policy)

    def test_gate_sil_001_vram_utilization_exceeds_safety_ceiling(self) -> None:
        roofline = self._build_roofline(
            vram_ratio=Decimal("0.9450"),
            bus_ratio=Decimal("0.7500"),
        )
        with self.assertRaises(ConstitutionalGateViolationError) as ctx:
            self.gate.validate_silicon_invariants(roofline=roofline, policy=self.policy)
        self.assertEqual(ctx.exception.rule_code, "GATE-SIL-001")
        self.assertEqual(ctx.exception.i18n_key, "gate.sil.001.violation")
        self.assertEqual(ctx.exception.i18n_params["utilization_pct"], Decimal("94.50"))
        self.assertEqual(ctx.exception.i18n_params["max_utilization_pct"], Decimal("90.00"))
        self.assertEqual(ctx.exception.i18n_params["reserve_pct"], Decimal("10.00"))

    def test_gate_sil_002_memory_bus_utilization_exceeds_saturation_ceiling(self) -> None:
        roofline = self._build_roofline(
            vram_ratio=Decimal("0.8500"),
            bus_ratio=Decimal("0.8925"),
        )
        with self.assertRaises(ConstitutionalGateViolationError) as ctx:
            self.gate.validate_silicon_invariants(roofline=roofline, policy=self.policy)
        self.assertEqual(ctx.exception.rule_code, "GATE-SIL-002")
        self.assertEqual(ctx.exception.i18n_key, "gate.sil.002.violation")
        self.assertEqual(ctx.exception.i18n_params["bus_utilization_pct"], Decimal("89.25"))
        self.assertEqual(ctx.exception.i18n_params["max_bus_utilization_pct"], Decimal("85.00"))

    def test_financial_invariants_pass_within_limits(self) -> None:
        tco = self._build_tco(total_amount=Decimal("25000.00"), amortization_months=36)
        self.gate.validate_financial_invariants(
            tco=tco,
            salvage_value_pct=Decimal("0.20"),
            policy=self.policy,
        )

    def test_gate_fin_001_non_positive_tco_rejected(self) -> None:
        tco = self._build_tco(total_amount=Decimal("0.00"), amortization_months=36)
        with self.assertRaises(ConstitutionalGateViolationError) as ctx:
            self.gate.validate_financial_invariants(
                tco=tco,
                salvage_value_pct=Decimal("0.20"),
                policy=self.policy,
            )
        self.assertEqual(ctx.exception.rule_code, "GATE-FIN-001")
        self.assertEqual(ctx.exception.i18n_key, "gate.fin.001.violation")
        self.assertEqual(ctx.exception.i18n_params["horizon_months"], 36)

    def test_gate_fin_002_amortization_or_salvage_out_of_bounds(self) -> None:
        tco_invalid_horizon = self._build_tco(total_amount=Decimal("25000.00"), amortization_months=96)
        with self.assertRaises(ConstitutionalGateViolationError) as ctx:
            self.gate.validate_financial_invariants(
                tco=tco_invalid_horizon,
                salvage_value_pct=Decimal("0.15"),
                policy=self.policy,
            )
        self.assertEqual(ctx.exception.rule_code, "GATE-FIN-002")
        self.assertEqual(ctx.exception.i18n_key, "gate.fin.002.violation")
        self.assertEqual(ctx.exception.i18n_params["months"], 96)

        tco_valid_horizon = self._build_tco(total_amount=Decimal("25000.00"), amortization_months=36)
        with self.assertRaises(ConstitutionalGateViolationError) as ctx_salvage:
            self.gate.validate_financial_invariants(
                tco=tco_valid_horizon,
                salvage_value_pct=Decimal("0.45"),
                policy=self.policy,
            )
        self.assertEqual(ctx_salvage.exception.rule_code, "GATE-FIN-002")
        self.assertEqual(ctx_salvage.exception.i18n_params["salvage_pct"], Decimal("45.00"))
        self.assertEqual(ctx_salvage.exception.i18n_params["max_salvage_pct"], Decimal("35.00"))


if __name__ == "__main__":
    unittest.main()
