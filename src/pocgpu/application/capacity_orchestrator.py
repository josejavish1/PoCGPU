import dataclasses
import hashlib
import json
from typing import Any, Protocol, TypeAlias, Literal
from enum import Enum

# --- Domain Primitives ---

TenantId: TypeAlias = str
ServingUnitId: TypeAlias = str
WorkloadProfileId: TypeAlias = str
DemandProfileId: TypeAlias = str
SloId: TypeAlias = str
ResiliencePolicyId: TypeAlias = str
PackingPolicyId: TypeAlias = str
BenchmarkRecordId: TypeAlias = str

# --- Helper for canonical hashing ---

def _to_canonical_dict(obj: Any) -> Any:
    """
    Recursively converts a dataclass instance or a dictionary into a canonical dictionary
    for consistent hashing.
    - Sorts dictionary keys.
    - Sorts lists of dataclasses/dictionaries by their 'id' field.
    """
    if dataclasses.is_dataclass(obj):
        data = {k: _to_canonical_dict(getattr(obj, k)) for k in obj.__dataclass_fields__}
        return dict(sorted(data.items()))
    elif isinstance(obj, dict):
        data = {k: _to_canonical_dict(v) for k, v in obj.items()}
        return dict(sorted(data.items()))
    elif isinstance(obj, list):
        canonical_items = [_to_canonical_dict(item) for item in obj]
        if canonical_items and all(isinstance(x, dict) for x in canonical_items):
            if all('id' in x for x in canonical_items):
                return sorted(canonical_items, key=lambda x: str(x['id']))
            return sorted(canonical_items, key=lambda x: json.dumps(x, sort_keys=True))
        return canonical_items
    else:
        return obj


# --- V2 Boundary Contracts (Requests, Snapshots, Results) ---

@dataclasses.dataclass(frozen=True)
class ServingUnitV2:
    id: ServingUnitId
    tenant_id: TenantId
    gpu_model: str
    memory_gb: int
    compute_units: int
    # Add other relevant serving unit attributes

    def _calculate_hash(self) -> str:
        canonical_data = _to_canonical_dict(self)
        json_string = json.dumps(canonical_data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(json_string.encode('utf-8')).hexdigest()

    def __post_init__(self) -> None:
        object.__setattr__(self, "version_hash", self._calculate_hash())


@dataclasses.dataclass(frozen=True)
class WorkloadProfileV2:
    id: WorkloadProfileId
    tenant_id: TenantId
    workload_type: str  # e.g., 'ML_INFERENCE', 'BATCH_PROCESSING'
    request_rate_rps: float  # Requests per second
    avg_latency_ms: float
    p99_latency_ms: float
    # Add other relevant workload profile attributes

    def _calculate_hash(self) -> str:
        canonical_data = _to_canonical_dict(self)
        json_string = json.dumps(canonical_data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(json_string.encode('utf-8')).hexdigest()

    def __post_init__(self) -> None:
        object.__setattr__(self, "version_hash", self._calculate_hash())


@dataclasses.dataclass(frozen=True)
class DemandProfileV2:
    id: DemandProfileId
    tenant_id: TenantId
    peak_multiplier: float
    burst_duration_seconds: int
    # Add other relevant demand profile attributes

    def _calculate_hash(self) -> str:
        canonical_data = _to_canonical_dict(self)
        json_string = json.dumps(canonical_data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(json_string.encode('utf-8')).hexdigest()

    def __post_init__(self) -> None:
        object.__setattr__(self, "version_hash", self._calculate_hash())


@dataclasses.dataclass(frozen=True)
class SloV2:
    id: SloId
    tenant_id: TenantId
    target_latency_ms: float
    target_availability_percent: float
    # Add other relevant SLO attributes

    def _calculate_hash(self) -> str:
        canonical_data = _to_canonical_dict(self)
        json_string = json.dumps(canonical_data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(json_string.encode('utf-8')).hexdigest()

    def __post_init__(self) -> None:
        object.__setattr__(self, "version_hash", self._calculate_hash())


@dataclasses.dataclass(frozen=True)
class ResiliencePolicyV2:
    id: ResiliencePolicyId
    tenant_id: TenantId
    policy_type: Literal['ZONE_REDUNDANCY', 'REGION_REDUNDANCY', 'SINGLE_ZONE']
    min_replicas: int
    # Add other relevant resilience policy attributes

    def _calculate_hash(self) -> str:
        canonical_data = _to_canonical_dict(self)
        json_string = json.dumps(canonical_data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(json_string.encode('utf-8')).hexdigest()

    def __post_init__(self) -> None:
        object.__setattr__(self, "version_hash", self._calculate_hash())


@dataclasses.dataclass(frozen=True)
class PackingPolicyV2:
    id: PackingPolicyId
    tenant_id: TenantId
    policy_type: Literal['DENSE_PACKING', 'SPARSE_PACKING']
    utilization_target_percent: float
    oversubscription_allowed: bool
    # Add other relevant packing policy attributes

    def _calculate_hash(self) -> str:
        canonical_data = _to_canonical_dict(self)
        json_string = json.dumps(canonical_data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(json_string.encode('utf-8')).hexdigest()

    def __post_init__(self) -> None:
        object.__setattr__(self, "version_hash", self._calculate_hash())


@dataclasses.dataclass(frozen=True)
class BenchmarkRecordV2:
    id: BenchmarkRecordId
    tenant_id: TenantId
    serving_unit_id: ServingUnitId
    workload_profile_id: WorkloadProfileId
    throughput_rps: float
    p99_latency_ms: float
    utilization_percent: float
    # Add other relevant benchmark attributes

    def _calculate_hash(self) -> str:
        canonical_data = _to_canonical_dict(self)
        json_string = json.dumps(canonical_data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(json_string.encode('utf-8')).hexdigest()

    def __post_init__(self) -> None:
        object.__setattr__(self, "version_hash", self._calculate_hash())


@dataclasses.dataclass(frozen=True)
class CapacityOrchestrationRequestV2:
    tenant_id: TenantId
    serving_unit_id: ServingUnitId
    workload_profile_id: WorkloadProfileId
    demand_profile_id: DemandProfileId
    slo_id: SloId
    resilience_policy_id: ResiliencePolicyId
    packing_policy_id: PackingPolicyId
    candidate_benchmark_ids: list[BenchmarkRecordId]

    def __post_init__(self) -> None:
        object.__setattr__(self, "candidate_benchmark_ids", sorted(self.candidate_benchmark_ids))


@dataclasses.dataclass(frozen=True)
class ScenarioSnapshotV2:
    request: CapacityOrchestrationRequestV2
    serving_unit: ServingUnitV2
    workload_profile: WorkloadProfileV2
    demand_profile: DemandProfileV2
    slo: SloV2
    resilience_policy: ResiliencePolicyV2
    packing_policy: PackingPolicyV2
    candidate_benchmarks: list[BenchmarkRecordV2]
    # Add hashes of all included entities for deterministic replay
    serving_unit_hash: str
    workload_profile_hash: str
    demand_profile_hash: str
    slo_hash: str
    resilience_policy_hash: str
    packing_policy_hash: str
    candidate_benchmark_hashes: list[str]

    def _calculate_hash(self) -> str:
        # Create a canonical dictionary representation of the snapshot
        # Ensure lists of benchmarks are sorted by ID for deterministic hashing
        canonical_data = _to_canonical_dict(self)
        json_string = json.dumps(canonical_data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(json_string.encode('utf-8')).hexdigest()

    def __post_init__(self) -> None:
        object.__setattr__(self, "snapshot_hash", self._calculate_hash())


class CertificationBlocker(str, Enum):
    INPUT_REQUIRED = "INPUT_REQUIRED"
    POLICY_REQUIRED = "POLICY_REQUIRED"
    BENCHMARK_REQUIRED = "BENCHMARK_REQUIRED"
    TECHNICAL_GATE_FAILED = "TECHNICAL_GATE_FAILED"
    PROVENANCE_GATE_FAILED = "PROVENANCE_GATE_FAILED"
    SLO_GATE_FAILED = "SLO_GATE_FAILED"
    RECONCILIATION_FAILED = "RECONCILIATION_FAILED"


@dataclasses.dataclass(frozen=True)
class CapacityOrchestrationResultV2:
    scenario_snapshot: ScenarioSnapshotV2
    certification_blocked: bool
    blockers: list[CertificationBlocker]
    recommended_serving_units: int | None
    estimated_cost_usd: float | None
    result_hash: str = dataclasses.field(default="")

    def _calculate_result_hash(self) -> str:
        temp_dict = {
            "scenario_snapshot": _to_canonical_dict(self.scenario_snapshot),
            "certification_blocked": self.certification_blocked,
            "blockers": [b.value if isinstance(b, Enum) else str(b) for b in self.blockers],
            "recommended_serving_units": self.recommended_serving_units,
            "estimated_cost_usd": self.estimated_cost_usd,
        }
        json_string = json.dumps(_to_canonical_dict(temp_dict), sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(json_string.encode('utf-8')).hexdigest()

    def __post_init__(self) -> None:
        if not self.result_hash:
            object.__setattr__(self, "result_hash", self._calculate_result_hash())


# --- Domain Repository Protocols ---

class ServingUnitCatalogPort(Protocol):
    def get_serving_unit(self, tenant_id: TenantId, serving_unit_id: ServingUnitId) -> ServingUnitV2 | None:
        """Retrieves a serving unit by its ID within a tenant's scope."""
        ...


class WorkloadRepositoryPort(Protocol):
    def get_workload_profile(self, tenant_id: TenantId, workload_profile_id: WorkloadProfileId) -> WorkloadProfileV2 | None:
        """Retrieves a workload profile by its ID within a tenant's scope."""
        ...

    def get_demand_profile(self, tenant_id: TenantId, demand_profile_id: DemandProfileId) -> DemandProfileV2 | None:
        """Retrieves a demand profile by its ID within a tenant's scope."""
        ...


class TopologyPolicyPort(Protocol):
    def get_slo(self, tenant_id: TenantId, slo_id: SloId) -> SloV2 | None:
        """Retrieves an SLO by its ID within a tenant's scope."""
        ...

    def get_resilience_policy(self, tenant_id: TenantId, resilience_policy_id: ResiliencePolicyId) -> ResiliencePolicyV2 | None:
        """Retrieves a resilience policy by its ID within a tenant's scope."""
        ...

    def get_packing_policy(self, tenant_id: TenantId, packing_policy_id: PackingPolicyId) -> PackingPolicyV2 | None:
        """Retrieves a packing policy by its ID within a tenant's scope."""
        ...


class BenchmarkRepositoryPort(Protocol):
    def get_benchmark_record(self, tenant_id: TenantId, benchmark_id: BenchmarkRecordId) -> BenchmarkRecordV2 | None:
        """Retrieves a benchmark record by its ID within a tenant's scope."""
        ...

    def get_benchmark_records_by_ids(self, tenant_id: TenantId, benchmark_ids: list[BenchmarkRecordId]) -> list[BenchmarkRecordV2]:
        """Retrieves multiple benchmark records by their IDs within a tenant's scope."""
        ...


# --- Capacity Orchestration Service ---

@dataclasses.dataclass
class CapacityOrchestrator:
    benchmark_repo: BenchmarkRepositoryPort
    serving_unit_catalog: ServingUnitCatalogPort
    workload_repo: WorkloadRepositoryPort
    topology_policy_repo: TopologyPolicyPort

    def orchestrate(self, request: CapacityOrchestrationRequestV2) -> CapacityOrchestrationResultV2:
        """
        Orchestrates capacity for a given request, enforcing tenant scope and deterministic replay.
        """
        tenant_id = request.tenant_id
        blockers: list[CertificationBlocker] = []

        # 1. Enforce tenant scope and resolve all required inputs
        serving_unit = self.serving_unit_catalog.get_serving_unit(tenant_id, request.serving_unit_id)
        if not serving_unit:
            blockers.append(CertificationBlocker.INPUT_REQUIRED)

        workload_profile = self.workload_repo.get_workload_profile(tenant_id, request.workload_profile_id)
        if not workload_profile:
            blockers.append(CertificationBlocker.INPUT_REQUIRED)

        demand_profile = self.workload_repo.get_demand_profile(tenant_id, request.demand_profile_id)
        if not demand_profile:
            blockers.append(CertificationBlocker.INPUT_REQUIRED)

        slo = self.topology_policy_repo.get_slo(tenant_id, request.slo_id)
        if not slo:
            blockers.append(CertificationBlocker.POLICY_REQUIRED)

        resilience_policy = self.topology_policy_repo.get_resilience_policy(tenant_id, request.resilience_policy_id)
        if not resilience_policy:
            blockers.append(CertificationBlocker.POLICY_REQUIRED)

        packing_policy = self.topology_policy_repo.get_packing_policy(tenant_id, request.packing_policy_id)
        if not packing_policy:
            blockers.append(CertificationBlocker.POLICY_REQUIRED)

        candidate_benchmarks = self.benchmark_repo.get_benchmark_records_by_ids(tenant_id, request.candidate_benchmark_ids)
        if not candidate_benchmarks:
            blockers.append(CertificationBlocker.BENCHMARK_REQUIRED)

        # If any critical input is missing, return a deterministic failure state
        if blockers:
            # Create a partial snapshot for hashing even if inputs are missing
            # This ensures deterministic replay for failure states too.
            scenario_snapshot = ScenarioSnapshotV2(
                request=request,
                serving_unit=serving_unit if serving_unit else ServingUnitV2(id=request.serving_unit_id, tenant_id=tenant_id, gpu_model="UNKNOWN", memory_gb=0, compute_units=0),
                workload_profile=workload_profile if workload_profile else WorkloadProfileV2(id=request.workload_profile_id, tenant_id=tenant_id, workload_type="UNKNOWN", request_rate_rps=0.0, avg_latency_ms=0.0, p99_latency_ms=0.0),
                demand_profile=demand_profile if demand_profile else DemandProfileV2(id=request.demand_profile_id, tenant_id=tenant_id, peak_multiplier=0.0, burst_duration_seconds=0),
                slo=slo if slo else SloV2(id=request.slo_id, tenant_id=tenant_id, target_latency_ms=0.0, target_availability_percent=0.0),
                resilience_policy=resilience_policy if resilience_policy else ResiliencePolicyV2(id=request.resilience_policy_id, tenant_id=tenant_id, policy_type='SINGLE_ZONE', min_replicas=0),
                packing_policy=packing_policy if packing_policy else PackingPolicyV2(id=request.packing_policy_id, tenant_id=tenant_id, policy_type='SPARSE_PACKING', utilization_target_percent=0.0, oversubscription_allowed=False),
                candidate_benchmarks=sorted(candidate_benchmarks, key=lambda bm: bm.id), # Ensure sorted for deterministic hash
                serving_unit_hash=serving_unit.version_hash if serving_unit else "",
                workload_profile_hash=workload_profile.version_hash if workload_profile else "",
                demand_profile_hash=demand_profile.version_hash if demand_profile else "",
                slo_hash=slo.version_hash if slo else "",
                resilience_policy_hash=resilience_policy.version_hash if resilience_policy else "",
                packing_policy_hash=packing_policy.version_hash if packing_policy else "",
                candidate_benchmark_hashes=sorted([bm.version_hash for bm in candidate_benchmarks]) # Ensure sorted for deterministic hash
            )
            return CapacityOrchestrationResultV2(
                scenario_snapshot=scenario_snapshot,
                certification_blocked=True,
                blockers=blockers,
                recommended_serving_units=None,
                estimated_cost_usd=None
            )

        # All required inputs are present, proceed with orchestration pipeline
        # 2. Record canonical hashes and versions into an immutable ScenarioSnapshot
        # Ensure candidate_benchmarks are sorted by ID for deterministic snapshot hash
        sorted_candidate_benchmarks = sorted(candidate_benchmarks, key=lambda bm: bm.id)
        sorted_candidate_benchmark_hashes = sorted([bm.version_hash for bm in sorted_candidate_benchmarks])

        scenario_snapshot = ScenarioSnapshotV2(
            request=request,
            serving_unit=serving_unit,
            workload_profile=workload_profile,
            demand_profile=demand_profile,
            slo=slo,
            resilience_policy=resilience_policy,
            packing_policy=packing_policy,
            candidate_benchmarks=sorted_candidate_benchmarks,
            serving_unit_hash=serving_unit.version_hash,
            workload_profile_hash=workload_profile.version_hash,
            demand_profile_hash=demand_profile.version_hash,
            slo_hash=slo.version_hash,
            resilience_policy_hash=resilience_policy.version_hash,
            packing_policy_hash=packing_policy.version_hash,
            candidate_benchmark_hashes=sorted_candidate_benchmark_hashes
        )

        # 4. Execute the canonical pipeline (simplified for POC)
        # This section would contain the actual complex logic for capacity calculation.
        # For this POC, we'll simulate a successful calculation.

        # CAP-001 benchmark compatibility (simplified: assume all are compatible)
        compatible_benchmarks = sorted_candidate_benchmarks

        if not compatible_benchmarks:
            blockers.append(CertificationBlocker.BENCHMARK_REQUIRED)

        # CAP-002 useful capacity selection (simplified: pick the first compatible benchmark)
        if compatible_benchmarks:
            selected_benchmark = compatible_benchmarks[0]
        else:
            selected_benchmark = None # Should be caught by BENCHMARK_REQUIRED blocker

        # Simulate sizing and utilization
        recommended_units = None
        estimated_cost = None

        if selected_benchmark and serving_unit and workload_profile and demand_profile and slo and resilience_policy and packing_policy:
            effective_request_rate = workload_profile.request_rate_rps * demand_profile.peak_multiplier
            capacity_per_unit = selected_benchmark.throughput_rps

            if capacity_per_unit > 0:
                raw_units = effective_request_rate / capacity_per_unit
                resilience_factor = resilience_policy.min_replicas if resilience_policy.min_replicas > 0 else 1
                resilient_units = max(raw_units, float(resilience_factor))

                if packing_policy.utilization_target_percent > 0:
                    target_utilization_ratio = packing_policy.utilization_target_percent / 100.0
                    packed_units = resilient_units / target_utilization_ratio
                else:
                    packed_units = resilient_units

                recommended_units = int(packed_units + 0.999999999)
                estimated_cost = recommended_units * 100.0

                if recommended_units > 10_000:
                    blockers.append(CertificationBlocker.TECHNICAL_GATE_FAILED)
            else:
                blockers.append(CertificationBlocker.TECHNICAL_GATE_FAILED)
                recommended_units = None
                estimated_cost = None

            if selected_benchmark.p99_latency_ms > slo.target_latency_ms:
                blockers.append(CertificationBlocker.SLO_GATE_FAILED)

            if recommended_units is not None and recommended_units <= 0:
                blockers.append(CertificationBlocker.TECHNICAL_GATE_FAILED)

            # Provenance gate (simplified: assume all benchmarks are valid for now)
            # Reconciliation gate (simplified: assume no reconciliation issues for now)

        else:
            # If we reached here, it means initial input checks passed, but some internal logic
            # might have failed to produce a selected_benchmark or other necessary components.
            # This should ideally be covered by more specific blockers earlier.
            if not selected_benchmark:
                blockers.append(CertificationBlocker.BENCHMARK_REQUIRED)
            if not serving_unit or not workload_profile or not demand_profile or not slo or not resilience_policy or not packing_policy:
                blockers.append(CertificationBlocker.TECHNICAL_GATE_FAILED)

        certification_blocked = bool(blockers)

        result = CapacityOrchestrationResultV2(
            scenario_snapshot=scenario_snapshot,
            certification_blocked=certification_blocked,
            blockers=blockers,
            recommended_serving_units=recommended_units,
            estimated_cost_usd=estimated_cost
        )

        # 6. Guarantee deterministic replay: result_hash is calculated in __post_init__
        return result