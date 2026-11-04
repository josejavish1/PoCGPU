"""End-to-End Integration Test for FinOpsAdvisorService."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from src.application.finops_advisor_service import FinOpsAdvisorService
from src.domain.models.financial import CurrencyCode, MonetaryAmount
from src.domain.models.hardware import CoolingTopology, DatacenterFacilitySpec
from src.domain.models.workload import (
    AttentionType,
    LlmWorkloadProfile,
    QuantizationPrecision,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_finops_advisor_service_full_workflow() -> None:
    service = FinOpsAdvisorService(REPO_ROOT)
    eur = CurrencyCode("EUR")

    # Define enterprise datacenter facility
    facility = DatacenterFacilitySpec(
        facility_id="ZURICH_TIER4_CPD",
        pue_rating=Decimal("1.2500"),
        max_rack_power_density_kw=Decimal("30.00"),
        electricity_rate_per_kwh=MonetaryAmount(Decimal("0.1600"), eur),
        colocation_rack_monthly_fee=MonetaryAmount(Decimal("1500.00"), eur),
        cooling_topology=CoolingTopology.AIR_COOLED,
        max_rack_units_u=42,
    )

    # Define Llama 3 70B production workload
    workload = LlmWorkloadProfile(
        model_id="LLAMA_3_70B_INSTRUCT",
        display_name="Meta Llama 3 70B Instruct",
        total_params_billion=Decimal("70.6000"),
        active_params_billion=Decimal("70.6000"),
        layers=80,
        hidden_size=8192,
        num_query_heads=64,
        num_kv_heads=8,
        head_dim=128,
        attention_type=AttentionType.GQA,
        mla_latent_dim=None,
        quantization=QuantizationPrecision.FP16,
        weights_bytes_per_param=Decimal("2.0000"),
        kv_cache_bytes_per_value=Decimal("2.0000"),
        max_context_length=8192,
        peak_concurrent_users=32,
        avg_prompt_tokens=2048,
        avg_generated_tokens=256,
        baseline_rps=Decimal("4.0000"),
        peak_burst_rps=Decimal("8.0000"),
        target_ttft_seconds=Decimal("0.5000"),
        target_tpot_ms=Decimal("20.00"),
    )

    # Client responses pointing toward On-Premises Sovereign
    responses = {
        "Q1_SOVEREIGNTY": "Q1_CONFIDENTIAL_CORPORATE",
        "Q2_DUTY_CYCLE": "Q2_SUSTAINED_24_7_BASELINE",
        "Q3_DATACENTER": "Q3_OWNED_CPD_AVAILABLE_KW",
        "Q4_ACCOUNTING": "Q4_CAPEX_ASSET_DEPRECIATION",
        "Q5_OPERATIONS": "Q5_MATURE_SRE_HARDWARE_TEAM",
    }

    result = service.run_full_advisory_simulation(
        vertical_id="BANKING_FINANCE",
        client_responses=responses,
        workload=workload,
        on_prem_chassis_id="SUPERMICRO_SYS_821GE_TNHR_H100",
        cloud_instance_id="gcp-a3-highgpu-8g-h100x8",
        datacenter_facility=facility,
        amortization_months=36,
        target_currency=eur,
        chassis_per_rack=1,
    )

    assert result["recommendation"]["archetype"] == "SOVEREIGN_ON_PREM_BARE_METAL"
    assert result["constitutional_gate"]["is_certified"] is True
    assert len(result["entry_hash"]) == 64
    assert Decimal(result["tco_comparison"]["on_prem_monthly"]) > Decimal("0")
    assert Decimal(result["tco_comparison"]["cloud_monthly"]) > Decimal("0")

    # Verify audit ledger integrity
    assert service.verify_ledger() is True
