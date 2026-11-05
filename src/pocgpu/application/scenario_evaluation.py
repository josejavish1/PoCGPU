"""Single canonical Phase 1 scenario-evaluation entry point."""

from __future__ import annotations

from pocgpu.application.policy_resolution import PolicyResolver
from pocgpu.domain.errors import DomainIssue, IssueKind, IssueSeverity
from pocgpu.domain.identifiers import SchemaId, SemanticVersion
from pocgpu.domain.ports.clock import Clock
from pocgpu.domain.ports.identity import IdentityProvider
from pocgpu.domain.ports.records import GovernedRecordRepository, PolicyRepository
from pocgpu.domain.ports.snapshots import SnapshotRepository
from pocgpu.domain.provenance import EvidenceClass, GovernedRecord
from pocgpu.domain.results import derive_result_state
from pocgpu.domain.scenarios import (
    CanonicalResult,
    OutputDomain,
    ResultSection,
    ScenarioDraft,
)
from pocgpu.domain.serialization import canonical_json_bytes, content_hash
from pocgpu.domain.snapshots import ScenarioSnapshot, SnapshotRecord

SNAPSHOT_SCHEMA_ID = SchemaId("schema.scenario-snapshot")
SNAPSHOT_SCHEMA_VERSION = SemanticVersion("1.0.0")


def _issue(
    code: str,
    kind: IssueKind,
    path: tuple[str, ...],
    **parameters: str,
) -> DomainIssue:
    return DomainIssue(
        code=code,
        kind=kind,
        severity=IssueSeverity.ERROR,
        path=path,
        parameters=tuple(sorted(parameters.items())),
        localization_key=f"error.scenario.{code.lower()}",
    )


class ScenarioEvaluationService:
    """Resolve, snapshot, and evaluate only Phase 1 foundation semantics."""

    def __init__(
        self,
        clock: Clock,
        identity_provider: IdentityProvider,
        record_repository: GovernedRecordRepository,
        policy_repository: PolicyRepository,
        snapshot_repository: SnapshotRepository,
        policy_resolver: PolicyResolver,
    ) -> None:
        self._clock = clock
        self._identity_provider = identity_provider
        self._record_repository = record_repository
        self._policy_repository = policy_repository
        self._snapshot_repository = snapshot_repository
        self._policy_resolver = policy_resolver

    def evaluate(self, scenario: ScenarioDraft) -> CanonicalResult:
        """Evaluate one immutable scenario without later-phase formulas."""

        captured_at = self._clock.now()
        issues: list[DomainIssue] = []
        resolved_records: list[GovernedRecord[object]] = []
        requested_records = tuple(
            sorted(
                set(scenario.input_record_ids).union(scenario.evidence_record_ids),
                key=lambda item: item.value,
            )
        )
        for record_id in requested_records:
            record = self._record_repository.get(scenario.tenant_id, record_id)
            if record is None:
                issues.append(
                    _issue(
                        "INPUT_RECORD_REQUIRED",
                        IssueKind.INPUT_REQUIRED,
                        ("records", record_id.value),
                        record_id=record_id.value,
                    )
                )
                continue
            if record.metadata.tenant_id != scenario.tenant_id:
                issues.append(
                    _issue(
                        "RECORD_TENANT_MISMATCH",
                        IssueKind.INVALID,
                        ("records", record_id.value),
                        record_id=record_id.value,
                    )
                )
                continue
            if not record.metadata.is_valid_at(captured_at):
                issues.append(
                    _issue(
                        "RECORD_STALE",
                        IssueKind.STALE,
                        ("records", record_id.value),
                        record_id=record_id.value,
                    )
                )
            resolved_records.append(record)

        policy_records = tuple(
            record
            for pack_id in scenario.policy_resolution_plan.pack_ids
            if (record := self._policy_repository.get(scenario.tenant_id, pack_id)) is not None
        )
        policy_result = self._policy_resolver.resolve(
            scenario.policy_resolution_plan,
            policy_records,
            captured_at,
        )
        issues.extend(policy_result.issues)

        unavailable_domains = tuple(
            domain for domain in scenario.requested_domains if domain is not OutputDomain.FOUNDATION
        )
        for domain in unavailable_domains:
            issues.append(
                _issue(
                    "OUTPUT_DOMAIN_UNAVAILABLE",
                    IssueKind.UNSUPPORTED,
                    ("requested_domains", domain.value),
                    domain=domain.value,
                )
            )

        snapshot_dependencies = (*resolved_records, *policy_records)
        snapshot_records = tuple(
            sorted(
                (self._snapshot_record(record) for record in snapshot_dependencies),
                key=lambda item: item.record_id.value,
            )
        )
        snapshot_id = self._identity_provider.new_snapshot_id()
        snapshot_payload = {
            "captured_at": captured_at,
            "policy_pack_ids": scenario.policy_resolution_plan.pack_ids,
            "records": snapshot_records,
            "scenario_id": scenario.scenario_id,
            "scenario_revision": scenario.revision,
            "tenant_id": scenario.tenant_id,
        }
        snapshot_hash = content_hash(
            canonical_json_bytes(
                snapshot_payload,
                SNAPSHOT_SCHEMA_ID,
                SNAPSHOT_SCHEMA_VERSION,
            )
        )
        snapshot = ScenarioSnapshot(
            snapshot_id=snapshot_id,
            tenant_id=scenario.tenant_id,
            scenario_id=scenario.scenario_id,
            scenario_revision=scenario.revision,
            captured_at=captured_at,
            records=snapshot_records,
            policy_pack_ids=scenario.policy_resolution_plan.pack_ids,
            content_hash=snapshot_hash,
        )
        self._snapshot_repository.add(snapshot)

        ordered_issues = tuple(sorted(issues, key=lambda item: (item.code, item.path)))
        calculations_complete = not ordered_issues and not unavailable_domains
        contains_assumptions = any(
            record.metadata.evidence_class is EvidenceClass.ASSUMED for record in resolved_records
        )
        state = derive_result_state(
            evaluation_requested=True,
            issues=ordered_issues,
            calculations_complete=calculations_complete,
            contains_assumptions=contains_assumptions,
            certification_requested=False,
            certification_gates=(),
        )
        sections = (
            (
                ResultSection(
                    domain=OutputDomain.FOUNDATION,
                    values=(
                        ("resolved_policy_count", len(policy_result.values)),
                        ("resolved_record_count", len(resolved_records)),
                    ),
                ),
            )
            if calculations_complete
            else ()
        )
        return CanonicalResult(
            scenario_id=scenario.scenario_id,
            scenario_revision=scenario.revision,
            snapshot_id=snapshot_id,
            snapshot_hash=snapshot_hash,
            engine_id=scenario.engine_id,
            engine_version=scenario.engine_version,
            state=state,
            issues=ordered_issues,
            sections=sections,
            evaluated_at=captured_at,
        )

    @staticmethod
    def _snapshot_record[T](record: GovernedRecord[T]) -> SnapshotRecord:
        serialized = canonical_json_bytes(
            record,
            record.metadata.schema_id,
            record.metadata.schema_version,
        )
        return SnapshotRecord(
            record_id=record.metadata.record_id,
            revision=record.metadata.revision,
            content_hash=content_hash(serialized),
        )
