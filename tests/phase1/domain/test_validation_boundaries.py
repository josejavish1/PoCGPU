"""Negative boundary tests for every fail-closed domain invariant."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, tzinfo
from decimal import Decimal
from functools import partial

import pytest

from pocgpu.domain.errors import (
    DomainIssue,
    DomainValidationError,
    IssueKind,
    IssueSeverity,
)
from pocgpu.domain.identifiers import (
    ContentHash,
    CurrencyCode,
    DimensionId,
    EngineId,
    FormulaId,
    GateId,
    OrganizationId,
    PolicyKey,
    PolicyPackId,
    RecordId,
    RecordRevision,
    RoleId,
    ScenarioId,
    SchemaId,
    SemanticVersion,
    SnapshotId,
    TenantId,
    UnitId,
)
from pocgpu.domain.money import FxObservation
from pocgpu.domain.numeric import RoundingMode, RoundingPolicy
from pocgpu.domain.organizations import OrganizationProfile
from pocgpu.domain.policies import (
    CanonicalObject,
    PolicyOverride,
    PolicyPack,
    PolicyResolutionPlan,
    PolicySetting,
)
from pocgpu.domain.provenance import (
    ApprovalState,
    AssumptionAcceptance,
    EvidenceClass,
    ProvenanceMetadata,
    QualityStatus,
    RecordOwner,
    SourceReference,
)
from pocgpu.domain.quantities import Quantity, UnitDefinition, convert_quantity
from pocgpu.domain.results import CertificationGateEvidence, ResultState, derive_result_state
from pocgpu.domain.scenarios import CanonicalResult, OutputDomain, ResultSection, ScenarioDraft
from pocgpu.domain.snapshots import ScenarioSnapshot, SnapshotRecord
from pocgpu.domain.time import AggregationKind, TimeWindow, UtcInstant, ValidityInterval

NOW = UtcInstant(datetime(2026, 6, 1, tzinfo=UTC))
LATER = UtcInstant(datetime(2027, 6, 1, tzinfo=UTC))
OWNER = RecordOwner(OrganizationId("org.synthetic"), RoleId("role.owner"))
EXPECTED_ERROR_PATHS: dict[str, frozenset[tuple[str, ...]]] = {
    "DUPLICATE_CANONICAL_FIELD": frozenset({("fields",)}),
    "DUPLICATE_ISSUE_PARAMETER": frozenset({("parameters",)}),
    "DUPLICATE_JURISDICTION": frozenset({("jurisdiction_ids",)}),
    "DUPLICATE_LOCALE": frozenset({("locale_preferences",)}),
    "DUPLICATE_POLICY_KEY": frozenset({("required_keys",)}),
    "DUPLICATE_POLICY_OVERRIDE_KEY": frozenset({("keys",)}),
    "DUPLICATE_POLICY_PACK": frozenset({("pack_ids",), ("policy_pack_ids",)}),
    "DUPLICATE_POLICY_SETTING": frozenset({("settings",)}),
    "DUPLICATE_RESULT_FIELD": frozenset({("values",)}),
    "DUPLICATE_RESULT_SECTION": frozenset({("sections",)}),
    "DUPLICATE_SNAPSHOT_RECORD": frozenset({("records",)}),
    "DUPLICATE_SOURCE_RECORD": frozenset({("source_record_ids",)}),
    "FORMULA_NOT_ALLOWED": frozenset({("formula_id",)}),
    "INVALID_ASSUMPTION_SCOPE": frozenset({("scope",)}),
    "INVALID_CANONICAL_FIELD": frozenset({("fields",)}),
    "INVALID_COLLECTION_METHOD": frozenset({("collection_method",)}),
    "INVALID_CONTEXT_VALUE": frozenset({("locale_preferences",)}),
    "INVALID_CURRENCY_CODE": frozenset({("currency",)}),
    "INVALID_FX_PAIR": frozenset({("currency",)}),
    "INVALID_FX_RATE": frozenset({("rate",)}),
    "INVALID_ISSUE_CODE": frozenset({("code",)}),
    "INVALID_LOCALIZATION_KEY": frozenset({("localization_key",)}),
    "INVALID_RESULT_FIELD": frozenset({("values",)}),
    "INVALID_ROUNDING_SCALE": frozenset({("scale",)}),
    "INVALID_SOURCE_ID": frozenset({("source_id",)}),
    "INVALID_TIME_INTERVAL": frozenset({("time_window",), ("valid_until",)}),
    "INVALID_UNIT_SCALE": frozenset({("scale_to_base",)}),
    "OBSERVATION_TIME_REQUIRED": frozenset({("observed_at",)}),
    "ORGANIZATION_NAME_REQUIRED": frozenset({("display_name",)}),
    "OUTPUT_DOMAIN_REQUIRED": frozenset({("requested_domains",)}),
    "POLICY_OVERRIDE_KEY_REQUIRED": frozenset({("keys",)}),
    "POLICY_TENANT_MISMATCH": frozenset({("policy_resolution_plan",)}),
    "SELF_SUPERSESSION": frozenset({("supersedes_record_id",)}),
    "SOURCE_LOCATION_REQUIRED": frozenset({("source",)}),
    "TIMEZONE_REQUIRED": frozenset({("instant",)}),
    "UNIT_DEFINITION_MISMATCH": frozenset({("source",)}),
    "UNIT_VERSION_MISMATCH": frozenset({("target", "version")}),
    "ASSUMPTION_ACCEPTANCE_NOT_ALLOWED": frozenset({("assumption_acceptance",)}),
}


def assert_error(code: str, operation: Callable[[], object]) -> None:
    with pytest.raises(DomainValidationError) as captured:
        operation()
    assert captured.value.code == code
    assert captured.value.path in EXPECTED_ERROR_PATHS[code]


def provenance(**changes: object) -> ProvenanceMetadata:
    values: dict[str, object] = {
        "tenant_id": TenantId("tenant.synthetic"),
        "record_id": RecordId("record.synthetic"),
        "schema_id": SchemaId("schema.synthetic"),
        "schema_version": SemanticVersion("1.0.0"),
        "revision": RecordRevision(1),
        "evidence_class": EvidenceClass.CONFIGURED,
        "source": None,
        "observed_at": None,
        "validity": ValidityInterval(NOW, LATER),
        "owner": OWNER,
        "quality_status": QualityStatus.VERIFIED,
        "collection_method": "test-method",
        "formula_id": None,
        "approval_state": ApprovalState.APPROVED,
        "supersedes_record_id": None,
        "source_record_ids": (),
        "assumption_acceptance": None,
    }
    values.update(changes)
    return ProvenanceMetadata(**values)  # type: ignore[arg-type]


def test_structured_issue_validation_and_error_context() -> None:
    error = DomainValidationError("SYNTHETIC", ("field",), (("limit", 2),))
    assert (error.code, error.path, error.parameters) == (
        "SYNTHETIC",
        ("field",),
        (("limit", 2),),
    )
    assert_error(
        "INVALID_ISSUE_CODE",
        lambda: DomainIssue(
            "bad", IssueKind.INVALID, IssueSeverity.ERROR, (), (), "issue.synthetic"
        ),
    )
    assert_error(
        "INVALID_LOCALIZATION_KEY",
        lambda: DomainIssue("VALID", IssueKind.INVALID, IssueSeverity.ERROR, (), (), ""),
    )
    assert_error(
        "DUPLICATE_ISSUE_PARAMETER",
        lambda: DomainIssue(
            "VALID",
            IssueKind.INVALID,
            IssueSeverity.ERROR,
            (),
            (("name", 1), ("name", 2)),
            "issue.synthetic",
        ),
    )


def test_identifier_and_rounding_boundaries() -> None:
    assert str(TenantId("tenant.synthetic")) == "tenant.synthetic"
    assert str(ContentHash("a" * 64)) == "a" * 64
    assert str(CurrencyCode("USD")) == "USD"
    for value in ("US", "usd", "U1D", "EU\u20ac"):
        assert_error("INVALID_CURRENCY_CODE", partial(CurrencyCode, value))
    assert_error("INVALID_ROUNDING_SCALE", lambda: RoundingPolicy(-1, RoundingMode.DOWN))
    assert_error("INVALID_ROUNDING_SCALE", lambda: RoundingPolicy(True, RoundingMode.DOWN))


class _IndeterminateTimezone(tzinfo):
    def utcoffset(self, dt: datetime | None) -> None:
        return None

    def dst(self, dt: datetime | None) -> None:
        return None

    def tzname(self, dt: datetime | None) -> None:
        return None


def _fx_from_values(common: dict[str, object], changes: dict[str, object]) -> FxObservation:
    return FxObservation(**(common | changes))  # type: ignore[arg-type]


def test_time_and_foreign_exchange_boundaries() -> None:
    assert_error(
        "TIMEZONE_REQUIRED",
        lambda: UtcInstant(datetime(2026, 1, 1, tzinfo=_IndeterminateTimezone())),
    )
    assert_error("INVALID_TIME_INTERVAL", lambda: TimeWindow(LATER, NOW, AggregationKind.TOTAL))

    common = {
        "observation_id": RecordId("fx.synthetic"),
        "base_currency": CurrencyCode("USD"),
        "quote_currency": CurrencyCode("EUR"),
        "rate": Decimal("1"),
        "observed_at": NOW,
        "valid_until": LATER,
        "source_record_id": RecordId("source.synthetic"),
    }
    assert_error(
        "INVALID_FX_RATE",
        partial(_fx_from_values, common, {"rate": Decimal("0")}),
    )
    assert_error(
        "INVALID_TIME_INTERVAL",
        partial(_fx_from_values, common, {"valid_until": NOW}),
    )
    assert_error(
        "INVALID_FX_PAIR",
        partial(_fx_from_values, common, {"quote_currency": CurrencyCode("USD")}),
    )


def test_unit_conversion_boundaries() -> None:
    dimension = DimensionId("dimension.synthetic")
    source = UnitDefinition(
        UnitId("unit.source"), dimension, SemanticVersion("1.0.0"), Decimal("1"), Decimal("0")
    )
    target = UnitDefinition(
        UnitId("unit.target"), dimension, SemanticVersion("1.0.0"), Decimal("2"), Decimal("0")
    )
    value = Quantity(Decimal("1"), source.unit_id, dimension)
    assert_error(
        "INVALID_UNIT_SCALE",
        lambda: UnitDefinition(
            UnitId("unit.invalid"), dimension, SemanticVersion("1.0.0"), Decimal("0"), Decimal("0")
        ),
    )
    assert_error(
        "UNIT_DEFINITION_MISMATCH",
        lambda: convert_quantity(
            Quantity(Decimal("1"), UnitId("unit.other"), dimension), source, target
        ),
    )
    assert_error(
        "UNIT_VERSION_MISMATCH",
        lambda: convert_quantity(
            value,
            source,
            UnitDefinition(
                target.unit_id, dimension, SemanticVersion("2.0.0"), Decimal("2"), Decimal("0")
            ),
        ),
    )


def _organization_from_values(
    common: dict[str, object], field: str, value: object
) -> OrganizationProfile:
    return OrganizationProfile(**(common | {field: value}))  # type: ignore[arg-type]


def test_organization_validation_boundaries() -> None:
    common = {
        "tenant_id": TenantId("tenant.synthetic"),
        "organization_id": OrganizationId("org.synthetic"),
        "display_name": "Synthetic",
        "policy_pack_ids": (PolicyPackId("pack.one"),),
        "locale_preferences": ("en-US",),
        "jurisdiction_ids": ("jurisdiction.one",),
        "context_ids": ("context.one",),
    }
    assert_error(
        "ORGANIZATION_NAME_REQUIRED",
        partial(_organization_from_values, common, "display_name", " "),
    )
    for field, value, code in (
        ("policy_pack_ids", (PolicyPackId("pack.one"),) * 2, "DUPLICATE_POLICY_PACK"),
        ("locale_preferences", ("en-US", "en-US"), "DUPLICATE_LOCALE"),
        ("jurisdiction_ids", ("one", "one"), "DUPLICATE_JURISDICTION"),
        ("locale_preferences", ("\u00e9",), "INVALID_CONTEXT_VALUE"),
    ):
        assert_error(
            code,
            partial(_organization_from_values, common, field, value),
        )


def test_policy_value_and_pack_boundaries() -> None:
    schema = SchemaId("schema.synthetic")
    key = PolicyKey("policy.synthetic")
    assert CanonicalObject(schema, (("field", "value"),)).fields == (("field", "value"),)
    assert_error(
        "INVALID_CANONICAL_FIELD",
        lambda: CanonicalObject(schema, (("", "value"),)),
    )
    assert_error(
        "INVALID_CANONICAL_FIELD",
        lambda: CanonicalObject(schema, (("\u00e9", "value"),)),
    )
    assert_error(
        "DUPLICATE_CANONICAL_FIELD",
        lambda: CanonicalObject(schema, (("field", 1), ("field", 2))),
    )
    assert_error(
        "POLICY_OVERRIDE_KEY_REQUIRED",
        lambda: PolicyOverride(PolicyPackId("pack.target"), ()),
    )
    assert_error(
        "DUPLICATE_POLICY_OVERRIDE_KEY",
        lambda: PolicyOverride(PolicyPackId("pack.target"), (key, key)),
    )
    setting = PolicySetting(key, schema, "value")
    assert_error(
        "DUPLICATE_POLICY_SETTING",
        lambda: PolicyPack(
            PolicyPackId("pack.synthetic"),
            TenantId("tenant.synthetic"),
            SemanticVersion("1.0.0"),
            (setting, setting),
            (),
        ),
    )
    assert_error(
        "DUPLICATE_POLICY_PACK",
        lambda: PolicyResolutionPlan(
            TenantId("tenant.synthetic"),
            (PolicyPackId("pack.synthetic"),) * 2,
            (),
        ),
    )
    assert_error(
        "DUPLICATE_POLICY_KEY",
        lambda: PolicyResolutionPlan(TenantId("tenant.synthetic"), (), (key, key)),
    )


def test_provenance_validation_boundaries() -> None:
    assert_error("INVALID_SOURCE_ID", lambda: SourceReference("", None, "internal"))
    assert_error("SOURCE_LOCATION_REQUIRED", lambda: SourceReference("source.one", None, None))
    assert_error("INVALID_ASSUMPTION_SCOPE", lambda: AssumptionAcceptance(OWNER, NOW, ""))
    assert_error("INVALID_COLLECTION_METHOD", lambda: provenance(collection_method=""))
    record = RecordId("record.synthetic")
    assert_error(
        "DUPLICATE_SOURCE_RECORD",
        lambda: provenance(source_record_ids=(RecordId("record.source"),) * 2),
    )
    assert_error("SELF_SUPERSESSION", lambda: provenance(supersedes_record_id=record))
    source = SourceReference("source.one", None, "internal")
    assert_error(
        "OBSERVATION_TIME_REQUIRED",
        lambda: provenance(evidence_class=EvidenceClass.INVOICE, source=source),
    )
    assert_error(
        "FORMULA_NOT_ALLOWED",
        lambda: provenance(formula_id=FormulaId("formula.synthetic")),
    )
    acceptance = AssumptionAcceptance(OWNER, NOW, "scenario.synthetic")
    assert_error(
        "ASSUMPTION_ACCEPTANCE_NOT_ALLOWED",
        lambda: provenance(assumption_acceptance=acceptance),
    )
    assert provenance().is_valid_at(NOW)


def _scenario_from_values(common: dict[str, object], changes: dict[str, object]) -> ScenarioDraft:
    return ScenarioDraft(**(common | changes))  # type: ignore[arg-type]


def test_scenario_and_certification_boundaries() -> None:
    tenant = TenantId("tenant.synthetic")
    plan = PolicyResolutionPlan(tenant, (), (PolicyKey("policy.required"),))
    common = {
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
        "policy_resolution_plan": plan,
        "requested_domains": (OutputDomain.FOUNDATION,),
        "created_at": NOW,
    }
    assert_error(
        "OUTPUT_DOMAIN_REQUIRED",
        partial(_scenario_from_values, common, {"requested_domains": ()}),
    )
    wrong_plan = PolicyResolutionPlan(TenantId("tenant.other"), (), (PolicyKey("policy.required"),))
    assert_error(
        "POLICY_TENANT_MISMATCH",
        partial(_scenario_from_values, common, {"policy_resolution_plan": wrong_plan}),
    )
    assert derive_result_state(True, (), False, False, False, ()) is ResultState.INPUT_REQUIRED
    gate = CertificationGateEvidence(GateId("gate.one"), True, (RecordId("evidence.one"),))
    empty = CertificationGateEvidence(GateId("gate.two"), True, ())
    assert derive_result_state(True, (), True, False, True, (empty,)) is ResultState.REJECTED
    assert derive_result_state(True, (), True, False, True, (gate, gate)) is ResultState.REJECTED


def _result_from_values(values: dict[str, object]) -> CanonicalResult:
    return CanonicalResult(**values)  # type: ignore[arg-type]


def _snapshot_from_values(values: dict[str, object]) -> ScenarioSnapshot:
    return ScenarioSnapshot(**values)  # type: ignore[arg-type]


def test_result_and_snapshot_collection_boundaries() -> None:
    section = ResultSection(OutputDomain.FOUNDATION, (("field", 1),))
    assert_error(
        "INVALID_RESULT_FIELD",
        lambda: ResultSection(OutputDomain.FOUNDATION, (("", 1),)),
    )
    assert_error(
        "DUPLICATE_RESULT_FIELD",
        lambda: ResultSection(OutputDomain.FOUNDATION, (("field", 1), ("field", 2))),
    )
    result_values = {
        "scenario_id": ScenarioId("scenario.synthetic"),
        "scenario_revision": RecordRevision(1),
        "snapshot_id": SnapshotId("snapshot.synthetic"),
        "snapshot_hash": ContentHash("a" * 64),
        "engine_id": EngineId("engine.synthetic"),
        "engine_version": SemanticVersion("1.0.0"),
        "state": ResultState.VALID,
        "issues": (),
        "sections": (section, section),
        "evaluated_at": NOW,
    }
    assert_error(
        "DUPLICATE_RESULT_SECTION",
        partial(_result_from_values, result_values),
    )
    snapshot_record = SnapshotRecord(
        RecordId("record.synthetic"), RecordRevision(1), ContentHash("b" * 64)
    )
    snapshot_values = {
        "snapshot_id": SnapshotId("snapshot.synthetic"),
        "tenant_id": TenantId("tenant.synthetic"),
        "scenario_id": ScenarioId("scenario.synthetic"),
        "scenario_revision": RecordRevision(1),
        "captured_at": NOW,
        "records": (snapshot_record, snapshot_record),
        "policy_pack_ids": (),
        "content_hash": ContentHash("c" * 64),
    }
    assert_error(
        "DUPLICATE_SNAPSHOT_RECORD",
        partial(_snapshot_from_values, snapshot_values),
    )
    snapshot_values["records"] = ()
    snapshot_values["policy_pack_ids"] = (PolicyPackId("pack.synthetic"),) * 2
    assert_error(
        "DUPLICATE_POLICY_PACK",
        partial(_snapshot_from_values, snapshot_values),
    )
