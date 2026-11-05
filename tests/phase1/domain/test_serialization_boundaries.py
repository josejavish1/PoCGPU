"""Canonical serialization tests for every supported representation boundary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

import pytest

from pocgpu.domain.identifiers import (
    ContentHash,
    CurrencyCode,
    RecordRevision,
    SchemaId,
    SemanticVersion,
    TenantId,
)
from pocgpu.domain.serialization import canonical_json_bytes, content_hash
from pocgpu.domain.time import UtcInstant

SCHEMA = SchemaId("schema.synthetic")
VERSION = SemanticVersion("1.0.0")


class Example(Enum):
    VALUE = 7


@dataclass(frozen=True)
class ExampleRecord:
    name: str


def payload(value: object) -> Any:
    import json

    return json.loads(canonical_json_bytes(value, SCHEMA, VERSION))["payload"]


def test_supported_canonical_types_and_timestamps() -> None:
    instant = UtcInstant(datetime(2026, 1, 2, 3, 4, 5, 120000, tzinfo=UTC))
    exact = UtcInstant(datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC))
    value = {
        "none": None,
        "boolean": True,
        "integer": 2,
        "decimal": Decimal("2.00"),
        "identifier": TenantId("tenant.synthetic"),
        "version": VERSION,
        "currency": CurrencyCode("USD"),
        "hash": ContentHash("a" * 64),
        "revision": RecordRevision(2),
        "instant": instant,
        "exact": exact,
        "enum": Example.VALUE,
        "record": ExampleRecord("synthetic"),
        "list": [1, 2],
        "tuple": (3, 4),
        "set": {"b", "a"},
        "frozen": frozenset({2, 1}),
    }
    result = payload(value)
    assert result["instant"] == "2026-01-02T03:04:05.12Z"
    assert result["exact"] == "2026-01-02T03:04:05Z"
    assert result["enum"] == 7
    assert result["record"] == {"name": "synthetic"}
    assert result["list"] == [1, 2]
    assert result["tuple"] == [3, 4]
    assert result["set"] == ["a", "b"]
    assert result["frozen"] == [1, 2]


def test_canonical_bytes_are_an_independently_fixed_protocol_fixture() -> None:
    actual = canonical_json_bytes(
        {"amount": Decimal("1.2300"), "tenant": TenantId("tenant.synthetic")},
        SCHEMA,
        VERSION,
    )
    expected = (
        b'{"payload":{"amount":"1.23","tenant":"tenant.synthetic"},'
        b'"schema_id":"schema.synthetic","schema_version":"1.0.0"}'
    )
    assert actual == expected
    assert (
        content_hash(actual).value
        == "66c0d30ca788ba18d4239c261530ad3873634ed7b6c870a3ae7d79190ae2674b"
    )


def test_rejected_canonical_boundaries() -> None:
    with pytest.raises(TypeError, match="RAW_DATETIME_PROHIBITED"):
        payload(datetime(2026, 1, 1, tzinfo=UTC))
    with pytest.raises(TypeError, match="CANONICAL_KEY_MUST_BE_STRING"):
        payload({1: "value"})
    with pytest.raises(TypeError, match="DUPLICATE_NORMALIZED_KEY"):
        payload({"caf\u00e9": 1, "cafe\u0301": 2})
    with pytest.raises(TypeError, match="CANONICAL_BYTES_REQUIRED"):
        content_hash("not-bytes")  # type: ignore[arg-type]


def test_domain_ports_are_importable_protocols() -> None:
    from pocgpu.domain.ports.audit import AuditLedger
    from pocgpu.domain.ports.units import UnitRegistry

    assert AuditLedger.__name__ == "AuditLedger"
    assert UnitRegistry.__name__ == "UnitRegistry"
