"""
Silicon Capacity & Calibrated Roofline Sizing Calculator
========================================================
Independent capacity sizing calculator implementing physical silicon laws,
Grouped-Query Attention (GQA) & Multi-Head Latent Attention (MLA) KV-cache scaling,
and calibrated Two-Regime Roofline models.
"""

from __future__ import annotations

from .domain.model import (
    STANDARD_VANILLA_PROFILE,
    TIER1_PRODUCTION_PROFILE,
    AcceleratorSpec,
    AttentionType,
    InterconnectTopology,
    ModelArchitectureSpec,
    PrecisionDtype,
    RooflineRegime,
    RooflineSizingEngine,
    RooflineSizingOutput,
    RuntimeOptimizationProfile,
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

__all__ = [
    "STANDARD_VANILLA_PROFILE",
    "TIER1_PRODUCTION_PROFILE",
    "AcceleratorSpec",
    "AttentionType",
    "InterconnectTopology",
    "ModelArchitectureSpec",
    "PrecisionDtype",
    "RooflineRegime",
    "RooflineSizingEngine",
    "RooflineSizingOutput",
    "RuntimeOptimizationProfile",
    "SizingDemandRequest",
    "calculate_activation_vram_gb",
    "calculate_allreduce_time_seconds",
    "calculate_dynamic_kv_cache_vram_gb",
    "calculate_kv_cache_bytes_per_token",
    "calculate_moe_active_weights_gb",
    "calculate_roofline_latencies",
    "calculate_silicon_topology",
    "calculate_static_weights_vram_gb",
    "get_bytes_per_param",
    "get_effective_peak_tflops",
]
