"""Deterministic JSON Schema generation for version 1 boundary contracts."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from pocgpu.contracts.v1 import (
    CanonicalResultContract,
    GovernedRecordContract,
    OrganizationProfileContract,
    PolicyPackContract,
    ScenarioContract,
)

SCHEMA_MODELS: dict[str, type[BaseModel]] = {
    "canonical-result.schema.json": CanonicalResultContract,
    "governed-record.schema.json": GovernedRecordContract,
    "organization-profile.schema.json": OrganizationProfileContract,
    "policy-pack.schema.json": PolicyPackContract,
    "scenario.schema.json": ScenarioContract,
}


def render_schemas() -> dict[str, str]:
    """Render every public schema with stable formatting."""

    return {
        filename: json.dumps(
            model.model_json_schema(mode="validation"),
            indent=2,
            sort_keys=True,
        )
        + "\n"
        for filename, model in SCHEMA_MODELS.items()
    }


def write_schemas(output_directory: Path) -> None:
    """Write generated schemas to one explicit directory."""

    output_directory.mkdir(parents=True, exist_ok=True)
    for filename, content in render_schemas().items():
        (output_directory / filename).write_text(content, encoding="utf-8")


if __name__ == "__main__":
    write_schemas(Path("schemas/v1"))
