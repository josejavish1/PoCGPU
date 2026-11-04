"""Architectural Fitness Gate: Pure Hexagonal Domain Layer Purity.

Asserts via AST static analysis that src/domain/ contains zero infrastructure,
filesystem, network, database, or UI imports.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOMAIN_DIR = REPO_ROOT / "src" / "domain"

FORBIDDEN_DOMAIN_MODULES = {
    "os",
    "sys",
    "pathlib",
    "shutil",
    "subprocess",
    "socket",
    "requests",
    "urllib",
    "http",
    "httpx",
    "aiohttp",
    "sqlite3",
    "psycopg2",
    "sqlalchemy",
    "redis",
    "pymongo",
    "boto3",
    "google",
    "google.cloud",
    "azure",
    "fastapi",
    "uvicorn",
    "flask",
    "streamlit",
    "jinja2",
    "pandas",
    "polars",
    "numpy",
    "torch",
    "vllm",
    "src.infrastructure",
    "src.adapters",
    "src.application",
    "src.ui",
}


def test_domain_hexagonal_purity() -> None:
    """Verifies that no domain module imports infrastructure, network, or filesystem packages."""
    assert DOMAIN_DIR.is_dir(), f"Domain directory not found at: {DOMAIN_DIR}"

    domain_files = list(DOMAIN_DIR.rglob("*.py"))
    assert len(domain_files) > 0, "No domain Python files found to inspect."

    violations = []

    for py_file in domain_files:
        content = py_file.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(py_file))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root_pkg = alias.name.split(".")[0]
                    if root_pkg in FORBIDDEN_DOMAIN_MODULES or alias.name in FORBIDDEN_DOMAIN_MODULES:
                        violations.append(
                            f"{py_file.name}:{node.lineno} imports forbidden module '{alias.name}'"
                        )
            elif isinstance(node, ast.ImportFrom) and node.module:
                root_pkg = node.module.split(".")[0]
                if root_pkg in FORBIDDEN_DOMAIN_MODULES or node.module in FORBIDDEN_DOMAIN_MODULES:
                    violations.append(
                        f"{py_file.name}:{node.lineno} imports forbidden module '{node.module}'"
                    )

    assert not violations, (
        f"Hexagonal Domain Purity Violations Detected ({len(violations)}):\n"
        + "\n".join(f" - {v}" for v in violations)
    )


if __name__ == "__main__":
    test_domain_hexagonal_purity()
    print("PASS: 100% Pure Hexagonal Domain Certified (0 violations).")
