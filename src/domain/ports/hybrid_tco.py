"""Domain Port for GAAP/IFRS On-Premise, Cloud, and Hybrid TCO Aggregation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal

from src.domain.models.assessment import ArchetypeRecommendationResult
from src.domain.models.financial import ComputedTcoBreakdown, MonetaryAmount
from src.domain.models.hardware import (
    CloudInstancePricingSpec,
    DatacenterFacilitySpec,
    ServerChassisSpec,
)
from src.domain.models.workload import LlmWorkloadProfile, RooflineSimulationResult


class HybridTcoAggregatorPort(ABC):
    """Domain Port computing deterministic GAAP/IFRS monthly TCO breakdowns."""

    @abstractmethod
    def compute_on_premise_tco(
        self,
        chassis: ServerChassisSpec,
        facility: DatacenterFacilitySpec,
        roofline: RooflineSimulationResult,
        amortization_months: int,
        chassis_per_rack: int,
        management_plane_monthly: MonetaryAmount,
        persistent_storage_monthly: MonetaryAmount,
        network_egress_monthly: MonetaryAmount,
        hours_per_month: Decimal | None = None,
    ) -> ComputedTcoBreakdown:
        """Computes amortized CapEx (net of dynamic salvage) and facility OpEx for on-premise clusters."""
        raise NotImplementedError

    @abstractmethod
    def compute_cloud_tco(
        self,
        cloud_spec: CloudInstancePricingSpec,
        workload: LlmWorkloadProfile,
        roofline: RooflineSimulationResult,
        amortization_months: int,
        spot_allocation_ratio: Decimal,
        reserved_allocation_ratio: Decimal,
        persistent_storage_gb: Decimal,
        monthly_egress_gb: Decimal,
        management_plane_monthly: MonetaryAmount,
        hours_per_month: Decimal,
    ) -> ComputedTcoBreakdown:
        """Computes elastic Cloud OpEx blending On-Demand, Reserved, and Spot allocations."""
        raise NotImplementedError

    @abstractmethod
    def compute_hybrid_tco(
        self,
        on_prem_tco: ComputedTcoBreakdown,
        cloud_tco: ComputedTcoBreakdown,
        recommendation: ArchetypeRecommendationResult,
    ) -> ComputedTcoBreakdown:
        """Aggregates weighted Hybrid TCO from base on-premise and burst cloud allocations."""
        raise NotImplementedError
