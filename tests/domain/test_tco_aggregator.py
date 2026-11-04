"""Unit tests for the GAAP/IFRS HybridTcoAggregator domain service."""

from __future__ import annotations

import unittest
from decimal import Decimal

from src.domain.models.assessment import ArchetypeRecommendationResult, DeploymentArchetype
from src.domain.models.financial import CurrencyCode, MonetaryAmount
from src.domain.models.hardware import (
    CloudInstancePricingSpec,
    CoolingTopology,
    DatacenterFacilitySpec,
    HardwareAcceleratorSpec,
    InterconnectType,
    ServerChassisSpec,
)
from src.domain.models.workload import (
    AttentionType,
    LlmWorkloadProfile,
    QuantizationPrecision,
    RooflineSimulationResult,
)
from src.domain.services.tco_aggregator import HybridTcoAggregator

USD = CurrencyCode("USD")


class TestHybridTcoAggregator(unittest.TestCase):
    """Verifies On-Premise, Cloud, and Hybrid TCO calculations and invariant enforcement."""

    def setUp(self) -> None:
        self.aggregator = HybridTcoAggregator()

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

        self.chassis = ServerChassisSpec(
            chassis_id="DGX-H100-8X",
            oem_vendor="NVIDIA",
            model_name="DGX H100",
            accelerator_sku=self.accelerator,
            accelerators_per_chassis=8,
            base_system_power_watts=Decimal("4600.0"),  # 8*700 + 4600 = 10200 W = 10.2 kW
            rack_units_u=8,
            capex_unit_price=MonetaryAmount(Decimal("300000.00"), USD),
            oem_warranty_annual_pct=Decimal("0.08"),
            salvage_value_by_horizon_months={
                36: Decimal("0.20"),
                48: Decimal("0.10"),
                60: Decimal("0.05"),
            },
        )

        self.facility = DatacenterFacilitySpec(
            facility_id="DC-TIER4-DLC",
            pue_rating=Decimal("1.25"),
            max_rack_power_density_kw=Decimal("45.0"),
            electricity_rate_per_kwh=MonetaryAmount(Decimal("0.1000"), USD),
            colocation_rack_monthly_fee=MonetaryAmount(Decimal("1500.00"), USD),
            cooling_topology=CoolingTopology.DIRECT_LIQUID_COOLED,
        )

        self.cloud_spec = CloudInstancePricingSpec(
            provider_id="AWS",
            region="us-east-1",
            instance_type="p5.48xlarge",
            accelerator_sku=self.accelerator,
            accelerators_per_instance=8,
            on_demand_hourly=MonetaryAmount(Decimal("98.3200"), USD),
            reserved_1yr_hourly=MonetaryAmount(Decimal("68.8200"), USD),
            reserved_3yr_hourly=MonetaryAmount(Decimal("49.1600"), USD),
            spot_hourly_mean=MonetaryAmount(Decimal("34.4100"), USD),
            spot_preemption_probability_daily=Decimal("0.05"),
            cold_boot_rebuild_seconds=Decimal("180.0"),
            storage_gb_monthly=MonetaryAmount(Decimal("0.1000"), USD),
            egress_gb_price=MonetaryAmount(Decimal("0.0900"), USD),
        )

        self.workload = LlmWorkloadProfile(
            model_id="llama-3-70b",
            display_name="Llama 3 70B Instruct",
            total_params_billion=Decimal("70.0"),
            active_params_billion=Decimal("70.0"),
            layers=80,
            hidden_size=8192,
            num_query_heads=64,
            num_kv_heads=8,
            head_dim=128,
            attention_type=AttentionType.GQA,
            mla_latent_dim=None,
            quantization=QuantizationPrecision.FP16,
            weights_bytes_per_param=Decimal("2.0"),
            kv_cache_bytes_per_value=Decimal("2.0"),
            max_context_length=8192,
            peak_concurrent_users=64,
            avg_prompt_tokens=1024,
            avg_generated_tokens=512,
            baseline_rps=Decimal("5.0"),
            peak_burst_rps=Decimal("15.0"),
            target_ttft_seconds=Decimal("1.5"),
            target_tpot_ms=Decimal("40.0"),
        )

        self.roofline = RooflineSimulationResult(
            chassis_or_instance_id="DGX-H100-8X",
            tensor_parallel_degree=8,
            pipeline_parallel_degree=1,
            required_cluster_nodes_baseline=3,
            model_weights_vram_gb=Decimal("140.0"),
            kv_cache_total_vram_gb=Decimal("120.0"),
            activation_buffer_vram_gb=Decimal("14.0"),
            total_required_vram_gb=Decimal("274.0"),
            cluster_total_vram_pool_gb=Decimal("1920.0"),
            vram_utilization_ratio=Decimal("0.4281"),
            ttft_seconds=Decimal("0.25"),
            tpot_ms_per_token=Decimal("18.5"),
            tokens_per_second_per_user=Decimal("54.05"),
            aggregate_cluster_throughput_tok_s=Decimal("3459.2"),
            memory_bus_utilization_ratio=Decimal("0.72"),
            model_flops_utilization_ratio=Decimal("0.48"),
            is_memory_bound=True,
        )

    def test_compute_on_premise_tco_exact_accounting(self) -> None:
        """Verifies exact amortization, salvage deduction, power PUE, rack count, and OEM support."""
        mgmt = MonetaryAmount(Decimal("1200.00"), USD)
        storage = MonetaryAmount(Decimal("800.00"), USD)
        egress = MonetaryAmount(Decimal("300.00"), USD)

        tco = self.aggregator.compute_on_premise_tco(
            chassis=self.chassis,
            facility=self.facility,
            roofline=self.roofline,
            amortization_months=36,
            chassis_per_rack=2,
            management_plane_monthly=mgmt,
            persistent_storage_monthly=storage,
            network_egress_monthly=egress,
        )

        # Total nodes = 3 -> Total CapEx = 3 * 300,000 = 900,000 USD
        # Salvage at 36m = 20% -> Net CapEx = 900,000 * 0.80 = 720,000 USD
        # Monthly compute = 720,000 / 36 = 20,000.0000 USD
        self.assertEqual(tco.hardware_compute_monthly, MonetaryAmount(Decimal("20000.0000"), USD))

        # Power: chassis TDP = 10.2 kW * 3 nodes * 1.25 PUE = 38.25 kW
        # Monthly kWh = 38.25 * 730 = 27,922.5 kWh
        # Monthly power cost = 27,922.5 * 0.10 = 2,792.2500 USD
        self.assertEqual(tco.facility_power_cooling_monthly, MonetaryAmount(Decimal("2792.2500"), USD))

        # Racks: ceil(3 / 2) = 2 racks -> 2 * 1,500 = 3,000.0000 USD
        self.assertEqual(tco.datacenter_rack_colocation_monthly, MonetaryAmount(Decimal("3000.0000"), USD))

        # OEM support: (900,000 * 0.08) / 12 = 72,000 / 12 = 6,000.0000 USD
        self.assertEqual(tco.oem_support_contract_monthly, MonetaryAmount(Decimal("6000.0000"), USD))

        # Total = 20,000 + 1,200 + 800 + 2,792.25 + 3,000 + 6,000 + 300 = 34,092.2500 USD
        self.assertEqual(tco.total_monthly_nominal_tco, MonetaryAmount(Decimal("34092.2500"), USD))
        self.assertTrue(tco.is_on_premise)
        self.assertEqual(tco.amortization_period_months, 36)

    def test_compute_cloud_tco_blended_rates(self) -> None:
        """Verifies blended Spot, Reserved, and On-Demand Cloud OpEx calculation."""
        mgmt = MonetaryAmount(Decimal("500.00"), USD)

        tco = self.aggregator.compute_cloud_tco(
            cloud_spec=self.cloud_spec,
            workload=self.workload,
            roofline=self.roofline,
            amortization_months=24,  # < 36 months uses reserved_1yr_hourly
            spot_allocation_ratio=Decimal("0.20"),
            reserved_allocation_ratio=Decimal("0.50"),
            persistent_storage_gb=Decimal("10000.0"),
            monthly_egress_gb=Decimal("5000.0"),
            management_plane_monthly=mgmt,
            hours_per_month=Decimal("730.0"),
        )

        # Blended hourly:
        # Spot: 34.4100 * 0.20 = 6.8820
        # Reserved 1yr: 68.8200 * 0.50 = 34.4100
        # On-Demand: 98.3200 * 0.30 = 29.4960
        # Sum = 70.7880 / hr
        # Monthly compute = 70.7880 * 3 instances * 730 hours = 155,025.7200 USD
        self.assertEqual(tco.hardware_compute_monthly, MonetaryAmount(Decimal("155025.7200"), USD))

        # Storage: 10,000 GB * 0.10 = 1,000.0000 USD
        self.assertEqual(tco.persistent_storage_monthly, MonetaryAmount(Decimal("1000.0000"), USD))

        # Egress: 5,000 GB * 0.09 = 450.0000 USD
        self.assertEqual(tco.network_egress_monthly, MonetaryAmount(Decimal("450.0000"), USD))

        # Facility/Rack/OEM are 0.0000 for Cloud
        self.assertEqual(tco.facility_power_cooling_monthly, MonetaryAmount(Decimal("0.0000"), USD))
        self.assertEqual(tco.datacenter_rack_colocation_monthly, MonetaryAmount(Decimal("0.0000"), USD))
        self.assertEqual(tco.oem_support_contract_monthly, MonetaryAmount(Decimal("0.0000"), USD))

        # Total = 155,025.72 + 500 + 1,000 + 450 = 156,975.7200 USD
        self.assertEqual(tco.total_monthly_nominal_tco, MonetaryAmount(Decimal("156975.7200"), USD))
        self.assertFalse(tco.is_on_premise)

    def test_compute_hybrid_tco_weighted_synthesis(self) -> None:
        """Verifies weighted synthesis of On-Premise base and Cloud burst TCO breakdowns."""
        on_prem_tco = self.aggregator.compute_on_premise_tco(
            chassis=self.chassis,
            facility=self.facility,
            roofline=self.roofline,
            amortization_months=36,
            chassis_per_rack=2,
            management_plane_monthly=MonetaryAmount(Decimal("1000.00"), USD),
            persistent_storage_monthly=MonetaryAmount(Decimal("1000.00"), USD),
            network_egress_monthly=MonetaryAmount(Decimal("200.00"), USD),
        )

        cloud_tco = self.aggregator.compute_cloud_tco(
            cloud_spec=self.cloud_spec,
            workload=self.workload,
            roofline=self.roofline,
            amortization_months=24,
            spot_allocation_ratio=Decimal("0.50"),
            reserved_allocation_ratio=Decimal("0.00"),
            persistent_storage_gb=Decimal("2000.0"),
            monthly_egress_gb=Decimal("1000.0"),
            management_plane_monthly=MonetaryAmount(Decimal("500.00"), USD),
            hours_per_month=Decimal("730.0"),
        )

        recommendation = ArchetypeRecommendationResult(
            recommended_archetype=DeploymentArchetype.HYBRID_CLOUD_BURST,
            on_prem_composite_score=Decimal("72.0"),
            cloud_composite_score=Decimal("65.0"),
            divergence_delta=Decimal("7.0"),
            recommended_base_load_split_pct=Decimal("0.70"),
            recommended_burst_load_split_pct=Decimal("0.30"),
            is_veto_enforced=False,
            veto_reason_i18n_key=None,
            strategic_rationale_i18n_keys=("domain.questionnaire.paradigm.hybrid_burst",),
        )

        hybrid_tco = self.aggregator.compute_hybrid_tco(
            on_prem_tco=on_prem_tco,
            cloud_tco=cloud_tco,
            recommendation=recommendation,
        )

        expected_compute = (
            on_prem_tco.hardware_compute_monthly.multiply(Decimal("0.70"))
            .add(cloud_tco.hardware_compute_monthly.multiply(Decimal("0.30")))
        )
        self.assertEqual(hybrid_tco.hardware_compute_monthly, expected_compute)

        expected_power = on_prem_tco.facility_power_cooling_monthly.multiply(Decimal("0.70"))
        self.assertEqual(hybrid_tco.facility_power_cooling_monthly, expected_power)

        self.assertTrue(hybrid_tco.is_on_premise)
        self.assertEqual(hybrid_tco.amortization_period_months, 36)

    def test_invalid_inputs_raise_value_error(self) -> None:
        """Verifies defensive guards against invalid amortization, allocation ratios, and splits."""
        mgmt = MonetaryAmount(Decimal("500.00"), USD)
        with self.assertRaises(ValueError):
            self.aggregator.compute_on_premise_tco(
                chassis=self.chassis,
                facility=self.facility,
                roofline=self.roofline,
                amortization_months=0,
                chassis_per_rack=2,
                management_plane_monthly=mgmt,
                persistent_storage_monthly=mgmt,
                network_egress_monthly=mgmt,
            )

        with self.assertRaises(ValueError):
            self.aggregator.compute_cloud_tco(
                cloud_spec=self.cloud_spec,
                workload=self.workload,
                roofline=self.roofline,
                amortization_months=24,
                spot_allocation_ratio=Decimal("0.60"),
                reserved_allocation_ratio=Decimal("0.50"),  # Sum 1.10 > 1.0
                persistent_storage_gb=Decimal("100.0"),
                monthly_egress_gb=Decimal("100.0"),
                management_plane_monthly=mgmt,
                hours_per_month=Decimal("730.0"),
            )


if __name__ == "__main__":
    unittest.main()
