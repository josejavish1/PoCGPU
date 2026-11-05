"""AST gates for the canonical package dependency direction."""

from __future__ import annotations

import ast
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPOSITORY_ROOT / "src" / "pocgpu"
FORBIDDEN_DOMAIN_ROOTS = frozenset(
    {
        "fastapi",
        "flask",
        "httpx",
        "os",
        "pathlib",
        "pydantic",
        "random",
        "requests",
        "socket",
        "subprocess",
    }
)


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def test_domain_uses_standard_library_and_internal_domain_only() -> None:
    domain = PACKAGE_ROOT / "domain"
    assert domain.is_dir()
    violations: list[str] = []
    for path in domain.rglob("*.py"):
        for module in imported_modules(path):
            root = module.split(".")[0]
            if root in FORBIDDEN_DOMAIN_ROOTS:
                violations.append(f"{path.relative_to(REPOSITORY_ROOT)} imports {module}")
            if module.startswith(("pocgpu.adapters", "pocgpu.application", "pocgpu.contracts")):
                violations.append(f"{path.relative_to(REPOSITORY_ROOT)} imports {module}")
    assert violations == []


def test_application_does_not_import_concrete_adapters() -> None:
    application = PACKAGE_ROOT / "application"
    assert application.is_dir()
    violations = [
        f"{path.relative_to(REPOSITORY_ROOT)} imports {module}"
        for path in application.rglob("*.py")
        for module in imported_modules(path)
        if module.startswith("pocgpu.adapters")
    ]
    assert violations == []


def test_canonical_package_never_imports_legacy_src_package() -> None:
    violations = [
        f"{path.relative_to(REPOSITORY_ROOT)} imports {module}"
        for path in PACKAGE_ROOT.rglob("*.py")
        for module in imported_modules(path)
        if module == "src" or module.startswith("src.")
    ]
    assert violations == []
