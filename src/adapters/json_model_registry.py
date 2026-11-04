"""JSON-backed Model Registry Adapter implementing ModelRegistryPort."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Optional, Sequence

from src.domain.exceptions import DomainLookupError
from src.domain.models.workload import (
    AttentionType,
    LlmWorkloadProfile,
    QuantizationPrecision,
)
from src.domain.ports.model_registry import ModelRegistryPort


class JsonModelRegistryAdapter(ModelRegistryPort):
    """Loads declarative LLM model architectures from JSON and constructs validated workload profiles."""

    def __init__(self, catalog_path: Path) -> None:
        self._catalog_path = catalog_path
        self._models_raw: dict[str, dict[str, Any]] = {}
        self._load_catalog()

    def _load_catalog(self) -> None:
        if not self._catalog_path.is_file():
            raise FileNotFoundError(f"Model catalog file not found at: {self._catalog_path}")
        raw = json.loads(self._catalog_path.read_text(encoding="utf-8"))
        self._models_raw = raw.get("models", {})
        self._quant_bytes_map = raw.get("quantization_bytes_map", {})

    def list_available_models(self) -> Sequence[str]:
        return tuple(self._models_raw.keys())

    def get_model_workload_profile(
        self,
        model_id: str,
        peak_concurrent_users: int,
        max_context_length: Optional[int],
        avg_prompt_tokens: int,
        avg_generated_tokens: int,
        baseline_rps: Decimal,
        peak_burst_rps: Decimal,
        quantization_override: Optional[QuantizationPrecision] = None,
    ) -> LlmWorkloadProfile:
        if model_id not in self._models_raw:
            raise DomainLookupError(f"Model '{model_id}' not found in model catalog.")

        m = self._models_raw[model_id]
        quant = quantization_override or QuantizationPrecision[m.get("default_quantization", "FP16")]
        ctx = max_context_length or int(m.get("default_max_context_length", 8192))

        mla_dim = int(m["mla_latent_dim"]) if m.get("mla_latent_dim") is not None else None

        if quantization_override is not None and quant.name in self._quant_bytes_map:
            q_info = self._quant_bytes_map[quant.name]
            weights_bytes = Decimal(q_info["weights_bytes_per_param"])
            kv_bytes = Decimal(q_info["kv_cache_bytes_per_value"])
        else:
            weights_bytes = Decimal(m["weights_bytes_per_param"])
            kv_bytes = Decimal(m["kv_cache_bytes_per_value"])

        return LlmWorkloadProfile(
            model_id=model_id,
            display_name=m["display_name"],
            total_params_billion=Decimal(m["total_params_billion"]),
            active_params_billion=Decimal(m["active_params_billion"]),
            layers=int(m["layers"]),
            hidden_size=int(m["hidden_size"]),
            num_query_heads=int(m["num_query_heads"]),
            num_kv_heads=int(m["num_kv_heads"]),
            head_dim=int(m["head_dim"]),
            attention_type=AttentionType[m["attention_type"]],
            mla_latent_dim=mla_dim,
            quantization=quant,
            weights_bytes_per_param=weights_bytes,
            kv_cache_bytes_per_value=kv_bytes,
            max_context_length=ctx,
            peak_concurrent_users=peak_concurrent_users,
            avg_prompt_tokens=avg_prompt_tokens,
            avg_generated_tokens=avg_generated_tokens,
            baseline_rps=baseline_rps,
            peak_burst_rps=peak_burst_rps,
            target_ttft_seconds=Decimal(m["target_ttft_seconds"]),
            target_tpot_ms=Decimal(m["target_tpot_ms"]),
        )

    @property
    def raw_catalog(self) -> Mapping[str, dict[str, Any]]:
        return MappingProxyType(self._models_raw)
