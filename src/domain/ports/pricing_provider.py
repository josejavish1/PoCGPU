"""Domain Ports for Cloud Pricing and Foreign Exchange Conversion."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Sequence

from src.domain.models.financial import CurrencyCode, MonetaryAmount
from src.domain.models.hardware import CloudInstancePricingSpec


class PricingProviderPort(ABC):
    """Driven Port for live cloud Spot/On-Demand rates and JIT currency conversion."""

    @abstractmethod
    def get_cloud_pricing(
        self,
        sku_id: str,
        region: Optional[str],
        target_currency: CurrencyCode,
    ) -> Sequence[CloudInstancePricingSpec]:
        """Fetches live cloud instance pricing specs for a given accelerator."""
        raise NotImplementedError

    @abstractmethod
    def convert_currency(
        self,
        amount: MonetaryAmount,
        target_currency: CurrencyCode,
    ) -> MonetaryAmount:
        """Converts monetary amounts using dynamic FX rates."""
        raise NotImplementedError
