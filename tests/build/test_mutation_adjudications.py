"""Mutation adjudication parser and set-control tests."""

from __future__ import annotations

from scripts.validate_mutation_adjudications import parse_survivors, validate


def test_survivor_parser_normalizes_mutmut_class_separator() -> None:
    separator = chr(0x01C1)
    output = f"    module.x{separator}Type{separator}method__mutmut_1: survived\n"
    assert parse_survivors(output) == {"module.x|Type|method__mutmut_1"}


def test_adjudication_validation_rejects_new_or_stale_entries() -> None:
    assert validate({"reviewed", "new"}, {"reviewed", "stale"}) == ({"new"}, {"stale"})
