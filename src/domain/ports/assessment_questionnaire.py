"""Domain Ports for Strategic Questionnaire and Archetype Recommendation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Mapping, Sequence

from src.domain.models.assessment import (
    ArchetypeRecommendationResult,
    AssessmentDecisionPolicy,
    QuestionnaireItemSchema,
)
from src.domain.models.workload import LlmWorkloadProfile


class AssessmentQuestionnairePort(ABC):
    """Driven Port loading localized dynamic questionnaire schemas."""

    @abstractmethod
    def fetch_questionnaire_schema(
        self,
        vertical_id: str,
        locale: str,
    ) -> Sequence[QuestionnaireItemSchema]:
        """Loads strategic non-functional questionnaire items for a given industry and locale."""
        raise NotImplementedError


class ArchetypeRecommendationPort(ABC):
    """Domain Port executing the multi-vector archetype recommendation matrix."""

    @abstractmethod
    def evaluate_assessment(
        self,
        schema: Sequence[QuestionnaireItemSchema],
        client_responses: Mapping[str, str],
        workload: LlmWorkloadProfile,
        policy: AssessmentDecisionPolicy,
    ) -> ArchetypeRecommendationResult:
        """Evaluates client responses, workload profile, and decision policy to recommend the optimal deployment archetype."""
        raise NotImplementedError
