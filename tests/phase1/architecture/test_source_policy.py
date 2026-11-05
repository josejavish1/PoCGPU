"""Static source controls for universality, explicit inputs, and language boundaries."""

from __future__ import annotations

import ast
import tokenize
import unicodedata
from dataclasses import MISSING, fields, is_dataclass
from pathlib import Path

import pocgpu.domain as domain_package

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPOSITORY_ROOT / "src" / "pocgpu"
CONTEXT_NAMES = frozenset(
    {
        "company",
        "context",
        "industry",
        "jurisdiction",
        "locale",
        "organization",
        "tenant",
        "vertical",
    }
)
PROHIBITED_CONTRACT_NAMES = frozenset(
    {"api_key", "credential", "password", "prompt", "secret", "token"}
)
NON_ENGLISH_TERMS = tuple(
    bytes.fromhex(encoded).decode("ascii")
    for encoded in (
        "656d7072657361",
        "636f737465",
        "636f73746f",
        "70726563696f",
        "7365727669646f72",
        "6e756265",
        "7573756172696f",
    )
)


def source_files() -> tuple[Path, ...]:
    return tuple(sorted(PACKAGE_ROOT.rglob("*.py")))


def test_canonical_source_contains_only_ascii_language_text() -> None:
    violations: list[str] = []
    for path in source_files():
        content = path.read_text(encoding="utf-8")
        for line_number, line in enumerate(content.splitlines(), start=1):
            if any(
                ord(character) > 127 and unicodedata.category(character).startswith("L")
                for character in line
            ):
                violations.append(
                    f"{path.relative_to(REPOSITORY_ROOT)}:{line_number}:non-ASCII letter"
                )
        with path.open("rb") as source:
            for token in tokenize.tokenize(source.readline):
                if token.type not in {tokenize.COMMENT, tokenize.STRING, tokenize.NAME}:
                    continue
                lowered = token.string.casefold()
                if any(term in lowered for term in NON_ENGLISH_TERMS):
                    violations.append(
                        f"{path.relative_to(REPOSITORY_ROOT)}:{token.start[0]}:language term"
                    )
    assert violations == []


def test_domain_dataclasses_have_no_implicit_field_defaults() -> None:
    violations: list[str] = []
    for path in source_files():
        if path.parent.name != "domain" and "domain" not in path.parts:
            continue
        module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in module.body:
            if not isinstance(node, ast.ClassDef):
                continue
            decorators = {
                ast.unparse(item.func if isinstance(item, ast.Call) else item)
                for item in node.decorator_list
            }
            if "dataclass" not in decorators:
                continue
            for statement in node.body:
                if isinstance(statement, ast.AnnAssign) and statement.value is not None:
                    violations.append(
                        f"{path.relative_to(REPOSITORY_ROOT)}:{statement.lineno}:field default"
                    )
    assert violations == []


def test_source_has_no_context_specific_literal_branches() -> None:
    violations: list[str] = []
    for path in source_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.If, ast.IfExp, ast.Match)):
                continue
            names = {item.id.casefold() for item in ast.walk(node) if isinstance(item, ast.Name)}
            strings = {
                item.value
                for item in ast.walk(node)
                if isinstance(item, ast.Constant) and isinstance(item.value, str)
            }
            if names.intersection(CONTEXT_NAMES) and strings:
                violations.append(f"{path.relative_to(REPOSITORY_ROOT)}:{node.lineno}")
    assert violations == []


def test_boundary_contracts_exclude_confidential_payload_fields() -> None:
    from pocgpu.contracts import v1

    violations: list[str] = []
    for value in vars(v1).values():
        model_fields = getattr(value, "model_fields", None)
        if not isinstance(model_fields, dict):
            continue
        forbidden = set(model_fields).intersection(PROHIBITED_CONTRACT_NAMES)
        violations.extend(f"{value.__name__}.{name}" for name in sorted(forbidden))
    assert violations == []


def test_domain_package_does_not_export_mutable_dataclass_defaults() -> None:
    for value in vars(domain_package).values():
        if not isinstance(value, type) or not is_dataclass(value):
            continue
        assert all(
            field.default is MISSING and field.default_factory is MISSING for field in fields(value)
        )
