"""Negative and positive controls for engineering governance enforcement."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from scripts.validate_engineering_constitution import validate_repository


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = Path("governance/constitution.manifest.json")


class EngineeringConstitutionTests(unittest.TestCase):
    def test_repository_constitution_is_valid(self) -> None:
        report = validate_repository(REPOSITORY_ROOT)

        self.assertTrue(
            report.is_valid,
            "\n".join(
                f"{issue.code}: {issue.path}: {issue.message}"
                for issue in report.issues
            ),
        )

    def test_missing_document_is_rejected(self) -> None:
        with self.fixture() as root:
            (root / "governance" / "records.md").unlink()

            self.assert_issue(root, "MISSING_DOCUMENT")

    def test_broken_link_is_rejected(self) -> None:
        with self.fixture() as root:
            index = root / "governance" / "index.md"
            index.write_text("# Index\n\n[Missing](absent.md)\n", encoding="utf-8")

            self.assert_issue(root, "BROKEN_LINK")

    def test_duplicate_identifier_is_rejected(self) -> None:
        with self.fixture() as root:
            records = root / "governance" / "records.md"
            content = records.read_text(encoding="utf-8")
            records.write_text(
                content + "| GOV-001 | Duplicate | 0 |\n",
                encoding="utf-8",
            )

            self.assert_issue(root, "DUPLICATE_IDENTIFIER")

    def test_disallowed_phase_is_rejected(self) -> None:
        with self.fixture() as root:
            records = root / "governance" / "records.md"
            content = records.read_text(encoding="utf-8").replace(
                "| GOV-001 | Active | 0 |",
                "| GOV-001 | Active | 2 |",
            )
            records.write_text(content, encoding="utf-8")

            self.assert_issue(root, "INVALID_PHASE")

    def test_forbidden_source_code_point_is_rejected(self) -> None:
        with self.fixture() as root:
            source = root / "src" / "module.py"
            source.write_text(
                "VALUE = " + repr("invalid" + chr(0x00E1)) + "\n",
                encoding="utf-8",
            )

            self.assert_issue(root, "FORBIDDEN_SOURCE_TEXT")

    def test_modified_legacy_file_is_rejected(self) -> None:
        with self.fixture(include_legacy=True) as root:
            legacy = root / "src" / "legacy.py"
            legacy.write_text(
                legacy.read_text(encoding="utf-8") + "CHANGED = True\n",
                encoding="utf-8",
            )

            self.assert_issue(root, "LEGACY_HASH_MISMATCH")

    def assert_issue(self, root: Path, expected_code: str) -> None:
        report = validate_repository(root, MANIFEST_PATH)
        codes = {issue.code for issue in report.issues}
        self.assertIn(expected_code, codes, report.issues)

    def fixture(self, include_legacy: bool = False) -> _TemporaryDirectoryContext:
        temporary_directory = tempfile.TemporaryDirectory()
        root = Path(temporary_directory.name)
        governance = root / "governance"
        source = root / "src"
        governance.mkdir()
        source.mkdir()

        (governance / "index.md").write_text(
            "# Index\n\n[Records](records.md)\n",
            encoding="utf-8",
        )
        (governance / "records.md").write_text(
            "# Records\n\n"
            "| ID | Status | Planned phase |\n"
            "|---|---|---:|\n"
            "| GOV-001 | Active | 0 |\n",
            encoding="utf-8",
        )
        (source / "module.py").write_text("VALUE = 'valid'\n", encoding="utf-8")

        legacy_files: list[dict[str, str]] = []
        if include_legacy:
            legacy_path = source / "legacy.py"
            legacy_path.write_text(
                "VALUE = " + repr("legacy" + chr(0x00E1)) + "\n",
                encoding="utf-8",
            )
            legacy_files.append(
                {
                    "path": "src/legacy.py",
                    "sha256": hashlib.sha256(legacy_path.read_bytes()).hexdigest(),
                }
            )

        manifest = self.build_manifest(legacy_files)
        (governance / "constitution.manifest.json").write_text(
            json.dumps(manifest, indent=2),
            encoding="utf-8",
        )
        return _TemporaryDirectoryContext(temporary_directory)

    @staticmethod
    def build_manifest(legacy_files: list[dict[str, str]]) -> dict[str, Any]:
        return {
            "schema_version": "1.0.0",
            "governance_phase": 0,
            "enforcement": {
                "required_files": ["governance/constitution.manifest.json"],
                "ci_workflow": None,
                "required_ci_commands": [],
            },
            "constitution": {
                "root": "governance",
                "require_complete_markdown_inventory": True,
                "required_documents": [
                    {"path": "index.md", "required_headings": ["# Index"]},
                    {"path": "records.md", "required_headings": ["# Records"]},
                ],
            },
            "registries": [
                {
                    "name": "governance_records",
                    "path_glob": "governance/records.md",
                    "declaration_pattern": (
                        r"^\| (?P<identifier>GOV-[0-9]{3}) \|"
                    ),
                    "expected_identifiers": ["GOV-001"],
                }
            ],
            "table_contracts": [
                {
                    "name": "governance ownership",
                    "path": "governance/records.md",
                    "registry": "governance_records",
                    "key_column": "ID",
                    "required_columns": ["ID", "Status", "Planned phase"],
                    "constraints": [
                        {"column": "Planned phase", "type": "phase_range"}
                    ],
                }
            ],
            "phase_policy": {"allowed_phases": [0, 1]},
            "link_policy": {
                "roots": ["governance"],
                "extensions": [".md"],
                "validate_fragments": True,
            },
            "canonical_text_policy": {
                "roots": ["governance"],
                "extensions": [".md", ".json"],
                "ascii_only": True,
            },
            "source_text_policy": {
                "roots": ["src"],
                "extensions": [".py"],
                "forbid_non_ascii_letters": True,
                "forbidden_code_points": ["U+00E1"],
                "localized_resources": [],
                "legacy_ratchet": {
                    "expires_before_phase": 1,
                    "files": legacy_files,
                },
            },
        }


class _TemporaryDirectoryContext:
    def __init__(self, wrapped: tempfile.TemporaryDirectory[str]) -> None:
        self._wrapped = wrapped
        self.name = wrapped.name

    def __enter__(self) -> Path:
        return Path(self.name)

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self._wrapped.cleanup()


if __name__ == "__main__":
    unittest.main()
