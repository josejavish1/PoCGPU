"""Property and metamorphic tests for exact numeric and serialization contracts."""

from __future__ import annotations

from decimal import Decimal

from hypothesis import given
from hypothesis import strategies as st

from pocgpu.domain.identifiers import SchemaId, SemanticVersion
from pocgpu.domain.numeric import canonical_decimal, parse_decimal_string
from pocgpu.domain.serialization import canonical_json_bytes


@given(st.decimals(allow_nan=False, allow_infinity=False, places=8))
def test_canonical_decimal_round_trip_preserves_numeric_value(value: Decimal) -> None:
    serialized = canonical_decimal(value)
    assert parse_decimal_string(serialized, "value") == value


@given(st.dictionaries(st.sampled_from(["a", "b", "c"]), st.integers(), max_size=3))
def test_mapping_insertion_order_does_not_change_canonical_bytes(
    values: dict[str, int],
) -> None:
    reversed_values = dict(reversed(tuple(values.items())))
    schema_id = SchemaId("schema.synthetic")
    version = SemanticVersion("1.0.0")
    assert canonical_json_bytes(values, schema_id, version) == canonical_json_bytes(
        reversed_values, schema_id, version
    )
