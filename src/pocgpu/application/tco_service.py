import dataclasses
import datetime
import hashlib
import json
from enum import Enum
from typing import Protocol, TypeAlias, Any
from uuid import UUID, uuid4

# --- Type Aliases ---
TenantId: TypeAlias = UUID
UtcInstant: TypeAlias = datetime.datetime

# --- Enums ---
class TcoCertificationStatus(Enum):
    """
    Represents the certification status of a TCO calculation result.
    """
    CERTIFIED = "CERTIFIED"
    INPUT_REQUIRED = "INPUT_REQUIRED"
    POLICY_REQUIRED = "POLICY_REQUIRED"
    STALE_EVIDENCE = "STALE_EVIDENCE"
    ASSUMPTION_BASED = "ASSUMPTION_BASED"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"

# --- Domain Models ---
@dataclasses.dataclass(frozen=True)
class EvidenceBlock:
    """
    Represents a block of financial evidence.
    """
    id: UUID
    tenant_id: TenantId
    data: dict[str, Any]
    version: str
    is_stale: bool
    captured_at: UtcInstant

@dataclasses.dataclass(frozen=True)
class Policy:
    """
    Represents an accounting or allocation policy.
    """
    id: UUID
    tenant_id: TenantId
    name: str
    definition: dict[str, Any]
    version: str
    is_resolved: bool

@dataclasses.dataclass(frozen=True)
class CapacityReference:
    """
    Represents an immutable Phase 2 capacity reference.
    """
    id: UUID
    tenant_id: TenantId
    reference_data: dict[str, Any]
    version: str

@dataclasses.dataclass(frozen=True)
class TcoInputSnapshot:
    """
    A snapshot of all governed inputs and immutable capacity references
    used for a TCO calculation.
    """
    evidence_blocks: tuple[EvidenceBlock, ...]
    policies: tuple[Policy, ...]
    capacity_references: tuple[CapacityReference, ...]
    assumed_power_cost_present: bool
    critical_facts_present: bool

@dataclasses.dataclass(frozen=True)
class TcoResult:
    """
    The canonical structure for a TCO calculation result.
    """
    calculated_value: float
    certification_status: TcoCertificationStatus
    provenance_hash: str
    json_bytes: bytes
    snapshot_id: UUID

# --- Repository Protocols ---
class EvidenceRepositoryProtocol(Protocol):
    """
    Protocol for managing financial evidence blocks.
    """
    def get_evidence_blocks(self, tenant_id: TenantId, ids: list[UUID]) -> list[EvidenceBlock]: ...
    def add_evidence_block(self, block: EvidenceBlock) -> None: ...

class PolicyRepositoryProtocol(Protocol):
    """
    Protocol for managing facility policies.
    """
    def get_policies(self, tenant_id: TenantId, ids: list[UUID]) -> list[Policy]: ...
    def add_policy(self, policy: Policy) -> None: ...

class CapacityReferenceRepositoryProtocol(Protocol):
    """
    Protocol for managing immutable capacity references.
    """
    def get_capacity_references(self, tenant_id: TenantId, ids: list[UUID]) -> list[CapacityReference]: ...
    def add_capacity_reference(self, reference: CapacityReference) -> None: ...

# --- In-Memory Adapters (for demonstration) ---
class InMemoryEvidenceRepository(EvidenceRepositoryProtocol):
    """
    Deterministic in-memory adapter for EvidenceBlock storage.
    """
    def __init__(self) -> None:
        self._store: dict[UUID, EvidenceBlock] = {}

    def get_evidence_blocks(self, tenant_id: TenantId, ids: list[UUID]) -> list[EvidenceBlock]:
        return [
            block for block_id, block in self._store.items()
            if block_id in ids and block.tenant_id == tenant_id
        ]

    def add_evidence_block(self, block: EvidenceBlock) -> None:
        self._store[block.id] = block

class InMemoryPolicyRepository(PolicyRepositoryProtocol):
    """
    Deterministic in-memory adapter for Policy storage.
    """
    def __init__(self) -> None:
        self._store: dict[UUID, Policy] = {}

    def get_policies(self, tenant_id: TenantId, ids: list[UUID]) -> list[Policy]:
        return [
            policy for policy_id, policy in self._store.items()
            if policy_id in ids and policy.tenant_id == tenant_id
        ]

    def add_policy(self, policy: Policy) -> None:
        self._store[policy.id] = policy

class InMemoryCapacityReferenceRepository(CapacityReferenceRepositoryProtocol):
    """
    Deterministic in-memory adapter for CapacityReference storage.
    """
    def __init__(self) -> None:
        self._store: dict[UUID, CapacityReference] = {}

    def get_capacity_references(self, tenant_id: TenantId, ids: list[UUID]) -> list[CapacityReference]:
        return [
            ref for ref_id, ref in self._store.items()
            if ref_id in ids and ref.tenant_id == tenant_id
        ]

    def add_capacity_reference(self, reference: CapacityReference) -> None:
        self._store[reference.id] = reference

# --- TCO Calculation Service ---
class TcoCalculationService:
    """
    Service responsible for resolving, snapshotting, calculating, and certifying TCO.
    Enforces tenant scope and certification gates.
    """
    def __init__(
        self,
        evidence_repo: EvidenceRepositoryProtocol,
        policy_repo: PolicyRepositoryProtocol,
        capacity_ref_repo: CapacityReferenceRepositoryProtocol,
    ) -> None:
        self._evidence_repo = evidence_repo
        self._policy_repo = policy_repo
        self._capacity_ref_repo = capacity_ref_repo

    def _resolve_and_snapshot_inputs(
        self,
        tenant_id: TenantId,
        evidence_ids: list[UUID],
        policy_ids: list[UUID],
        capacity_ref_ids: list[UUID],
        assumed_power_cost_present: bool,
        critical_facts_required: bool = True,
    ) -> TcoInputSnapshot:
        """
        Resolves and snapshots all governed inputs and Phase 2 immutable capacity references.
        """
        resolved_evidence = self._evidence_repo.get_evidence_blocks(tenant_id, evidence_ids)
        resolved_policies = self._policy_repo.get_policies(tenant_id, policy_ids)
        resolved_capacity_refs = self._capacity_ref_repo.get_capacity_references(tenant_id, capacity_ref_ids)

        # Determine if critical facts are present.
        # For this POC, we'll define "critical facts" as simply having *any* evidence if required.
        # A real system would check for specific evidence types/keys.
        critical_facts_present = (not critical_facts_required) or (len(resolved_evidence) > 0)

        return TcoInputSnapshot(
            evidence_blocks=tuple(sorted(resolved_evidence, key=lambda x: x.id)),
            policies=tuple(sorted(resolved_policies, key=lambda x: x.id)),
            capacity_references=tuple(sorted(resolved_capacity_refs, key=lambda x: x.id)),
            assumed_power_cost_present=assumed_power_cost_present,
            critical_facts_present=critical_facts_present,
        )

    def _determine_certification_status(self, snapshot: TcoInputSnapshot) -> TcoCertificationStatus:
        """
        Enforces certification gates based on the input snapshot.
        """
        if not snapshot.critical_facts_present:
            return TcoCertificationStatus.INPUT_REQUIRED

        if any(not policy.is_resolved for policy in snapshot.policies):
            return TcoCertificationStatus.POLICY_REQUIRED

        if any(evidence.is_stale for evidence in snapshot.evidence_blocks):
            return TcoCertificationStatus.STALE_EVIDENCE

        if snapshot.assumed_power_cost_present:
            return TcoCertificationStatus.ASSUMPTION_BASED

        return TcoCertificationStatus.CERTIFIED

    def _perform_calculation(self, snapshot: TcoInputSnapshot) -> float:
        """
        Performs a dummy TCO calculation based on the snapshot.
        In a real system, this would be a complex logic.
        """
        base_cost = 100.0
        for evidence in snapshot.evidence_blocks:
            base_cost += evidence.data.get("cost_factor", 0.0)
        for policy in snapshot.policies:
            base_cost += policy.definition.get("policy_impact", 0.0)
        for ref in snapshot.capacity_references:
            base_cost += ref.reference_data.get("capacity_cost", 0.0)

        if snapshot.assumed_power_cost_present:
            base_cost *= 1.1

        return round(base_cost, 2)

    def _generate_deterministic_output(self, snapshot: TcoInputSnapshot, calculated_value: float, status: TcoCertificationStatus) -> tuple[bytes, str]:
        """
        Generates deterministic JSON serialization bytes and SHA-256 provenance hash.
        """
        class CustomJsonEncoder(json.JSONEncoder):
            def default(self, obj: Any) -> Any:
                if isinstance(obj, UUID):
                    return str(obj)
                if isinstance(obj, datetime.datetime):
                    return obj.isoformat()
                if isinstance(obj, Enum):
                    return obj.value
                if dataclasses.is_dataclass(obj):
                    return dataclasses.asdict(obj)
                return super().default(obj)

        serializable_data = {
            "calculated_value": calculated_value,
            "certification_status": status,
            "input_snapshot": snapshot,
        }

        json_bytes = json.dumps(
            serializable_data,
            sort_keys=True,
            separators=(",", ":"),
            cls=CustomJsonEncoder
        ).encode("utf-8")

        provenance_hash = hashlib.sha256(json_bytes).hexdigest()
        return json_bytes, provenance_hash

    def calculate_tco(
        self,
        tenant_id: TenantId,
        evidence_ids: list[UUID],
        policy_ids: list[UUID],
        capacity_ref_ids: list[UUID],
        assumed_power_cost_present: bool = False,
        critical_facts_required: bool = True,
    ) -> TcoResult:
        """
        Resolves and snapshots all governed inputs and Phase 2 immutable capacity references
        prior to calculation. Enforces certification gates and guarantees deterministic
        TcoResult structures, JSON serialization bytes, and SHA-256 provenance hashes.
        """
        input_snapshot = self._resolve_and_snapshot_inputs(
            tenant_id=tenant_id,
            evidence_ids=evidence_ids,
            policy_ids=policy_ids,
            capacity_ref_ids=capacity_ref_ids,
            assumed_power_cost_present=assumed_power_cost_present,
            critical_facts_required=critical_facts_required,
        )

        certification_status = self._determine_certification_status(input_snapshot)

        calculated_value: float
        if certification_status in {TcoCertificationStatus.INPUT_REQUIRED, TcoCertificationStatus.POLICY_REQUIRED}:
            calculated_value = 0.0
        else:
            calculated_value = self._perform_calculation(input_snapshot)

        json_bytes, provenance_hash = self._generate_deterministic_output(
            input_snapshot, calculated_value, certification_status
        )

        return TcoResult(
            calculated_value=calculated_value,
            certification_status=certification_status,
            provenance_hash=provenance_hash,
            json_bytes=json_bytes,
            snapshot_id=uuid4(),
        )
