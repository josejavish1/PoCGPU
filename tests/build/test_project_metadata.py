"""Contract tests for the reproducible Phase 1 build metadata."""

from __future__ import annotations

import tomllib
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_project_metadata_declares_canonical_package_contract() -> None:
    metadata_path = REPOSITORY_ROOT / "pyproject.toml"
    assert metadata_path.is_file()

    metadata = tomllib.loads(metadata_path.read_text(encoding="utf-8"))
    project = metadata["project"]

    assert project["name"] == "pocgpu"
    assert project["requires-python"] == ">=3.12,<3.14"
    assert project["dependencies"] == ["pydantic>=2.12,<3"]
    assert metadata["build-system"]["build-backend"] == "hatchling.build"


def test_development_toolchain_is_declared_without_runtime_leakage() -> None:
    metadata = tomllib.loads((REPOSITORY_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    declared = metadata["dependency-groups"]["dev"]
    expected_names = {
        "hypothesis",
        "mypy",
        "mutmut",
        "pip-audit",
        "pytest",
        "pytest-cov",
        "ruff",
    }

    assert {requirement.split(">=")[0] for requirement in declared} == expected_names


def test_python_and_dependency_lock_are_versioned() -> None:
    assert (REPOSITORY_ROOT / ".python-version").read_text(encoding="utf-8") == ("3.12.14\n")
    lock_path = REPOSITORY_ROOT / "uv.lock"
    assert lock_path.is_file()
    lock = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    assert lock["revision"] >= 1
    assert lock["requires-python"] == ">=3.12, <3.14"
    assert {package["name"] for package in lock["package"]}.issuperset(
        {"pocgpu", "pydantic", "pytest", "ruff"}
    )
