"""Unit tests for RooflinePhysicsEngine."""

from __future__ import annotations

from decimal import Decimal
import pytest

from src.domain.models.hardware import HardwareAcceleratorSpec, InterconnectType
from src.domain.models.workload import (
    AttentionType,
    LlmWorkloadProfile,
    QuantizationPrecision,
)
from src.domain.services.roofline_engine import RooflinePhysicsEngine


@pytest.fixture
def h100_sxm5_spec() -> HardwareAcceleratorSpec:
    """Provides a canonical NVIDIA H100 SXM5 80GB accelerator specification."""
    return HardwareAcceleratorSpec(
        sku_id="NVIDIA_H100_SXM5_80GB",
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


@pytest.fixture
def llama3_70b_workload() -> LlmWorkloadProfile:
    """Provides a canonical 70B GQA FP16 workload profile."""
    return LlmWorkloadProfile(
        model_id="META_LLAMA_3_3_70B_INSTRUCT",
        display_name="Llama 3.3 70B Instruct",
        total_params_billion=Decimal("70.6"),
        active_params_billion=Decimal("70.6"),
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
        peak_concurrent_users=32,
        avg_prompt_tokens=1024,
        avg_generated_tokens=512,
        baseline_rps=Decimal("5.0"),
        peak_burst_rps=Decimal("15.0"),
        target_ttft_seconds=Decimal("1.5"),
        target_tpot_ms=Decimal("40.0"),
    )


@pytest.fixture
def deepseek_mla_workload() -> LlmWorkloadProfile:
    """Provides a Multi-Head Latent Attention (MLA) MoE workload profile."""
    return LlmWorkloadProfile(
        model_id="DEEPSEEK_V3_671B_MOE_FP8",
        display_name="DeepSeek V3 671B MoE (FP8)",
        total_params_billion=Decimal("671.0"),
        active_params_billion=Decimal("37.0"),
        layers=61,
        hidden_size=7168,
        num_query_heads=128,
        num_kv_heads=128,
        head_dim=128,
        attention_type=AttentionType.MLA,
        mla_latent_dim=512,
        quantization=QuantizationPrecision.FP8,
        weights_bytes_per_param=Decimal("1.0"),
        kv_cache_bytes_per_value=Decimal("1.0"),
        max_context_length=16384,
        peak_concurrent_users=64,
        avg_prompt_tokens=2048,
        avg_generated_tokens=512,
        baseline_rps=Decimal("10.0"),
        peak_burst_rps=Decimal("30.0"),
        target_ttft_seconds=Decimal("2.0"),
        target_tpot_ms=Decimal("35.0"),
    )


def test_simulate_roofline_gqa_70b_single_node_sizing(
    h100_sxm5_spec: HardwareAcceleratorSpec,
    llama3_70b_workload: LlmWorkloadProfile,
) -> None:
    """Verifies exact VRAM allocation, TP degree, and latency metrics for a 70B GQA model."""
    engine = RooflinePhysicsEngine()
    result = engine.simulate_roofline(
        candidate_id="DGX_H100_8X",
        workload=llama3_70b_workload,
        accelerator=h100_sxm5_spec,
        accelerators_per_node=8,
        max_vram_utilization_ratio=Decimal("0.90"),
    )

    assert result.chassis_or_instance_id == "DGX_H100_8X"
    assert result.required_cluster_nodes_baseline == 1
    assert result.tensor_parallel_degree in (4, 8)
    assert result.pipeline_parallel_degree in (1, 2)
    assert result.cluster_total_vram_pool_gb == Decimal("640.0000")
    assert result.model_weights_vram_gb == Decimal("131.5027")
    assert result.kv_cache_total_vram_gb == Decimal("15.0000")
    assert Decimal("0.0") < result.activation_buffer_vram_gb <= Decimal("10.0000")
    assert result.total_required_vram_gb > Decimal("146.0000")
    assert Decimal("0.0") < result.vram_utilization_ratio < Decimal("0.9000")
    assert result.ttft_seconds > Decimal("0")
    assert result.tpot_ms_per_token > Decimal("0")
    assert result.tokens_per_second_per_user > Decimal("0")
    assert result.aggregate_cluster_throughput_tok_s > Decimal("0")
    assert Decimal("0.0") < result.memory_bus_utilization_ratio <= Decimal("1.0000")
    assert result.model_flops_utilization_ratio == Decimal("0.4500")
    assert isinstance(result.is_memory_bound, bool)


def test_simulate_roofline_mla_moe_multi_node_scaling(
    h100_sxm5_spec: HardwareAcceleratorSpec,
    deepseek_mla_workload: LlmWorkloadProfile,
) -> None:
    """Verifies multi-node scaling and MLA KV cache compression for a 671B MoE model."""
    engine = RooflinePhysicsEngine()
    result = engine.simulate_roofline(
        candidate_id="HGX_H100_8X_NODE",
        workload=deepseek_mla_workload,
        accelerator=h100_sxm5_spec,
        accelerators_per_node=8,
        max_vram_utilization_ratio=Decimal("0.90"),
    )

    assert result.required_cluster_nodes_baseline == 2
    assert result.tensor_parallel_degree == 8
    assert result.pipeline_parallel_degree == 2
    assert result.cluster_total_vram_pool_gb == Decimal("1280.0000")
    assert result.total_required_vram_gb > Decimal("576.0000")
    assert result.vram_utilization_ratio <= Decimal("0.9000")
    assert isinstance(result.is_memory_bound, bool)


def test_simulate_roofline_rejects_invalid_inputs(
    h100_sxm5_spec: HardwareAcceleratorSpec,
    llama3_70b_workload: LlmWorkloadProfile,
) -> None:
    """Verifies defensive input validation on candidate_id, node counts, and VRAM ceiling."""
    engine = RooflinePhysicsEngine()

    with pytest.raises(ValueError, match="Candidate identifier"):
        engine.simulate_roofline(
            candidate_id="   ",
            workload=llama3_70b_workload,
            accelerator=h100_sxm5_spec,
            accelerators_per_node=8,
            max_vram_utilization_ratio=Decimal("0.90"),
        )

    with pytest.raises(ValueError, match="accelerators_per_node"):
        engine.simulate_roofline(
            candidate_id="NODE_01",
            workload=llama3_70b_workload,
            accelerator=h100_sxm5_spec,
            accelerators_per_node=0,
            max_vram_utilization_ratio=Decimal("0.90"),
        )

    with pytest.raises(ValueError, match="max_vram_utilization_ratio"):
        engine.simulate_roofline(
            candidate_id="NODE_01",
            workload=llama3_70b_workload,
            accelerator=h100_sxm5_spec,
            accelerators_per_node=8,
            max_vram_utilization_ratio=Decimal("1.05"),
        )
