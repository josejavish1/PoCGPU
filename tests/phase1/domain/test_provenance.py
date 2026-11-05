"""Conditional invariant tests for governed record provenance."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from pocgpu.domain.errors import DomainValidationError
from pocgpu.domain.identifiers import (
    FormulaId,
    OrganizationId,
    RecordId,
    RecordRevision,
    RoleId,
    SchemaId,
    SemanticVersion,
    TenantId,
)
from pocgpu.domain.provenance import (
    ApprovalState,
    AssumptionAcceptance,
    EvidenceClass,
    GovernedRecord,
    ProvenanceMetadata,
    QualityStatus,
    RecordOwner,
    SourceReference,
)
from pocgpu.domain.time import UtcInstant, ValidityInterval

NOW = UtcInstant(datetime(2026, 11, 4, 8, 0, tzinfo=UTC))
VALIDITY = ValidityInterval(
    start=UtcInstant(datetime(2026, 1, 1, tzinfo=UTC)),
    end=UtcInstant(datetime(2027, 1, 1, tzinfo=UTC)),
)
OWNER = RecordOwner(OrganizationId("org.synthetic"), RoleId("role.owner"))


def metadata(
    evidence_class: EvidenceClass,
    *,
    source: SourceReference | None,
    observed_at: UtcInstant | None,
    formula_id: FormulaId | None,
    source_records: tuple[RecordId, ...],
    acceptance: AssumptionAcceptance | None,
) -> ProvenanceMetadata:
    return ProvenanceMetadata(
        tenant_id=TenantId("tenant.synthetic"),
        record_id=RecordId("record.synthetic"),
        schema_id=SchemaId("schema.synthetic"),
        schema_version=SemanticVersion("1.0.0"),
        revision=RecordRevision(1),
        evidence_class=evidence_class,
        source=source,
        observed_at=observed_at,
        validity=VALIDITY,
        owner=OWNER,
        quality_status=QualityStatus.VERIFIED,
        collection_method="synthetic-test",
        formula_id=formula_id,
        approval_state=ApprovalState.APPROVED,
        supersedes_record_id=None,
        source_record_ids=source_records,
        assumption_acceptance=acceptance,
    )


def test_measured_record_requires_source_and_observation() -> None:
    with pytest.raises(DomainValidationError, match="SOURCE_REQUIRED"):
        metadata(
            EvidenceClass.MEASURED,
            source=None,
            observed_at=NOW,
            formula_id=None,
            source_records=(),
            acceptance=None,
        )

    valid = metadata(
        EvidenceClass.MEASURED,
        source=SourceReference("source.synthetic", None, "internal.synthetic"),
        observed_at=NOW,
        formula_id=None,
        source_records=(),
        acceptance=None,
    )
    assert GovernedRecord(metadata=valid, value="synthetic").metadata == valid


def test_derived_record_requires_formula_and_lineage() -> None:
    with pytest.raises(DomainValidationError, match="DERIVATION_REQUIRED"):
        metadata(
            EvidenceClass.DERIVED,
            source=None,
            observed_at=None,
            formula_id=None,
            source_records=(),
            acceptance=None,
        )

    derived = metadata(
        EvidenceClass.DERIVED,
        source=None,
        observed_at=None,
        formula_id=FormulaId("formula.synthetic"),
        source_records=(RecordId("record.source"),),
        acceptance=None,
    )
    assert derived.formula_id == FormulaId("formula.synthetic")


def test_assumption_requires_explicit_acceptance() -> None:
    with pytest.raises(DomainValidationError, match="ASSUMPTION_ACCEPTANCE_REQUIRED"):
        metadata(
            EvidenceClass.ASSUMED,
            source=None,
            observed_at=None,
            formula_id=None,
            source_records=(),
            acceptance=None,
        )

    accepted = metadata(
        EvidenceClass.ASSUMED,
        source=None,
        observed_at=None,
        formula_id=None,
        source_records=(),
        acceptance=AssumptionAcceptance(OWNER, NOW, "scenario.synthetic"),
    )
    assert accepted.assumption_acceptance is not None
