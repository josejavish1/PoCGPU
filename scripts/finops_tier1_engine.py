#!/usr/bin/env python3
"""
Enterprise Tier-1 LLM Inference FinOps Engine & Capacity Planner
================================================================
Architectural model combining:
1. Exact Grouped-Query Attention (GQA) & Multi-head Latent Attention (MLA) VRAM sizing.
2. Arithmetic Intensity & Roofline Performance Modeling (Compute-bound Prefill vs Bandwidth-bound Decode).
3. Corporate FinOps Unit Economics: Duty-cycle hibernation, asymmetric pricing (Prefill vs Decode),
   KV-cache prompt amortization, and public frontier API break-even analysis.

Strictly adhering to Tier-1 infrastructure engineering standards (OpenAI, Anthropic, SemiAnalysis, vLLM).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


# ==============================================================================
# 1. HARDWARE CATALOG & HARDWARE SPECIFICATIONS
# ==============================================================================

class InterconnectType(str, Enum):
    PCIE_GEN4 = "PCIe Gen4 (64 GB/s bidirectional)"
    PCIE_GEN5 = "PCIe Gen5 (128 GB/s bidirectional)"
    NVLINK_SXM4 = "NVLink 3 (600 GB/s bidirectional)"
    NVLINK_SXM5 = "NVLink 4 (900 GB/s bidirectional)"


@dataclass(frozen=True)
class GPUSpec:
    name: str
    vram_gb: float
    memory_bandwidth_gb_s: float
    fp16_tflops: float
    fp8_tflops: float
    interconnect: InterconnectType
    gcp_ondemand_usd_hr: float
    gcp_spot_usd_hr: float
    typical_tdp_watts: int

    @property
    def bus_penalty_factor(self) -> float:
        """Penalty multiplier for Tensor Parallelism communication overhead."""
        if self.interconnect in (InterconnectType.NVLINK_SXM4, InterconnectType.NVLINK_SXM5):
            return 0.94
        elif self.interconnect == InterconnectType.PCIE_GEN5:
            return 0.82
        else:
            return 0.70  # PCIe Gen4 bottleneck under high-concurrency all-reduce


GPU_CATALOG: Dict[str, GPUSpec] = {
    "NVIDIA_L4": GPUSpec(
        name="NVIDIA L4 24GB",
        vram_gb=24.0,
        memory_bandwidth_gb_s=300.0,
        fp16_tflops=120.0,
        fp8_tflops=240.0,
        interconnect=InterconnectType.PCIE_GEN4,
        gcp_ondemand_usd_hr=0.70,
        gcp_spot_usd_hr=0.28,
        typical_tdp_watts=72,
    ),
    "NVIDIA_A100_40GB": GPUSpec(
        name="NVIDIA A100 SXM4 40GB",
        vram_gb=40.0,
        memory_bandwidth_gb_s=1555.0,
        fp16_tflops=312.0,
        fp8_tflops=312.0,
        interconnect=InterconnectType.NVLINK_SXM4,
        gcp_ondemand_usd_hr=2.93,
        gcp_spot_usd_hr=0.88,
        typical_tdp_watts=400,
    ),
    "NVIDIA_A100_80GB": GPUSpec(
        name="NVIDIA A100 SXM4 80GB",
        vram_gb=80.0,
        memory_bandwidth_gb_s=2039.0,
        fp16_tflops=312.0,
        fp8_tflops=312.0,
        interconnect=InterconnectType.NVLINK_SXM4,
        gcp_ondemand_usd_hr=3.67,
        gcp_spot_usd_hr=1.10,
        typical_tdp_watts=400,
    ),
    "NVIDIA_H100_80GB": GPUSpec(
        name="NVIDIA H100 SXM5 80GB",
        vram_gb=80.0,
        memory_bandwidth_gb_s=3350.0,
        fp16_tflops=989.0,
        fp8_tflops=1978.0,
        interconnect=InterconnectType.NVLINK_SXM5,
        gcp_ondemand_usd_hr=5.50,
        gcp_spot_usd_hr=2.00,
        typical_tdp_watts=700,
    ),
    "NVIDIA_H200_141GB": GPUSpec(
        name="NVIDIA H200 SXM5 141GB",
        vram_gb=141.0,
        memory_bandwidth_gb_s=4800.0,
        fp16_tflops=989.0,
        fp8_tflops=1978.0,
        interconnect=InterconnectType.NVLINK_SXM5,
        gcp_ondemand_usd_hr=6.80,
        gcp_spot_usd_hr=2.60,
        typical_tdp_watts=700,
    ),
}


# ==============================================================================
# 2. MODEL ARCHITECTURE PRESETS
# ==============================================================================

class AttentionMechanism(str, Enum):
    MHA = "Multi-Head Attention"
    GQA = "Grouped-Query Attention"
    MLA = "Multi-head Latent Attention (DeepSeek)"


class WeightPrecision(str, Enum):
    FP16 = "FP16 (16-bit, 2.0 bytes/param)"
    BF16 = "BF16 (16-bit, 2.0 bytes/param)"
    FP8 = "FP8 (8-bit, 1.0 bytes/param)"
    INT8 = "INT8 (8-bit, 1.0 bytes/param)"
    INT4 = "INT4 / AWQ / GPTQ (4-bit, 0.55 bytes/param)"

    @property
    def bytes_per_param(self) -> float:
        if self in (WeightPrecision.FP16, WeightPrecision.BF16):
            return 2.0
        elif self in (WeightPrecision.FP8, WeightPrecision.INT8):
            return 1.0
        elif self == WeightPrecision.INT4:
            return 0.55  # 0.50 bytes weights + 0.05 quantization scales/zeros
        return 2.0


@dataclass(frozen=True)
class ModelArchitecture:
    name: str
    total_params_billion: float
    active_params_billion: float
    layers: int
    hidden_size: int
    num_query_heads: int
    num_kv_heads: int
    head_dim: int
    attention_type: AttentionMechanism
    mla_latent_dim: Optional[int] = None

    def kv_cache_bytes_per_token(self, kv_precision_bytes: float = 2.0) -> float:
        """
        Calculates exact memory consumed by 1 token in the KV cache across all layers.
        Formula:
          - MHA/GQA: 2 (K+V) * layers * num_kv_heads * head_dim * bytes_per_element
          - MLA: 2 * layers * mla_latent_dim * bytes_per_element
        """
        if self.attention_type == AttentionMechanism.MLA and self.mla_latent_dim:
            return 2.0 * self.layers * self.mla_latent_dim * kv_precision_bytes
        else:
            return 2.0 * self.layers * self.num_kv_heads * self.head_dim * kv_precision_bytes


MODEL_PRESETS: Dict[str, ModelArchitecture] = {
    "mistral-7b": ModelArchitecture(
        name="Mistral-7B-Instruct-v0.3",
        total_params_billion=7.24,
        active_params_billion=7.24,
        layers=32,
        hidden_size=4096,
        num_query_heads=32,
        num_kv_heads=8,  # GQA factor: 4x reduction
        head_dim=128,
        attention_type=AttentionMechanism.GQA,
    ),
    "llama3-8b": ModelArchitecture(
        name="Llama-3.1-8B-Instruct",
        total_params_billion=8.03,
        active_params_billion=8.03,
        layers=32,
        hidden_size=4096,
        num_query_heads=32,
        num_kv_heads=8,  # GQA factor: 4x reduction
        head_dim=128,
        attention_type=AttentionMechanism.GQA,
    ),
    "qwen2.5-32b": ModelArchitecture(
        name="Qwen-2.5-32B-Instruct",
        total_params_billion=32.5,
        active_params_billion=32.5,
        layers=64,
        hidden_size=5120,
        num_query_heads=40,
        num_kv_heads=8,  # GQA factor: 5x reduction
        head_dim=128,
        attention_type=AttentionMechanism.GQA,
    ),
    "llama3-70b": ModelArchitecture(
        name="Llama-3.1-70B-Instruct",
        total_params_billion=70.6,
        active_params_billion=70.6,
        layers=80,
        hidden_size=8192,
        num_query_heads=64,
        num_kv_heads=8,  # GQA factor: 8x reduction
        head_dim=128,
        attention_type=AttentionMechanism.GQA,
    ),
    "deepseek-v3-moe": ModelArchitecture(
        name="DeepSeek-V3-671B-MoE",
        total_params_billion=671.0,
        active_params_billion=37.0,  # 37B active parameters per token
        layers=61,
        hidden_size=7168,
        num_query_heads=128,
        num_kv_heads=128,
        head_dim=128,
        attention_type=AttentionMechanism.MLA,
        mla_latent_dim=576,  # Multi-head Latent Attention compressed KV projection
    ),
}


# ==============================================================================
# 3. CAPACITY PLANNER & ROOFLINE LATENCY SIMULATOR
# ==============================================================================

@dataclass
class SizingResult:
    model_name: str
    target_gpu: str
    weight_precision: str
    kv_precision_bytes: float
    weights_vram_gb: float
    kv_cache_total_gb: float
    activation_overhead_gb: float
    total_vram_required_gb: float
    usable_vram_per_gpu_gb: float
    required_gpus_raw: int
    optimal_gpus_tensor_parallel: int
    tensor_parallel_size: int
    pipeline_parallel_size: int
    total_nodes: int
    # Roofline Performance Outputs
    ttft_seconds: float
    tpot_ms_per_token: float
    tokens_per_second_per_user: float
    aggregate_throughput_tokens_sec: float
    hardware_hourly_cost_ondemand: float
    hardware_hourly_cost_spot: float


class LLMCapacityPlanner:
    """Computes exact physical VRAM footprint and Roofline execution bounds."""

    @staticmethod
    def calculate(
        model: ModelArchitecture,
        gpu: GPUSpec,
        precision: WeightPrecision,
        kv_cache_bytes: float,
        max_context_length: int,
        peak_concurrency: int,
        gpu_memory_utilization: float = 0.90,
        model_flops_utilization: float = 0.45,
    ) -> SizingResult:
        # 1. Memory sizing
        weights_vram_gb = (model.total_params_billion * 1e9 * precision.bytes_per_param) / (1024**3)
        bytes_per_token = model.kv_cache_bytes_per_token(kv_cache_bytes)
        total_tokens_in_flight = max_context_length * peak_concurrency
        kv_cache_total_gb = (total_tokens_in_flight * bytes_per_token) / (1024**3)

        # Activation memory during forward pass (empirical batch scaling)
        activation_overhead_gb = max(1.5, weights_vram_gb * 0.08 * math.log2(max(2, peak_concurrency)))
        total_required_vram_gb = weights_vram_gb + kv_cache_total_gb + activation_overhead_gb

        usable_vram_per_gpu = gpu.vram_gb * gpu_memory_utilization
        raw_gpus = math.ceil(total_required_vram_gb / usable_vram_per_gpu)

        # Enforce standard distributed parallel topology (power of 2 TP up to 8)
        if raw_gpus <= 1:
            tp, pp = 1, 1
        elif raw_gpus <= 2:
            tp, pp = 2, 1
        elif raw_gpus <= 4:
            tp, pp = 4, 1
        elif raw_gpus <= 8:
            tp, pp = 8, 1
        else:
            tp = 8
            pp = math.ceil(raw_gpus / 8)

        optimal_gpus = tp * pp
        gpus_per_node = 8 if optimal_gpus >= 8 else (optimal_gpus if optimal_gpus in (1, 2, 4) else 4)
        total_nodes = math.ceil(optimal_gpus / gpus_per_node)

        # 2. Roofline Performance Modeling
        # A. Prefill Phase (Compute-Bound): TTFT
        prompt_tokens = int(max_context_length * 0.80)
        prefill_flops = 2.0 * (model.active_params_billion * 1e9) * prompt_tokens
        effective_tflops = (gpu.fp16_tflops if precision in (WeightPrecision.FP16, WeightPrecision.BF16) else gpu.fp8_tflops)
        cluster_prefill_tflops = effective_tflops * optimal_gpus * model_flops_utilization * gpu.bus_penalty_factor
        ttft_seconds = max(0.015, prefill_flops / (cluster_prefill_tflops * 1e12))

        # B. Decode Phase (Memory-Bandwidth Bound): TPOT
        # In decode, weights are reloaded from HBM for each step, alongside active KV cache
        bytes_read_per_decode_step = (weights_vram_gb + (kv_cache_total_gb * (prompt_tokens / max_context_length))) * (1024**3)
        effective_bandwidth = gpu.memory_bandwidth_gb_s * optimal_gpus * (1024**3) * gpu.bus_penalty_factor
        step_time_sec = bytes_read_per_decode_step / effective_bandwidth
        tpot_ms_per_token = max(5.0, step_time_sec * 1000.0)
        tok_per_sec_per_user = 1000.0 / tpot_ms_per_token
        aggregate_throughput = tok_per_sec_per_user * peak_concurrency

        return SizingResult(
            model_name=model.name,
            target_gpu=gpu.name,
            weight_precision=precision.name,
            kv_precision_bytes=kv_cache_bytes,
            weights_vram_gb=round(weights_vram_gb, 2),
            kv_cache_total_gb=round(kv_cache_total_gb, 2),
            activation_overhead_gb=round(activation_overhead_gb, 2),
            total_vram_required_gb=round(total_required_vram_gb, 2),
            usable_vram_per_gpu_gb=round(usable_vram_per_gpu, 2),
            required_gpus_raw=raw_gpus,
            optimal_gpus_tensor_parallel=optimal_gpus,
            tensor_parallel_size=tp,
            pipeline_parallel_size=pp,
            total_nodes=total_nodes,
            ttft_seconds=round(ttft_seconds, 3),
            tpot_ms_per_token=round(tpot_ms_per_token, 2),
            tokens_per_second_per_user=round(tok_per_sec_per_user, 1),
            aggregate_throughput_tokens_sec=round(aggregate_throughput, 1),
            hardware_hourly_cost_ondemand=round(optimal_gpus * gpu.gcp_ondemand_usd_hr, 2),
            hardware_hourly_cost_spot=round(optimal_gpus * gpu.gcp_spot_usd_hr, 2),
        )


# ==============================================================================
# 4. FINOPS TCO, UNIT ECONOMICS & BREAK-EVEN CHARGEBACK ENGINE
# ==============================================================================

@dataclass
class ChargebackResult:
    monthly_active_hours: int
    is_hibernated_schedule: bool
    monthly_gpu_compute_usd: float
    monthly_cpu_management_usd: float
    monthly_persistent_storage_usd: float
    monthly_networking_egress_usd: float
    total_monthly_tco_usd: float
    effective_utilization_pct: float
    monthly_token_production_millions: float
    cost_per_1m_input_tokens_usd: float
    cost_per_1m_output_tokens_usd: float
    cost_per_1m_cached_tokens_usd: float
    billed_price_1m_input_usd: float
    billed_price_1m_output_usd: float
    billed_price_1m_cached_usd: float
    commercial_margin_pct: float
    break_even_tokens_vs_gpt4o_millions: float
    break_even_tokens_vs_claude35_millions: float
    annual_savings_vs_frontier_api_usd: float


class LLMChargebackEngine:
    """Computes exact TCO, token pricing under bandwidth asymmetry, and break-even."""

    @staticmethod
    def calculate(
        sizing: SizingResult,
        use_spot_pricing: bool = False,
        active_hours_per_day: int = 11,
        active_days_per_month: int = 22,
        effective_utilization_pct: float = 30.0,
        storage_disk_gb: int = 250,
        commercial_margin_pct: float = 20.0,
        estimated_monthly_egress_tb: float = 0.5,
    ) -> ChargebackResult:
        # Duty cycle calculation: 24/7 = 730h vs Enterprise business hours + hibernation
        if active_hours_per_day >= 24:
            monthly_active_hours = 730
            is_hibernated = False
        else:
            monthly_active_hours = active_hours_per_day * active_days_per_month
            is_hibernated = True

        gpu_rate = sizing.hardware_hourly_cost_spot if use_spot_pricing else sizing.hardware_hourly_cost_ondemand
        monthly_gpu_compute = gpu_rate * monthly_active_hours

        # Orchestration (e2-standard-4 node for LiteLLM Gateway, PostgreSQL, Observability)
        cpu_mgmt_hourly_usd = 0.134
        monthly_cpu_management = cpu_mgmt_hourly_usd * monthly_active_hours

        # Storage (Zonal SSD pd-ssd @ $0.17/GB-month, preserved 24/7)
        monthly_storage = storage_disk_gb * 0.17

        # Egress Network ($0.08/GB)
        monthly_egress = estimated_monthly_egress_tb * 1024.0 * 0.08

        total_monthly_tco = monthly_gpu_compute + monthly_cpu_management + monthly_storage + monthly_egress

        # Monthly Token Generation Capacity
        util_factor = effective_utilization_pct / 100.0
        seconds_active = monthly_active_hours * 3600.0
        total_monthly_tokens = sizing.aggregate_throughput_tokens_sec * seconds_active * util_factor
        total_tokens_millions = max(1.0, total_monthly_tokens / 1e6)

        # Asymmetric Memory-Bandwidth Pricing: Output token costs 3.0x input token
        # Enterprise ratio: 3 input tokens per 1 output token (3:1 ratio)
        input_token_share = 0.75
        output_token_share = 0.25
        weighted_tokens = (total_monthly_tokens * input_token_share * 1.0) + (total_monthly_tokens * output_token_share * 3.0)

        base_unit_cost = total_monthly_tco / max(1.0, weighted_tokens)
        cost_input_1m = base_unit_cost * 1.0 * 1_000_000
        cost_output_1m = base_unit_cost * 3.0 * 1_000_000
        cost_cached_1m = cost_input_1m * 0.20  # 80% discount on cache hit

        margin_mult = 1.0 + (commercial_margin_pct / 100.0)
        billed_input_1m = cost_input_1m * margin_mult
        billed_output_1m = cost_output_1m * margin_mult
        billed_cached_1m = cost_cached_1m * margin_mult

        # Break-Even Comparison against Frontier APIs (Blended 3:1 input:output)
        # GPT-4o: $2.50 / $10.00 -> Blended = (2.50 * 0.75) + (10.00 * 0.25) = $4.375 / 1M
        gpt4o_blended_1m = 4.375
        claude35_blended_1m = (3.00 * 0.75) + (15.00 * 0.25)  # $6.00 / 1M

        break_even_gpt4o = total_monthly_tco / (gpt4o_blended_1m / 1e6) / 1e6
        break_even_claude35 = total_monthly_tco / (claude35_blended_1m / 1e6) / 1e6

        # Annual savings at current capacity vs GPT-4o
        public_api_monthly_equivalent = (total_tokens_millions * gpt4o_blended_1m)
        annual_savings = max(0.0, (public_api_monthly_equivalent - total_monthly_tco) * 12.0)

        return ChargebackResult(
            monthly_active_hours=monthly_active_hours,
            is_hibernated_schedule=is_hibernated,
            monthly_gpu_compute_usd=round(monthly_gpu_compute, 2),
            monthly_cpu_management_usd=round(monthly_cpu_management, 2),
            monthly_persistent_storage_usd=round(monthly_storage, 2),
            monthly_networking_egress_usd=round(monthly_egress, 2),
            total_monthly_tco_usd=round(total_monthly_tco, 2),
            effective_utilization_pct=effective_utilization_pct,
            monthly_token_production_millions=round(total_tokens_millions, 2),
            cost_per_1m_input_tokens_usd=round(cost_input_1m, 4),
            cost_per_1m_output_tokens_usd=round(cost_output_1m, 4),
            cost_per_1m_cached_tokens_usd=round(cost_cached_1m, 4),
            billed_price_1m_input_usd=round(billed_input_1m, 4),
            billed_price_1m_output_usd=round(billed_output_1m, 4),
            billed_price_1m_cached_usd=round(billed_cached_1m, 4),
            commercial_margin_pct=commercial_margin_pct,
            break_even_tokens_vs_gpt4o_millions=round(break_even_gpt4o, 2),
            break_even_tokens_vs_claude35_millions=round(break_even_claude35, 2),
            annual_savings_vs_frontier_api_usd=round(annual_savings, 2),
        )


# ==============================================================================
# 5. CLI EXECUTIVE REPORT FORMATTER
# ==============================================================================

def render_executive_report(sizing: SizingResult, chargeback: ChargebackResult) -> None:
    sep = "=" * 80
    sub_sep = "-" * 80
    print(sep)
    print("  ENTERPRISE TIER-1 INFERENCE CAPACITY PLANNING & FINOPS AUDIT REPORT")
    print(sep)
    print(f" Target Model:            {sizing.model_name}")
    print(f" Weight Precision:        {sizing.weight_precision}")
    print(f" Target Silicion:         {sizing.target_gpu}")
    print(sub_sep)
    print(" 1. PHYSICAL MEMORY ALLOCATION (VRAM FOOTPRINT)")
    print(f"    - Base Model Weights:             {sizing.weights_vram_gb:8.2f} GB (Immutable Resident)")
    print(f"    - KV Cache Buffer (PagedAttn):    {sizing.kv_cache_total_gb:8.2f} GB (Elastic Pool)")
    print(f"    - Activation Overhead:            {sizing.activation_overhead_gb:8.2f} GB (Peak Forward Pass)")
    print(f"    - Total Cluster VRAM Needed:      {sizing.total_vram_required_gb:8.2f} GB")
    print(f"    -> RECOMMENDED CLUSTER TOPOLOGY:  {sizing.optimal_gpus_tensor_parallel}x GPUs across {sizing.total_nodes} node(s)")
    print(f"       Parallel Distribution:         Tensor Parallel (TP={sizing.tensor_parallel_size}), Pipeline Parallel (PP={sizing.pipeline_parallel_size})")
    print(sub_sep)
    print(" 2. ROOFLINE INFERENCE PERFORMANCE (SLA SIMULATION)")
    print(f"    - TTFT (Time to First Token):     {sizing.ttft_seconds:8.3f} s  (Compute-Bound Prefill)")
    print(f"    - TPOT (Time per Output Token):   {sizing.tpot_ms_per_token:8.2f} ms (Memory-Bandwidth Bound)")
    print(f"    - Interactive Speed per User:     {sizing.tokens_per_second_per_user:8.1f} tokens/s")
    print(f"    - Aggregate Cluster Throughput:   {sizing.aggregate_throughput_tokens_sec:8.1f} tokens/s under peak concurrency")
    print(sub_sep)
    print(" 3. FINOPS TOTAL COST OF OWNERSHIP (TCO) & CHARGEBACK ECONOMICS")
    print(f"    - Monthly Operational Schedule:   {chargeback.monthly_active_hours} hours/month (Hibernated: {chargeback.is_hibernated_schedule})")
    print(f"    - GPU Compute Cost:               ${chargeback.monthly_gpu_compute_usd:9.2f} / month")
    print(f"    - Management Node (CPU/Gateway):  ${chargeback.monthly_cpu_management_usd:9.2f} / month")
    print(f"    - Persistent Storage (Weights/DB):${chargeback.monthly_persistent_storage_usd:9.2f} / month")
    print(f"    - Network Egress:                 ${chargeback.monthly_networking_egress_usd:9.2f} / month")
    print(f"    ----------------------------------------------------------------------------")
    print(f"    -> TOTAL MONTHLY TCO:             ${chargeback.total_monthly_tco_usd:9.2f} / month")
    print(f"    - Token Production Capacity:      {chargeback.monthly_token_production_millions:9.2f} Million tokens/month ({chargeback.effective_utilization_pct}% duty cycle)")
    print(sub_sep)
    print(" 4. DEPARTMENTAL BILLING RATES (ASYMMETRIC PRICING SCHEDULE)")
    print(f"    - Cost Price (Input 1M tokens):   ${chargeback.cost_per_1m_input_tokens_usd:9.4f}")
    print(f"    - Cost Price (Output 1M tokens):  ${chargeback.cost_per_1m_output_tokens_usd:9.4f} (3.0x bandwidth penalty)")
    print(f"    - Cost Price (Cached 1M tokens):  ${chargeback.cost_per_1m_cached_tokens_usd:9.4f} (80% prompt caching discount)")
    print(f"    -> BILLED TO DEPARTMENTS (+{chargeback.commercial_margin_pct:.0f}%):")
    print(f"       * Input Tokens Rate:           ${chargeback.billed_price_1m_input_usd:9.4f} / 1M tokens")
    print(f"       * Output Tokens Rate:          ${chargeback.billed_price_1m_output_usd:9.4f} / 1M tokens")
    print(f"       * Prompt Cache Hit Rate:       ${chargeback.billed_price_1m_cached_usd:9.4f} / 1M tokens")
    print(sub_sep)
    print(" 5. FRONTIER API BREAK-EVEN ANALYSIS (ROI VS PUBLIC APIS)")
    print(f"    - Break-even vs OpenAI GPT-4o:    {chargeback.break_even_tokens_vs_gpt4o_millions:9.2f} M tokens/month")
    print(f"    - Break-even vs Claude 3.5 Sonnet:{chargeback.break_even_tokens_vs_claude35_millions:9.2f} M tokens/month")
    print(f"    -> ESTIMATED ANNUAL SAVINGS:      ${chargeback.annual_savings_vs_frontier_api_usd:9.2f} / year vs OpenAI API")
    print(sep)


def main() -> None:
    parser = argparse.ArgumentParser(description="Tier-1 Enterprise LLM Inference FinOps & Sizing Planner")
    parser.add_argument("--model", choices=list(MODEL_PRESETS.keys()), default="mistral-7b", help="Model architecture preset")
    parser.add_argument("--gpu", choices=list(GPU_CATALOG.keys()), default="NVIDIA_L4", help="Target NVIDIA GPU hardware")
    parser.add_argument("--precision", choices=["FP16", "BF16", "FP8", "INT8", "INT4"], default="FP16", help="Weight precision")
    parser.add_argument("--kv-bytes", type=float, default=2.0, help="Bytes per KV cache value (2.0=FP16, 1.0=FP8)")
    parser.add_argument("--context", type=int, default=4096, help="Maximum context window per request")
    parser.add_argument("--concurrency", type=int, default=24, help="Peak concurrent user requests")
    parser.add_argument("--hours-per-day", type=int, default=11, help="Active hours per day (default 11 for corporate schedule, 24 for 24/7)")
    parser.add_argument("--days-per-month", type=int, default=22, help="Active days per month (default 22 for business days, 30 for continuous)")
    parser.add_argument("--utilization", type=float, default=30.0, help="Effective GPU active utilization percentage (default 30%%)")
    parser.add_argument("--spot", action="store_true", help="Use GCP Spot GPU pricing instead of On-Demand")
    parser.add_argument("--margin", type=float, default=20.0, help="Commercial profit margin percentage")
    parser.add_argument("--json", action="store_true", help="Output raw JSON format for programmatic ingestion")

    args = parser.parse_args()

    model_spec = MODEL_PRESETS[args.model]
    gpu_spec = GPU_CATALOG[args.gpu]
    precision_enum = WeightPrecision[args.precision]

    sizing = LLMCapacityPlanner.calculate(
        model=model_spec,
        gpu=gpu_spec,
        precision=precision_enum,
        kv_cache_bytes=args.kv_bytes,
        max_context_length=args.context,
        peak_concurrency=args.concurrency,
    )

    chargeback = LLMChargebackEngine.calculate(
        sizing=sizing,
        use_spot_pricing=args.spot,
        active_hours_per_day=args.hours_per_day,
        active_days_per_month=args.days_per_month,
        effective_utilization_pct=args.utilization,
        commercial_margin_pct=args.margin,
    )

    if args.json:
        payload = {
            "sizing": asdict(sizing),
            "chargeback": asdict(chargeback),
        }
        print(json.dumps(payload, indent=2))
    else:
        render_executive_report(sizing, chargeback)


if __name__ == "__main__":
    main()
