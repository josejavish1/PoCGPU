"""Roofline Physics Engine for Distributed LLM Inference Sizing."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_EVEN

from src.domain.models.hardware import HardwareAcceleratorSpec
from src.domain.models.validation import assert_strict_decimal, decimal_ceil_div
from src.domain.models.workload import (
    AttentionType,
    LlmWorkloadProfile,
    QuantizationPrecision,
    RooflineSimulationResult,
)
from src.domain.ports.roofline_simulation import RooflineSimulationPort


@dataclass(frozen=True)
class RooflinePhysicsPolicy:
    """Tunable computer architecture constants for distributed LLM inference simulation."""

    bytes_per_gibibyte: Decimal = Decimal("1073741824")
    bytes_per_gigabyte_sec: Decimal = Decimal("1000000000")
    gflops_per_tflops: Decimal = Decimal("1000")
    tflops_scale_factor: Decimal = Decimal("1000000000000")
    activation_bytes_per_element: Decimal = Decimal("2.0")
    active_batch_max_tokens: int = 4096
    microbatch_tokens_per_user: int = 32
    cuda_context_overhead_gb: Decimal = Decimal("1.0000")
    kv_headroom_rebuild_buffer_gb: Decimal = Decimal("2.0000")
    min_kv_headroom_floor_gb: Decimal = Decimal("0.1000")
    baseline_mfu_ratio: Decimal = Decimal("0.4500")
    baseline_mbu_ratio: Decimal = Decimal("0.6500")
    mac_flops_per_token_param: Decimal = Decimal("2.0")
    one_billion_scale: Decimal = Decimal("1000000000")
    two_billion_scale: Decimal = Decimal("2000000000")
    milliseconds_per_second: Decimal = Decimal("1000")
    min_latency_ms_floor: Decimal = Decimal("0.001")

    def __post_init__(self) -> None:
        assert_strict_decimal(self.bytes_per_gibibyte, "bytes_per_gibibyte")
        assert_strict_decimal(self.bytes_per_gigabyte_sec, "bytes_per_gigabyte_sec")
        assert_strict_decimal(self.gflops_per_tflops, "gflops_per_tflops")
        assert_strict_decimal(self.tflops_scale_factor, "tflops_scale_factor")
        assert_strict_decimal(self.activation_bytes_per_element, "activation_bytes_per_element")
        assert_strict_decimal(self.cuda_context_overhead_gb, "cuda_context_overhead_gb")
        assert_strict_decimal(self.kv_headroom_rebuild_buffer_gb, "kv_headroom_rebuild_buffer_gb")
        assert_strict_decimal(self.min_kv_headroom_floor_gb, "min_kv_headroom_floor_gb")
        assert_strict_decimal(self.baseline_mfu_ratio, "baseline_mfu_ratio")
        assert_strict_decimal(self.baseline_mbu_ratio, "baseline_mbu_ratio")
        assert_strict_decimal(self.mac_flops_per_token_param, "mac_flops_per_token_param")
        assert_strict_decimal(self.one_billion_scale, "one_billion_scale")
        assert_strict_decimal(self.two_billion_scale, "two_billion_scale")
        assert_strict_decimal(self.milliseconds_per_second, "milliseconds_per_second")
        assert_strict_decimal(self.min_latency_ms_floor, "min_latency_ms_floor")

        if (
            self.bytes_per_gibibyte <= Decimal("0")
            or self.bytes_per_gigabyte_sec <= Decimal("0")
            or self.gflops_per_tflops <= Decimal("0")
            or self.tflops_scale_factor <= Decimal("0")
            or self.activation_bytes_per_element <= Decimal("0")
            or self.cuda_context_overhead_gb < Decimal("0")
            or self.kv_headroom_rebuild_buffer_gb < Decimal("0")
            or self.min_kv_headroom_floor_gb <= Decimal("0")
            or not (Decimal("0") < self.baseline_mfu_ratio <= Decimal("1.0"))
            or not (Decimal("0") < self.baseline_mbu_ratio <= Decimal("1.0"))
        ):
            raise ValueError("RooflinePhysicsPolicy physical and efficiency constants must be strictly positive.")

        if isinstance(self.active_batch_max_tokens, bool) or not isinstance(self.active_batch_max_tokens, int) or self.active_batch_max_tokens <= 0:
            raise ValueError(f"active_batch_max_tokens must be a positive integer, got {self.active_batch_max_tokens}.")
        if isinstance(self.microbatch_tokens_per_user, bool) or not isinstance(self.microbatch_tokens_per_user, int) or self.microbatch_tokens_per_user <= 0:
            raise ValueError(f"microbatch_tokens_per_user must be a positive integer, got {self.microbatch_tokens_per_user}.")


class RooflinePhysicsEngine(RooflineSimulationPort):
    """Deterministic Roofline model for LLM VRAM allocation, distributed parallelism, and latency."""

    def __init__(self, policy: RooflinePhysicsPolicy | None = None) -> None:
        self._policy = policy or RooflinePhysicsPolicy()

    def simulate_roofline(
        self,
        candidate_id: str,
        workload: LlmWorkloadProfile,
        accelerator: HardwareAcceleratorSpec,
        accelerators_per_node: int,
        max_vram_utilization_ratio: Decimal,
    ) -> RooflineSimulationResult:
        """Calculates physical memory footprints, distributed sharding, and latency bounds."""
        if not candidate_id or not candidate_id.strip():
            raise ValueError("Candidate identifier must be a non-empty string.")
        if isinstance(accelerators_per_node, bool) or not isinstance(accelerators_per_node, int) or accelerators_per_node <= 0:
            raise ValueError(f"accelerators_per_node must be a positive integer, got {accelerators_per_node}.")
        assert_strict_decimal(max_vram_utilization_ratio, "max_vram_utilization_ratio")
        if not (Decimal("0") < max_vram_utilization_ratio <= Decimal("1.0")):
            raise ValueError(
                f"max_vram_utilization_ratio must be in range (0.0, 1.0], got {max_vram_utilization_ratio}."
            )

        p = self._policy

        # 1. Model Weights Footprint
        raw_weights_bytes = (
            workload.total_params_billion * p.one_billion_scale * workload.weights_bytes_per_param
        )
        weights_vram_gb = (raw_weights_bytes / p.bytes_per_gibibyte).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_EVEN
        )

        # 2. KV Cache Footprint across all active concurrent sequences
        bytes_per_token = workload.compute_kv_cache_bytes_per_token()
        total_cluster_tokens = workload.peak_concurrent_users * (
            workload.avg_prompt_tokens + workload.avg_generated_tokens
        )
        kv_cache_vram_gb = (
            (Decimal(total_cluster_tokens) * bytes_per_token) / p.bytes_per_gibibyte
        ).quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN)

        # 3. Activation Buffer Footprint (continuous batching micro-batch forward pass)
        active_tokens = min(
            workload.peak_concurrent_users * p.microbatch_tokens_per_user,
            p.active_batch_max_tokens,
        )
        activation_vram_gb = (
            (Decimal(active_tokens) * Decimal(workload.hidden_size) * p.activation_bytes_per_element)
            / p.bytes_per_gibibyte
            + p.cuda_context_overhead_gb
        ).quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN)

        # 4. Single-node usable VRAM & Dynamic Tensor Parallelism derivation
        # In GQA/MHA, ensure clean KV head divisibility without splitting attention heads improperly
        candidate_tps = sorted(
            [
                d for d in range(1, accelerators_per_node + 1)
                if (accelerators_per_node % d == 0)
                and (workload.num_query_heads % d == 0)
                and (workload.attention_type == AttentionType.MLA or workload.num_kv_heads % d == 0 or d % workload.num_kv_heads == 0)
            ],
            reverse=True,
        )
        tp_degree = candidate_tps[0] if candidate_tps else 1

        single_accel_usable_vram = accelerator.vram_gb * max_vram_utilization_ratio
        single_node_usable_vram = single_accel_usable_vram * Decimal(tp_degree)

        # Nodes needed to shard a single model copy (Pipeline Parallelism) using pure Decimal ceiling
        pp_degree = max(1, decimal_ceil_div(weights_vram_gb, single_node_usable_vram))
        nodes_per_replica = pp_degree

        # KV capacity per replica after deducting weights and activation
        replica_usable_vram = single_node_usable_vram * Decimal(nodes_per_replica)
        replica_kv_headroom = replica_usable_vram - weights_vram_gb - activation_vram_gb

        if replica_kv_headroom <= Decimal("0"):
            needed_vram = weights_vram_gb + activation_vram_gb + p.kv_headroom_rebuild_buffer_gb
            nodes_per_replica = max(nodes_per_replica + 1, decimal_ceil_div(needed_vram, single_node_usable_vram))
            pp_degree = nodes_per_replica
            replica_usable_vram = single_node_usable_vram * Decimal(nodes_per_replica)
            replica_kv_headroom = replica_usable_vram - weights_vram_gb - activation_vram_gb

        # 5. Quantization-Aware Silicon Compute Selection
        if workload.quantization == QuantizationPrecision.FP8 and accelerator.fp8_tflops > Decimal("0"):
            selected_silicon_tflops = accelerator.fp8_tflops
        elif (
            workload.quantization in (
                QuantizationPrecision.INT8,
                QuantizationPrecision.INT4,
                QuantizationPrecision.AWQ,
                QuantizationPrecision.GPTQ,
            )
            and accelerator.int8_tops > Decimal("0")
        ):
            selected_silicon_tflops = accelerator.int8_tops
        else:
            selected_silicon_tflops = accelerator.fp16_tflops

        active_weights_bytes = (
            workload.active_params_billion * p.one_billion_scale * workload.weights_bytes_per_param
        )
        single_replica_accelerators = nodes_per_replica * tp_degree

        replica_eff_tflops = (
            selected_silicon_tflops
            * accelerator.tensor_parallel_efficiency_factor
            * Decimal(single_replica_accelerators)
        )
        replica_eff_bw_gbps = (
            accelerator.memory_bandwidth_gbps
            * accelerator.tensor_parallel_efficiency_factor
            * Decimal(single_replica_accelerators)
        )

        # In pipeline parallelism decode, instantaneous weight streaming is bounded by TP degree across stages
        decode_stage_bw_gbps = (
            accelerator.memory_bandwidth_gbps
            * accelerator.tensor_parallel_efficiency_factor
            * Decimal(tp_degree)
        )

        # Single-replica decode capacity estimate for sizing (including context KV reads)
        avg_active_context_tokens = Decimal(workload.avg_prompt_tokens) + (Decimal(workload.avg_generated_tokens) / p.mac_flops_per_token_param)
        nominal_kv_bytes_per_step = Decimal(workload.peak_concurrent_users) * avg_active_context_tokens * bytes_per_token
        single_replica_bytes_per_step = active_weights_bytes + nominal_kv_bytes_per_step
        nominal_effective_decode_bytes_sec = decode_stage_bw_gbps * p.bytes_per_gigabyte_sec * p.baseline_mbu_ratio
        single_replica_tpot_sec = single_replica_bytes_per_step / nominal_effective_decode_bytes_sec
        single_replica_tok_per_sec = Decimal("1.0") / max(Decimal("0.0001"), single_replica_tpot_sec)
        single_replica_aggregate_tok_s = single_replica_tok_per_sec * Decimal(workload.peak_concurrent_users)

        # Throughput SLA requirement based on sustained baseline queries
        required_baseline_tok_s = workload.baseline_rps * Decimal(workload.avg_generated_tokens)
        dp_replicas_throughput = max(1, decimal_ceil_div(required_baseline_tok_s, max(Decimal("1.0"), single_replica_aggregate_tok_s)))

        # Data Parallel (DP) replicas needed to absorb total KV cache demand AND meet throughput SLA
        dp_replicas_vram = max(
            1,
            decimal_ceil_div(kv_cache_vram_gb, max(p.min_kv_headroom_floor_gb, replica_kv_headroom)),
        )
        dp_replicas = max(dp_replicas_vram, dp_replicas_throughput)

        # Intra-node replicas packing if accelerators_per_node >= tp_degree * nodes_per_replica
        intra_node_replicas = max(1, accelerators_per_node // (tp_degree * nodes_per_replica))
        required_nodes = decimal_ceil_div(Decimal(dp_replicas), Decimal(intra_node_replicas)) * nodes_per_replica
        total_cluster_accelerators = required_nodes * accelerators_per_node

        cluster_total_vram_pool_gb = (
            accelerator.vram_gb * Decimal(total_cluster_accelerators)
        ).quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN)

        total_weights_cluster_vram = weights_vram_gb * Decimal(dp_replicas)
        total_required_vram_gb = (
            total_weights_cluster_vram + kv_cache_vram_gb + (activation_vram_gb * Decimal(dp_replicas))
        ).quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN)

        vram_utilization_ratio = min(
            Decimal("1.0000"),
            (total_required_vram_gb / cluster_total_vram_pool_gb).quantize(
                Decimal("0.0001"), rounding=ROUND_HALF_EVEN
            ),
        )

        cluster_eff_bw_gbps = (
            accelerator.memory_bandwidth_gbps
            * accelerator.tensor_parallel_efficiency_factor
            * Decimal(total_cluster_accelerators)
        )

        # Prefill Time to First Token (TTFT)
        prefill_flops = (
            Decimal(workload.avg_prompt_tokens) * workload.active_params_billion * p.two_billion_scale
        )
        effective_prefill_flops_sec = replica_eff_tflops * p.tflops_scale_factor * p.baseline_mfu_ratio
        ttft_seconds = (prefill_flops / effective_prefill_flops_sec).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_EVEN
        )

        # Decode Time Per Output Token (TPOT)
        # Accurately includes active sequence context KV cache read per decode step
        users_per_replica = max(1, decimal_ceil_div(Decimal(workload.peak_concurrent_users), Decimal(dp_replicas)))
        avg_active_context_tokens = Decimal(workload.avg_prompt_tokens) + (Decimal(workload.avg_generated_tokens) / p.mac_flops_per_token_param)
        kv_bytes_per_decode_step = Decimal(users_per_replica) * avg_active_context_tokens * bytes_per_token
        bytes_per_decode_step = active_weights_bytes + kv_bytes_per_decode_step
        effective_decode_bytes_sec = decode_stage_bw_gbps * p.bytes_per_gigabyte_sec * p.baseline_mbu_ratio

        tpot_seconds = bytes_per_decode_step / effective_decode_bytes_sec
        tpot_ms_per_token = (tpot_seconds * p.milliseconds_per_second).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_EVEN
        )

        tokens_per_second_per_user = (
            p.milliseconds_per_second / max(p.min_latency_ms_floor, tpot_ms_per_token)
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)

        aggregate_cluster_throughput_tok_s = (
            tokens_per_second_per_user * Decimal(workload.peak_concurrent_users)
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)

        # 6. Physical Memory Bus Utilization Ratio (Non-Tautological, Non-Inflated Continuous Batch Sizing)
        actual_demanded_tokens_sec = min(
            workload.peak_burst_rps * Decimal(workload.avg_generated_tokens),
            aggregate_cluster_throughput_tok_s,
        )
        decode_steps_per_sec = actual_demanded_tokens_sec / Decimal(max(1, workload.peak_concurrent_users))
        actual_bus_bandwidth_demand = decode_steps_per_sec * bytes_per_decode_step * Decimal(dp_replicas)
        total_bus_bandwidth_capacity = cluster_eff_bw_gbps * p.bytes_per_gigabyte_sec

        memory_bus_utilization_ratio = min(
            Decimal("1.0000"),
            (actual_bus_bandwidth_demand / total_bus_bandwidth_capacity).quantize(
                Decimal("0.0001"), rounding=ROUND_HALF_EVEN
            ),
        )

        # 7. Dynamic Roofline Ridge Point Evaluation using active weights for MoE
        ridge_point_flops_per_byte = (
            selected_silicon_tflops * p.tflops_scale_factor
        ) / (accelerator.memory_bandwidth_gbps * p.bytes_per_gigabyte_sec)

        operational_intensity_prefill = (
            prefill_flops / max(Decimal("1.0"), active_weights_bytes)
        )
        is_memory_bound = operational_intensity_prefill < ridge_point_flops_per_byte

        is_ttft_sla_met = bool(ttft_seconds <= workload.target_ttft_seconds)
        is_tpot_sla_met = bool(tpot_ms_per_token <= workload.target_tpot_ms)

        return RooflineSimulationResult(
            chassis_or_instance_id=candidate_id,
            tensor_parallel_degree=tp_degree,
            pipeline_parallel_degree=pp_degree,
            required_cluster_nodes_baseline=required_nodes,
            model_weights_vram_gb=weights_vram_gb,
            kv_cache_total_vram_gb=kv_cache_vram_gb,
            activation_buffer_vram_gb=activation_vram_gb,
            total_required_vram_gb=total_required_vram_gb,
            cluster_total_vram_pool_gb=cluster_total_vram_pool_gb,
            vram_utilization_ratio=vram_utilization_ratio,
            ttft_seconds=ttft_seconds,
            tpot_ms_per_token=tpot_ms_per_token,
            tokens_per_second_per_user=tokens_per_second_per_user,
            aggregate_cluster_throughput_tok_s=aggregate_cluster_throughput_tok_s,
            memory_bus_utilization_ratio=memory_bus_utilization_ratio,
            model_flops_utilization_ratio=p.baseline_mfu_ratio,
            is_memory_bound=is_memory_bound,
            is_ttft_sla_met=is_ttft_sla_met,
            is_tpot_sla_met=is_tpot_sla_met,
        )
