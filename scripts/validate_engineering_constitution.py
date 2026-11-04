#!/usr/bin/env python3
"""Validate the versioned engineering constitution and its governance ratchets."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit


DEFAULT_MANIFEST = Path("docs/engineering-constitution/constitution.manifest.json")
EXTERNAL_LINK_SCHEMES = frozenset({"http", "https", "mailto"})


@dataclass(frozen=True, order=True)
class ValidationIssue:
    """One deterministic governance validation failure."""

    code: str
    path: str
    message: str


@dataclass
class ValidationReport:
    """Complete validation result with stable metrics for CI evidence."""

    issues: list[ValidationIssue] = field(default_factory=list)
    metrics: dict[str, int] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        return not self.issues

    def add(self, code: str, path: str | Path, message: str) -> None:
        self.issues.append(ValidationIssue(code=code, path=str(path), message=message))


class ConstitutionValidator:
    """Apply manifest-defined controls to one repository snapshot."""

    def __init__(self, repository_root: Path, manifest: dict[str, Any]) -> None:
        self.repository_root = repository_root.resolve()
        self.manifest = manifest
        self.report = ValidationReport()
        self.registry_values: dict[str, set[str]] = {}

    def validate(self) -> ValidationReport:
        if not self._validate_manifest_shape():
            return self.report

        self._validate_document_inventory()
        self._validate_enforcement_artifacts()
        self._validate_registries()
        self._validate_table_contracts()
        self._validate_links()
        self._validate_canonical_text()
        self._validate_source_text()
        self.report.issues.sort()
        return self.report

    def _validate_manifest_shape(self) -> bool:
        required_sections = {
            "schema_version": str,
            "governance_phase": int,
            "enforcement": dict,
            "constitution": dict,
            "registries": list,
            "table_contracts": list,
            "phase_policy": dict,
            "link_policy": dict,
            "canonical_text_policy": dict,
            "source_text_policy": dict,
        }
        is_valid = True
        for name, expected_type in required_sections.items():
            value = self.manifest.get(name)
            if not isinstance(value, expected_type) or isinstance(value, bool):
                self.report.add(
                    "MANIFEST_SCHEMA",
                    DEFAULT_MANIFEST,
                    f"Field '{name}' must be {expected_type.__name__}.",
                )
                is_valid = False
        schema_version = self.manifest.get("schema_version")
        if isinstance(schema_version, str) and re.fullmatch(
            r"[0-9]+\.[0-9]+\.[0-9]+", schema_version
        ) is None:
            self.report.add(
                "MANIFEST_SCHEMA",
                DEFAULT_MANIFEST,
                "Schema version must use semantic version notation.",
            )
            is_valid = False
        return is_valid

    def _repository_path(self, relative_path: str | Path) -> Path | None:
        candidate = (self.repository_root / relative_path).resolve()
        try:
            candidate.relative_to(self.repository_root)
        except ValueError:
            self.report.add(
                "PATH_ESCAPE",
                relative_path,
                "Manifest path resolves outside the repository root.",
            )
            return None
        return candidate

    def _relative_path(self, path: Path) -> str:
        return path.resolve().relative_to(self.repository_root).as_posix()

    def _read_text(self, path: Path) -> str | None:
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError as error:
            self.report.add("INVALID_UTF8", self._relative_path(path), str(error))
        except OSError as error:
            self.report.add("READ_FAILURE", self._relative_path(path), str(error))
        return None

    def _validate_document_inventory(self) -> None:
        policy = self.manifest["constitution"]
        root = self._repository_path(str(policy.get("root", "")))
        documents = policy.get("required_documents")
        if root is None:
            return
        if not isinstance(documents, list):
            self.report.add(
                "MANIFEST_SCHEMA",
                DEFAULT_MANIFEST,
                "Constitution required_documents must be a list.",
            )
            return

        declared_paths: list[str] = []
        for record in documents:
            if not isinstance(record, dict) or not isinstance(record.get("path"), str):
                self.report.add(
                    "MANIFEST_SCHEMA",
                    DEFAULT_MANIFEST,
                    "Each required document must define a string path.",
                )
                continue
            relative_document = Path(str(policy.get("root", ""))) / record["path"]
            declared_paths.append(relative_document.as_posix())
            document = self._repository_path(relative_document)
            if document is None:
                continue
            if not document.is_file():
                self.report.add(
                    "MISSING_DOCUMENT",
                    relative_document,
                    "Required constitution document does not exist.",
                )
                continue
            content = self._read_text(document)
            if content is None:
                continue
            lines = set(content.splitlines())
            headings = record.get("required_headings", [])
            if not isinstance(headings, list) or not all(
                isinstance(item, str) for item in headings
            ):
                self.report.add(
                    "MANIFEST_SCHEMA",
                    DEFAULT_MANIFEST,
                    f"Document '{record['path']}' has invalid required_headings.",
                )
                continue
            for heading in headings:
                if heading not in lines:
                    self.report.add(
                        "MISSING_HEADING",
                        relative_document,
                        f"Required heading is missing: {heading}",
                    )

        for path, count in Counter(declared_paths).items():
            if count > 1:
                self.report.add(
                    "DUPLICATE_DOCUMENT",
                    path,
                    "Document appears more than once in the manifest.",
                )

        if policy.get("require_complete_markdown_inventory") is True and root.is_dir():
            actual_paths = {
                self._relative_path(path) for path in root.rglob("*.md") if path.is_file()
            }
            declared_set = set(declared_paths)
            for path in sorted(actual_paths - declared_set):
                self.report.add(
                    "UNDECLARED_DOCUMENT",
                    path,
                    "Markdown document is not declared in the constitution manifest.",
                )
            for path in sorted(declared_set - actual_paths):
                if not (self.repository_root / path).is_file():
                    continue
                self.report.add(
                    "DOCUMENT_EXTENSION",
                    path,
                    "Complete Markdown inventory contains a non-Markdown document.",
                )

        self.report.metrics["documents"] = len(set(declared_paths))

    def _validate_enforcement_artifacts(self) -> None:
        policy = self.manifest["enforcement"]
        required_files = policy.get("required_files")
        workflow_value = policy.get("ci_workflow")
        required_commands = policy.get("required_ci_commands")
        if (
            not isinstance(required_files, list)
            or not all(isinstance(item, str) for item in required_files)
            or (workflow_value is not None and not isinstance(workflow_value, str))
            or not isinstance(required_commands, list)
            or not all(isinstance(item, str) for item in required_commands)
        ):
            self.report.add(
                "MANIFEST_SCHEMA",
                DEFAULT_MANIFEST,
                "Enforcement files, workflow, and CI commands have invalid types.",
            )
            return

        for path_value, count in Counter(required_files).items():
            if count > 1:
                self.report.add(
                    "DUPLICATE_ENFORCEMENT_FILE",
                    DEFAULT_MANIFEST,
                    f"Enforcement file appears more than once: {path_value}",
                )
            path = self._repository_path(path_value)
            if path is not None and not path.is_file():
                self.report.add(
                    "MISSING_ENFORCEMENT_FILE",
                    path_value,
                    "Required enforcement file does not exist.",
                )

        if workflow_value is not None:
            workflow = self._repository_path(workflow_value)
            if workflow is not None and workflow.is_file():
                content = self._read_text(workflow)
                if content is not None:
                    for command in required_commands:
                        if command not in content:
                            self.report.add(
                                "MISSING_CI_COMMAND",
                                workflow_value,
                                f"Required governance command is absent: {command}",
                            )
            elif workflow is not None:
                self.report.add(
                    "MISSING_CI_WORKFLOW",
                    workflow_value,
                    "Required governance workflow does not exist.",
                )
        elif required_commands:
            self.report.add(
                "MANIFEST_SCHEMA",
                DEFAULT_MANIFEST,
                "CI commands require a workflow path.",
            )

        self.report.metrics["enforcement_files"] = len(set(required_files))
        self.report.metrics["ci_commands"] = len(set(required_commands))

    def _validate_registries(self) -> None:
        total_identifiers = 0
        seen_registry_names: set[str] = set()
        for registry in self.manifest["registries"]:
            if not isinstance(registry, dict):
                self.report.add(
                    "MANIFEST_SCHEMA",
                    DEFAULT_MANIFEST,
                    "Each registry must be an object.",
                )
                continue
            name = registry.get("name")
            path_glob = registry.get("path_glob")
            pattern_text = registry.get("declaration_pattern")
            expected = registry.get("expected_identifiers")
            if (
                not isinstance(name, str)
                or not isinstance(path_glob, str)
                or not isinstance(pattern_text, str)
                or not isinstance(expected, list)
                or not all(isinstance(item, str) for item in expected)
            ):
                self.report.add(
                    "MANIFEST_SCHEMA",
                    DEFAULT_MANIFEST,
                    "Registry name, path_glob, declaration_pattern, and identifiers are required.",
                )
                continue
            if name in seen_registry_names:
                self.report.add(
                    "DUPLICATE_REGISTRY",
                    DEFAULT_MANIFEST,
                    f"Registry name is duplicated: {name}",
                )
                continue
            seen_registry_names.add(name)

            try:
                pattern = re.compile(pattern_text, re.MULTILINE)
            except re.error as error:
                self.report.add(
                    "INVALID_PATTERN",
                    DEFAULT_MANIFEST,
                    f"Registry '{name}' pattern is invalid: {error}",
                )
                continue
            if "identifier" not in pattern.groupindex:
                self.report.add(
                    "INVALID_PATTERN",
                    DEFAULT_MANIFEST,
                    f"Registry '{name}' pattern must define an identifier group.",
                )
                continue

            matches: list[str] = []
            files = sorted(self.repository_root.glob(path_glob))
            if not files:
                self.report.add(
                    "EMPTY_REGISTRY_SOURCE",
                    path_glob,
                    f"Registry '{name}' matched no files.",
                )
            for path in files:
                if not path.is_file():
                    continue
                try:
                    path.resolve().relative_to(self.repository_root)
                except ValueError:
                    self.report.add(
                        "PATH_ESCAPE",
                        path,
                        f"Registry '{name}' matched a file outside the repository.",
                    )
                    continue
                content = self._read_text(path)
                if content is not None:
                    matches.extend(
                        match.group("identifier") for match in pattern.finditer(content)
                    )

            duplicate_expected = sorted(
                identifier
                for identifier, count in Counter(expected).items()
                if count > 1
            )
            for identifier in duplicate_expected:
                self.report.add(
                    "DUPLICATE_EXPECTED_IDENTIFIER",
                    DEFAULT_MANIFEST,
                    f"Registry '{name}' repeats expected identifier '{identifier}'.",
                )

            duplicate_matches = sorted(
                identifier
                for identifier, count in Counter(matches).items()
                if count > 1
            )
            for identifier in duplicate_matches:
                self.report.add(
                    "DUPLICATE_IDENTIFIER",
                    path_glob,
                    f"Registry '{name}' declares '{identifier}' more than once.",
                )

            expected_set = set(expected)
            actual_set = set(matches)
            for identifier in sorted(expected_set - actual_set):
                self.report.add(
                    "MISSING_IDENTIFIER",
                    path_glob,
                    f"Registry '{name}' is missing '{identifier}'.",
                )
            for identifier in sorted(actual_set - expected_set):
                self.report.add(
                    "UNDECLARED_IDENTIFIER",
                    path_glob,
                    f"Registry '{name}' contains undeclared identifier '{identifier}'.",
                )

            self.registry_values[name] = actual_set
            total_identifiers += len(actual_set)

        self.report.metrics["registries"] = len(self.registry_values)
        self.report.metrics["identifiers"] = total_identifiers

    @staticmethod
    def _split_table_row(line: str) -> list[str]:
        return [cell.strip() for cell in line.strip().strip("|").split("|")]

    def _find_table(
        self, content: str, required_columns: list[str]
    ) -> tuple[list[str], list[list[str]]] | None:
        lines = content.splitlines()
        for index, line in enumerate(lines[:-1]):
            if not line.lstrip().startswith("|"):
                continue
            header = self._split_table_row(line)
            if not set(required_columns).issubset(header):
                continue
            separator = self._split_table_row(lines[index + 1])
            if len(separator) != len(header) or not all(
                re.fullmatch(r":?-{3,}:?", cell) for cell in separator
            ):
                continue
            rows: list[list[str]] = []
            for row_line in lines[index + 2 :]:
                if not row_line.lstrip().startswith("|"):
                    break
                row = self._split_table_row(row_line)
                if len(row) == len(header):
                    rows.append(row)
            return header, rows
        return None

    def _validate_table_contracts(self) -> None:
        allowed_phases = self.manifest["phase_policy"].get("allowed_phases", [])
        if not isinstance(allowed_phases, list) or not all(
            isinstance(phase, int) and not isinstance(phase, bool)
            for phase in allowed_phases
        ):
            self.report.add(
                "MANIFEST_SCHEMA",
                DEFAULT_MANIFEST,
                "Phase policy allowed_phases must be a list of integers.",
            )
            allowed_phase_set: set[int] = set()
        else:
            allowed_phase_set = set(allowed_phases)

        validated_tables = 0
        for contract in self.manifest["table_contracts"]:
            if not isinstance(contract, dict):
                self.report.add(
                    "MANIFEST_SCHEMA",
                    DEFAULT_MANIFEST,
                    "Each table contract must be an object.",
                )
                continue
            path_value = contract.get("path")
            registry_name = contract.get("registry")
            key_column = contract.get("key_column")
            required_columns = contract.get("required_columns")
            if (
                not isinstance(path_value, str)
                or not isinstance(registry_name, str)
                or not isinstance(key_column, str)
                or not isinstance(required_columns, list)
                or not all(isinstance(column, str) for column in required_columns)
            ):
                self.report.add(
                    "MANIFEST_SCHEMA",
                    DEFAULT_MANIFEST,
                    "Table path, registry, key column, and required columns are required.",
                )
                continue
            if key_column not in required_columns:
                self.report.add(
                    "MANIFEST_SCHEMA",
                    DEFAULT_MANIFEST,
                    f"Table key column must be required: {key_column}",
                )
                continue
            path = self._repository_path(path_value)
            if path is None:
                continue
            if not path.is_file():
                self.report.add(
                    "MISSING_TABLE_DOCUMENT",
                    path_value,
                    "Table contract document does not exist.",
                )
                continue
            content = self._read_text(path)
            if content is None:
                continue
            table = self._find_table(content, required_columns)
            if table is None:
                self.report.add(
                    "MISSING_TABLE",
                    path_value,
                    f"Required table was not found for contract '{contract.get('name', '')}'.",
                )
                continue
            header, rows = table
            indexes = {column: header.index(column) for column in required_columns}
            keys = [row[indexes[key_column]] for row in rows]
            for key, count in Counter(keys).items():
                if count > 1:
                    self.report.add(
                        "DUPLICATE_TABLE_KEY",
                        path_value,
                        f"Table key appears more than once: {key}",
                    )

            registry_keys = self.registry_values.get(registry_name)
            if registry_keys is None:
                self.report.add(
                    "UNKNOWN_REGISTRY",
                    DEFAULT_MANIFEST,
                    f"Table contract references unknown registry '{registry_name}'.",
                )
            else:
                table_keys = set(keys)
                for key in sorted(registry_keys - table_keys):
                    self.report.add(
                        "MISSING_TABLE_KEY",
                        path_value,
                        f"Registry identifier is missing from the table: {key}",
                    )
                for key in sorted(table_keys - registry_keys):
                    self.report.add(
                        "UNKNOWN_TABLE_KEY",
                        path_value,
                        f"Table contains an identifier outside its registry: {key}",
                    )

            constraints = contract.get("constraints", [])
            if not isinstance(constraints, list):
                self.report.add(
                    "MANIFEST_SCHEMA",
                    DEFAULT_MANIFEST,
                    "Table constraints must be a list.",
                )
                continue
            for row in rows:
                key = row[indexes[key_column]]
                for constraint in constraints:
                    self._validate_table_cell(
                        constraint,
                        header,
                        row,
                        key,
                        path_value,
                        allowed_phase_set,
                    )
            validated_tables += 1

        self.report.metrics["table_contracts"] = validated_tables

    def _validate_table_cell(
        self,
        constraint: Any,
        header: list[str],
        row: list[str],
        key: str,
        path: str,
        allowed_phases: set[int],
    ) -> None:
        if not isinstance(constraint, dict):
            self.report.add(
                "MANIFEST_SCHEMA",
                DEFAULT_MANIFEST,
                "Each table constraint must be an object.",
            )
            return
        column = constraint.get("column")
        constraint_type = constraint.get("type")
        if not isinstance(column, str) or column not in header:
            self.report.add(
                "MANIFEST_SCHEMA",
                DEFAULT_MANIFEST,
                f"Constraint column is absent from the table header: {column}",
            )
            return
        value = row[header.index(column)]

        if constraint_type == "phase_range":
            match = re.fullmatch(r"([0-9]+)(?:-([0-9]+))?", value)
            if match is None:
                self.report.add(
                    "INVALID_PHASE",
                    path,
                    f"Row '{key}' has an invalid phase value in '{column}': {value}",
                )
                return
            start = int(match.group(1))
            end = int(match.group(2) or match.group(1))
            if start > end or any(
                phase not in allowed_phases for phase in range(start, end + 1)
            ):
                self.report.add(
                    "INVALID_PHASE",
                    path,
                    f"Row '{key}' references a disallowed phase range: {value}",
                )
        elif constraint_type == "pattern":
            pattern_text = constraint.get("pattern")
            if not isinstance(pattern_text, str):
                self.report.add(
                    "MANIFEST_SCHEMA",
                    DEFAULT_MANIFEST,
                    f"Pattern constraint for '{column}' has no pattern.",
                )
                return
            try:
                is_match = re.fullmatch(pattern_text, value) is not None
            except re.error as error:
                self.report.add(
                    "INVALID_PATTERN",
                    DEFAULT_MANIFEST,
                    f"Constraint pattern for '{column}' is invalid: {error}",
                )
                return
            if not is_match:
                self.report.add(
                    "INVALID_TABLE_VALUE",
                    path,
                    f"Row '{key}' has an invalid value in '{column}': {value}",
                )
        elif constraint_type == "allowed_values":
            values = constraint.get("values")
            if not isinstance(values, list) or not all(
                isinstance(item, str) for item in values
            ):
                self.report.add(
                    "MANIFEST_SCHEMA",
                    DEFAULT_MANIFEST,
                    f"Allowed-values constraint for '{column}' is invalid.",
                )
                return
            if value not in values:
                self.report.add(
                    "INVALID_TABLE_VALUE",
                    path,
                    f"Row '{key}' has a disallowed value in '{column}': {value}",
                )
        else:
            self.report.add(
                "MANIFEST_SCHEMA",
                DEFAULT_MANIFEST,
                f"Unknown table constraint type: {constraint_type}",
            )

    @staticmethod
    def _heading_anchors(content: str) -> set[str]:
        anchors: set[str] = set()
        counts: Counter[str] = Counter()
        for line in content.splitlines():
            match = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", line)
            if match is None:
                continue
            base = match.group(1).strip().lower()
            base = re.sub(r"[^\w\- ]", "", base)
            base = re.sub(r"\s+", "-", base)
            count = counts[base]
            anchor = base if count == 0 else f"{base}-{count}"
            counts[base] += 1
            anchors.add(anchor)
        return anchors

    def _validate_links(self) -> None:
        policy = self.manifest["link_policy"]
        roots = policy.get("roots", [])
        extensions = policy.get("extensions", [])
        validate_fragments = policy.get("validate_fragments") is True
        if not isinstance(roots, list) or not isinstance(extensions, list):
            self.report.add(
                "MANIFEST_SCHEMA",
                DEFAULT_MANIFEST,
                "Link policy roots and extensions must be lists.",
            )
            return

        checked_links = 0
        link_pattern = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
        for root_value in roots:
            if not isinstance(root_value, str):
                continue
            root = self._repository_path(root_value)
            if root is None:
                continue
            if not root.is_dir():
                self.report.add(
                    "MISSING_LINK_ROOT",
                    root_value,
                    "Configured link root does not exist or is not a directory.",
                )
                continue
            for path in sorted(item for item in root.rglob("*") if item.is_file()):
                if path.suffix not in extensions:
                    continue
                content = self._read_text(path)
                if content is None:
                    continue
                for raw_target in link_pattern.findall(content):
                    target_text = raw_target.strip()
                    if target_text.startswith("<") and ">" in target_text:
                        target_text = target_text[1 : target_text.index(">")]
                    else:
                        target_text = target_text.split(maxsplit=1)[0]
                    parsed = urlsplit(target_text)
                    if parsed.scheme.lower() in EXTERNAL_LINK_SCHEMES:
                        continue
                    if parsed.scheme or parsed.netloc:
                        self.report.add(
                            "UNSUPPORTED_LINK",
                            self._relative_path(path),
                            f"Unsupported link target: {target_text}",
                        )
                        continue
                    checked_links += 1
                    if parsed.path:
                        target = (path.parent / unquote(parsed.path)).resolve()
                    else:
                        target = path.resolve()
                    try:
                        target.relative_to(self.repository_root)
                    except ValueError:
                        self.report.add(
                            "LINK_ESCAPE",
                            self._relative_path(path),
                            f"Link resolves outside the repository: {target_text}",
                        )
                        continue
                    if not target.exists():
                        self.report.add(
                            "BROKEN_LINK",
                            self._relative_path(path),
                            f"Link target does not exist: {target_text}",
                        )
                        continue
                    if parsed.fragment and validate_fragments:
                        if not target.is_file() or target.suffix != ".md":
                            self.report.add(
                                "INVALID_LINK_FRAGMENT",
                                self._relative_path(path),
                                f"Fragment target is not a Markdown file: {target_text}",
                            )
                            continue
                        target_content = self._read_text(target)
                        if target_content is None:
                            continue
                        fragment = unquote(parsed.fragment).lower()
                        if fragment not in self._heading_anchors(target_content):
                            self.report.add(
                                "BROKEN_LINK_FRAGMENT",
                                self._relative_path(path),
                                f"Heading fragment does not exist: {target_text}",
                            )

        self.report.metrics["local_links"] = checked_links

    def _iter_policy_files(self, policy: dict[str, Any]) -> list[Path]:
        roots = policy.get("roots", [])
        extensions = policy.get("extensions", [])
        if not isinstance(roots, list) or not isinstance(extensions, list):
            self.report.add(
                "MANIFEST_SCHEMA",
                DEFAULT_MANIFEST,
                "Text policy roots and extensions must be lists.",
            )
            return []
        extension_set = {item for item in extensions if isinstance(item, str)}
        paths: set[Path] = set()
        for root_value in roots:
            if not isinstance(root_value, str):
                continue
            root = self._repository_path(root_value)
            if root is None:
                continue
            if not root.is_dir():
                self.report.add(
                    "MISSING_TEXT_ROOT",
                    root_value,
                    "Configured text root does not exist or is not a directory.",
                )
                continue
            paths.update(
                path
                for path in root.rglob("*")
                if path.is_file() and path.suffix in extension_set
            )
        return sorted(paths)

    def _validate_canonical_text(self) -> None:
        policy = self.manifest["canonical_text_policy"]
        files = self._iter_policy_files(policy)
        for path in files:
            content = self._read_text(path)
            if content is None:
                continue
            if policy.get("ascii_only") is True and not content.isascii():
                code_points = sorted(
                    {f"U+{ord(character):04X}" for character in content if not character.isascii()}
                )
                self.report.add(
                    "NON_ASCII_CANONICAL_TEXT",
                    self._relative_path(path),
                    f"Canonical text contains non-ASCII code points: {', '.join(code_points)}",
                )
        self.report.metrics["canonical_text_files"] = len(files)

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(65536), b""):
                digest.update(block)
        return digest.hexdigest()

    @staticmethod
    def _is_forbidden_source_character(
        character: str,
        explicit_forbidden: set[str],
        forbid_non_ascii_letters: bool,
    ) -> bool:
        if character in explicit_forbidden:
            return True
        return (
            forbid_non_ascii_letters
            and not character.isascii()
            and unicodedata.category(character).startswith("L")
        )

    def _validate_source_text(self) -> None:
        policy = self.manifest["source_text_policy"]
        code_points = policy.get("forbidden_code_points", [])
        if not isinstance(code_points, list) or not all(
            isinstance(item, str) and re.fullmatch(r"U\+[0-9A-Fa-f]{4,6}", item)
            for item in code_points
        ):
            self.report.add(
                "MANIFEST_SCHEMA",
                DEFAULT_MANIFEST,
                "Source forbidden_code_points must use U+ hexadecimal notation.",
            )
            return
        forbidden = {chr(int(value[2:], 16)) for value in code_points}
        forbid_non_ascii_letters = policy.get("forbid_non_ascii_letters")
        if not isinstance(forbid_non_ascii_letters, bool):
            self.report.add(
                "MANIFEST_SCHEMA",
                DEFAULT_MANIFEST,
                "Source forbid_non_ascii_letters must be a boolean.",
            )
            return

        localized_values = policy.get("localized_resources", [])
        if not isinstance(localized_values, list) or not all(
            isinstance(item, str) for item in localized_values
        ):
            self.report.add(
                "MANIFEST_SCHEMA",
                DEFAULT_MANIFEST,
                "Localized resources must be a list of paths.",
            )
            return
        localized = set(localized_values)
        for path_value in sorted(localized):
            path = self._repository_path(path_value)
            if path is not None and not path.is_file():
                self.report.add(
                    "MISSING_LOCALIZED_RESOURCE",
                    path_value,
                    "Declared localized resource does not exist.",
                )

        ratchet = policy.get("legacy_ratchet", {})
        ratchet_files = ratchet.get("files", []) if isinstance(ratchet, dict) else []
        expiry = ratchet.get("expires_before_phase") if isinstance(ratchet, dict) else None
        current_phase = self.manifest["governance_phase"]
        if not isinstance(expiry, int) or isinstance(expiry, bool):
            self.report.add(
                "MANIFEST_SCHEMA",
                DEFAULT_MANIFEST,
                "Legacy ratchet must define an integer expiry phase.",
            )
            return
        if not isinstance(ratchet_files, list):
            self.report.add(
                "MANIFEST_SCHEMA",
                DEFAULT_MANIFEST,
                "Legacy ratchet files must be a list.",
            )
            return
        if current_phase >= expiry and ratchet_files:
            self.report.add(
                "EXPIRED_LEGACY_RATCHET",
                DEFAULT_MANIFEST,
                f"Legacy source exceptions expired before phase {expiry}.",
            )

        frozen: dict[str, str] = {}
        for entry in ratchet_files:
            if (
                not isinstance(entry, dict)
                or not isinstance(entry.get("path"), str)
                or not isinstance(entry.get("sha256"), str)
                or re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]) is None
            ):
                self.report.add(
                    "MANIFEST_SCHEMA",
                    DEFAULT_MANIFEST,
                    "Each legacy ratchet entry requires a path and lowercase SHA-256.",
                )
                continue
            path_value = entry["path"]
            if path_value in frozen:
                self.report.add(
                    "DUPLICATE_LEGACY_ENTRY",
                    DEFAULT_MANIFEST,
                    f"Legacy path appears more than once: {path_value}",
                )
                continue
            frozen[path_value] = entry["sha256"]
            path = self._repository_path(path_value)
            if path is None:
                continue
            if not path.is_file():
                self.report.add(
                    "MISSING_LEGACY_FILE",
                    path_value,
                    "Frozen legacy file does not exist.",
                )
                continue
            actual_hash = self._sha256(path)
            if actual_hash != entry["sha256"]:
                self.report.add(
                    "LEGACY_HASH_MISMATCH",
                    path_value,
                    "Frozen legacy file changed and must be remediated instead of rebaselined.",
                )
            content = self._read_text(path)
            if content is not None and not any(
                self._is_forbidden_source_character(
                    character,
                    forbidden,
                    forbid_non_ascii_letters,
                )
                for character in content
            ):
                self.report.add(
                    "UNNECESSARY_LEGACY_ENTRY",
                    path_value,
                    "Legacy exception has no forbidden code point and must be removed.",
                )

        overlap = localized.intersection(frozen)
        for path_value in sorted(overlap):
            self.report.add(
                "OVERLAPPING_TEXT_EXCEPTION",
                path_value,
                "A file cannot be both a localized resource and a frozen legacy file.",
            )

        files = self._iter_policy_files(policy)
        scanned_paths = {self._relative_path(path) for path in files}
        for path_value in sorted(frozen):
            if path_value not in scanned_paths:
                self.report.add(
                    "LEGACY_FILE_OUTSIDE_POLICY",
                    path_value,
                    "Legacy exception is outside the governed source inventory.",
                )
        for path_value in sorted(localized):
            if path_value not in scanned_paths:
                self.report.add(
                    "LOCALIZED_FILE_OUTSIDE_POLICY",
                    path_value,
                    "Localized resource is outside the governed source inventory.",
                )

        for path in files:
            relative_path = self._relative_path(path)
            if relative_path in localized or relative_path in frozen:
                continue
            content = self._read_text(path)
            if content is None:
                continue
            violations = sorted(
                {
                    f"U+{ord(character):04X}"
                    for character in content
                    if self._is_forbidden_source_character(
                        character,
                        forbidden,
                        forbid_non_ascii_letters,
                    )
                }
            )
            if violations:
                self.report.add(
                    "FORBIDDEN_SOURCE_TEXT",
                    relative_path,
                    f"Source contains forbidden code points: {', '.join(violations)}",
                )

        self.report.metrics["source_text_files"] = len(files)
        self.report.metrics["localized_resources"] = len(localized)
        self.report.metrics["frozen_legacy_files"] = len(frozen)


def validate_repository(
    repository_root: Path | str,
    manifest_path: Path | str = DEFAULT_MANIFEST,
) -> ValidationReport:
    """Validate a repository without raising for expected governance failures."""

    root = Path(repository_root).resolve()
    manifest_candidate = Path(manifest_path)
    manifest = (
        manifest_candidate.resolve()
        if manifest_candidate.is_absolute()
        else (root / manifest_candidate).resolve()
    )
    report = ValidationReport()
    try:
        manifest.relative_to(root)
    except ValueError:
        report.add(
            "MANIFEST_PATH_ESCAPE",
            manifest,
            "Manifest must be located inside the repository root.",
        )
        return report
    if not manifest.is_file():
        report.add("MISSING_MANIFEST", manifest, "Governance manifest does not exist.")
        return report
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        report.add("INVALID_MANIFEST", manifest, str(error))
        return report
    if not isinstance(data, dict):
        report.add("INVALID_MANIFEST", manifest, "Manifest root must be an object.")
        return report
    return ConstitutionValidator(root, data).validate()


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate the repository engineering constitution."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root. Defaults to the parent of the scripts directory.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Manifest path relative to the repository root.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format for validation evidence.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_argument_parser().parse_args(argv)
    report = validate_repository(args.repo_root, args.manifest)
    if args.format == "json":
        payload = {
            "valid": report.is_valid,
            "metrics": report.metrics,
            "issues": [asdict(issue) for issue in report.issues],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif report.is_valid:
        metrics = ", ".join(
            f"{name}={value}" for name, value in sorted(report.metrics.items())
        )
        print(f"PASS: engineering constitution validation completed ({metrics}).")
    else:
        print(
            f"FAIL: engineering constitution validation found {len(report.issues)} issue(s).",
            file=sys.stderr,
        )
        for issue in report.issues:
            print(
                f"{issue.code} | {issue.path} | {issue.message}",
                file=sys.stderr,
            )
    return 0 if report.is_valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
