"""Domain Ports for Hardware and Chassis Catalog Resolution."""

from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Sequence

from src.domain.models.financial import CurrencyCode
from src.domain.models.hardware import HardwareAcceleratorSpec, ServerChassisSpec


class HardwareRegistryPort(ABC):
    """Driven Port for resolving physical accelerator silicon and server chassis BOMs."""

    @abstractmethod
    def get_accelerator_spec(self, sku_id: str) -> HardwareAcceleratorSpec:
        """Dynamically resolves silicon physics specification. Raises DomainLookupError if absent."""
        raise NotImplementedError

    @abstractmethod
    def list_compatible_chassis(
        self,
        min_vram_gb: Decimal,
        max_rack_kw: Decimal,
    ) -> Sequence[ServerChassisSpec]:
        """Queries on-premise server chassis meeting thermal and capacity limits."""
        raise NotImplementedError
