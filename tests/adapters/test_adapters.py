"""Comprehensive Unit Tests for Infrastructure Adapters and Audit Ledger."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
import pytest

from src.adapters.crypto_audit_ledger import CryptographicAuditLedgerAdapter
from src.adapters.json_hardware_registry import JsonHardwareRegistryAdapter
from src.adapters.json_model_registry import JsonModelRegistryAdapter
from src.adapters.json_pricing_provider import JsonPricingProviderAdapter
from src.adapters.json_questionnaire_loader import JsonQuestionnaireLoaderAdapter
from src.domain.exceptions import DomainLookupError
from src.domain.models.assessment import ArchetypeRecommendationResult, DeploymentArchetype
from src.domain.models.financial import ActuarialRiskMetrics, ComputedTcoBreakdown, CurrencyCode, MonetaryAmount
from src.domain.models.workload import RooflineSimulationResult

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = REPO_ROOT / "config"


@pytest.fixture
def hardware_registry() -> JsonHardwareRegistryAdapter:
    return JsonHardwareRegistryAdapter(CONFIG_DIR / "catalogs" / "hardware_catalog.json")


@pytest.fixture
def pricing_provider(hardware_registry: JsonHardwareRegistryAdapter) -> JsonPricingProviderAdapter:
    return JsonPricingProviderAdapter(CONFIG_DIR / "catalogs" / "pricing_catalog.json", hardware_registry)


@pytest.fixture
def questionnaire_loader() -> JsonQuestionnaireLoaderAdapter:
    return JsonQuestionnaireLoaderAdapter(CONFIG_DIR / "questionnaires" / "questionnaires.json")


@pytest.fixture
def model_registry() -> JsonModelRegistryAdapter:
    return JsonModelRegistryAdapter(CONFIG_DIR / "catalogs" / "models_catalog.json")


def test_model_registry_resolves_profiles(model_registry: JsonModelRegistryAdapter) -> None:
    models = model_registry.list_available_models()
    assert "LLAMA_3_70B_INSTRUCT" in models
    assert "DEEPSEEK_V3_671B_MOE_FP8" in models

    profile = model_registry.get_model_workload_profile(
        model_id="LLAMA_3_70B_INSTRUCT",
        peak_concurrent_users=32,
        max_context_length=8192,
        avg_prompt_tokens=2048,
        avg_generated_tokens=256,
        baseline_rps=Decimal("4.0"),
        peak_burst_rps=Decimal("8.0"),
    )
    assert profile.total_params_billion == Decimal("70.6000")
    assert profile.layers == 80
    assert profile.num_kv_heads == 8


def test_hardware_registry_resolves_h100_and_unknown_raises(hardware_registry: JsonHardwareRegistryAdapter) -> None:
    spec = hardware_registry.get_accelerator_spec("NVIDIA_H100_SXM5_80GB")
    assert spec.vendor == "NVIDIA"
    assert spec.vram_gb == Decimal("80.0")
    assert spec.memory_bandwidth_gbps == Decimal("3350.0")

    with pytest.raises(DomainLookupError):
        hardware_registry.get_accelerator_spec("UNKNOWN_SILICON_SKU")


def test_hardware_registry_list_compatible_chassis(hardware_registry: JsonHardwareRegistryAdapter) -> None:
    compatible = hardware_registry.list_compatible_chassis(
        min_vram_gb=Decimal("600.0"),
        max_rack_kw=Decimal("25.0"),
    )
    assert len(compatible) >= 1
    assert any("H100" in c.chassis_id for c in compatible)


def test_pricing_provider_fx_conversion(pricing_provider: JsonPricingProviderAdapter) -> None:
    usd = CurrencyCode("USD")
    eur = CurrencyCode("EUR")
    amount_usd = MonetaryAmount(Decimal("100.00"), usd)
    amount_eur = pricing_provider.convert_currency(amount_usd, eur)
    assert amount_eur.currency == eur
    assert amount_eur.amount == Decimal("92.0000")


def test_pricing_provider_resolves_cloud_instances(pricing_provider: JsonPricingProviderAdapter) -> None:
    usd = CurrencyCode("USD")
    instances = pricing_provider.get_cloud_pricing("NVIDIA_H100_SXM5_80GB", region=None, target_currency=usd)
    assert len(instances) >= 2
    assert any(inst.provider_id == "GCP" for inst in instances)
    assert any(inst.provider_id == "AWS" for inst in instances)

    # Test direct lookup by instance_id
    inst = pricing_provider.get_cloud_instance_by_id("gcp-a3-highgpu-8g-h100x8", target_currency=usd)
    assert inst.instance_id == "gcp-a3-highgpu-8g-h100x8"
    assert inst.provider_id == "GCP"

    # Test list_all_cloud_instances
    all_inst = pricing_provider.list_all_cloud_instances(target_currency=usd)
    assert len(all_inst) >= 5


def test_questionnaire_loader_fetches_schema(questionnaire_loader: JsonQuestionnaireLoaderAdapter) -> None:
    schema = questionnaire_loader.fetch_questionnaire_schema("BANKING_FINANCE", "en")
    assert len(schema) == 5
    question_ids = [q.question_id for q in schema]
    assert "Q1_SOVEREIGNTY" in question_ids
    assert "Q2_DUTY_CYCLE" in question_ids


def test_cryptographic_audit_ledger_integrity_and_tampering(tmp_path: Path) -> None:
    ledger_file = tmp_path / "test_ledger.jsonl"
    adapter = CryptographicAuditLedgerAdapter(ledger_file)

    rec = ArchetypeRecommendationResult(
        recommended_archetype=DeploymentArchetype.SOVEREIGN_ON_PREM,
        on_prem_composite_score=Decimal("85.0000"),
        cloud_composite_score=Decimal("30.0000"),
        divergence_delta=Decimal("55.0000"),
        recommended_base_load_split_pct=Decimal("1.0000"),
        recommended_burst_load_split_pct=Decimal("0.0000"),
        is_veto_enforced=False,
        veto_reason_i18n_key=None,
        strategic_rationale_i18n_keys=("test_rationale",),
    )
    roof = RooflineSimulationResult(
        chassis_or_instance_id="TEST_CHASSIS",
        tensor_parallel_degree=8,
        pipeline_parallel_degree=1,
        required_cluster_nodes_baseline=1,
        model_weights_vram_gb=Decimal("130.0000"),
        kv_cache_total_vram_gb=Decimal("15.0000"),
        activation_buffer_vram_gb=Decimal("2.0000"),
        total_required_vram_gb=Decimal("147.0000"),
        cluster_total_vram_pool_gb=Decimal("640.0000"),
        vram_utilization_ratio=Decimal("0.2300"),
        ttft_seconds=Decimal("0.0400"),
        tpot_ms_per_token=Decimal("8.50"),
        tokens_per_second_per_user=Decimal("117.00"),
        aggregate_cluster_throughput_tok_s=Decimal("1170.00"),
        memory_bus_utilization_ratio=Decimal("0.6500"),
        model_flops_utilization_ratio=Decimal("0.4500"),
        is_memory_bound=True,
    )
    usd = CurrencyCode("USD")
    zero = MonetaryAmount(Decimal("0.00"), usd)
    ten = MonetaryAmount(Decimal("1000.00"), usd)
    sev = MonetaryAmount(Decimal("7000.00"), usd)
    tco = ComputedTcoBreakdown(
        hardware_compute_monthly=ten,
        management_plane_monthly=ten,
        persistent_storage_monthly=ten,
        facility_power_cooling_monthly=ten,
        datacenter_rack_colocation_monthly=ten,
        oem_support_contract_monthly=ten,
        network_egress_monthly=ten,
        total_monthly_nominal_tco=sev,
        amortization_period_months=36,
        is_on_premise=True,
    )
    act = ActuarialRiskMetrics(
        loss_event_frequency_annual=Decimal("0.5000"),
        single_loss_expectancy=ten,
        annualized_loss_expectancy=MonetaryAmount(Decimal("500.00"), usd),
        monthly_risk_adjusted_reserve=MonetaryAmount(Decimal("41.6667"), usd),
        expected_hardware_mtbf_hours=Decimal("17520.00"),
        expected_recovery_mttr_hours=Decimal("4.0000"),
        total_monthly_risk_adjusted_tco=MonetaryAmount(Decimal("7041.6667"), usd),
    )

    hash1 = adapter.append_audit_entry(rec, roof, tco, act, {"test": "metadata_1"})
    hash2 = adapter.append_audit_entry(rec, roof, tco, act, {"test": "metadata_2"})
    assert len(hash1) == 64
    assert len(hash2) == 64
    assert hash1 != hash2

    assert adapter.verify_ledger_chain_integrity() is True

    # Tamper with file
    lines = ledger_file.read_text(encoding="utf-8").splitlines()
    tampered_entry = json.loads(lines[0])
    tampered_entry["recommendation"]["on_prem_score"] = "99.9999"
    lines[0] = json.dumps(tampered_entry)
    ledger_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    assert adapter.verify_ledger_chain_integrity() is False
