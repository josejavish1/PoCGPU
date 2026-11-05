"""Immutable governed record provenance and conditional evidence rules."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

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
from pocgpu.domain.time import UtcInstant, ValidityInterval


class EvidenceClass(StrEnum):
    """Normative evidence classification."""

    INVOICE = "INVOICE"
    MEASURED = "MEASURED"
    CONFIGURED = "CONFIGURED"
    ASSUMED = "ASSUMED"
    DERIVED = "DERIVED"


class ApprovalState(StrEnum):
    """Governed record approval lifecycle."""

    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"


class QualityStatus(StrEnum):
    """Evidence quality status independent from approval."""

    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    ESTIMATED = "ESTIMATED"


@dataclass(frozen=True, slots=True)
class RecordOwner:
    """Organization and role accountable for one governed record."""

    organization_id: OrganizationId
    role_id: RoleId


@dataclass(frozen=True, slots=True)
class SourceReference:
    """External or internal source identity without copied confidential content."""

    source_id: str
    source_uri: str | None
    internal_reference: str | None

    def __post_init__(self) -> None:
        if not self.source_id or not self.source_id.isascii():
            raise DomainValidationError("INVALID_SOURCE_ID", ("source_id",))
        if self.source_uri is None and self.internal_reference is None:
            raise DomainValidationError("SOURCE_LOCATION_REQUIRED", ("source",))


@dataclass(frozen=True, slots=True)
class AssumptionAcceptance:
    """Explicit acceptance evidence for an assumed value."""

    accepted_by: RecordOwner
    accepted_at: UtcInstant
    scope: str

    def __post_init__(self) -> None:
        if not self.scope or not self.scope.isascii():
            raise DomainValidationError("INVALID_ASSUMPTION_SCOPE", ("scope",))


@dataclass(frozen=True, slots=True)
class ProvenanceMetadata:
    """Complete immutable provenance shared by governed records."""

    tenant_id: TenantId
    record_id: RecordId
    schema_id: SchemaId
    schema_version: SemanticVersion
    revision: RecordRevision
    evidence_class: EvidenceClass
    source: SourceReference | None
    observed_at: UtcInstant | None
    validity: ValidityInterval
    owner: RecordOwner
    quality_status: QualityStatus
    collection_method: str
    formula_id: FormulaId | None
    approval_state: ApprovalState
    supersedes_record_id: RecordId | None
    source_record_ids: tuple[RecordId, ...]
    assumption_acceptance: AssumptionAcceptance | None

    def __post_init__(self) -> None:
        if not self.collection_method or not self.collection_method.isascii():
            raise DomainValidationError("INVALID_COLLECTION_METHOD", ("collection_method",))
        if len(self.source_record_ids) != len(set(self.source_record_ids)):
            raise DomainValidationError("DUPLICATE_SOURCE_RECORD", ("source_record_ids",))
        if self.supersedes_record_id == self.record_id:
            raise DomainValidationError("SELF_SUPERSESSION", ("supersedes_record_id",))

        if self.evidence_class in {EvidenceClass.INVOICE, EvidenceClass.MEASURED}:
            if self.source is None:
                raise DomainValidationError("SOURCE_REQUIRED", ("source",))
            if self.observed_at is None:
                raise DomainValidationError("OBSERVATION_TIME_REQUIRED", ("observed_at",))

        if self.evidence_class is EvidenceClass.DERIVED:
            if self.formula_id is None or not self.source_record_ids:
                raise DomainValidationError("DERIVATION_REQUIRED", ("formula_id",))
        elif self.formula_id is not None:
            raise DomainValidationError("FORMULA_NOT_ALLOWED", ("formula_id",))

        if self.evidence_class is EvidenceClass.ASSUMED:
            if self.assumption_acceptance is None:
                raise DomainValidationError(
                    "ASSUMPTION_ACCEPTANCE_REQUIRED", ("assumption_acceptance",)
                )
        elif self.assumption_acceptance is not None:
            raise DomainValidationError(
                "ASSUMPTION_ACCEPTANCE_NOT_ALLOWED", ("assumption_acceptance",)
            )

    def is_valid_at(self, instant: UtcInstant) -> bool:
        return self.validity.contains(instant)


@dataclass(frozen=True, slots=True)
class GovernedRecord[T]:
    """Immutable value paired with complete governed metadata."""

    metadata: ProvenanceMetadata
    value: T
