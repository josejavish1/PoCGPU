"""LLM Workload and Roofline Simulation Value Objects."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Optional

from src.domain.models.validation import assert_strict_decimal


class AttentionType(str, Enum):
    MHA = "MHA"
    GQA = "GQA"
    MLA = "MLA"


class QuantizationPrecision(str, Enum):
    FP32 = "FP32"
    FP16 = "FP16"
    BF16 = "BF16"
    FP8 = "FP8"
    INT8 = "INT8"
    FP6 = "FP6"
    INT4 = "INT4"
    NF4 = "NF4"
    AWQ = "AWQ"
    GPTQ = "GPTQ"
    GGUF = "GGUF"
    CUSTOM = "CUSTOM"


@dataclass(frozen=True)
class LlmWorkloadProfile:
    """Enterprise LLM model architecture and production traffic profile."""

    model_id: str
    display_name: str
    total_params_billion: Decimal
    active_params_billion: Decimal
    layers: int
    hidden_size: int
    num_query_heads: int
    num_kv_heads: int
    head_dim: int
    attention_type: AttentionType
    mla_latent_dim: Optional[int]
    quantization: QuantizationPrecision
    weights_bytes_per_param: Decimal       # Declared dynamically from model profile (e.g. 2.0 for FP16, 0.55 for INT4)
    kv_cache_bytes_per_value: Decimal      # Bytes per KV cache element (e.g. 2.0 for FP16, 1.0 for FP8)
    max_context_length: int
    peak_concurrent_users: int
    avg_prompt_tokens: int
    avg_generated_tokens: int
    baseline_rps: Decimal
    peak_burst_rps: Decimal
    target_ttft_seconds: Decimal
    target_tpot_ms: Decimal

    def __post_init__(self) -> None:
        if (
            isinstance(self.layers, bool) or not isinstance(self.layers, int) or self.layers <= 0
            or isinstance(self.hidden_size, bool) or not isinstance(self.hidden_size, int) or self.hidden_size <= 0
            or isinstance(self.num_query_heads, bool) or not isinstance(self.num_query_heads, int) or self.num_query_heads <= 0
            or isinstance(self.head_dim, bool) or not isinstance(self.head_dim, int) or self.head_dim <= 0
        ):
            raise ValueError(f"Model '{self.model_id}' architecture dimensions must be strictly positive integers.")

        assert_strict_decimal(self.total_params_billion, "total_params_billion")
        assert_strict_decimal(self.active_params_billion, "active_params_billion")
        assert_strict_decimal(self.weights_bytes_per_param, "weights_bytes_per_param")
        assert_strict_decimal(self.kv_cache_bytes_per_value, "kv_cache_bytes_per_value")
        assert_strict_decimal(self.baseline_rps, "baseline_rps")
        assert_strict_decimal(self.peak_burst_rps, "peak_burst_rps")
        assert_strict_decimal(self.target_ttft_seconds, "target_ttft_seconds")
        assert_strict_decimal(self.target_tpot_ms, "target_tpot_ms")

        if self.total_params_billion <= Decimal("0") or self.active_params_billion <= Decimal("0"):
            raise ValueError(f"Model '{self.model_id}' parameter counts must be strictly positive.")

        if self.active_params_billion > self.total_params_billion:
            raise ValueError(
                f"Model '{self.model_id}' active parameters ({self.active_params_billion}B) "
                f"cannot exceed total parameters ({self.total_params_billion}B)."
            )

        if self.weights_bytes_per_param <= Decimal("0") or self.kv_cache_bytes_per_value <= Decimal("0"):
            raise ValueError(f"Model '{self.model_id}' quantization bytes per value must be strictly positive.")

        if (
            isinstance(self.max_context_length, bool) or not isinstance(self.max_context_length, int) or self.max_context_length <= 0
            or isinstance(self.peak_concurrent_users, bool) or not isinstance(self.peak_concurrent_users, int) or self.peak_concurrent_users <= 0
            or isinstance(self.avg_prompt_tokens, bool) or not isinstance(self.avg_prompt_tokens, int) or self.avg_prompt_tokens <= 0
            or isinstance(self.avg_generated_tokens, bool) or not isinstance(self.avg_generated_tokens, int) or self.avg_generated_tokens <= 0
        ):
            raise ValueError(
                f"Model '{self.model_id}' context length, concurrency, and token counts must be strictly positive integers."
            )

        if self.avg_prompt_tokens + self.avg_generated_tokens > self.max_context_length:
            raise ValueError(
                f"Model '{self.model_id}' total average tokens ({self.avg_prompt_tokens + self.avg_generated_tokens}) "
                f"cannot exceed max_context_length ({self.max_context_length})."
            )

        if self.baseline_rps <= Decimal("0") or self.peak_burst_rps < self.baseline_rps:
            raise ValueError(
                f"Model '{self.model_id}' traffic invariant violated: "
                f"peak_burst_rps ({self.peak_burst_rps}) must be >= baseline_rps ({self.baseline_rps}) > 0."
            )

        if self.target_ttft_seconds <= Decimal("0") or self.target_tpot_ms <= Decimal("0"):
            raise ValueError(f"Model '{self.model_id}' SLA latency targets must be strictly positive.")

        if self.attention_type == AttentionType.MLA:
            if self.mla_latent_dim is None or isinstance(self.mla_latent_dim, bool) or not isinstance(self.mla_latent_dim, int) or self.mla_latent_dim <= 0:
                raise ValueError(
                    f"Invalid model configuration for '{self.model_id}': "
                    "AttentionType.MLA requires a strictly positive integer mla_latent_dim."
                )
        else:
            if isinstance(self.num_kv_heads, bool) or not isinstance(self.num_kv_heads, int) or self.num_kv_heads <= 0 or (self.num_query_heads % self.num_kv_heads != 0):
                raise ValueError(
                    f"Invalid model configuration for '{self.model_id}': "
                    "num_kv_heads must be positive integer and evenly divide num_query_heads."
                )

    def compute_kv_cache_bytes_per_token(self) -> Decimal:
        """Computes exact memory consumed by 1 token in the KV cache across all layers.

        Note: Multi-Head Latent Attention (MLA, DeepSeek-V2/V3) compresses K and V jointly
        into a single shared latent vector per token, hence multiplier is 1 (not 2).
        Standard MHA/GQA stores separate Key and Value tensors, hence multiplier is 2.
        """
        if self.attention_type == AttentionType.MLA and self.mla_latent_dim:
            return Decimal(self.layers * self.mla_latent_dim) * self.kv_cache_bytes_per_value
        else:
            return Decimal(2 * self.layers * self.num_kv_heads * self.head_dim) * self.kv_cache_bytes_per_value


@dataclass(frozen=True)
class RooflineSimulationResult:
    """Roofline compute and memory-bandwidth bound simulation result with consistent ratio units."""

    chassis_or_instance_id: str
    tensor_parallel_degree: int
    pipeline_parallel_degree: int
    required_cluster_nodes_baseline: int
    model_weights_vram_gb: Decimal
    kv_cache_total_vram_gb: Decimal
    activation_buffer_vram_gb: Decimal
    total_required_vram_gb: Decimal
    cluster_total_vram_pool_gb: Decimal
    vram_utilization_ratio: Decimal              # Normalized in [0.0, 1.0]
    ttft_seconds: Decimal
    tpot_ms_per_token: Decimal
    tokens_per_second_per_user: Decimal
    aggregate_cluster_throughput_tok_s: Decimal
    memory_bus_utilization_ratio: Decimal        # Normalized in [0.0, 1.0]
    model_flops_utilization_ratio: Decimal       # Normalized in [0.0, 1.0]
    is_memory_bound: bool
    is_ttft_sla_met: bool = True
    is_tpot_sla_met: bool = True

    def __post_init__(self) -> None:
        if isinstance(self.tensor_parallel_degree, bool) or not isinstance(self.tensor_parallel_degree, int) or self.tensor_parallel_degree <= 0:
            raise ValueError(f"tensor_parallel_degree must be positive integer, got {self.tensor_parallel_degree}.")
        if isinstance(self.pipeline_parallel_degree, bool) or not isinstance(self.pipeline_parallel_degree, int) or self.pipeline_parallel_degree <= 0:
            raise ValueError(f"pipeline_parallel_degree must be positive integer, got {self.pipeline_parallel_degree}.")
        if isinstance(self.required_cluster_nodes_baseline, bool) or not isinstance(self.required_cluster_nodes_baseline, int) or self.required_cluster_nodes_baseline <= 0:
            raise ValueError(f"required_cluster_nodes_baseline must be positive integer, got {self.required_cluster_nodes_baseline}.")

        assert_strict_decimal(self.model_weights_vram_gb, "model_weights_vram_gb")
        assert_strict_decimal(self.kv_cache_total_vram_gb, "kv_cache_total_vram_gb")
        assert_strict_decimal(self.activation_buffer_vram_gb, "activation_buffer_vram_gb")
        assert_strict_decimal(self.total_required_vram_gb, "total_required_vram_gb")
        assert_strict_decimal(self.cluster_total_vram_pool_gb, "cluster_total_vram_pool_gb")
        assert_strict_decimal(self.vram_utilization_ratio, "vram_utilization_ratio")
        assert_strict_decimal(self.ttft_seconds, "ttft_seconds")
        assert_strict_decimal(self.tpot_ms_per_token, "tpot_ms_per_token")
        assert_strict_decimal(self.tokens_per_second_per_user, "tokens_per_second_per_user")
        assert_strict_decimal(self.aggregate_cluster_throughput_tok_s, "aggregate_cluster_throughput_tok_s")
        assert_strict_decimal(self.memory_bus_utilization_ratio, "memory_bus_utilization_ratio")
        assert_strict_decimal(self.model_flops_utilization_ratio, "model_flops_utilization_ratio")

        if not (Decimal("0") <= self.vram_utilization_ratio <= Decimal("1.0")):
            raise ValueError(f"vram_utilization_ratio must be in [0, 1], got {self.vram_utilization_ratio}.")
        if not (Decimal("0") <= self.memory_bus_utilization_ratio <= Decimal("1.0")):
            raise ValueError(f"memory_bus_utilization_ratio must be in [0, 1], got {self.memory_bus_utilization_ratio}.")
        if not (Decimal("0") <= self.model_flops_utilization_ratio <= Decimal("1.0")):
            raise ValueError(f"model_flops_utilization_ratio must be in [0, 1], got {self.model_flops_utilization_ratio}.")
