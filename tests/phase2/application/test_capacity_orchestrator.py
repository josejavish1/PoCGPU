import dataclasses
import pytest
import hashlib
import json
from typing import Any

from src.pocgpu.application.capacity_orchestrator import (
    CapacityOrchestrator,
    CapacityOrchestrationRequestV2,
    CapacityOrchestrationResultV2,
    ScenarioSnapshotV2,
    ServingUnitV2,
    WorkloadProfileV2,
    DemandProfileV2,
    SloV2,
    ResiliencePolicyV2,
    PackingPolicyV2,
    BenchmarkRecordV2,
    CertificationBlocker,
    ServingUnitCatalogPort,
    WorkloadRepositoryPort,
    TopologyPolicyPort,
    BenchmarkRepositoryPort,
    TenantId,
    ServingUnitId,
    WorkloadProfileId,
    DemandProfileId,
    SloId,
    ResiliencePolicyId,
    PackingPolicyId,
    BenchmarkRecordId,
    _to_canonical_dict
)

# --- In-memory/Fixture Adapters ---

@dataclasses.dataclass
class InMemoryServingUnitCatalog(ServingUnitCatalogPort):
    _serving_units: dict[TenantId, dict[ServingUnitId, ServingUnitV2]] = dataclasses.field(default_factory=dict)

    def get_serving_unit(self, tenant_id: TenantId, serving_unit_id: ServingUnitId) -> ServingUnitV2 | None:
        return self._serving_units.get(tenant_id, {}).get(serving_unit_id)


@dataclasses.dataclass
class InMemoryWorkloadRepository(WorkloadRepositoryPort):
    _workload_profiles: dict[TenantId, dict[WorkloadProfileId, WorkloadProfileV2]] = dataclasses.field(default_factory=dict)
    _demand_profiles: dict[TenantId, dict[DemandProfileId, DemandProfileV2]] = dataclasses.field(default_factory=dict)

    def get_workload_profile(self, tenant_id: TenantId, workload_profile_id: WorkloadProfileId) -> WorkloadProfileV2 | None:
        return self._workload_profiles.get(tenant_id, {}).get(workload_profile_id)

    def get_demand_profile(self, tenant_id: TenantId, demand_profile_id: DemandProfileId) -> DemandProfileV2 | None:
        return self._demand_profiles.get(tenant_id, {}).get(demand_profile_id)


@dataclasses.dataclass
class InMemoryTopologyPolicyRepository(TopologyPolicyPort):
    _slos: dict[TenantId, dict[SloId, SloV2]] = dataclasses.field(default_factory=dict)
    _resilience_policies: dict[TenantId, dict[ResiliencePolicyId, ResiliencePolicyV2]] = dataclasses.field(default_factory=dict)
    _packing_policies: dict[TenantId, dict[PackingPolicyId, PackingPolicyV2]] = dataclasses.field(default_factory=dict)

    def get_slo(self, tenant_id: TenantId, slo_id: SloId) -> SloV2 | None:
        return self._slos.get(tenant_id, {}).get(slo_id)

    def get_resilience_policy(self, tenant_id: TenantId, resilience_policy_id: ResiliencePolicyId) -> ResiliencePolicyV2 | None:
        return self._resilience_policies.get(tenant_id, {}).get(resilience_policy_id)

    def get_packing_policy(self, tenant_id: TenantId, packing_policy_id: PackingPolicyId) -> PackingPolicyV2 | None:
        return self._packing_policies.get(tenant_id, {}).get(packing_policy_id)


@dataclasses.dataclass
class InMemoryBenchmarkRepository(BenchmarkRepositoryPort):
    _benchmarks: dict[TenantId, dict[BenchmarkRecordId, BenchmarkRecordV2]] = dataclasses.field(default_factory=dict)

    def get_benchmark_record(self, tenant_id: TenantId, benchmark_id: BenchmarkRecordId) -> BenchmarkRecordV2 | None:
        return self._benchmarks.get(tenant_id, {}).get(benchmark_id)

    def get_benchmark_records_by_ids(self, tenant_id: TenantId, benchmark_ids: list[BenchmarkRecordId]) -> list[BenchmarkRecordV2]:
        tenant_benchmarks = self._benchmarks.get(tenant_id, {})
        return [tenant_benchmarks[bm_id] for bm_id in benchmark_ids if bm_id in tenant_benchmarks]


# --- Fixtures ---

@pytest.fixture
def mock_repos() -> dict[str, Any]:
    tenant_id = "tenant-123"

    serving_unit_a = ServingUnitV2(id="gpu-sku-a", tenant_id=tenant_id, gpu_model="NVIDIA A100", memory_gb=80, compute_units=6912)
    serving_unit_b = ServingUnitV2(id="gpu-sku-b", tenant_id=tenant_id, gpu_model="NVIDIA V100", memory_gb=32, compute_units=5120)

    workload_ml_inference = WorkloadProfileV2(id="ml-inference-v1", tenant_id=tenant_id, workload_type="ML_INFERENCE", request_rate_rps=1000.0, avg_latency_ms=10.0, p99_latency_ms=20.0)
    workload_batch_processing = WorkloadProfileV2(id="batch-processing-v1", tenant_id=tenant_id, workload_type="BATCH_PROCESSING", request_rate_rps=100.0, avg_latency_ms=100.0, p99_latency_ms=200.0)

    demand_peak_q4 = DemandProfileV2(id="peak-demand-q4", tenant_id=tenant_id, peak_multiplier=1.5, burst_duration_seconds=300)
    demand_steady = DemandProfileV2(id="steady-demand", tenant_id=tenant_id, peak_multiplier=1.0, burst_duration_seconds=0)

    slo_99_9_latency = SloV2(id="99.9-latency", tenant_id=tenant_id, target_latency_ms=25.0, target_availability_percent=99.9)
    slo_99_0_latency = SloV2(id="99.0-latency", tenant_id=tenant_id, target_latency_ms=50.0, target_availability_percent=99.0)

    resilience_dr_zone = ResiliencePolicyV2(id="dr-zone-redundancy", tenant_id=tenant_id, policy_type='ZONE_REDUNDANCY', min_replicas=2)
    resilience_single_zone = ResiliencePolicyV2(id="single-zone", tenant_id=tenant_id, policy_type='SINGLE_ZONE', min_replicas=1)

    packing_dense = PackingPolicyV2(id="dense-packing-v2", tenant_id=tenant_id, policy_type='DENSE_PACKING', utilization_target_percent=80.0, oversubscription_allowed=False)
    packing_sparse = PackingPolicyV2(id="sparse-packing-v1", tenant_id=tenant_id, policy_type='SPARSE_PACKING', utilization_target_percent=50.0, oversubscription_allowed=True)

    benchmark_gpu_a_ml_v1_001 = BenchmarkRecordV2(id="bm-gpu-a-ml-v1-001", tenant_id=tenant_id, serving_unit_id="gpu-sku-a", workload_profile_id="ml-inference-v1", throughput_rps=10000.0, p99_latency_ms=15.0, utilization_percent=70.0)
    benchmark_gpu_a_ml_v1_002 = BenchmarkRecordV2(id="bm-gpu-a-ml-v1-002", tenant_id=tenant_id, serving_unit_id="gpu-sku-a", workload_profile_id="ml-inference-v1", throughput_rps=12000.0, p99_latency_ms=18.0, utilization_percent=85.0)
    benchmark_gpu_b_ml_v1_001 = BenchmarkRecordV2(id="bm-gpu-b-ml-v1-001", tenant_id=tenant_id, serving_unit_id="gpu-sku-b", workload_profile_id="ml-inference-v1", throughput_rps=5000.0, p99_latency_ms=25.0, utilization_percent=60.0)

    return {
        "serving_unit_catalog": InMemoryServingUnitCatalog(_serving_units={tenant_id: {serving_unit_a.id: serving_unit_a, serving_unit_b.id: serving_unit_b}}),
        "workload_repo": InMemoryWorkloadRepository(
            _workload_profiles={tenant_id: {workload_ml_inference.id: workload_ml_inference, workload_batch_processing.id: workload_batch_processing}},
            _demand_profiles={tenant_id: {demand_peak_q4.id: demand_peak_q4, demand_steady.id: demand_steady}}
        ),
        "topology_policy_repo": InMemoryTopologyPolicyRepository(
            _slos={tenant_id: {slo_99_9_latency.id: slo_99_9_latency, slo_99_0_latency.id: slo_99_0_latency}},
            _resilience_policies={tenant_id: {resilience_dr_zone.id: resilience_dr_zone, resilience_single_zone.id: resilience_single_zone}},
            _packing_policies={tenant_id: {packing_dense.id: packing_dense, packing_sparse.id: packing_sparse}}
        ),
        "benchmark_repo": InMemoryBenchmarkRepository(_benchmarks={
            tenant_id: {
                benchmark_gpu_a_ml_v1_001.id: benchmark_gpu_a_ml_v1_001,
                benchmark_gpu_a_ml_v1_002.id: benchmark_gpu_a_ml_v1_002,
                benchmark_gpu_b_ml_v1_001.id: benchmark_gpu_b_ml_v1_001,
            }
        })
    }


@pytest.fixture
def orchestrator(mock_repos: dict[str, Any]) -> CapacityOrchestrator:
    return CapacityOrchestrator(
        benchmark_repo=mock_repos["benchmark_repo"],
        serving_unit_catalog=mock_repos["serving_unit_catalog"],
        workload_repo=mock_repos["workload_repo"],
        topology_policy_repo=mock_repos["topology_policy_repo"],
    )


@pytest.fixture
def valid_request() -> CapacityOrchestrationRequestV2:
    return CapacityOrchestrationRequestV2(
        tenant_id="tenant-123",
        serving_unit_id="gpu-sku-a",
        workload_profile_id="ml-inference-v1",
        demand_profile_id="peak-demand-q4",
        slo_id="99.9-latency",
        resilience_policy_id="dr-zone-redundancy",
        packing_policy_id="dense-packing-v2",
        candidate_benchmark_ids=["bm-gpu-a-ml-v1-001", "bm-gpu-a-ml-v1-002"],
    )


@pytest.fixture
def tenant_id() -> TenantId: return "tenant-123"
@pytest.fixture
def serving_unit_id() -> ServingUnitId: return "gpu-sku-a"
@pytest.fixture
def workload_profile_id() -> WorkloadProfileId: return "ml-inference-v1"
@pytest.fixture
def demand_profile_id() -> DemandProfileId: return "peak-demand-q4"
@pytest.fixture
def slo_id() -> SloId: return "99.9-latency"
@pytest.fixture
def resilience_policy_id() -> ResiliencePolicyId: return "dr-zone-redundancy"
@pytest.fixture
def packing_policy_id() -> PackingPolicyId: return "dense-packing-v2"
@pytest.fixture
def benchmark_id_1() -> BenchmarkRecordId: return "bm-gpu-a-ml-v1-001"
@pytest.fixture
def benchmark_id_2() -> BenchmarkRecordId: return "bm-gpu-a-ml-v1-002"


# --- Tests ---

def test_successful_orchestration(orchestrator: CapacityOrchestrator, valid_request: CapacityOrchestrationRequestV2) -> None:
    """Tests a successful capacity orchestration scenario."""
    result = orchestrator.orchestrate(valid_request)

    assert not result.certification_blocked
    assert not result.blockers
    assert result.recommended_serving_units is not None
    assert result.recommended_serving_units > 0
    assert result.estimated_cost_usd is not None
    assert result.estimated_cost_usd > 0.0
    assert result.scenario_snapshot is not None
    assert result.scenario_snapshot.snapshot_hash is not None
    assert result.result_hash is not None

    # Verify snapshot content
    snapshot = result.scenario_snapshot
    assert snapshot.request == valid_request
    assert snapshot.serving_unit.id == valid_request.serving_unit_id
    assert snapshot.workload_profile.id == valid_request.workload_profile_id
    assert snapshot.demand_profile.id == valid_request.demand_profile_id
    assert snapshot.slo.id == valid_request.slo_id
    assert snapshot.resilience_policy.id == valid_request.resilience_policy_id
    assert snapshot.packing_policy.id == valid_request.packing_policy_id
    assert len(snapshot.candidate_benchmarks) == len(valid_request.candidate_benchmark_ids)
    assert all(bm.id in valid_request.candidate_benchmark_ids for bm in snapshot.candidate_benchmarks)

    # Verify hashes are present
    assert snapshot.serving_unit_hash
    assert snapshot.workload_profile_hash
    assert snapshot.demand_profile_hash
    assert snapshot.slo_hash
    assert snapshot.resilience_policy_hash
    assert snapshot.packing_policy_hash
    assert snapshot.candidate_benchmark_hashes
    assert len(snapshot.candidate_benchmark_hashes) == len(snapshot.candidate_benchmarks)


def test_missing_serving_unit_blocks_certification(orchestrator: CapacityOrchestrator, valid_request: CapacityOrchestrationRequestV2) -> None:
    """Tests that a missing serving unit blocks certification."""
    request_with_missing_su = dataclasses.replace(valid_request, serving_unit_id="non-existent-gpu")
    result = orchestrator.orchestrate(request_with_missing_su)

    assert result.certification_blocked
    assert CertificationBlocker.INPUT_REQUIRED in result.blockers
    assert result.recommended_serving_units is None
    assert result.estimated_cost_usd is None
    assert result.scenario_snapshot is not None
    assert result.scenario_snapshot.snapshot_hash is not None
    assert result.result_hash is not None


def test_missing_workload_profile_blocks_certification(orchestrator: CapacityOrchestrator, valid_request: CapacityOrchestrationRequestV2) -> None:
    """Tests that a missing workload profile blocks certification."""
    request_with_missing_wp = dataclasses.replace(valid_request, workload_profile_id="non-existent-workload")
    result = orchestrator.orchestrate(request_with_missing_wp)

    assert result.certification_blocked
    assert CertificationBlocker.INPUT_REQUIRED in result.blockers
    assert result.recommended_serving_units is None
    assert result.estimated_cost_usd is None


def test_missing_demand_profile_blocks_certification(orchestrator: CapacityOrchestrator, valid_request: CapacityOrchestrationRequestV2) -> None:
    """Tests that a missing demand profile blocks certification."""
    request_with_missing_dp = dataclasses.replace(valid_request, demand_profile_id="non-existent-demand")
    result = orchestrator.orchestrate(request_with_missing_dp)

    assert result.certification_blocked
    assert CertificationBlocker.INPUT_REQUIRED in result.blockers
    assert result.recommended_serving_units is None
    assert result.estimated_cost_usd is None


def test_missing_slo_blocks_certification(orchestrator: CapacityOrchestrator, valid_request: CapacityOrchestrationRequestV2) -> None:
    """Tests that a missing SLO blocks certification."""
    request_with_missing_slo = dataclasses.replace(valid_request, slo_id="non-existent-slo")
    result = orchestrator.orchestrate(request_with_missing_slo)

    assert result.certification_blocked
    assert CertificationBlocker.POLICY_REQUIRED in result.blockers
    assert result.recommended_serving_units is None
    assert result.estimated_cost_usd is None


def test_missing_resilience_policy_blocks_certification(orchestrator: CapacityOrchestrator, valid_request: CapacityOrchestrationRequestV2) -> None:
    """Tests that a missing resilience policy blocks certification."""
    request_with_missing_rp = dataclasses.replace(valid_request, resilience_policy_id="non-existent-rp")
    result = orchestrator.orchestrate(request_with_missing_rp)

    assert result.certification_blocked
    assert CertificationBlocker.POLICY_REQUIRED in result.blockers
    assert result.recommended_serving_units is None
    assert result.estimated_cost_usd is None


def test_missing_packing_policy_blocks_certification(orchestrator: CapacityOrchestrator, valid_request: CapacityOrchestrationRequestV2) -> None:
    """Tests that a missing packing policy blocks certification."""
    request_with_missing_pp = dataclasses.replace(valid_request, packing_policy_id="non-existent-pp")
    result = orchestrator.orchestrate(request_with_missing_pp)

    assert result.certification_blocked
    assert CertificationBlocker.POLICY_REQUIRED in result.blockers
    assert result.recommended_serving_units is None
    assert result.estimated_cost_usd is None


def test_missing_candidate_benchmarks_blocks_certification(orchestrator: CapacityOrchestrator, valid_request: CapacityOrchestrationRequestV2) -> None:
    """Tests that missing candidate benchmarks block certification."""
    request_with_missing_bm = dataclasses.replace(valid_request, candidate_benchmark_ids=["non-existent-bm"])
    result = orchestrator.orchestrate(request_with_missing_bm)

    assert result.certification_blocked
    assert CertificationBlocker.BENCHMARK_REQUIRED in result.blockers
    assert result.recommended_serving_units is None
    assert result.estimated_cost_usd is None


def test_empty_candidate_benchmarks_blocks_certification(orchestrator: CapacityOrchestrator, valid_request: CapacityOrchestrationRequestV2) -> None:
    """Tests that an empty list of candidate benchmarks blocks certification."""
    request_with_empty_bm = dataclasses.replace(valid_request, candidate_benchmark_ids=[])
    result = orchestrator.orchestrate(request_with_empty_bm)

    assert result.certification_blocked
    assert CertificationBlocker.BENCHMARK_REQUIRED in result.blockers
    assert result.recommended_serving_units is None
    assert result.estimated_cost_usd is None


def test_slo_violation_blocks_certification(orchestrator: CapacityOrchestrator, mock_repos: dict[str, Any], valid_request: CapacityOrchestrationRequestV2) -> None:
    """Tests that an SLO violation blocks certification."""
    # Create a benchmark that violates the SLO (p99_latency_ms > target_latency_ms)
    tenant_id = valid_request.tenant_id
    violating_benchmark = BenchmarkRecordV2(
        id="bm-violating-slo",
        tenant_id=tenant_id,
        serving_unit_id=valid_request.serving_unit_id,
        workload_profile_id=valid_request.workload_profile_id,
        throughput_rps=10000.0,
        p99_latency_ms=30.0, # Higher than 99.9-latency's 25.0ms target
        utilization_percent=70.0
    )
    mock_repos["benchmark_repo"]._benchmarks[tenant_id][violating_benchmark.id] = violating_benchmark

    request_with_violating_bm = dataclasses.replace(valid_request, candidate_benchmark_ids=[violating_benchmark.id])
    result = orchestrator.orchestrate(request_with_violating_bm)

    assert result.certification_blocked
    assert CertificationBlocker.SLO_GATE_FAILED in result.blockers
    assert result.recommended_serving_units is not None # Calculation might still happen, but blocked by SLO


def test_deterministic_replay_scenario_snapshot_hash(
    orchestrator: CapacityOrchestrator,
    tenant_id: TenantId,
    serving_unit_id: ServingUnitId,
    workload_profile_id: WorkloadProfileId,
    demand_profile_id: DemandProfileId,
    slo_id: SloId,
    resilience_policy_id: ResiliencePolicyId,
    packing_policy_id: PackingPolicyId,
    benchmark_id_1: BenchmarkRecordId,
    benchmark_id_2: BenchmarkRecordId
) -> None:
    """
    Tests that identical inputs (even with reordered benchmark IDs) produce identical
    ScenarioSnapshotV2 hashes.
    """
    request_1 = CapacityOrchestrationRequestV2(
        tenant_id=tenant_id,
        serving_unit_id=serving_unit_id,
        workload_profile_id=workload_profile_id,
        demand_profile_id=demand_profile_id,
        slo_id=slo_id,
        resilience_policy_id=resilience_policy_id,
        packing_policy_id=packing_policy_id,
        candidate_benchmark_ids=[benchmark_id_1, benchmark_id_2],
    )

    request_2 = CapacityOrchestrationRequestV2(
        tenant_id=tenant_id,
        serving_unit_id=serving_unit_id,
        workload_profile_id=workload_profile_id,
        demand_profile_id=demand_profile_id,
        slo_id=slo_id,
        resilience_policy_id=resilience_policy_id,
        packing_policy_id=packing_policy_id,
        candidate_benchmark_ids=[benchmark_id_2, benchmark_id_1], # Reordered
    )

    result_1 = orchestrator.orchestrate(request_1)
    result_2 = orchestrator.orchestrate(request_2)

    assert result_1.scenario_snapshot.snapshot_hash == result_2.scenario_snapshot.snapshot_hash
    assert result_1.result_hash == result_2.result_hash


def test_scenario_snapshot_hash_stability_across_runs(orchestrator: CapacityOrchestrator, valid_request: CapacityOrchestrationRequestV2) -> None:
    """Tests that the scenario snapshot hash is stable across multiple runs with identical inputs."""
    result_1 = orchestrator.orchestrate(valid_request)
    result_2 = orchestrator.orchestrate(valid_request)

    assert result_1.scenario_snapshot.snapshot_hash == result_2.scenario_snapshot.snapshot_hash
    assert result_1.result_hash == result_2.result_hash


def test_scenario_snapshot_hash_changes_with_input_change(orchestrator: CapacityOrchestrator, valid_request: CapacityOrchestrationRequestV2, mock_repos: dict[str, Any]) -> None:
    """Tests that the scenario snapshot hash changes if an input changes."""
    result_original = orchestrator.orchestrate(valid_request)

    # Change a non-benchmark input (e.g., workload profile request rate)
    original_workload = mock_repos["workload_repo"].get_workload_profile(valid_request.tenant_id, valid_request.workload_profile_id)
    assert original_workload is not None
    modified_workload = dataclasses.replace(original_workload, request_rate_rps=2000.0)
    mock_repos["workload_repo"]._workload_profiles[valid_request.tenant_id][valid_request.workload_profile_id] = modified_workload

    result_modified = orchestrator.orchestrate(valid_request)

    assert result_original.scenario_snapshot.snapshot_hash != result_modified.scenario_snapshot.snapshot_hash
    assert result_original.result_hash != result_modified.result_hash


def test_scenario_snapshot_hash_changes_with_benchmark_change(orchestrator: CapacityOrchestrator, valid_request: CapacityOrchestrationRequestV2, mock_repos: dict[str, Any]) -> None:
    """Tests that the scenario snapshot hash changes if a benchmark record changes."""
    result_original = orchestrator.orchestrate(valid_request)

    # Change a benchmark record (e.g., throughput_rps of bm-gpu-a-ml-v1-001)
    original_benchmark = mock_repos["benchmark_repo"].get_benchmark_record(valid_request.tenant_id, "bm-gpu-a-ml-v1-001")
    assert original_benchmark is not None
    modified_benchmark = dataclasses.replace(original_benchmark, throughput_rps=15000.0)
    mock_repos["benchmark_repo"]._benchmarks[valid_request.tenant_id]["bm-gpu-a-ml-v1-001"] = modified_benchmark

    result_modified = orchestrator.orchestrate(valid_request)

    assert result_original.scenario_snapshot.snapshot_hash != result_modified.scenario_snapshot.snapshot_hash
    assert result_original.result_hash != result_modified.result_hash


def test_to_canonical_dict_sorts_lists_of_dataclasses() -> None:
    """Tests that _to_canonical_dict correctly sorts lists of dataclasses by 'id'."""
    @dataclasses.dataclass(frozen=True)
    class Item:
        id: str
        value: int

    list_unsorted = [
        Item(id="b", value=2),
        Item(id="a", value=1),
        Item(id="c", value=3),
    ]

    list_sorted = [
        Item(id="a", value=1),
        Item(id="b", value=2),
        Item(id="c", value=3),
    ]

    canonical_unsorted = _to_canonical_dict(list_unsorted)
    canonical_sorted = _to_canonical_dict(list_sorted)

    assert canonical_unsorted == canonical_sorted
    assert canonical_unsorted == [
        {'id': 'a', 'value': 1},
        {'id': 'b', 'value': 2},
        {'id': 'c', 'value': 3},
    ]


def test_to_canonical_dict_sorts_lists_of_dicts() -> None:
    """Tests that _to_canonical_dict correctly sorts lists of dictionaries by 'id'."""
    list_unsorted = [
        {"id": "b", "value": 2},
        {"id": "a", "value": 1},
        {"id": "c", "value": 3},
    ]

    list_sorted = [
        {"id": "a", "value": 1},
        {"id": "b", "value": 2},
        {"id": "c", "value": 3},
    ]

    canonical_unsorted = _to_canonical_dict(list_unsorted)
    canonical_sorted = _to_canonical_dict(list_sorted)

    assert canonical_unsorted == canonical_sorted
    assert canonical_unsorted == [
        {'id': 'a', 'value': 1},
        {'id': 'b', 'value': 2},
        {'id': 'c', 'value': 3},
    ]


def test_to_canonical_dict_handles_mixed_list_types() -> None:
    """Tests that _to_canonical_dict handles lists with mixed types (some sortable, some not)."""
    @dataclasses.dataclass(frozen=True)
    class Item:
        id: str
        value: int

    list_mixed = [
        Item(id="b", value=2),
        {"id": "a", "value": 1},
        "simple_string",
        Item(id="c", value=3),
        {"no_id_key": 4},
    ]

    # This list should not be sorted by 'id' because not all elements are sortable by 'id'
    canonical_mixed = _to_canonical_dict(list_mixed)

    assert canonical_mixed == [
        {'id': 'b', 'value': 2},
        {'id': 'a', 'value': 1},
        'simple_string',
        {'id': 'c', 'value': 3},
        {'no_id_key': 4},
    ]


def test_to_canonical_dict_handles_nested_structures() -> None:
    """Tests that _to_canonical_dict correctly handles nested dataclasses and lists."""
    @dataclasses.dataclass(frozen=True)
    class SubItem:
        id: str
        data: str

    @dataclasses.dataclass(frozen=True)
    class MainItem:
        id: str
        name: str
        sub_items: list[SubItem]
        details: dict[str, Any]

    obj_unsorted = MainItem(
        id="main-1",
        name="Test Main",
        sub_items=[
            SubItem(id="s2", data="data2"),
            SubItem(id="s1", data="data1"),
        ],
        details={
            "z_key": 3,
            "a_key": 1,
            "b_key": 2,
        }
    )

    obj_sorted = MainItem(
        id="main-1",
        name="Test Main",
        sub_items=[
            SubItem(id="s1", data="data1"),
            SubItem(id="s2", data="data2"),
        ],
        details={
            "a_key": 1,
            "b_key": 2,
            "z_key": 3,
        }
    )

    canonical_unsorted = _to_canonical_dict(obj_unsorted)
    canonical_sorted = _to_canonical_dict(obj_sorted)

    assert canonical_unsorted == canonical_sorted
    expected_canonical = {
        'details': {'a_key': 1, 'b_key': 2, 'z_key': 3},
        'id': 'main-1',
        'name': 'Test Main',
        'sub_items': [
            {'data': 'data1', 'id': 's1'},
            {'data': 'data2', 'id': 's2'}
        ]
    }
    assert canonical_unsorted == expected_canonical


def test_to_canonical_dict_handles_empty_list() -> None:
    """Tests that _to_canonical_dict handles empty lists correctly."""
    assert _to_canonical_dict([]) == []


def test_to_canonical_dict_handles_list_of_scalars() -> None:
    """Tests that _to_canonical_dict handles lists of scalar values correctly."""
    list_scalars = [3, 1, 2]
    canonical_scalars = _to_canonical_dict(list_scalars)
    assert canonical_scalars == [3, 1, 2] # Should not be sorted as they don't have 'id'


def test_to_canonical_dict_handles_none_values() -> None:
    """Tests that _to_canonical_dict handles None values correctly."""
    @dataclasses.dataclass(frozen=True)
    class OptionalItem:
        id: str
        optional_field: Any | None

    obj_with_none = OptionalItem(id="test", optional_field=None)
    canonical_obj = _to_canonical_dict(obj_with_none)
    assert canonical_obj == {'id': 'test', 'optional_field': None}


def test_to_canonical_dict_handles_complex_nested_structure_for_hashing() -> None:
    """Ensures complex nested structures are canonicalized for consistent hashing."""
    @dataclasses.dataclass(frozen=True)
    class InnerConfig:
        name: str
        value: int

    @dataclasses.dataclass(frozen=True)
    class OuterConfig:
        id: str
        settings: dict[str, Any]
        items: list[InnerConfig]

    obj1 = OuterConfig(
        id="config-1",
        settings={
            "paramB": 20,
            "paramA": 10,
            "paramC": {"subC": 30, "subA": 10}
        },
        items=[
            InnerConfig(name="itemY", value=2),
            InnerConfig(name="itemX", value=1)
        ]
    )

    obj2 = OuterConfig(
        id="config-1",
        settings={
            "paramA": 10,
            "paramB": 20,
            "paramC": {"subA": 10, "subC": 30}
        },
        items=[
            InnerConfig(name="itemX", value=1),
            InnerConfig(name="itemY", value=2)
        ]
    )

    canonical1 = _to_canonical_dict(obj1)
    canonical2 = _to_canonical_dict(obj2)

    assert canonical1 == canonical2

    # Verify the structure of the canonical output
    expected_canonical = {
        'id': 'config-1',
        'items': [
            {'name': 'itemX', 'value': 1},
            {'name': 'itemY', 'value': 2}
        ],
        'settings': {
            'paramA': 10,
            'paramB': 20,
            'paramC': {'subA': 10, 'subC': 30}
        }
    }
    assert canonical1 == expected_canonical

    # Test hash consistency
    hash1 = hashlib.sha256(json.dumps(canonical1, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()
    hash2 = hashlib.sha256(json.dumps(canonical2, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()
    assert hash1 == hash2


def test_tenant_scope_enforcement_serving_unit(orchestrator: CapacityOrchestrator, mock_repos: dict[str, Any], valid_request: CapacityOrchestrationRequestV2) -> None:
    """Tests that serving unit retrieval respects tenant scope."""
    other_tenant_id = "tenant-456"
    serving_unit_other_tenant = ServingUnitV2(id="gpu-sku-a", tenant_id=other_tenant_id, gpu_model="NVIDIA A100", memory_gb=80, compute_units=6912)
    mock_repos["serving_unit_catalog"]._serving_units[other_tenant_id] = {serving_unit_other_tenant.id: serving_unit_other_tenant}

    request_other_tenant = dataclasses.replace(valid_request, tenant_id=other_tenant_id)
    result = orchestrator.orchestrate(request_other_tenant)

    # Should be blocked because the benchmark IDs in valid_request are for "tenant-123"
    # and the serving unit for "gpu-sku-a" for "tenant-123" is not found under "tenant-456"
    assert result.certification_blocked
    assert CertificationBlocker.INPUT_REQUIRED in result.blockers # For serving unit
    assert CertificationBlocker.BENCHMARK_REQUIRED in result.blockers # For benchmarks


def test_tenant_scope_enforcement_benchmark(orchestrator: CapacityOrchestrator, mock_repos: dict[str, Any], valid_request: CapacityOrchestrationRequestV2) -> None:
    """Tests that benchmark retrieval respects tenant scope."""
    other_tenant_id = "tenant-456"
    # Add a benchmark with the same ID but for a different tenant
    benchmark_other_tenant = BenchmarkRecordV2(id="bm-gpu-a-ml-v1-001", tenant_id=other_tenant_id, serving_unit_id="gpu-sku-a", workload_profile_id="ml-inference-v1", throughput_rps=10000.0, p99_latency_ms=15.0, utilization_percent=70.0)
    mock_repos["benchmark_repo"]._benchmarks[other_tenant_id] = {benchmark_other_tenant.id: benchmark_other_tenant}

    # Request for original tenant, but try to fetch a benchmark that only exists for other_tenant_id
    request_with_other_tenant_benchmark = dataclasses.replace(valid_request, candidate_benchmark_ids=["bm-gpu-a-ml-v1-001"])
    # Temporarily remove the benchmark from the original tenant to ensure it's not found
    original_benchmark = mock_repos["benchmark_repo"]._benchmarks[valid_request.tenant_id].pop("bm-gpu-a-ml-v1-001")

    result = orchestrator.orchestrate(request_with_other_tenant_benchmark)

    assert result.certification_blocked
    assert CertificationBlocker.BENCHMARK_REQUIRED in result.blockers

    # Restore original benchmark for other tests
    mock_repos["benchmark_repo"]._benchmarks[valid_request.tenant_id]["bm-gpu-a-ml-v1-001"] = original_benchmark


def test_result_hash_deterministic_replay(orchestrator: CapacityOrchestrator, valid_request: CapacityOrchestrationRequestV2) -> None:
    """Tests that identical inputs produce identical result hashes."""
    result_1 = orchestrator.orchestrate(valid_request)
    result_2 = orchestrator.orchestrate(valid_request)

    assert result_1.result_hash == result_2.result_hash
    assert result_1.scenario_snapshot.snapshot_hash == result_2.scenario_snapshot.snapshot_hash


def test_result_hash_changes_with_input_change(orchestrator: CapacityOrchestrator, valid_request: CapacityOrchestrationRequestV2, mock_repos: dict[str, Any]) -> None:
    """Tests that the result hash changes if an input changes."""
    result_original = orchestrator.orchestrate(valid_request)

    # Change a non-benchmark input (e.g., workload profile request rate)
    original_workload = mock_repos["workload_repo"].get_workload_profile(valid_request.tenant_id, valid_request.workload_profile_id)
    assert original_workload is not None
    modified_workload = dataclasses.replace(original_workload, request_rate_rps=2000.0)
    mock_repos["workload_repo"]._workload_profiles[valid_request.tenant_id][valid_request.workload_profile_id] = modified_workload

    result_modified = orchestrator.orchestrate(valid_request)

    assert result_original.result_hash != result_modified.result_hash


def test_result_hash_changes_with_benchmark_change(orchestrator: CapacityOrchestrator, valid_request: CapacityOrchestrationRequestV2, mock_repos: dict[str, Any]) -> None:
    """Tests that the result hash changes if a benchmark record changes."""
    result_original = orchestrator.orchestrate(valid_request)

    # Change a benchmark record (e.g., throughput_rps of bm-gpu-a-ml-v1-001)
    original_benchmark = mock_repos["benchmark_repo"].get_benchmark_record(valid_request.tenant_id, "bm-gpu-a-ml-v1-001")
    assert original_benchmark is not None
    modified_benchmark = dataclasses.replace(original_benchmark, throughput_rps=15000.0)
    mock_repos["benchmark_repo"]._benchmarks[valid_request.tenant_id]["bm-gpu-a-ml-v1-001"] = modified_benchmark

    result_modified = orchestrator.orchestrate(valid_request)

    assert result_original.result_hash != result_modified.result_hash


def test_result_hash_deterministic_with_reordered_benchmarks(
    orchestrator: CapacityOrchestrator,
    tenant_id: TenantId,
    serving_unit_id: ServingUnitId,
    workload_profile_id: WorkloadProfileId,
    demand_profile_id: DemandProfileId,
    slo_id: SloId,
    resilience_policy_id: ResiliencePolicyId,
    packing_policy_id: PackingPolicyId,
    benchmark_id_1: BenchmarkRecordId,
    benchmark_id_2: BenchmarkRecordId
) -> None:
    """
    Tests that reordering candidate benchmark IDs in the request still produces
    the same result hash due to canonicalization.
    """
    request_1 = CapacityOrchestrationRequestV2(
        tenant_id=tenant_id,
        serving_unit_id=serving_unit_id,
        workload_profile_id=workload_profile_id,
        demand_profile_id=demand_profile_id,
        slo_id=slo_id,
        resilience_policy_id=resilience_policy_id,
        packing_policy_id=packing_policy_id,
        candidate_benchmark_ids=[benchmark_id_1, benchmark_id_2],
    )

    request_2 = CapacityOrchestrationRequestV2(
        tenant_id=tenant_id,
        serving_unit_id=serving_unit_id,
        workload_profile_id=workload_profile_id,
        demand_profile_id=demand_profile_id,
        slo_id=slo_id,
        resilience_policy_id=resilience_policy_id,
        packing_policy_id=packing_policy_id,
        candidate_benchmark_ids=[benchmark_id_2, benchmark_id_1], # Reordered
    )

    result_1 = orchestrator.orchestrate(request_1)
    result_2 = orchestrator.orchestrate(request_2)

    assert result_1.result_hash == result_2.result_hash
    assert result_1.scenario_snapshot.snapshot_hash == result_2.scenario_snapshot.snapshot_hash


def test_technical_gate_failure_zero_capacity_benchmark(orchestrator: CapacityOrchestrator, mock_repos: dict[str, Any], valid_request: CapacityOrchestrationRequestV2) -> None:
    """Tests that a benchmark with zero throughput leads to a technical gate failure."""
    tenant_id = valid_request.tenant_id
    zero_capacity_benchmark = BenchmarkRecordV2(
        id="bm-zero-capacity",
        tenant_id=tenant_id,
        serving_unit_id=valid_request.serving_unit_id,
        workload_profile_id=valid_request.workload_profile_id,
        throughput_rps=0.0, # Zero throughput
        p99_latency_ms=10.0,
        utilization_percent=50.0
    )
    mock_repos["benchmark_repo"]._benchmarks[tenant_id][zero_capacity_benchmark.id] = zero_capacity_benchmark

    request_zero_capacity_bm = dataclasses.replace(valid_request, candidate_benchmark_ids=[zero_capacity_benchmark.id])
    result = orchestrator.orchestrate(request_zero_capacity_bm)

    assert result.certification_blocked
    assert CertificationBlocker.TECHNICAL_GATE_FAILED in result.blockers
    assert result.recommended_serving_units is None # Or potentially a very high number, depending on exact calculation


def test_technical_gate_failure_zero_utilization_target(orchestrator: CapacityOrchestrator, mock_repos: dict[str, Any], valid_request: CapacityOrchestrationRequestV2) -> None:
    """Tests that a packing policy with zero utilization target is handled gracefully (no division by zero)."""
    tenant_id = valid_request.tenant_id
    zero_util_packing_policy = PackingPolicyV2(
        id="zero-util-packing",
        tenant_id=tenant_id,
        policy_type='DENSE_PACKING',
        utilization_target_percent=0.0, # Zero utilization target
        oversubscription_allowed=False
    )
    mock_repos["topology_policy_repo"]._packing_policies[tenant_id][zero_util_packing_policy.id] = zero_util_packing_policy

    request_zero_util_pp = dataclasses.replace(valid_request, packing_policy_id=zero_util_packing_policy.id)
    result = orchestrator.orchestrate(request_zero_util_pp)

    assert not result.certification_blocked # Should not block, just use raw resilient units
    assert result.recommended_serving_units is not None
    assert result.recommended_serving_units > 0


def test_technical_gate_failure_zero_min_replicas(orchestrator: CapacityOrchestrator, mock_repos: dict[str, Any], valid_request: CapacityOrchestrationRequestV2) -> None:
    """Tests that a resilience policy with zero min_replicas is handled gracefully (defaults to 1)."""
    tenant_id = valid_request.tenant_id
    zero_min_replicas_rp = ResiliencePolicyV2(
        id="zero-min-replicas",
        tenant_id=tenant_id,
        policy_type='SINGLE_ZONE',
        min_replicas=0 # Zero min replicas
    )
    mock_repos["topology_policy_repo"]._resilience_policies[tenant_id][zero_min_replicas_rp.id] = zero_min_replicas_rp

    request_zero_min_replicas_rp = dataclasses.replace(valid_request, resilience_policy_id=zero_min_replicas_rp.id)
    result = orchestrator.orchestrate(request_zero_min_replicas_rp)

    assert not result.certification_blocked # Should not block, defaults to 1
    assert result.recommended_serving_units is not None
    assert result.recommended_serving_units > 0


def test_technical_gate_failure_excessive_recommended_units(orchestrator: CapacityOrchestrator, mock_repos: dict[str, Any], valid_request: CapacityOrchestrationRequestV2) -> None:
    """Tests that an extremely high number of recommended units triggers a technical gate failure."""
    tenant_id = valid_request.tenant_id
    # Create a workload with extremely high request rate
    high_demand_workload = WorkloadProfileV2(
        id="high-demand-workload",
        tenant_id=tenant_id,
        workload_type="ML_INFERENCE",
        request_rate_rps=1_000_000_000.0, # 1 billion RPS
        avg_latency_ms=10.0,
        p99_latency_ms=20.0
    )
    mock_repos["workload_repo"]._workload_profiles[tenant_id][high_demand_workload.id] = high_demand_workload

    request_high_demand = dataclasses.replace(valid_request, workload_profile_id=high_demand_workload.id)
    result = orchestrator.orchestrate(request_high_demand)

    assert result.certification_blocked
    assert CertificationBlocker.TECHNICAL_GATE_FAILED in result.blockers
    assert result.recommended_serving_units is not None # Calculation still happens, but flagged
    assert result.recommended_serving_units > 0 # Should be a very large number


def test_input_required_blocker_deterministic_hash(orchestrator: CapacityOrchestrator, valid_request: CapacityOrchestrationRequestV2) -> None:
    """Tests that the snapshot hash is deterministic even for INPUT_REQUIRED blockers."""
    request_missing_su_1 = dataclasses.replace(valid_request, serving_unit_id="non-existent-gpu")
    request_missing_su_2 = dataclasses.replace(valid_request, serving_unit_id="non-existent-gpu") # Identical request

    result_1 = orchestrator.orchestrate(request_missing_su_1)
    result_2 = orchestrator.orchestrate(request_missing_su_2)

    assert result_1.certification_blocked
    assert result_2.certification_blocked
    assert CertificationBlocker.INPUT_REQUIRED in result_1.blockers
    assert CertificationBlocker.INPUT_REQUIRED in result_2.blockers

    assert result_1.scenario_snapshot.snapshot_hash == result_2.scenario_snapshot.snapshot_hash
    assert result_1.result_hash == result_2.result_hash


def test_policy_required_blocker_deterministic_hash(orchestrator: CapacityOrchestrator, valid_request: CapacityOrchestrationRequestV2) -> None:
    """Tests that the snapshot hash is deterministic even for POLICY_REQUIRED blockers."""
    request_missing_slo_1 = dataclasses.replace(valid_request, slo_id="non-existent-slo")
    request_missing_slo_2 = dataclasses.replace(valid_request, slo_id="non-existent-slo") # Identical request

    result_1 = orchestrator.orchestrate(request_missing_slo_1)
    result_2 = orchestrator.orchestrate(request_missing_slo_2)

    assert result_1.certification_blocked
    assert result_2.certification_blocked
    assert CertificationBlocker.POLICY_REQUIRED in result_1.blockers
    assert CertificationBlocker.POLICY_REQUIRED in result_2.blockers

    assert result_1.scenario_snapshot.snapshot_hash == result_2.scenario_snapshot.snapshot_hash
    assert result_1.result_hash == result_2.result_hash


def test_benchmark_required_blocker_deterministic_hash(orchestrator: CapacityOrchestrator, valid_request: CapacityOrchestrationRequestV2) -> None:
    """Tests that the snapshot hash is deterministic even for BENCHMARK_REQUIRED blockers."""
    request_missing_bm_1 = dataclasses.replace(valid_request, candidate_benchmark_ids=["non-existent-bm"])
    request_missing_bm_2 = dataclasses.replace(valid_request, candidate_benchmark_ids=["non-existent-bm"])

    result_1 = orchestrator.orchestrate(request_missing_bm_1)
    result_2 = orchestrator.orchestrate(request_missing_bm_2)

    assert result_1.certification_blocked
    assert result_2.certification_blocked
    assert CertificationBlocker.BENCHMARK_REQUIRED in result_1.blockers
    assert CertificationBlocker.BENCHMARK_REQUIRED in result_2.blockers

    assert result_1.scenario_snapshot.snapshot_hash == result_2.scenario_snapshot.snapshot_hash
    assert result_1.result_hash == result_2.result_hash