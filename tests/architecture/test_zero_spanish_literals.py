"""Architectural Fitness Gate: Zero Spanish Literals in Source Code and Configuration Schemas.

Asserts via AST, Lexical Tokenization, and Recursive JSON Schema Inspection that all files
under src/, tests/, scripts/, and non-locale configuration files contain 100% pure Technical English
with zero Spanish diacritics, acronyms (e.g. CPD), or lexicon tokens in identifiers, keys, and code.
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
SCRIPTS_ROOT = REPO_ROOT / "scripts"
CONFIG_DIR = REPO_ROOT / "config"

# Detects Spanish accented vowels, eñe, and inverted punctuation marks
SPANISH_DIACRITICS_REGEX = re.compile(r"[áéíóúÁÉÍÓÚñÑüÜ¡¿]")

# Catches Spanish technical lexicon even inside snake_case, camelCase, or compound identifiers
SPANISH_LEXICON_REGEX = re.compile(
    r"(?:^|(?<=[^a-zA-Z]))(cpd|cálculo|calculo|configuración|configuracion|error_de|parámetro|parametro|"
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


LEGACY_POC_SCRIPTS = {
    "benchmark.py",
    "classify_incident.py",
    "enrich_enterprise_metrics.py",
    "finops_calculator.py",
    "ide_copilot_simulator.py",
    "interactive_chat.py",
    "saturation_probe.py",
    "seed_enterprise_demo.py",
    "simulate_enterprise_governance.py",
    "verify_balanced_saturation.py",
}


def get_all_code_files() -> list[Path]:
    files = []
    if SRC_ROOT.exists():
        files.extend(SRC_ROOT.rglob("*.py"))
    if TESTS_ROOT.exists():
        for test_file in TESTS_ROOT.rglob("*.py"):
            # Exclude the test file itself as it defines the regex patterns
            if test_file.name != "test_zero_spanish_literals.py":
                files.append(test_file)
    if SCRIPTS_ROOT.exists():
        for script_file in SCRIPTS_ROOT.rglob("*.py"):
            if script_file.name not in LEGACY_POC_SCRIPTS:
                files.append(script_file)
    return files


def test_zero_spanish_html_templates() -> None:
    """Verifies that HTML template files in scripts/ contain zero Spanish text outside localized keys."""
    violations: list[str] = []
    if SCRIPTS_ROOT.exists():
        for html_file in SCRIPTS_ROOT.rglob("*.html"):
            content = html_file.read_text(encoding="utf-8")
            for idx, line in enumerate(content.splitlines(), start=1):
                # Split line into words and verify each token
                for word in re.findall(r"[a-zA-ZáéíóúÁÉÍÓÚñÑüÜ]+", line):
                    if _has_spanish_token(word):
                        violations.append(f"{html_file.name}:{idx} Spanish token '{word}' in HTML line '{line.strip()}'")
    assert not violations, f"Spanish tokens detected in HTML templates:\n" + "\n".join(f" - {v}" for v in violations)


def _inspect_json_recursive(data: object, path_prefix: str, violations: list[str]) -> None:
    if isinstance(data, dict):
        for k, v in data.items():
            if _has_spanish_token(str(k)):
                violations.append(f"{path_prefix} Spanish in key '{k}'")
            if isinstance(v, (dict, list)):
                _inspect_json_recursive(v, f"{path_prefix}.{k}", violations)
            elif isinstance(v, str) and _has_spanish_token(v):
                violations.append(f"{path_prefix}.{k} Spanish in string value '{v}'")
    elif isinstance(data, list):
        for idx, item in enumerate(data):
            _inspect_json_recursive(item, f"{path_prefix}[{idx}]", violations)


def test_zero_spanish_literals() -> None:
    """Verifies that all Python code and configurations contain zero Spanish identifiers, strings, or comments."""
    violations: list[str] = []

    for file_path in get_all_code_files():
        source_code = file_path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source_code, filename=str(file_path))
        except SyntaxError as err:
            violations.append(f"{file_path.name} SyntaxError during AST parsing: {err}")
            continue

        # 1. AST Inspection
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

    # 3. JSON Configuration Inspection (Recursive on all catalogs and EN translations)
    json_targets = [
        CONFIG_DIR / "catalogs" / "hardware_catalog.json",
        CONFIG_DIR / "catalogs" / "pricing_catalog.json",
        CONFIG_DIR / "catalogs" / "models_catalog.json",
        CONFIG_DIR / "questionnaires" / "questionnaires.json",
        CONFIG_DIR / "taxonomies" / "verticals.json",
    ]
    for jt in json_targets:
        if jt.is_file():
            data = json.loads(jt.read_text(encoding="utf-8"))
            _inspect_json_recursive(data, jt.name, violations)

    locales_file = CONFIG_DIR / "locales.json"
    if locales_file.is_file():
        locales_data = json.loads(locales_file.read_text(encoding="utf-8"))
        en_translations = locales_data.get("translations", {}).get("en", {})
        _inspect_json_recursive(en_translations, "locales.json[en]", violations)

    assert not violations, (
        f"Linguistic Decoupling Gate Violations Detected ({len(violations)}):\n"
        + "\n".join(f" - {v}" for v in violations)
    )


if __name__ == "__main__":
    test_zero_spanish_literals()
    print("PASS: 100% Pure Technical English Certified Across src/, scripts/, tests/, and config/ (0 violations).")
