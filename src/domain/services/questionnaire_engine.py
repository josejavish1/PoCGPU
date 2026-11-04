"""Questionnaire Decision Engine implementing Multi-Vector Archetype Recommendation."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_EVEN
from typing import Mapping, Sequence

from src.domain.exceptions import DomainLookupError
from src.domain.models.assessment import (
    ArchetypeRecommendationResult,
    AssessmentDecisionPolicy,
    DeploymentArchetype,
    QuestionnaireItemSchema,
)
from src.domain.models.workload import LlmWorkloadProfile
from src.domain.ports.assessment_questionnaire import ArchetypeRecommendationPort


class QuestionnaireDecisionEngine(ArchetypeRecommendationPort):
    """Deterministic decision matrix evaluating customer requirements into target archetypes."""

    def evaluate_assessment(
        self,
        schema: Sequence[QuestionnaireItemSchema],
        client_responses: Mapping[str, str],
        workload: LlmWorkloadProfile,
        policy: AssessmentDecisionPolicy,
    ) -> ArchetypeRecommendationResult:
        """Evaluates client responses, workload profile, and decision policy to recommend the optimal deployment archetype."""
        if not schema:
            raise ValueError("Assessment schema cannot be empty.")
        if not client_responses:
            raise ValueError("Client responses mapping cannot be empty.")

        total_weight = Decimal("0.0000")
        weighted_on_prem_sum = Decimal("0.0000")
        weighted_cloud_sum = Decimal("0.0000")

        has_on_prem_veto = False
        on_prem_veto_reason: str | None = None

        has_cloud_veto = False
        cloud_veto_reason: str | None = None

        rationales: list[str] = []

        for question in schema:
            if question.question_id not in client_responses:
                raise DomainLookupError(
                    f"Missing required response for question '{question.question_id}' ({question.dimension_name})."
                )

            selected_option_id = client_responses[question.question_id]
            matched_option = next(
                (opt for opt in question.options if opt.option_id == selected_option_id),
                None,
            )

            if matched_option is None:
                raise DomainLookupError(
                    f"Invalid option '{selected_option_id}' selected for question '{question.question_id}'."
                )

            total_weight += question.weight
            weighted_on_prem_sum += question.weight * matched_option.on_prem_affinity_score
            weighted_cloud_sum += question.weight * matched_option.cloud_affinity_score

            rationales.append(matched_option.i18n_label_key)

            if matched_option.is_hard_on_prem_veto:
                has_on_prem_veto = True
                on_prem_veto_reason = matched_option.i18n_label_key

            if matched_option.is_hard_cloud_veto:
                has_cloud_veto = True
                cloud_veto_reason = matched_option.i18n_label_key

        if total_weight <= Decimal("0"):
            raise ValueError("Total questionnaire schema weight must be strictly positive.")

        on_prem_composite = (weighted_on_prem_sum / total_weight).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_EVEN
        )
        cloud_composite = (weighted_cloud_sum / total_weight).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_EVEN
        )
        divergence_delta = abs(on_prem_composite - cloud_composite).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_EVEN
        )

        # 1. Mutual Veto Deadlock
        if has_on_prem_veto and has_cloud_veto:
            rationales.append(policy.deadlock_resolution_i18n_key)
            deadlock_burst_split = Decimal("1.0000") - policy.deadlock_base_split_pct
            return ArchetypeRecommendationResult(
                recommended_archetype=policy.deadlock_default_archetype,
                on_prem_composite_score=on_prem_composite,
                cloud_composite_score=cloud_composite,
                divergence_delta=divergence_delta,
                recommended_base_load_split_pct=policy.deadlock_base_split_pct,
                recommended_burst_load_split_pct=deadlock_burst_split,
                is_veto_enforced=True,
                veto_reason_i18n_key=policy.deadlock_resolution_i18n_key,
                strategic_rationale_i18n_keys=tuple(rationales),
            )

        # 2. Hard On-Prem Veto -> Force Cloud
        if has_on_prem_veto:
            return ArchetypeRecommendationResult(
                recommended_archetype=DeploymentArchetype.ELASTIC_CLOUD,
                on_prem_composite_score=on_prem_composite,
                cloud_composite_score=cloud_composite,
                divergence_delta=divergence_delta,
                recommended_base_load_split_pct=Decimal("0.0000"),
                recommended_burst_load_split_pct=Decimal("1.0000"),
                is_veto_enforced=True,
                veto_reason_i18n_key=on_prem_veto_reason,
                strategic_rationale_i18n_keys=tuple(rationales),
            )

        # 3. Hard Cloud Veto -> Force On-Prem
        if has_cloud_veto:
            return ArchetypeRecommendationResult(
                recommended_archetype=DeploymentArchetype.SOVEREIGN_ON_PREM,
                on_prem_composite_score=on_prem_composite,
                cloud_composite_score=cloud_composite,
                divergence_delta=divergence_delta,
                recommended_base_load_split_pct=Decimal("1.0000"),
                recommended_burst_load_split_pct=Decimal("0.0000"),
                is_veto_enforced=True,
                veto_reason_i18n_key=cloud_veto_reason,
                strategic_rationale_i18n_keys=tuple(rationales),
            )

        # 4. Standard Decision & Peak-to-Average Ratio (PAR) Analysis
        peak_to_average_ratio = workload.peak_burst_rps / workload.baseline_rps

        if (
            divergence_delta <= policy.hybrid_divergence_threshold
            and peak_to_average_ratio >= policy.min_hybrid_peak_to_average_ratio
        ):
            # Compute dynamic load split: base capacity covers baseline RPS, cloud covers peak burst
            raw_base_split = (Decimal("1.0000") / peak_to_average_ratio).quantize(
                Decimal("0.0001"), rounding=ROUND_HALF_EVEN
            )
            base_split = max(
                policy.min_base_load_split_pct,
                min(policy.max_base_load_split_pct, raw_base_split),
            )
            burst_split = Decimal("1.0000") - base_split

            rationales.append(policy.hybrid_paradigm_i18n_key)
            return ArchetypeRecommendationResult(
                recommended_archetype=DeploymentArchetype.HYBRID_CLOUD_BURST,
                on_prem_composite_score=on_prem_composite,
                cloud_composite_score=cloud_composite,
                divergence_delta=divergence_delta,
                recommended_base_load_split_pct=base_split,
                recommended_burst_load_split_pct=burst_split,
                is_veto_enforced=False,
                veto_reason_i18n_key=None,
                strategic_rationale_i18n_keys=tuple(rationales),
            )

        if on_prem_composite >= cloud_composite:
            rationales.append(policy.on_premise_paradigm_i18n_key)
            return ArchetypeRecommendationResult(
                recommended_archetype=DeploymentArchetype.SOVEREIGN_ON_PREM,
                on_prem_composite_score=on_prem_composite,
                cloud_composite_score=cloud_composite,
                divergence_delta=divergence_delta,
                recommended_base_load_split_pct=Decimal("1.0000"),
                recommended_burst_load_split_pct=Decimal("0.0000"),
                is_veto_enforced=False,
                veto_reason_i18n_key=None,
                strategic_rationale_i18n_keys=tuple(rationales),
            )
        else:
            rationales.append(policy.cloud_paradigm_i18n_key)
            return ArchetypeRecommendationResult(
                recommended_archetype=DeploymentArchetype.ELASTIC_CLOUD,
                on_prem_composite_score=on_prem_composite,
                cloud_composite_score=cloud_composite,
                divergence_delta=divergence_delta,
                recommended_base_load_split_pct=Decimal("0.0000"),
                recommended_burst_load_split_pct=Decimal("1.0000"),
                is_veto_enforced=False,
                veto_reason_i18n_key=None,
                strategic_rationale_i18n_keys=tuple(rationales),
            )
