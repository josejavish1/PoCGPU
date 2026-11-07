"""
Unit Tests for the Silicon Capacity & Analytical Roofline Sizing Calculator
==========================================================================
Verifies deterministic silicon physics equations, GQA vs MLA KV-cache scaling,
sparse MoE expert activation, and Two-Regime Roofline latency models.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add calculators/sizing/src to path for testing
CALCULATOR_SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(CALCULATOR_SRC))

from sizing import (  # type: ignore # noqa: E402
    STANDARD_VANILLA_PROFILE,
    TIER1_PRODUCTION_PROFILE,
    AcceleratorSpec,
    AttentionType,
    InterconnectTopology,
    ModelArchitectureSpec,
    PrecisionDtype,
    RooflineRegime,
    RooflineSizingEngine,
    SizingDemandRequest,
    calculate_activation_vram_gb,
    calculate_allreduce_time_seconds,
    calculate_dynamic_kv_cache_vram_gb,
    calculate_kv_cache_bytes_per_token,
    calculate_moe_active_weights_gb,
    calculate_roofline_latencies,
    calculate_silicon_topology,
    calculate_static_weights_vram_gb,
    get_bytes_per_param,
    get_effective_peak_tflops,
)

# Reference Accelerator Specifications
L4_SPEC = AcceleratorSpec(
    chip_id="NVIDIA_L4_24GB",
    vendor="NVIDIA",
    architecture="Ada Lovelace",
    fp16_tflops=121.0,
    fp8_tflops=242.0,
    int8_tops=242.0,
    vram_gb=24.0,
    memory_bandwidth_gbps=300.0,
    interconnect_topology=InterconnectTopology.PCIE_RING,
    interconnect_bandwidth_gbps=64.0,
    allreduce_base_latency_us=18.0,
    base_mfu_prefill=0.38,
    base_bw_efficiency=0.74,
    tdp_watts=72.0,
)

H100_SPEC = AcceleratorSpec(
    chip_id="NVIDIA_H100_SXM5_80GB",
    vendor="NVIDIA",
    architecture="Hopper",
    fp16_tflops=989.0,
    fp8_tflops=1979.0,
    int8_tops=1979.0,
    vram_gb=80.0,
    memory_bandwidth_gbps=3350.0,
    interconnect_topology=InterconnectTopology.NVSWITCH_SHARP,
    interconnect_bandwidth_gbps=900.0,
    allreduce_base_latency_us=1.2,
    base_mfu_prefill=0.65,
    base_bw_efficiency=0.85,
    tdp_watts=700.0,
)

# Reference Model Specifications
MISTRAL_7B_SPEC = ModelArchitectureSpec(
    model_id="MISTRAL_7B_INSTRUCT",
    display_name="Mistral 7B Instruct v0.3",
    total_params_billion=7.24,
    active_params_billion=7.24,
    layers=32,
    hidden_size=4096,
    num_query_heads=32,
    num_kv_heads=8,
    head_dim=128,
    attention_type=AttentionType.GQA,
    default_max_context_length=8192,
)

DEEPSEEK_V3_SPEC = ModelArchitectureSpec(
    model_id="DEEPSEEK_V3",
    display_name="DeepSeek V3 (MLA + MoE)",
    total_params_billion=671.0,
    active_params_billion=37.0,
    layers=61,
    hidden_size=7168,
    num_query_heads=128,
    num_kv_heads=1,  # Compressed latent representation
    head_dim=128,
    attention_type=AttentionType.MLA,
    default_max_context_length=32768,
    num_routed_experts=256,
    num_active_experts_per_token=8,
    mla_latent_kv_dim=512,
    mla_decoupled_rope_dim=64,
)


class TestSiliconMemoryPhysics:
    """Verifies deterministic VRAM calculations for weights, MLA, and KV cache."""

    def test_bytes_per_param(self) -> None:
        assert get_bytes_per_param(PrecisionDtype.FP16) == 2.0
        assert get_bytes_per_param(PrecisionDtype.BF16) == 2.0
        assert get_bytes_per_param(PrecisionDtype.FP8) == 1.0
        assert get_bytes_per_param(PrecisionDtype.INT8) == 1.0
        assert get_bytes_per_param(PrecisionDtype.INT4) == 0.55

    def test_static_weights_vram(self) -> None:
        vram_fp16 = calculate_static_weights_vram_gb(MISTRAL_7B_SPEC, PrecisionDtype.FP16)
        assert 13.4 < vram_fp16 < 13.6
        vram_fp8 = calculate_static_weights_vram_gb(MISTRAL_7B_SPEC, PrecisionDtype.FP8)
        assert 6.7 < vram_fp8 < 6.8

    def test_gqa_vs_mla_kv_cache_compression(self) -> None:
        # Standard GQA: 32 layers * 8 heads * 128 dim * 2 (K & V) * 1 byte (FP8) * paging overhead ≈ 66.5 KB/tok
        bytes_gqa = calculate_kv_cache_bytes_per_token(
            model=MISTRAL_7B_SPEC,
            kv_cache_precision=PrecisionDtype.FP8,
            block_size=32,
        )
        assert 65_000.0 < bytes_gqa < 68_000.0

        # DeepSeek MLA: 61 layers * (512 dc + 64 dR) * 1 byte (FP8) * paging overhead ≈ 35.6 KB/tok
        # Notice: DeepSeek is a 671B model, yet its KV cache per token is 46% SMALLER than 7B Mistral!
        bytes_mla = calculate_kv_cache_bytes_per_token(
            model=DEEPSEEK_V3_SPEC,
            kv_cache_precision=PrecisionDtype.FP8,
            block_size=32,
        )
        assert bytes_mla < bytes_gqa
        assert 34_000.0 < bytes_mla < 37_000.0

    def test_dynamic_kv_cache_vram(self) -> None:
        kv_gb = calculate_dynamic_kv_cache_vram_gb(
            layers=32,
            num_kv_heads=8,
            head_dim=128,
            concurrency_users=30,
            max_context_length=2048,
            kv_cache_precision=PrecisionDtype.FP8,
            model=MISTRAL_7B_SPEC,
        )
        assert 3.5 < kv_gb < 4.5

    def test_silicon_topology(self) -> None:
        raw, tp, pp = calculate_silicon_topology(140.0, 80.0, 0.90)
        assert raw == 2
        assert tp == 2
        assert pp == 1

    def test_moe_active_weights_streaming_scaling(self) -> None:
        # For batch size = 1, only k=8 experts out of 256 are loaded
        # Active weights in FP8 is significantly smaller than total 671B model weights
        weights_b1 = calculate_moe_active_weights_gb(
            model=DEEPSEEK_V3_SPEC,
            precision=PrecisionDtype.FP8,
            active_batch_size=1,
        )
        # For batch size = 64, more experts are activated across users
        weights_b64 = calculate_moe_active_weights_gb(
            model=DEEPSEEK_V3_SPEC,
            precision=PrecisionDtype.FP8,
            active_batch_size=64,
        )
        # Total static weights = 671B in FP8 ≈ 624 GB
        total_static = calculate_static_weights_vram_gb(DEEPSEEK_V3_SPEC, PrecisionDtype.FP8)

        assert weights_b1 < weights_b64
        assert weights_b64 < total_static
        assert weights_b1 < 60.0  # Far less than 624 GB total weights!

    def test_activation_vram_formula(self) -> None:
        # Activation memory based on max_num_batched_tokens and TP workspace
        act_tp2 = calculate_activation_vram_gb(
            model=MISTRAL_7B_SPEC, max_num_batched_tokens=4096, tp=2
        )
        act_tp8 = calculate_activation_vram_gb(
            model=MISTRAL_7B_SPEC, max_num_batched_tokens=4096, tp=8
        )
        assert act_tp8 > act_tp2  # Larger TP requires more NCCL workspace buffers


class TestTwoRegimeRooflineAndNetworkCollectives:
    """Verifies Two-Regime Roofline, Precision TFLOPS switching, and Network Collectives."""

    def test_precision_aware_tflops_switching(self) -> None:
        # L4 FP16 TFLOPS = 121, FP8 TFLOPS = 242
        assert get_effective_peak_tflops(L4_SPEC, PrecisionDtype.FP16) == 121.0
        assert get_effective_peak_tflops(L4_SPEC, PrecisionDtype.FP8) == 242.0
        assert get_effective_peak_tflops(H100_SPEC, PrecisionDtype.FP8) == 1979.0

    def test_allreduce_latency_nvswitch_vs_pcie(self) -> None:
        # 16 MB message across TP=8 over 32 layers
        msg_bytes = 16.0 * 1024.0 * 1024.0
        # PCIe Ring (L4): O(TP) hops + 18us per hop + 64 GB/s bus
        time_pcie = calculate_allreduce_time_seconds(
            accel=L4_SPEC,
            tp=8,
            layers_per_pp_stage=32.0,
            message_bytes=msg_bytes,
        )
        # NVSwitch SHARP (H100): O(1) in-network reduction + 1.2us + 900 GB/s bus
        time_nvswitch = calculate_allreduce_time_seconds(
            accel=H100_SPEC,
            tp=8,
            layers_per_pp_stage=32.0,
            message_bytes=msg_bytes,
        )
        # NVSwitch must be an order of magnitude faster than PCIe Ring All-Reduce!
        assert time_nvswitch < (time_pcie / 8.0)

    def test_quadratic_attention_prefill_scaling(self) -> None:
        # Short context (256 tokens) vs Long context (16,384 tokens)
        ttft_short, _, _, _ = calculate_roofline_latencies(
            model_spec=MISTRAL_7B_SPEC,
            accelerator_spec=L4_SPEC,
            precision=PrecisionDtype.FP8,
            kv_cache_precision=PrecisionDtype.FP8,
            concurrency_users=1,
            prompt_tokens=256,
            completion_tokens=50,
            topology_tp=2,
            topology_pp=1,
            runtime_profile=TIER1_PRODUCTION_PROFILE,
        )
        ttft_long, _, _, _ = calculate_roofline_latencies(
            model_spec=MISTRAL_7B_SPEC,
            accelerator_spec=L4_SPEC,
            precision=PrecisionDtype.FP8,
            kv_cache_precision=PrecisionDtype.FP8,
            concurrency_users=1,
            prompt_tokens=16384,
            completion_tokens=50,
            topology_tp=2,
            topology_pp=1,
            runtime_profile=TIER1_PRODUCTION_PROFILE,
        )
        # Ratio of prompt tokens is 64x, but attention FLOPs scales quadratically
        assert ttft_long > (ttft_short * 70.0)

    def test_h100_vs_l4_decode_acceleration(self) -> None:
        _, tpot_l4, _, regime_l4 = calculate_roofline_latencies(
            model_spec=MISTRAL_7B_SPEC,
            accelerator_spec=L4_SPEC,
            precision=PrecisionDtype.FP8,
            kv_cache_precision=PrecisionDtype.FP8,
            concurrency_users=15,
            prompt_tokens=200,
            completion_tokens=100,
            topology_tp=2,
            topology_pp=1,
            runtime_profile=TIER1_PRODUCTION_PROFILE,
        )
        _, tpot_h100, _, _ = calculate_roofline_latencies(
            model_spec=MISTRAL_7B_SPEC,
            accelerator_spec=H100_SPEC,
            precision=PrecisionDtype.FP8,
            kv_cache_precision=PrecisionDtype.FP8,
            concurrency_users=15,
            prompt_tokens=200,
            completion_tokens=100,
            topology_tp=2,
            topology_pp=1,
            runtime_profile=TIER1_PRODUCTION_PROFILE,
        )
        assert regime_l4 == RooflineRegime.MEMORY_BANDWIDTH_BOUND
        # H100 with HBM3 (3,350 GB/s) and NVSwitch delivers sub-8ms decode
        assert tpot_h100 < 8.0
        assert tpot_h100 < (tpot_l4 / 3.0)


class TestRooflineSizingEngineIntegration:
    """Verifies end-to-end evaluation with the canonical RooflineSizingEngine."""

    def test_mistral_on_dual_l4_vanilla_vs_tier1_tuned(self) -> None:
        engine = RooflineSizingEngine()
        demand = SizingDemandRequest(
            model_spec=MISTRAL_7B_SPEC,
            accelerator_spec=L4_SPEC,
            concurrency_users=30,
            prompt_tokens=200,
            completion_tokens=100,
            precision=PrecisionDtype.FP16,
            kv_cache_precision=PrecisionDtype.FP16,
            runtime_profile=STANDARD_VANILLA_PROFILE,
            sla_target_ttft_ms=1000.0,
            sla_target_tpot_ms=60.0,
        )
        vanilla_result = engine.evaluate_sizing(demand)

        assert vanilla_result.weights_vram_gb > 13.0
        assert vanilla_result.topology_tensor_parallel >= 2

        # Tuned profile (FP8 W8A8 weights, FP8 KV, Prefix Caching)
        demand_tuned = SizingDemandRequest(
            model_spec=MISTRAL_7B_SPEC,
            accelerator_spec=L4_SPEC,
            concurrency_users=30,
            prompt_tokens=200,
            completion_tokens=100,
            precision=PrecisionDtype.FP8,
            kv_cache_precision=PrecisionDtype.FP8,
            runtime_profile=TIER1_PRODUCTION_PROFILE,
            sla_target_ttft_ms=1000.0,
            sla_target_tpot_ms=60.0,
        )
        tuned_result = engine.evaluate_sizing(demand_tuned)

        # Tuned profile cuts weights in half (13.5 GB -> 6.74 GB)
        assert tuned_result.weights_vram_gb < (vanilla_result.weights_vram_gb * 0.55)
        # Tuned profile accelerates decode and throughput
        assert (
            tuned_result.estimated_cluster_throughput_tps
            > vanilla_result.estimated_cluster_throughput_tps
        )
