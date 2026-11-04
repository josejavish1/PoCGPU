"""Guided Assessment and Archetype Recommendation Value Objects."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Optional, Sequence

from src.domain.models.validation import assert_strict_decimal


class DeploymentArchetype(str, Enum):
    SOVEREIGN_ON_PREM = "SOVEREIGN_ON_PREM_BARE_METAL"
    ELASTIC_CLOUD = "ELASTIC_PUBLIC_CLOUD_DEDICATED"
    HYBRID_CLOUD_BURST = "TIERED_HYBRID_SOVEREIGN_BURST"


@dataclass(frozen=True)
class AssessmentDecisionPolicy:
    """Configurable decision policy parameters for the archetype recommendation matrix."""

    hybrid_divergence_threshold: Decimal
    min_base_load_split_pct: Decimal
    max_base_load_split_pct: Decimal
    min_hybrid_peak_to_average_ratio: Decimal = Decimal("1.5000")
    deadlock_default_archetype: DeploymentArchetype = DeploymentArchetype.SOVEREIGN_ON_PREM
    deadlock_base_split_pct: Decimal = Decimal("1.0000")
    on_premise_paradigm_i18n_key: str = "domain.questionnaire.paradigm.on_premise"
    cloud_paradigm_i18n_key: str = "domain.questionnaire.paradigm.cloud_native"
    hybrid_paradigm_i18n_key: str = "domain.questionnaire.paradigm.hybrid_burst"
    deadlock_resolution_i18n_key: str = "domain.questionnaire.deadlock.resolution"

    def __post_init__(self) -> None:
        assert_strict_decimal(self.hybrid_divergence_threshold, "hybrid_divergence_threshold")
        assert_strict_decimal(self.min_base_load_split_pct, "min_base_load_split_pct")
        assert_strict_decimal(self.max_base_load_split_pct, "max_base_load_split_pct")
        assert_strict_decimal(self.min_hybrid_peak_to_average_ratio, "min_hybrid_peak_to_average_ratio")
        assert_strict_decimal(self.deadlock_base_split_pct, "deadlock_base_split_pct")

        if not (Decimal("0") <= self.min_base_load_split_pct <= self.max_base_load_split_pct <= Decimal("1.0")):
            raise ValueError(
                f"Split bounds must satisfy 0 <= min ({self.min_base_load_split_pct}) "
                f"<= max ({self.max_base_load_split_pct}) <= 1.0."
            )
        if self.hybrid_divergence_threshold < Decimal("0"):
            raise ValueError(f"hybrid_divergence_threshold cannot be negative, got {self.hybrid_divergence_threshold}.")
        if self.min_hybrid_peak_to_average_ratio <= Decimal("1.0"):
            raise ValueError(
                f"min_hybrid_peak_to_average_ratio must be > 1.0, got {self.min_hybrid_peak_to_average_ratio}."
            )
        if not (Decimal("0") <= self.deadlock_base_split_pct <= Decimal("1.0")):
            raise ValueError(f"deadlock_base_split_pct must be in [0, 1], got {self.deadlock_base_split_pct}.")


@dataclass(frozen=True)
class QuestionnaireCriterionOption:
    """Selectable option within a strategic non-functional assessment question."""

    option_id: str
    i18n_label_key: str
    on_prem_affinity_score: Decimal  # Normalized [0.0, 100.0]
    cloud_affinity_score: Decimal    # Normalized [0.0, 100.0]
    is_hard_on_prem_veto: bool       # e.g. strictly forbidden by law to touch public cloud
    is_hard_cloud_veto: bool         # e.g. strictly zero datacenter physical facilities available

    def __post_init__(self) -> None:
        assert_strict_decimal(self.on_prem_affinity_score, "on_prem_affinity_score")
        assert_strict_decimal(self.cloud_affinity_score, "cloud_affinity_score")

        if not (Decimal("0") <= self.on_prem_affinity_score <= Decimal("100.0")):
            raise ValueError(f"on_prem_affinity_score must be in [0, 100], got {self.on_prem_affinity_score}.")
        if not (Decimal("0") <= self.cloud_affinity_score <= Decimal("100.0")):
            raise ValueError(f"cloud_affinity_score must be in [0, 100], got {self.cloud_affinity_score}.")


@dataclass(frozen=True)
class QuestionnaireItemSchema:
    """Strategic assessment question definition with weight and options."""

    question_id: str
    dimension_name: str
    i18n_prompt_key: str
    weight: Decimal                  # Relative importance [0.1, 3.0]
    options: Sequence[QuestionnaireCriterionOption]

    def __post_init__(self) -> None:
        assert_strict_decimal(self.weight, "weight")
        if self.weight <= Decimal("0"):
            raise ValueError(f"Question '{self.question_id}' weight must be strictly positive, got {self.weight}.")

        if not self.options:
            raise ValueError(f"Question '{self.question_id}' must define at least one selectable option.")

        # Guarantee deep immutability
        if not isinstance(self.options, tuple):
            object.__setattr__(self, "options", tuple(self.options))


@dataclass(frozen=True)
class ArchetypeRecommendationResult:
    """Outcome of the multi-vector assessment decision matrix."""

    recommended_archetype: DeploymentArchetype
    on_prem_composite_score: Decimal
    cloud_composite_score: Decimal
    divergence_delta: Decimal
    recommended_base_load_split_pct: Decimal    # % allocated to on-premise base
    recommended_burst_load_split_pct: Decimal   # % allocated to cloud bursting
    is_veto_enforced: bool
    veto_reason_i18n_key: Optional[str]
    strategic_rationale_i18n_keys: Sequence[str]

    def __post_init__(self) -> None:
        assert_strict_decimal(self.on_prem_composite_score, "on_prem_composite_score")
        assert_strict_decimal(self.cloud_composite_score, "cloud_composite_score")
        assert_strict_decimal(self.divergence_delta, "divergence_delta")
        assert_strict_decimal(self.recommended_base_load_split_pct, "recommended_base_load_split_pct")
        assert_strict_decimal(self.recommended_burst_load_split_pct, "recommended_burst_load_split_pct")

        if not (Decimal("0") <= self.recommended_base_load_split_pct <= Decimal("1.0")):
            raise ValueError(
                f"recommended_base_load_split_pct must be in [0, 1], got {self.recommended_base_load_split_pct}."
            )
        if not (Decimal("0") <= self.recommended_burst_load_split_pct <= Decimal("1.0")):
            raise ValueError(
                f"recommended_burst_load_split_pct must be in [0, 1], got {self.recommended_burst_load_split_pct}."
            )

        split_sum = self.recommended_base_load_split_pct + self.recommended_burst_load_split_pct
        if split_sum != Decimal("1.0000"):
            raise ValueError(
                f"ArchetypeRecommendationResult split percentages must sum to 1.0000, got {split_sum}."
            )

        # Guarantee deep immutability
        if not isinstance(self.strategic_rationale_i18n_keys, tuple):
            object.__setattr__(
                self,
                "strategic_rationale_i18n_keys",
                tuple(self.strategic_rationale_i18n_keys),
            )
