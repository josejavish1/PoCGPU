"""JSON-backed Assessment Questionnaire Schema Loader Adapter."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Sequence

from src.domain.models.assessment import (
    QuestionnaireCriterionOption,
    QuestionnaireItemSchema,
)
from src.domain.ports.assessment_questionnaire import AssessmentQuestionnairePort


class JsonQuestionnaireLoaderAdapter(AssessmentQuestionnairePort):
    """Loads strategic non-functional assessment questionnaire schemas with vertical-specific weights."""

    def __init__(self, questionnaire_path: Path) -> None:
        self._questionnaire_path = questionnaire_path
        self._raw_data: dict = {}
        self._load_schema()

    def _load_schema(self) -> None:
        if not self._questionnaire_path.is_file():
            raise FileNotFoundError(f"Questionnaire file not found at: {self._questionnaire_path}")
        self._raw_data = json.loads(self._questionnaire_path.read_text(encoding="utf-8"))

    def fetch_questionnaire_schema(
        self,
        vertical_id: str,
        locale: str,
    ) -> Sequence[QuestionnaireItemSchema]:
        """Loads strategic questionnaire items customized for the requested industry vertical and locale."""
        overrides = (
            self._raw_data.get("vertical_overrides", {})
            .get(vertical_id, {})
            .get("question_weights", {})
        )

        schema_items: list[QuestionnaireItemSchema] = []
        for q in self._raw_data.get("questions", []):
            qid = q["question_id"]
            effective_weight = Decimal(overrides.get(qid, q["weight"]))

            options: list[QuestionnaireCriterionOption] = []
            for opt in q.get("options", []):
                options.append(
                    QuestionnaireCriterionOption(
                        option_id=opt["option_id"],
                        i18n_label_key=opt["i18n_label_key"],
                        on_prem_affinity_score=Decimal(opt["on_prem_affinity_score"]),
                        cloud_affinity_score=Decimal(opt["cloud_affinity_score"]),
                        is_hard_on_prem_veto=bool(opt.get("is_hard_on_prem_veto", False)),
                        is_hard_cloud_veto=bool(opt.get("is_hard_cloud_veto", False)),
                    )
                )

            schema_items.append(
                QuestionnaireItemSchema(
                    question_id=qid,
                    dimension_name=q["dimension_name"],
                    i18n_prompt_key=q["i18n_prompt_key"],
                    weight=effective_weight,
                    options=tuple(options),
                )
            )

        return tuple(schema_items)
