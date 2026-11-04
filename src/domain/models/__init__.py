"""Canonical Domain Models for Universal Hybrid FinOps Advisor."""

from src.domain.models.financial import (
    CurrencyCode,
    MonetaryAmount,
    ComputedTcoBreakdown,
    ActuarialRiskMetrics,
)
from src.domain.models.hardware import (
    InterconnectType,
    CoolingTopology,
    HardwareAcceleratorSpec,
    ServerChassisSpec,
    CloudInstancePricingSpec,
    DatacenterFacilitySpec,
)
from src.domain.models.workload import (
    AttentionType,
    QuantizationPrecision,
    LlmWorkloadProfile,
    RooflineSimulationResult,
)
from src.domain.models.assessment import (
    DeploymentArchetype,
    AssessmentDecisionPolicy,
    QuestionnaireCriterionOption,
    QuestionnaireItemSchema,
    ArchetypeRecommendationResult,
)

__all__ = [
    "CurrencyCode",
    "MonetaryAmount",
    "ComputedTcoBreakdown",
    "ActuarialRiskMetrics",
    "InterconnectType",
    "CoolingTopology",
    "HardwareAcceleratorSpec",
    "ServerChassisSpec",
    "CloudInstancePricingSpec",
    "DatacenterFacilitySpec",
    "AttentionType",
    "QuantizationPrecision",
    "LlmWorkloadProfile",
    "RooflineSimulationResult",
    "DeploymentArchetype",
    "AssessmentDecisionPolicy",
    "QuestionnaireCriterionOption",
    "QuestionnaireItemSchema",
    "ArchetypeRecommendationResult",
]
