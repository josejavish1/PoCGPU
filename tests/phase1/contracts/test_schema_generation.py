"""Strict boundary model and deterministic schema export tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from pocgpu.contracts.schema_export import render_schemas
from pocgpu.contracts.v1 import PolicySettingContract

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def test_boundary_contract_rejects_unknown_fields_and_float_values() -> None:
    with pytest.raises(ValidationError):
        PolicySettingContract.model_validate(
            {
                "key": "foundation.mode",
                "value_schema_id": "schema.decimal",
                "value": 1.5,
            }
        )
    with pytest.raises(ValidationError):
        PolicySettingContract.model_validate(
            {
                "key": "foundation.mode",
                "value_schema_id": "schema.identifier",
                "value": "explicit",
                "unexpected": True,
            }
        )


def test_checked_in_schemas_match_clean_generation() -> None:
    rendered = render_schemas()
    schema_root = REPOSITORY_ROOT / "schemas" / "v1"

    assert set(rendered) == {
        "canonical-result.schema.json",
        "governed-record.schema.json",
        "organization-profile.schema.json",
        "policy-pack.schema.json",
        "scenario.schema.json",
    }
    for filename, content in rendered.items():
        checked_in = (schema_root / filename).read_text(encoding="utf-8")
        assert json.loads(checked_in) == json.loads(content)
