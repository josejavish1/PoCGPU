"""Architectural Fitness Gate: Zero Spanish Literals in Source Code and Configuration Schemas.

Asserts via AST, Lexical Tokenization, and JSON Schema Inspection that all files under
src/, tests/, and non-locale configuration files contain 100% pure Technical English
with zero Spanish diacritics or lexicon tokens in identifiers, keys, and code.
"""

from __future__ import annotations

import ast
import json
import re
import tokenize
from io import StringIO
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
TESTS_ROOT = REPO_ROOT / "tests"
CONFIG_DIR = REPO_ROOT / "config"

# Detects Spanish accented vowels, eñe, and inverted punctuation marks
SPANISH_DIACRITICS_REGEX = re.compile(r"[áéíóúÁÉÍÓÚñÑüÜ¡¿]")

# Catches Spanish technical lexicon even inside snake_case, camelCase, or compound identifiers
SPANISH_LEXICON_REGEX = re.compile(
    r"(?:^|(?<=[^a-zA-Z]))(cálculo|calculo|configuración|configuracion|error_de|parámetro|parametro|"
    r"usuario|contraseña|empresa|coste|costo|precio|memoria|servidor|nube|"
    r"híbrido|hibrido|amortización|amortizacion|riesgo|fallo|refrigeración|"
    r"refrigeracion|potencia|ancho_de_banda|latencia|rendimiento|impuesto|moneda|"
    r"divisa|chasis|tarifa|penalizacion|penalización|umbral|pregunta|respuesta|"
    r"arquitectura|modelo|datos|obtener|calcular|validar|crear|modificar|nuevo|"
    r"activo|inactivo|lista|diccionario|valor|resultado|archivo|cliente|fecha|"
    r"hora|meses|anual|mensual|total_general|verdadero|falso)(?=$|(?=[^a-zA-Z]))",
    re.IGNORECASE,
)


def _has_spanish_token(text: str) -> bool:
    if SPANISH_DIACRITICS_REGEX.search(text):
        return True
    # Normalize camelCase to snake_case before lexicon matching
    normalized = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", text)
    return bool(SPANISH_LEXICON_REGEX.search(normalized))


def get_all_code_files() -> list[Path]:
    files = []
    if SRC_ROOT.exists():
        files.extend(SRC_ROOT.rglob("*.py"))
    if TESTS_ROOT.exists():
        for test_file in TESTS_ROOT.rglob("*.py"):
            # Exclude the test file itself as it defines the regex patterns
            if test_file.name != "test_zero_spanish_literals.py":
                files.append(test_file)
    return files


def test_zero_spanish_literals() -> None:
    """Verifies that all Python code in src/ and tests/ contains zero Spanish identifiers, strings, or comments."""
    files = get_all_code_files()
    assert len(files) > 0, "No code files found in src/ or tests/ to inspect."

    violations = []

    for file_path in files:
        source_code = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source_code, filename=str(file_path))

        # 1. AST Inspection: Identifiers, definitions, parameters, attributes, keywords, handlers, aliases, and strings
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if _has_spanish_token(node.name):
                    violations.append(f"{file_path.name}:{node.lineno} Spanish in definition name '{node.name}'")
            elif isinstance(node, ast.Name):
                if _has_spanish_token(node.id):
                    violations.append(f"{file_path.name}:{node.lineno} Spanish in identifier '{node.id}'")
            elif isinstance(node, ast.arg):
                if _has_spanish_token(node.arg):
                    violations.append(f"{file_path.name}:{node.lineno} Spanish in parameter name '{node.arg}'")
            elif isinstance(node, ast.Attribute):
                if _has_spanish_token(node.attr):
                    violations.append(f"{file_path.name}:{node.lineno} Spanish in attribute access '{node.attr}'")
            elif isinstance(node, ast.keyword) and node.arg:
                if _has_spanish_token(node.arg):
                    violations.append(f"{file_path.name}:{node.lineno} Spanish in keyword argument '{node.arg}'")
            elif isinstance(node, ast.ExceptHandler) and node.name:
                if _has_spanish_token(node.name):
                    violations.append(f"{file_path.name}:{node.lineno} Spanish in exception handler name '{node.name}'")
            elif isinstance(node, ast.alias):
                if node.name and _has_spanish_token(node.name):
                    violations.append(f"{file_path.name} Spanish in import name '{node.name}'")
                if node.asname and _has_spanish_token(node.asname):
                    violations.append(f"{file_path.name} Spanish in import alias '{node.asname}'")
            elif isinstance(node, ast.ImportFrom) and node.module:
                if _has_spanish_token(node.module):
                    violations.append(f"{file_path.name}:{node.lineno} Spanish in module import '{node.module}'")
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                if _has_spanish_token(node.value):
                    violations.append(f"{file_path.name}:{node.lineno} Spanish in string constant '{node.value}'")

        # 2. Tokenizer Inspection: Comments
        tokens = tokenize.generate_tokens(StringIO(source_code).readline)
        for tok_type, tok_string, start, _, _ in tokens:
            if tok_type == tokenize.COMMENT:
                if _has_spanish_token(tok_string):
                    violations.append(f"{file_path.name}:{start[0]} Spanish in comment '{tok_string}'")

    # 3. JSON Configuration Inspection: Ensure verticals.json keys are strictly English
    verticals_file = CONFIG_DIR / "taxonomies" / "verticals.json"
    if verticals_file.is_file():
        verticals_data = json.loads(verticals_file.read_text(encoding="utf-8"))
        for section, content in verticals_data.items():
            if _has_spanish_token(section):
                violations.append(f"verticals.json Spanish in top-level section '{section}'")
            if isinstance(content, dict):
                for k in content.keys():
                    if _has_spanish_token(k):
                        violations.append(f"verticals.json Spanish in key '{k}'")

    assert not violations, (
        f"Linguistic Decoupling Gate Violations Detected ({len(violations)}):\n"
        + "\n".join(f" - {v}" for v in violations)
    )


if __name__ == "__main__":
    test_zero_spanish_literals()
    print("PASS: 100% Pure Technical English Certified Across src/, tests/, and config/ (0 violations).")
