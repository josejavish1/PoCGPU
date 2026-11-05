#!/usr/bin/env python3
"""Fail when mutation survivors differ from the reviewed adjudication set."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

DEFAULT_ADJUDICATIONS = Path("tests/phase1/mutation-adjudications.json")
MUTMUT_CLASS_SEPARATOR = chr(0x01C1)


def parse_survivors(output: str) -> set[str]:
    """Parse stable survivor identities from mutmut result text."""

    survivors: set[str] = set()
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped.endswith(": survived"):
            continue
        identity = stripped.removesuffix(": survived")
        survivors.add(identity.replace(MUTMUT_CLASS_SEPARATOR, "|"))
    return survivors


def load_expected(path: Path) -> set[str]:
    """Load the exact reviewed survivor set from a versioned JSON document."""

    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema_version") != "1.0.0":
        raise ValueError("UNSUPPORTED_ADJUDICATION_SCHEMA")
    values = document.get("equivalent_survivors")
    if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
        raise ValueError("INVALID_ADJUDICATION_SET")
    if len(values) != len(set(values)):
        raise ValueError("DUPLICATE_ADJUDICATION")
    return set(values)


def validate(actual: set[str], expected: set[str]) -> tuple[set[str], set[str]]:
    """Return unreviewed survivors and stale adjudications."""

    return actual - expected, expected - actual


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adjudications", type=Path, default=DEFAULT_ADJUDICATIONS)
    arguments = parser.parse_args()

    completed = subprocess.run(
        [str(Path(sys.executable).with_name("mutmut")), "results"],
        check=True,
        capture_output=True,
        text=True,
    )
    actual = parse_survivors(completed.stdout)
    expected = load_expected(arguments.adjudications)
    unreviewed, stale = validate(actual, expected)
    if unreviewed or stale:
        for identity in sorted(unreviewed):
            print(f"UNREVIEWED_MUTANT:{identity}", file=sys.stderr)
        for identity in sorted(stale):
            print(f"STALE_ADJUDICATION:{identity}", file=sys.stderr)
        return 1
    print(f"Mutation adjudications valid: {len(actual)} equivalent survivors.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
