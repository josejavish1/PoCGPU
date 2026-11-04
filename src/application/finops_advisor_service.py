"""FinOps Advisor Application Service orchestrating assessment, sizing, risk, and TCO."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Optional, Sequence

from src.adapters.crypto_audit_ledger import CryptographicAuditLedgerAdapter
from src.adapters.json_hardware_registry import JsonHardwareRegistryAdapter
from src.adapters.json_pricing_provider import JsonPricingProviderAdapter
from src.adapters.json_questionnaire_loader import JsonQuestionnaireLoaderAdapter
from src.domain.exceptions import ConstitutionalGateViolationError, DomainLookupError
from src.domain.models.assessment import (
    ArchetypeRecommendationResult,
    AssessmentDecisionPolicy,
    DeploymentArchetype,
    QuestionnaireItemSchema,
)
from src.domain.models.financial import (
    ActuarialRiskMetrics,
    ComputedTcoBreakdown,
    CurrencyCode,
    MonetaryAmount,
)
from src.domain.models.hardware import (
    CloudInstancePricingSpec,
    CoolingTopology,
    DatacenterFacilitySpec,
    HardwareAcceleratorSpec,
    ServerChassisSpec,
)
from src.domain.models.workload import (
    AttentionType,
    LlmWorkloadProfile,
    QuantizationPrecision,
    RooflineSimulationResult,
)
from src.domain.ports.constitutional_gate import ConstitutionalGatePolicy
from src.domain.services.actuarial_engine import OpenFairActuarialEngine
from src.domain.services.cfo_gate import CfoActuarialGate
from src.domain.services.questionnaire_engine import QuestionnaireDecisionEngine
from src.domain.services.roofline_engine import (
    RooflinePhysicsEngine,
    RooflinePhysicsPolicy,
)
from src.domain.services.tco_aggregator import HybridTcoAggregator


class FinOpsAdvisorService:
    """Enterprise application orchestrator for universal hybrid capacity planning and governance."""

    def __init__(self, repo_root: Path) -> None:
        self._repo_root = repo_root
        self._config_dir = repo_root / "config"
        self._working_dir = repo_root / "working"

        # Initialize adapters
        self._hardware_registry = JsonHardwareRegistryAdapter(
            self._config_dir / "catalogs" / "hardware_catalog.json"
        )
        self._pricing_provider = JsonPricingProviderAdapter(
            self._config_dir / "catalogs" / "pricing_catalog.json",
            self._hardware_registry,
        )
        self._questionnaire_loader = JsonQuestionnaireLoaderAdapter(
            self._config_dir / "questionnaires" / "questionnaires.json"
        )
        self._audit_ledger = CryptographicAuditLedgerAdapter(
            self._working_dir / "audit_ledger.jsonl"
        )

        # Load policies from config
        self._load_policies()

        # Initialize domain calculation engines
        self._questionnaire_engine = QuestionnaireDecisionEngine()
        self._roofline_engine = RooflinePhysicsEngine(self._roofline_policy)
        self._actuarial_engine = OpenFairActuarialEngine(**self._actuarial_kwargs)
        self._cfo_gate = CfoActuarialGate()
        self._tco_aggregator = HybridTcoAggregator(**self._tco_kwargs)

    def _load_policies(self) -> None:
        verticals_file = self._config_dir / "taxonomies" / "verticals.json"
        raw_verticals = json.loads(verticals_file.read_text(encoding="utf-8"))
        p = raw_verticals.get("default_policies", {})

        # 1. Constitutional Gate Policy
        cg = p.get("constitutional_gate", {})
        cooling_map = {
            CoolingTopology[top_name]: Decimal(limit_str)
            for top_name, limit_str in cg.get("max_power_kw_by_cooling_topology", {}).items()
        }
        self._constitutional_policy = ConstitutionalGatePolicy(
            max_rack_power_kw=Decimal(cg["max_rack_power_kw"]),
            max_power_kw_by_cooling_topology=cooling_map,
            min_carnot_pue=Decimal(cg["min_carnot_pue"]),
            max_vram_utilization_ratio=Decimal(cg["max_vram_utilization_ratio"]),
            max_memory_bus_utilization_ratio=Decimal(cg["max_memory_bus_utilization_ratio"]),
            min_amortization_months=int(cg["min_amortization_months"]),
            max_amortization_months=int(cg["max_amortization_months"]),
            max_salvage_value_ratio=Decimal(cg["max_salvage_value_ratio"]),
            max_rack_units_u=int(cg.get("max_rack_units_u", 42)),
        )

        # 2. Assessment Decision Policy
        ad = p.get("assessment_decision", {})
        deadlock_arch_str = ad.get("deadlock_default_archetype", "SOVEREIGN_ON_PREM")
        try:
            deadlock_arch = DeploymentArchetype(deadlock_arch_str)
        except ValueError:
            deadlock_arch = DeploymentArchetype[deadlock_arch_str]

        self._assessment_policy = AssessmentDecisionPolicy(
            hybrid_divergence_threshold=Decimal(ad["hybrid_divergence_threshold"]),
            min_base_load_split_pct=Decimal(ad["min_base_load_split_pct"]),
            max_base_load_split_pct=Decimal(ad["max_base_load_split_pct"]),
            min_hybrid_peak_to_average_ratio=Decimal(ad.get("min_hybrid_peak_to_average_ratio", "1.5000")),
            deadlock_default_archetype=deadlock_arch,
            deadlock_base_split_pct=Decimal(ad.get("deadlock_base_split_pct", "1.0000")),
            on_premise_paradigm_i18n_key=ad.get("on_premise_paradigm_i18n_key", "domain.questionnaire.paradigm.on_premise"),
            cloud_paradigm_i18n_key=ad.get("cloud_paradigm_i18n_key", "domain.questionnaire.paradigm.cloud_native"),
            hybrid_paradigm_i18n_key=ad.get("hybrid_paradigm_i18n_key", "domain.questionnaire.paradigm.hybrid_burst"),
            deadlock_resolution_i18n_key=ad.get("deadlock_resolution_i18n_key", "domain.questionnaire.deadlock.resolution"),
        )

        # 3. Roofline Physics Policy
        rp = p.get("roofline_physics", {})
        self._roofline_policy = RooflinePhysicsPolicy(
            bytes_per_gibibyte=Decimal(rp["bytes_per_gibibyte"]),
            bytes_per_gigabyte_sec=Decimal(rp["bytes_per_gigabyte_sec"]),
            gflops_per_tflops=Decimal(rp["gflops_per_tflops"]),
            tflops_scale_factor=Decimal(rp["tflops_scale_factor"]),
            activation_bytes_per_element=Decimal(rp["activation_bytes_per_element"]),
            active_batch_max_tokens=int(rp["active_batch_max_tokens"]),
            microbatch_tokens_per_user=int(rp.get("microbatch_tokens_per_user", 32)),
            cuda_context_overhead_gb=Decimal(rp.get("cuda_context_overhead_gb", "1.0000")),
            kv_headroom_rebuild_buffer_gb=Decimal(rp.get("kv_headroom_rebuild_buffer_gb", "2.0000")),
            min_kv_headroom_floor_gb=Decimal(rp.get("min_kv_headroom_floor_gb", "0.1000")),
            baseline_mfu_ratio=Decimal(rp["baseline_mfu_ratio"]),
            baseline_mbu_ratio=Decimal(rp["baseline_mbu_ratio"]),
        )

        # 4. Actuarial Policy kwargs
        ap = p.get("actuarial_policy", {})
        self._actuarial_kwargs = {
            "hours_per_year": Decimal(ap["hours_per_year"]),
            "days_per_year": Decimal(ap["days_per_year"]),
            "months_per_year": Decimal(ap["months_per_year"]),
            "seconds_per_hour": Decimal(ap["seconds_per_hour"]),
            "min_lef_floor": Decimal(ap["min_lef_floor"]),
            "hot_spare_failover_mttr_hours": Decimal(ap["hot_spare_failover_mttr_hours"]),
            "cloud_weight_streaming_gbps": Decimal(ap["cloud_weight_streaming_gbps"]),
        }

        # 5. TCO Policy kwargs
        tp = p.get("tco_policy", {})
        self._tco_kwargs = {
            "default_hours_per_month": Decimal(tp.get("default_hours_per_month", "730.00")),
            "reserved_3yr_cutoff_months": int(tp.get("reserved_3yr_cutoff_months", 36)),
            "reserved_1yr_cutoff_months": int(tp.get("reserved_1yr_cutoff_months", 12)),
            "months_per_year": Decimal(tp.get("months_per_year", "12.00")),
            "hybrid_on_prem_majority_threshold": Decimal(tp.get("hybrid_on_prem_majority_threshold", "0.5000")),
        }

    def get_questionnaire_schema(self, vertical_id: str, locale: str = "en") -> Sequence[QuestionnaireItemSchema]:
        """Fetches the 5 strategic assessment questions."""
        return self._questionnaire_loader.fetch_questionnaire_schema(vertical_id, locale)

    def evaluate_guided_assessment(
        self,
        vertical_id: str,
        client_responses: Mapping[str, str],
        workload: LlmWorkloadProfile,
        locale: str = "en",
    ) -> ArchetypeRecommendationResult:
        """Evaluates customer responses and outputs the optimal deployment archetype."""
        schema = self.get_questionnaire_schema(vertical_id, locale)
        return self._questionnaire_engine.evaluate_assessment(
            schema=schema,
            client_responses=client_responses,
            workload=workload,
            policy=self._assessment_policy,
        )

    def run_full_advisory_simulation(
        self,
        vertical_id: str,
        client_responses: Mapping[str, str],
        workload: LlmWorkloadProfile,
        on_prem_chassis_id: str,
        cloud_instance_id: str,
        datacenter_facility: DatacenterFacilitySpec,
        amortization_months: int,
        target_currency: CurrencyCode,
        duty_cycle_hours_per_month: Optional[Decimal] = None,
        chassis_per_rack: int = 4,
        management_plane_monthly_usd: Decimal = Decimal("500.00"),
        persistent_storage_monthly_usd: Decimal = Decimal("400.00"),
        network_egress_monthly_usd: Decimal = Decimal("350.00"),
    ) -> dict[str, Any]:
        """Executes full end-to-end FinOps evaluation: Assessment -> Roofline -> Actuarial -> Gate -> TCO -> Ledger."""
        # 1. Evaluate guided assessment
        recommendation = self.evaluate_guided_assessment(vertical_id, client_responses, workload)

        # 2. Resolve on-prem chassis and cloud instance
        raw_chassis = self._hardware_registry.available_chassis.get(on_prem_chassis_id)
        if not raw_chassis:
            raise DomainLookupError(f"Chassis '{on_prem_chassis_id}' not found in catalog.")

        converted_capex = self._pricing_provider.convert_currency(raw_chassis.capex_unit_price, target_currency)
        chassis = ServerChassisSpec(
            chassis_id=raw_chassis.chassis_id,
            oem_vendor=raw_chassis.oem_vendor,
            model_name=raw_chassis.model_name,
            accelerator_sku=raw_chassis.accelerator_sku,
            accelerators_per_chassis=raw_chassis.accelerators_per_chassis,
            base_system_power_watts=raw_chassis.base_system_power_watts,
            rack_units_u=raw_chassis.rack_units_u,
            capex_unit_price=converted_capex,
            oem_warranty_annual_pct=raw_chassis.oem_warranty_annual_pct,
            salvage_value_by_horizon_months=dict(raw_chassis.salvage_value_by_horizon_months),
        )

        raw_cloud = self._pricing_provider.available_cloud_instances.get(cloud_instance_id)
        if not raw_cloud:
            raise DomainLookupError(f"Cloud instance '{cloud_instance_id}' not found in catalog.")

        cloud_spec = CloudInstancePricingSpec(
            provider_id=raw_cloud.provider_id,
            region=raw_cloud.region,
            instance_type=raw_cloud.instance_type,
            accelerator_sku=raw_cloud.accelerator_sku,
            accelerators_per_instance=raw_cloud.accelerators_per_instance,
            on_demand_hourly=self._pricing_provider.convert_currency(raw_cloud.on_demand_hourly, target_currency),
            reserved_1yr_hourly=self._pricing_provider.convert_currency(raw_cloud.reserved_1yr_hourly, target_currency),
            reserved_3yr_hourly=self._pricing_provider.convert_currency(raw_cloud.reserved_3yr_hourly, target_currency),
            spot_hourly_mean=self._pricing_provider.convert_currency(raw_cloud.spot_hourly_mean, target_currency),
            spot_preemption_probability_daily=raw_cloud.spot_preemption_probability_daily,
            cold_boot_rebuild_seconds=raw_cloud.cold_boot_rebuild_seconds,
            storage_gb_monthly=self._pricing_provider.convert_currency(raw_cloud.storage_gb_monthly, target_currency),
            egress_gb_price=self._pricing_provider.convert_currency(raw_cloud.egress_gb_price, target_currency),
        )

        # 3. Simulate Roofline for On-Prem and Cloud
        on_prem_roofline = self._roofline_engine.simulate_roofline(
            candidate_id=chassis.chassis_id,
            workload=workload,
            accelerator=chassis.accelerator_sku,
            accelerators_per_node=chassis.accelerators_per_chassis,
            max_vram_utilization_ratio=self._constitutional_policy.max_vram_utilization_ratio,
        )

        cloud_roofline = self._roofline_engine.simulate_roofline(
            candidate_id=cloud_spec.instance_type,
            workload=workload,
            accelerator=cloud_spec.accelerator_sku,
            accelerators_per_node=cloud_spec.accelerators_per_instance,
            max_vram_utilization_ratio=self._constitutional_policy.max_vram_utilization_ratio,
        )

        # 4. Currency conversion of auxiliary cost lines
        usd = CurrencyCode("USD")
        management_plane_monthly = self._pricing_provider.convert_currency(
            MonetaryAmount(management_plane_monthly_usd, usd), target_currency
        )
        persistent_storage_monthly = self._pricing_provider.convert_currency(
            MonetaryAmount(persistent_storage_monthly_usd, usd), target_currency
        )
        network_egress_monthly = self._pricing_provider.convert_currency(
            MonetaryAmount(network_egress_monthly_usd, usd), target_currency
        )

        # 5. Compute On-Premise TCO
        on_prem_tco = self._tco_aggregator.compute_on_premise_tco(
            chassis=chassis,
            facility=datacenter_facility,
            roofline=on_prem_roofline,
            amortization_months=amortization_months,
            chassis_per_rack=chassis_per_rack,
            management_plane_monthly=management_plane_monthly,
            persistent_storage_monthly=persistent_storage_monthly,
            network_egress_monthly=network_egress_monthly,
            hours_per_month=duty_cycle_hours_per_month,
        )

        # 6. Compute Cloud TCO (blended Spot/Reserved)
        cloud_tco = self._tco_aggregator.compute_cloud_tco(
            cloud_spec=cloud_spec,
            workload=workload,
            roofline=cloud_roofline,
            amortization_months=amortization_months,
            spot_allocation_ratio=Decimal("0.5000"),
            reserved_allocation_ratio=Decimal("0.3000"),
            persistent_storage_gb=Decimal("500.00"),
            monthly_egress_gb=Decimal("1000.00"),
            management_plane_monthly=management_plane_monthly,
            hours_per_month=duty_cycle_hours_per_month or Decimal("730.00"),
        )

        # 7. Compute Hybrid TCO
        hybrid_tco = self._tco_aggregator.compute_hybrid_tco(
            on_prem_tco=on_prem_tco,
            cloud_tco=cloud_tco,
            recommendation=recommendation,
        )

        # 8. Actuarial Risk Assessment
        sla_penalty = MonetaryAmount(Decimal("1000.00"), target_currency)
        on_prem_risk = self._actuarial_engine.evaluate_on_premise_hardware_risk(
            chassis=chassis,
            cluster_node_count=on_prem_roofline.required_cluster_nodes_baseline,
            hourly_sla_penalty=sla_penalty,
            spare_chassis_count=1,
            nominal_monthly_tco=on_prem_tco.total_monthly_nominal_tco,
        )
        cloud_risk = self._actuarial_engine.evaluate_cloud_spot_preemption_risk(
            cloud_spec=cloud_spec,
            cluster_instance_count=cloud_roofline.required_cluster_nodes_baseline,
            hourly_sla_penalty=sla_penalty,
            roofline=cloud_roofline,
            nominal_monthly_tco=cloud_tco.total_monthly_nominal_tco,
        )

        # 9. Constitutional Gate Invariants Audit
        gate_violations = []
        try:
            self._cfo_gate.validate_physical_invariants(
                chassis=chassis,
                facility=datacenter_facility,
                chassis_count_per_rack=chassis_per_rack,
                policy=self._constitutional_policy,
            )
            self._cfo_gate.validate_silicon_invariants(
                roofline=on_prem_roofline,
                policy=self._constitutional_policy,
            )
            self._cfo_gate.validate_financial_invariants(
                tco=on_prem_tco,
                salvage_value_pct=chassis.get_salvage_value_pct(amortization_months),
                policy=self._constitutional_policy,
            )
        except ConstitutionalGateViolationError as err:
            gate_violations.append({
                "rule_code": err.rule_code,
                "i18n_key": err.i18n_key,
                "i18n_params": {k: str(v) for k, v in err.i18n_params.items()},
            })

        # 10. Record immutable audit entry
        provenance = {
            "vertical_id": vertical_id,
            "on_prem_chassis_id": on_prem_chassis_id,
            "cloud_instance_id": cloud_instance_id,
            "amortization_months": str(amortization_months),
            "target_currency": str(target_currency),
            "gate_status": "CERTIFIED" if not gate_violations else "VIOLATIONS_DETECTED",
        }
        entry_hash = self._audit_ledger.append_audit_entry(
            recommendation=recommendation,
            roofline=on_prem_roofline,
            tco_breakdown=hybrid_tco,
            actuarial_metrics=on_prem_risk,
            provenance_metadata=provenance,
        )

        return {
            "entry_hash": entry_hash,
            "recommendation": {
                "archetype": recommendation.recommended_archetype.value,
                "on_prem_score": str(recommendation.on_prem_composite_score),
                "cloud_score": str(recommendation.cloud_composite_score),
                "divergence_delta": str(recommendation.divergence_delta),
                "base_split_pct": str(recommendation.recommended_base_load_split_pct),
                "burst_split_pct": str(recommendation.recommended_burst_load_split_pct),
                "is_veto_enforced": recommendation.is_veto_enforced,
                "veto_reason_i18n_key": recommendation.veto_reason_i18n_key,
            },
            "on_prem_roofline": {
                "required_nodes": on_prem_roofline.required_cluster_nodes_baseline,
                "total_gpus": on_prem_roofline.required_cluster_nodes_baseline * chassis.accelerators_per_chassis,
                "tensor_parallel_degree": on_prem_roofline.tensor_parallel_degree,
                "pipeline_parallel_degree": on_prem_roofline.pipeline_parallel_degree,
                "weights_vram_gb": str(on_prem_roofline.model_weights_vram_gb),
                "kv_cache_vram_gb": str(on_prem_roofline.kv_cache_total_vram_gb),
                "vram_utilization_ratio": str(on_prem_roofline.vram_utilization_ratio),
                "memory_bus_utilization_ratio": str(on_prem_roofline.memory_bus_utilization_ratio),
                "tokens_per_second_per_user": str(on_prem_roofline.tokens_per_second_per_user),
                "aggregate_throughput_tok_s": str(on_prem_roofline.aggregate_cluster_throughput_tok_s),
                "ttft_seconds": str(on_prem_roofline.ttft_seconds),
                "tpot_ms": str(on_prem_roofline.tpot_ms_per_token),
            },
            "tco_comparison": {
                "on_prem_monthly": str(on_prem_tco.total_monthly_nominal_tco.amount),
                "cloud_monthly": str(cloud_tco.total_monthly_nominal_tco.amount),
                "hybrid_monthly": str(hybrid_tco.total_monthly_nominal_tco.amount),
                "currency": str(target_currency),
                "breakdown": {
                    "hardware_compute": str(on_prem_tco.hardware_compute_monthly.amount),
                    "power_cooling": str(on_prem_tco.facility_power_cooling_monthly.amount),
                    "rack_colocation": str(on_prem_tco.datacenter_rack_colocation_monthly.amount),
                    "oem_support": str(on_prem_tco.oem_support_contract_monthly.amount),
                    "control_plane": str(on_prem_tco.management_plane_monthly.amount),
                    "storage": str(on_prem_tco.persistent_storage_monthly.amount),
                    "egress": str(on_prem_tco.network_egress_monthly.amount),
                },
            },
            "actuarial_risk": {
                "on_prem": {
                    "annual_lef": str(on_prem_risk.loss_event_frequency_annual),
                    "mtbf_hours": str(on_prem_risk.expected_hardware_mtbf_hours),
                    "recovery_mttr_hours": str(on_prem_risk.expected_recovery_mttr_hours),
                    "monthly_reserve": str(on_prem_risk.monthly_risk_adjusted_reserve.amount),
                    "risk_adjusted_tco": str(on_prem_risk.total_monthly_risk_adjusted_tco.amount),
                },
                "cloud_spot": {
                    "annual_lef": str(cloud_risk.loss_event_frequency_annual),
                    "mtbf_hours": str(cloud_risk.expected_hardware_mtbf_hours),
                    "recovery_mttr_hours": str(cloud_risk.expected_recovery_mttr_hours),
                    "monthly_reserve": str(cloud_risk.monthly_risk_adjusted_reserve.amount),
                    "risk_adjusted_tco": str(cloud_risk.total_monthly_risk_adjusted_tco.amount),
                },
            },
            "constitutional_gate": {
                "is_certified": len(gate_violations) == 0,
                "violations": gate_violations,
            },
        }

    def verify_ledger(self) -> bool:
        """Cryptographically verifies audit ledger integrity."""
        return self._audit_ledger.verify_ledger_chain_integrity()
