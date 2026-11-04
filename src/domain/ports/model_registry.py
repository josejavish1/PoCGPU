"""Domain Port for Model Workload Profile Resolution."""

from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Optional, Sequence

from src.domain.models.workload import LlmWorkloadProfile, QuantizationPrecision


class ModelRegistryPort(ABC):
    """Driven Port resolving declarative LLM model architectures into workload profiles."""

    @abstractmethod
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
        """Resolves model architecture parameters into an immutable LlmWorkloadProfile."""
        raise NotImplementedError

    @abstractmethod
    def list_available_models(self) -> Sequence[str]:
        """Returns identifiers of all registered LLM models."""
        raise NotImplementedError
