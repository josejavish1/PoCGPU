"""Unit tests for QuestionnaireDecisionEngine."""

from __future__ import annotations

import unittest
from decimal import Decimal

from src.domain.exceptions import DomainLookupError
from src.domain.models.assessment import (
    AssessmentDecisionPolicy,
    DeploymentArchetype,
    QuestionnaireCriterionOption,
    QuestionnaireItemSchema,
)
from src.domain.models.workload import (
    AttentionType,
    LlmWorkloadProfile,
    QuantizationPrecision,
)
from src.domain.services.questionnaire_engine import QuestionnaireDecisionEngine


class TestQuestionnaireDecisionEngine(unittest.TestCase):
    """Comprehensive test suite verifying multi-vector archetype evaluation, vetoes, and hybrid splits."""

    def setUp(self) -> None:
        self.engine = QuestionnaireDecisionEngine()
        self.default_policy = AssessmentDecisionPolicy(
            hybrid_divergence_threshold=Decimal("15.00"),
            min_base_load_split_pct=Decimal("0.2000"),
            max_base_load_split_pct=Decimal("0.8000"),
        )
        self.schema = [
            QuestionnaireItemSchema(
                question_id="q_sovereignty",
                dimension_name="domain.questionnaire.dim.sovereignty",
                i18n_prompt_key="prompt.sovereignty",
                weight=Decimal("2.0"),
                options=(
                    QuestionnaireCriterionOption(
                        option_id="opt_airgap",
                        i18n_label_key="opt.sovereignty.airgap",
                        on_prem_affinity_score=Decimal("100.0"),
                        cloud_affinity_score=Decimal("0.0"),
                        is_hard_on_prem_veto=False,
                        is_hard_cloud_veto=True,
                    ),
                    QuestionnaireCriterionOption(
                        option_id="opt_balanced_gov",
                        i18n_label_key="opt.sovereignty.balanced",
                        on_prem_affinity_score=Decimal("60.0"),
                        cloud_affinity_score=Decimal("55.0"),
                        is_hard_on_prem_veto=False,
                        is_hard_cloud_veto=False,
                    ),
                    QuestionnaireCriterionOption(
                        option_id="opt_public_saas",
                        i18n_label_key="opt.sovereignty.public",
                        on_prem_affinity_score=Decimal("15.0"),
                        cloud_affinity_score=Decimal("90.0"),
                        is_hard_on_prem_veto=False,
                        is_hard_cloud_veto=False,
                    ),
                ),
            ),
            QuestionnaireItemSchema(
                question_id="q_datacenter",
                dimension_name="domain.questionnaire.dim.datacenter",
                i18n_prompt_key="prompt.datacenter",
                weight=Decimal("1.0"),
                options=(
                    QuestionnaireCriterionOption(
                        option_id="opt_dlc_ready",
                        i18n_label_key="opt.dc.dlc_ready",
                        on_prem_affinity_score=Decimal("90.0"),
                        cloud_affinity_score=Decimal("20.0"),
                        is_hard_on_prem_veto=False,
                        is_hard_cloud_veto=False,
                    ),
                    QuestionnaireCriterionOption(
                        option_id="opt_colo_hybrid",
                        i18n_label_key="opt.dc.colo_hybrid",
                        on_prem_affinity_score=Decimal("50.0"),
                        cloud_affinity_score=Decimal("60.0"),
                        is_hard_on_prem_veto=False,
                        is_hard_cloud_veto=False,
                    ),
                    QuestionnaireCriterionOption(
                        option_id="opt_no_facility",
                        i18n_label_key="opt.dc.no_facility",
                        on_prem_affinity_score=Decimal("0.0"),
                        cloud_affinity_score=Decimal("100.0"),
                        is_hard_on_prem_veto=True,
                        is_hard_cloud_veto=False,
                    ),
                ),
            ),
        ]

    @staticmethod
    def _create_workload(baseline_rps: Decimal, peak_burst_rps: Decimal) -> LlmWorkloadProfile:
        return LlmWorkloadProfile(
            model_id="llama-3-70b-instruct",
            display_name="Llama 3 70B Instruct",
            total_params_billion=Decimal("70.6"),
            active_params_billion=Decimal("70.6"),
            layers=80,
            hidden_size=8192,
            num_query_heads=64,
            num_kv_heads=8,
            head_dim=128,
            attention_type=AttentionType.GQA,
            mla_latent_dim=None,
            quantization=QuantizationPrecision.FP16,
            weights_bytes_per_param=Decimal("2.0"),
            kv_cache_bytes_per_value=Decimal("2.0"),
            max_context_length=8192,
            peak_concurrent_users=250,
            avg_prompt_tokens=1024,
            avg_generated_tokens=512,
            baseline_rps=baseline_rps,
            peak_burst_rps=peak_burst_rps,
            target_ttft_seconds=Decimal("0.80"),
            target_tpot_ms=Decimal("25.0"),
        )

    def test_recommend_sovereign_on_prem_by_score(self) -> None:
        workload = self._create_workload(baseline_rps=Decimal("10.0"), peak_burst_rps=Decimal("12.0"))
        responses = {
            "q_sovereignty": "opt_balanced_gov",  # weight 2.0: on_prem=60, cloud=55
            "q_datacenter": "opt_dlc_ready",      # weight 1.0: on_prem=90, cloud=20
        }
        # Weighted on_prem = (120 + 90) / 3 = 70.0000
        # Weighted cloud   = (110 + 20) / 3 = 43.3333
        result = self.engine.evaluate_assessment(self.schema, responses, workload, self.default_policy)

        self.assertEqual(result.recommended_archetype, DeploymentArchetype.SOVEREIGN_ON_PREM)
        self.assertEqual(result.on_prem_composite_score, Decimal("70.0000"))
        self.assertEqual(result.cloud_composite_score, Decimal("43.3333"))
        self.assertEqual(result.divergence_delta, Decimal("26.6667"))
        self.assertEqual(result.recommended_base_load_split_pct, Decimal("1.0000"))
        self.assertEqual(result.recommended_burst_load_split_pct, Decimal("0.0000"))
        self.assertFalse(result.is_veto_enforced)
        self.assertIsNone(result.veto_reason_i18n_key)
        self.assertIn("domain.questionnaire.paradigm.on_premise", result.strategic_rationale_i18n_keys)

    def test_recommend_elastic_cloud_by_score(self) -> None:
        workload = self._create_workload(baseline_rps=Decimal("10.0"), peak_burst_rps=Decimal("30.0"))
        responses = {
            "q_sovereignty": "opt_public_saas",   # weight 2.0: on_prem=15, cloud=90
            "q_datacenter": "opt_colo_hybrid",    # weight 1.0: on_prem=50, cloud=60
        }
        # Weighted on_prem = (30 + 50) / 3 = 26.6667
        # Weighted cloud   = (180 + 60) / 3 = 80.0000
        result = self.engine.evaluate_assessment(self.schema, responses, workload, self.default_policy)

        self.assertEqual(result.recommended_archetype, DeploymentArchetype.ELASTIC_CLOUD)
        self.assertEqual(result.on_prem_composite_score, Decimal("26.6667"))
        self.assertEqual(result.cloud_composite_score, Decimal("80.0000"))
        self.assertEqual(result.divergence_delta, Decimal("53.3333"))
        self.assertEqual(result.recommended_base_load_split_pct, Decimal("0.0000"))
        self.assertEqual(result.recommended_burst_load_split_pct, Decimal("1.0000"))
        self.assertFalse(result.is_veto_enforced)
        self.assertIsNone(result.veto_reason_i18n_key)
        self.assertIn("domain.questionnaire.paradigm.cloud_native", result.strategic_rationale_i18n_keys)

    def test_recommend_hybrid_cloud_burst_with_dynamic_split(self) -> None:
        # PAR = 25.0 / 10.0 = 2.5 (>= 1.5) -> raw base split = 1 / 2.5 = 0.4000
        workload = self._create_workload(baseline_rps=Decimal("10.0"), peak_burst_rps=Decimal("25.0"))
        responses = {
            "q_sovereignty": "opt_balanced_gov",  # weight 2.0: on_prem=60, cloud=55
            "q_datacenter": "opt_colo_hybrid",    # weight 1.0: on_prem=50, cloud=60
        }
        # Weighted on_prem = (120 + 50) / 3 = 56.6667
        # Weighted cloud   = (110 + 60) / 3 = 56.6667
        # Divergence = 0.0000 <= 15.00
        result = self.engine.evaluate_assessment(self.schema, responses, workload, self.default_policy)

        self.assertEqual(result.recommended_archetype, DeploymentArchetype.HYBRID_CLOUD_BURST)
        self.assertEqual(result.on_prem_composite_score, Decimal("56.6667"))
        self.assertEqual(result.cloud_composite_score, Decimal("56.6667"))
        self.assertEqual(result.divergence_delta, Decimal("0.0000"))
        self.assertEqual(result.recommended_base_load_split_pct, Decimal("0.4000"))
        self.assertEqual(result.recommended_burst_load_split_pct, Decimal("0.6000"))
        self.assertFalse(result.is_veto_enforced)
        self.assertIsNone(result.veto_reason_i18n_key)
        self.assertIn("domain.questionnaire.paradigm.hybrid_burst", result.strategic_rationale_i18n_keys)

    def test_hybrid_base_load_split_clamped_to_policy_minimum(self) -> None:
        # PAR = 100.0 / 10.0 = 10.0 -> raw base split = 0.1000, clamped to min_base_load_split_pct = 0.2000
        workload = self._create_workload(baseline_rps=Decimal("10.0"), peak_burst_rps=Decimal("100.0"))
        responses = {
            "q_sovereignty": "opt_balanced_gov",
            "q_datacenter": "opt_colo_hybrid",
        }
        result = self.engine.evaluate_assessment(self.schema, responses, workload, self.default_policy)

        self.assertEqual(result.recommended_archetype, DeploymentArchetype.HYBRID_CLOUD_BURST)
        self.assertEqual(result.recommended_base_load_split_pct, Decimal("0.2000"))
        self.assertEqual(result.recommended_burst_load_split_pct, Decimal("0.8000"))

    def test_low_par_prevents_hybrid_even_when_divergence_is_low(self) -> None:
        # PAR = 12.0 / 10.0 = 1.2 (< 1.5), so should fall back to score winner (on_prem == cloud -> on_prem)
        workload = self._create_workload(baseline_rps=Decimal("10.0"), peak_burst_rps=Decimal("12.0"))
        responses = {
            "q_sovereignty": "opt_balanced_gov",
            "q_datacenter": "opt_colo_hybrid",
        }
        result = self.engine.evaluate_assessment(self.schema, responses, workload, self.default_policy)

        self.assertEqual(result.recommended_archetype, DeploymentArchetype.SOVEREIGN_ON_PREM)
        self.assertEqual(result.recommended_base_load_split_pct, Decimal("1.0000"))
        self.assertEqual(result.recommended_burst_load_split_pct, Decimal("0.0000"))

    def test_hard_cloud_veto_forces_sovereign_on_prem(self) -> None:
        workload = self._create_workload(baseline_rps=Decimal("10.0"), peak_burst_rps=Decimal("50.0"))
        responses = {
            "q_sovereignty": "opt_airgap",        # is_hard_cloud_veto=True
            "q_datacenter": "opt_colo_hybrid",
        }
        result = self.engine.evaluate_assessment(self.schema, responses, workload, self.default_policy)

        self.assertEqual(result.recommended_archetype, DeploymentArchetype.SOVEREIGN_ON_PREM)
        self.assertTrue(result.is_veto_enforced)
        self.assertEqual(result.veto_reason_i18n_key, "opt.sovereignty.airgap")
        self.assertEqual(result.recommended_base_load_split_pct, Decimal("1.0000"))
        self.assertEqual(result.recommended_burst_load_split_pct, Decimal("0.0000"))

    def test_hard_on_prem_veto_forces_elastic_cloud(self) -> None:
        workload = self._create_workload(baseline_rps=Decimal("10.0"), peak_burst_rps=Decimal("12.0"))
        responses = {
            "q_sovereignty": "opt_balanced_gov",
            "q_datacenter": "opt_no_facility",    # is_hard_on_prem_veto=True
        }
        result = self.engine.evaluate_assessment(self.schema, responses, workload, self.default_policy)

        self.assertEqual(result.recommended_archetype, DeploymentArchetype.ELASTIC_CLOUD)
        self.assertTrue(result.is_veto_enforced)
        self.assertEqual(result.veto_reason_i18n_key, "opt.dc.no_facility")
        self.assertEqual(result.recommended_base_load_split_pct, Decimal("0.0000"))
        self.assertEqual(result.recommended_burst_load_split_pct, Decimal("1.0000"))

    def test_mutual_veto_deadlock_resolution(self) -> None:
        workload = self._create_workload(baseline_rps=Decimal("10.0"), peak_burst_rps=Decimal("30.0"))
        responses = {
            "q_sovereignty": "opt_airgap",        # is_hard_cloud_veto=True
            "q_datacenter": "opt_no_facility",    # is_hard_on_prem_veto=True
        }
        result = self.engine.evaluate_assessment(self.schema, responses, workload, self.default_policy)

        self.assertEqual(result.recommended_archetype, DeploymentArchetype.SOVEREIGN_ON_PREM)
        self.assertTrue(result.is_veto_enforced)
        self.assertEqual(result.veto_reason_i18n_key, "domain.questionnaire.deadlock.resolution")
        self.assertIn("domain.questionnaire.deadlock.resolution", result.strategic_rationale_i18n_keys)
        self.assertEqual(result.recommended_base_load_split_pct, Decimal("1.0000"))
        self.assertEqual(result.recommended_burst_load_split_pct, Decimal("0.0000"))

    def test_missing_question_response_raises_lookup_error(self) -> None:
        workload = self._create_workload(baseline_rps=Decimal("10.0"), peak_burst_rps=Decimal("20.0"))
        with self.assertRaises(DomainLookupError):
            self.engine.evaluate_assessment(
                self.schema,
                {"q_sovereignty": "opt_balanced_gov"},
                workload,
                self.default_policy,
            )

    def test_invalid_option_id_raises_lookup_error(self) -> None:
        workload = self._create_workload(baseline_rps=Decimal("10.0"), peak_burst_rps=Decimal("20.0"))
        with self.assertRaises(DomainLookupError):
            self.engine.evaluate_assessment(
                self.schema,
                {"q_sovereignty": "non_existent_option", "q_datacenter": "opt_dlc_ready"},
                workload,
                self.default_policy,
            )


if __name__ == "__main__":
    unittest.main()
