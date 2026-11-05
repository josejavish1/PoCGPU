"""Exact protocol tests designed to reject behavior-changing domain mutations."""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from functools import partial

import pytest

from pocgpu.domain.errors import DomainValidationError
from pocgpu.domain.identifiers import (
    ContentHash,
    CurrencyCode,
    DimensionId,
    EngineId,
    OrganizationId,
    PolicyPackId,
    RecordId,
    RecordRevision,
    RoleId,
    ScenarioId,
    SchemaId,
    SemanticVersion,
    TenantId,
    UnitId,
)
from pocgpu.domain.money import FxObservation, Money, convert_money
from pocgpu.domain.numeric import (
    RoundingMode,
    RoundingPolicy,
    canonical_decimal,
    parse_decimal_string,
    require_decimal,
)
from pocgpu.domain.organizations import OrganizationProfile
from pocgpu.domain.policies import PolicyResolutionPlan
from pocgpu.domain.provenance import (
    ApprovalState,
    AssumptionAcceptance,
    EvidenceClass,
    ProvenanceMetadata,
    QualityStatus,
    RecordOwner,
)
from pocgpu.domain.quantities import Quantity, UnitDefinition, convert_quantity
from pocgpu.domain.scenarios import OutputDomain, ScenarioDraft
from pocgpu.domain.serialization import canonical_json_bytes, content_hash
from pocgpu.domain.time import AggregationKind, TimeWindow, UtcInstant, ValidityInterval

NOW = UtcInstant(datetime(2026, 1, 1, tzinfo=UTC))
LATER = UtcInstant(datetime(2027, 1, 1, tzinfo=UTC))


def exact_error(
    operation: Callable[[], object], code: str, path: tuple[str, ...]
) -> DomainValidationError:
    with pytest.raises(DomainValidationError) as captured:
        operation()
    assert captured.value.args == (code,)
    assert captured.value.code == code
    assert captured.value.path == path
    assert captured.value.parameters == ()
    return captured.value


def scenario_with(**changes: object) -> ScenarioDraft:
    tenant = TenantId("tenant.synthetic")
    values: dict[str, object] = {
        "scenario_id": ScenarioId("scenario.synthetic"),
        "tenant_id": tenant,
        "organization_id": OrganizationId("org.synthetic"),
        "revision": RecordRevision(1),
        "schema_id": SchemaId("schema.synthetic"),
        "schema_version": SemanticVersion("1.0.0"),
        "engine_id": EngineId("engine.synthetic"),
        "engine_version": SemanticVersion("1.0.0"),
        "input_record_ids": (),
        "evidence_record_ids": (),
        "accepted_assumption_record_ids": (),
        "policy_resolution_plan": PolicyResolutionPlan(tenant, (), ()),
        "requested_domains": (OutputDomain.FOUNDATION,),
        "created_at": NOW,
    }
    values.update(changes)
    return ScenarioDraft(**values)  # type: ignore[arg-type]


def organization_with(**changes: object) -> OrganizationProfile:
    values: dict[str, object] = {
        "tenant_id": TenantId("tenant.synthetic"),
        "organization_id": OrganizationId("org.synthetic"),
        "display_name": "Synthetic",
        "policy_pack_ids": (),
        "locale_preferences": (),
        "jurisdiction_ids": (),
        "context_ids": (),
    }
    values.update(changes)
    return OrganizationProfile(**values)  # type: ignore[arg-type]


def scenario_field(field: str, value: object) -> ScenarioDraft:
    return scenario_with(**{field: value})


def organization_field(field: str, value: object) -> OrganizationProfile:
    return organization_with(**{field: value})


def metadata(**changes: object) -> ProvenanceMetadata:
    tenant = TenantId("tenant.synthetic")
    record_id = RecordId("record.synthetic")
    owner = RecordOwner(OrganizationId("org.synthetic"), RoleId("role.owner"))
    values: dict[str, object] = {
        "tenant_id": tenant,
        "record_id": record_id,
        "schema_id": SchemaId("schema.synthetic"),
        "schema_version": SemanticVersion("1.0.0"),
        "revision": RecordRevision(1),
        "evidence_class": EvidenceClass.CONFIGURED,
        "source": None,
        "observed_at": None,
        "validity": ValidityInterval(NOW, LATER),
        "owner": owner,
        "quality_status": QualityStatus.VERIFIED,
        "collection_method": "synthetic-test",
        "formula_id": None,
        "approval_state": ApprovalState.APPROVED,
        "supersedes_record_id": None,
        "source_record_ids": (),
        "assumption_acceptance": None,
    }
    values.update(changes)
    return ProvenanceMetadata(**values)  # type: ignore[arg-type]


def test_identifier_protocol_edges_and_exact_errors() -> None:
    assert len(TenantId("x" * 128).value) == 128
    exact_error(lambda: TenantId("x" * 129), "INVALID_IDENTIFIER", ("TenantId",))
    exact_error(lambda: TenantId(1), "INVALID_IDENTIFIER", ("TenantId",))  # type: ignore[arg-type]
    exact_error(
        lambda: SemanticVersion(1),  # type: ignore[arg-type]
        "INVALID_SEMANTIC_VERSION",
        ("version",),
    )
    exact_error(lambda: RecordRevision(0), "INVALID_RECORD_REVISION", ("revision",))
    exact_error(lambda: RecordRevision(-1), "INVALID_RECORD_REVISION", ("revision",))
    exact_error(
        lambda: ContentHash(1),  # type: ignore[arg-type]
        "INVALID_CONTENT_HASH",
        ("content_hash",),
    )


def test_numeric_protocol_edges_and_all_rounding_modes() -> None:
    for value in (Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")):
        exact_error(partial(require_decimal, value, "number"), "DECIMAL_REQUIRED", ("number",))
    exact_error(
        lambda: parse_decimal_string(1, "number"),  # type: ignore[arg-type]
        "INVALID_DECIMAL_STRING",
        ("number",),
    )
    exact_error(
        lambda: canonical_decimal(Decimal("NaN")),
        "DECIMAL_REQUIRED",
        ("value",),
    )
    assert canonical_decimal(Decimal("100.000")) == "100"
    assert canonical_decimal(Decimal("0.00100")) == "0.001"
    assert RoundingPolicy(0, RoundingMode.DOWN).apply(Decimal("1.9")) == Decimal("1")
    cases = {
        RoundingMode.HALF_EVEN: Decimal("2.34"),
        RoundingMode.HALF_UP: Decimal("2.35"),
        RoundingMode.DOWN: Decimal("2.34"),
        RoundingMode.UP: Decimal("2.35"),
        RoundingMode.FLOOR: Decimal("-2.35"),
        RoundingMode.CEILING: Decimal("2.35"),
    }
    for mode, expected in cases.items():
        value = Decimal("-2.341") if mode is RoundingMode.FLOOR else Decimal("2.345")
        assert RoundingPolicy(2, mode).apply(value) == expected
    exact_error(
        lambda: RoundingPolicy(2, RoundingMode.DOWN).apply(Decimal("NaN")),
        "DECIMAL_REQUIRED",
        ("value",),
    )


def test_money_quantity_and_time_exact_failures() -> None:
    exact_error(lambda: Money(Decimal("NaN"), CurrencyCode("USD")), "DECIMAL_REQUIRED", ("amount",))
    dimension = DimensionId("dimension.synthetic")
    version = SemanticVersion("1.0.0")
    source = UnitDefinition(UnitId("source"), dimension, version, Decimal("1"), Decimal("0"))
    other = DimensionId("dimension.other")
    target = UnitDefinition(UnitId("target"), other, version, Decimal("1"), Decimal("0"))
    exact_error(
        lambda: convert_quantity(Quantity(Decimal("1"), source.unit_id, dimension), source, target),
        "DIMENSION_MISMATCH",
        ("target",),
    )
    observation = FxObservation(
        RecordId("fx.synthetic"),
        CurrencyCode("USD"),
        CurrencyCode("EUR"),
        Decimal("1"),
        NOW,
        LATER,
        RecordId("source.synthetic"),
    )
    exact_error(
        lambda: convert_money(
            Money(Decimal("1"), CurrencyCode("USD")), CurrencyCode("GBP"), observation
        ),
        "FX_CURRENCY_MISMATCH",
        ("currency",),
    )
    exact_error(
        lambda: FxObservation(
            RecordId("fx.invalid"),
            CurrencyCode("USD"),
            CurrencyCode("EUR"),
            Decimal("NaN"),
            NOW,
            LATER,
            RecordId("source.synthetic"),
        ),
        "DECIMAL_REQUIRED",
        ("rate",),
    )
    exact_error(
        lambda: UnitDefinition(UnitId("invalid"), dimension, version, Decimal("NaN"), Decimal("0")),
        "DECIMAL_REQUIRED",
        ("scale_to_base",),
    )
    exact_error(
        lambda: UnitDefinition(UnitId("invalid"), dimension, version, Decimal("1"), Decimal("NaN")),
        "DECIMAL_REQUIRED",
        ("offset_to_base",),
    )
    exact_error(
        lambda: Quantity(Decimal("NaN"), UnitId("invalid"), dimension),
        "DECIMAL_REQUIRED",
        ("magnitude",),
    )
    exact_error(lambda: UtcInstant("invalid"), "TIMEZONE_REQUIRED", ("instant",))  # type: ignore[arg-type]
    exact_error(lambda: ValidityInterval(NOW, NOW), "INVALID_TIME_INTERVAL", ("validity",))
    exact_error(
        lambda: TimeWindow(NOW, NOW, AggregationKind.TOTAL),
        "INVALID_TIME_INTERVAL",
        ("time_window",),
    )


def test_utc_normalization_does_not_depend_on_host_timezone() -> None:
    previous = os.environ.get("TZ")
    os.environ["TZ"] = "Etc/GMT-2"
    time.tzset()
    try:
        instant = UtcInstant(datetime(2026, 1, 1, 3, tzinfo=UTC))
        assert instant.value.tzinfo is UTC
        assert instant.value.hour == 3
    finally:
        if previous is None:
            del os.environ["TZ"]
        else:
            os.environ["TZ"] = previous
        time.tzset()


def test_every_scenario_collection_reports_its_exact_path() -> None:
    duplicate = RecordId("record.synthetic")
    for field in (
        "input_record_ids",
        "evidence_record_ids",
        "accepted_assumption_record_ids",
    ):
        exact_error(
            partial(scenario_field, field, (duplicate, duplicate)),
            "DUPLICATE_SCENARIO_REFERENCE",
            (field,),
        )
    exact_error(
        lambda: scenario_with(requested_domains=(OutputDomain.FOUNDATION,) * 2),
        "DUPLICATE_SCENARIO_REFERENCE",
        ("requested_domains",),
    )


def test_every_organization_collection_reports_its_exact_path() -> None:
    cases: tuple[tuple[str, object, str], ...] = (
        ("policy_pack_ids", (PolicyPackId("pack.one"),) * 2, "DUPLICATE_POLICY_PACK"),
        ("locale_preferences", ("en", "en"), "DUPLICATE_LOCALE"),
        ("jurisdiction_ids", ("one", "one"), "DUPLICATE_JURISDICTION"),
        ("context_ids", ("one", "one"), "DUPLICATE_CONTEXT_ID"),
    )
    for field, value, code in cases:
        exact_error(partial(organization_field, field, value), code, (field,))
    for field in ("locale_preferences", "jurisdiction_ids", "context_ids"):
        exact_error(
            partial(organization_field, field, ("\u00e9",)),
            "INVALID_CONTEXT_VALUE",
            (field,),
        )


def test_provenance_disjunctions_fail_independently() -> None:
    exact_error(
        lambda: metadata(evidence_class=EvidenceClass.MEASURED),
        "SOURCE_REQUIRED",
        ("source",),
    )
    exact_error(
        lambda: metadata(
            evidence_class=EvidenceClass.DERIVED, source_record_ids=(RecordId("one"),)
        ),
        "DERIVATION_REQUIRED",
        ("formula_id",),
    )
    exact_error(
        lambda: metadata(evidence_class=EvidenceClass.DERIVED),
        "DERIVATION_REQUIRED",
        ("formula_id",),
    )
    exact_error(
        lambda: metadata(evidence_class=EvidenceClass.ASSUMED),
        "ASSUMPTION_ACCEPTANCE_REQUIRED",
        ("assumption_acceptance",),
    )
    acceptance = AssumptionAcceptance(
        RecordOwner(OrganizationId("org.synthetic"), RoleId("role.owner")), NOW, "scope"
    )
    assert metadata(evidence_class=EvidenceClass.ASSUMED, assumption_acceptance=acceptance)


def test_serialization_error_tokens_and_mixed_set_order_are_exact() -> None:
    schema = SchemaId("schema.synthetic")
    version = SemanticVersion("1.0.0")

    def serialize(value: object) -> bytes:
        return canonical_json_bytes(value, schema, version)

    for value, message in (
        (1.0, "FLOAT_PROHIBITED"),
        (datetime(2026, 1, 1, tzinfo=UTC), "RAW_DATETIME_PROHIBITED"),
        ({1: "value"}, "CANONICAL_KEY_MUST_BE_STRING"),
        ({"caf\u00e9": 1, "cafe\u0301": 2}, "DUPLICATE_NORMALIZED_KEY"),
        (object(), "UNSUPPORTED_CANONICAL_TYPE:object"),
    ):
        with pytest.raises(TypeError) as captured:
            serialize(value)
        assert captured.value.args == (message,)
    with pytest.raises(TypeError) as captured:
        content_hash("invalid")  # type: ignore[arg-type]
    assert captured.value.args == ("CANONICAL_BYTES_REQUIRED",)

    mixed = canonical_json_bytes(frozenset({1, "1"}), schema, version)
    assert mixed == (b'{"payload":["1",1],"schema_id":"schema.synthetic","schema_version":"1.0.0"}')
    numeric_set = canonical_json_bytes(frozenset({2, 10}), schema, version)
    assert numeric_set == (
        b'{"payload":[10,2],"schema_id":"schema.synthetic","schema_version":"1.0.0"}'
    )
    unicode_set = canonical_json_bytes(frozenset({"z", "\u00e9"}), schema, version)
    assert b"\\u00e9" not in unicode_set
    assert json.loads(unicode_set)["payload"] == ["z", "\u00e9"]
