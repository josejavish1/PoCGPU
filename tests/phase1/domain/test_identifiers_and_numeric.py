"""Boundary tests for identifiers, versions, exact decimals, and rounding."""

from __future__ import annotations

from decimal import Decimal

import pytest

from pocgpu.domain.errors import DomainValidationError
from pocgpu.domain.identifiers import (
    ContentHash,
    RecordRevision,
    SemanticVersion,
    TenantId,
)
from pocgpu.domain.numeric import (
    RoundingMode,
    RoundingPolicy,
    canonical_decimal,
    parse_decimal_string,
    require_decimal,
)


@pytest.mark.parametrize(
    "value",
    ["tenant.alpha", "A-1", "a:b_c.2", "0"],
)
def test_opaque_identifier_accepts_protocol_form(value: str) -> None:
    assert TenantId(value).value == value


@pytest.mark.parametrize(
    "value",
    ["", " leading", "trailing ", "slash/value", "accent\u00e1", "x" * 129],
)
def test_opaque_identifier_rejects_invalid_protocol_form(value: str) -> None:
    with pytest.raises(DomainValidationError, match="INVALID_IDENTIFIER"):
        TenantId(value)


def test_versions_revisions_and_hashes_are_strict() -> None:
    assert str(SemanticVersion("1.2.3-beta.1+build.7")) == "1.2.3-beta.1+build.7"
    assert RecordRevision(1).value == 1
    assert ContentHash("a" * 64).value == "a" * 64

    with pytest.raises(DomainValidationError, match="INVALID_SEMANTIC_VERSION"):
        SemanticVersion("1.2")
    with pytest.raises(DomainValidationError, match="INVALID_RECORD_REVISION"):
        RecordRevision(True)
    with pytest.raises(DomainValidationError, match="INVALID_CONTENT_HASH"):
        ContentHash("A" * 64)


@pytest.mark.parametrize("value", [1, 1.0, True, "1.0", None])
def test_domain_decimal_rejects_implicit_coercion(value: object) -> None:
    with pytest.raises(DomainValidationError, match="DECIMAL_REQUIRED"):
        require_decimal(value, "value")


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity", "+1", "01", "1,2", " 1"])
def test_boundary_decimal_parser_rejects_noncanonical_text(value: str) -> None:
    with pytest.raises(DomainValidationError, match="INVALID_DECIMAL_STRING"):
        parse_decimal_string(value, "value")


def test_decimal_serialization_and_rounding_are_explicit() -> None:
    assert canonical_decimal(Decimal("1.2300")) == "1.23"
    assert canonical_decimal(Decimal("1E+3")) == "1000"
    assert canonical_decimal(Decimal("-0.000")) == "0"
    assert parse_decimal_string("-12.340", "value") == Decimal("-12.340")

    policy = RoundingPolicy(scale=2, mode=RoundingMode.HALF_EVEN)
    assert policy.apply(Decimal("2.345")) == Decimal("2.34")
    assert policy.apply(Decimal("2.355")) == Decimal("2.36")
