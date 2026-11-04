"""Domain Port for Open FAIR Actuarial Risk Modeling."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from src.domain.models.financial import ActuarialRiskMetrics, MonetaryAmount
from src.domain.models.hardware import CloudInstancePricingSpec, ServerChassisSpec
from src.domain.models.workload import RooflineSimulationResult


class ActuarialRiskPort(ABC):
    """Domain Port evaluating Open FAIR loss expectancies for On-Premise RMA and Cloud Spot."""

    @abstractmethod
    def evaluate_on_premise_hardware_risk(
        self,
        chassis: ServerChassisSpec,
        cluster_node_count: int,
        hourly_sla_penalty: MonetaryAmount,
        spare_chassis_count: int = 0,
        nominal_monthly_tco: Optional[MonetaryAmount] = None,
    ) -> ActuarialRiskMetrics:
        """Evaluates hardware silicon failure rate (AFR), MTBF, and RMA replacement ALE."""
        raise NotImplementedError

    @abstractmethod
    def evaluate_cloud_spot_preemption_risk(
        self,
        cloud_spec: CloudInstancePricingSpec,
        cluster_instance_count: int,
        hourly_sla_penalty: MonetaryAmount,
        roofline: RooflineSimulationResult,
        nominal_monthly_tco: Optional[MonetaryAmount] = None,
    ) -> ActuarialRiskMetrics:
        """Evaluates Cloud Spot preemption probability, cold rebuild MTTR, and eviction ALE."""
        raise NotImplementedError
