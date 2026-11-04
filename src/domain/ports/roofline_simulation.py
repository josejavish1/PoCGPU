"""Domain Port for Roofline Physics and Distributed Inference Sizing."""

from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal

from src.domain.models.hardware import HardwareAcceleratorSpec
from src.domain.models.workload import LlmWorkloadProfile, RooflineSimulationResult


class RooflineSimulationPort(ABC):
    """Domain Port computing VRAM allocation, Tensor Parallelism, and Roofline latency bounds."""

    @abstractmethod
    def simulate_roofline(
        self,
        candidate_id: str,
        workload: LlmWorkloadProfile,
        accelerator: HardwareAcceleratorSpec,
        accelerators_per_node: int,
        max_vram_utilization_ratio: Decimal,
    ) -> RooflineSimulationResult:
        """Calculates physical memory footprints and prefill/decode latency bounds without hardcoded limits."""
        raise NotImplementedError
