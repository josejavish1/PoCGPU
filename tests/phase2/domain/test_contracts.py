from datetime import datetime, timedelta
from decimal import Decimal
import pytest

from src.pocgpu.domain.capacity.contracts import (
    BenchmarkLoadPoint,
    BenchmarkRecord,
    CapacityResult,
    CompatibilityPolicy,
    DemandProfile,
    PackingPolicy,
    ResiliencePolicy,
    ServiceLevelObjective,
    ServingUnit,
    ServingUnitFingerprint,
    WorkloadProfile,
)


# --- ServingUnit Tests ---
def test_serving_unit_creation():
    su = ServingUnit(
        model_revision="v1.0", engine="TensorRT", version="8.6", runtime_stack="CUDA12.0",
        hardware_topology="A100-80GB", accelerator_count=8, parallelism_strategy="DP",
        precision="FP16", scheduler_config="FIFO", context_limit=4096,
        caching_mode="LRU", residency="OnPrem", deployment_settings={"env": "prod"},
    )
    assert su.model_revision == "v1.0"
    assert su.accelerator_count == 8
    assert su.deployment_settings == {"env": "prod"}


def test_serving_unit_immutability():
    su = ServingUnit(
        model_revision="v1.0", engine="TensorRT", version="8.6", runtime_stack="CUDA12.0",
        hardware_topology="A100-80GB", accelerator_count=8, parallelism_strategy="DP",
        precision="FP16", scheduler_config="FIFO", context_limit=4096,
        caching_mode="LRU", residency="OnPrem", deployment_settings={},
    )
    with pytest.raises(AttributeError):
        # noinspection PyDataclass
        su.model_revision = "v1.1"


def test_serving_unit_invalid_accelerator_count():
    with pytest.raises(ValueError, match="accelerator_count must be positive"):
        ServingUnit(
            model_revision="v1.0", engine="TensorRT", version="8.6", runtime_stack="CUDA12.0",
            hardware_topology="A100-80GB", accelerator_count=0, parallelism_strategy="DP",
            precision="FP16", scheduler_config="FIFO", context_limit=4096,
            caching_mode="LRU", residency="OnPrem", deployment_settings={},
        )


def test_serving_unit_invalid_context_limit():
    with pytest.raises(ValueError, match="context_limit must be positive"):
        ServingUnit(
            model_revision="v1.0", engine="TensorRT", version="8.6", runtime_stack="CUDA12.0",
            hardware_topology="A100-80GB", accelerator_count=8, parallelism_strategy="DP",
            precision="FP16", scheduler_config="FIFO", context_limit=-1,
            caching_mode="LRU", residency="OnPrem", deployment_settings={},
        )


# --- ServingUnitFingerprint Tests ---
def test_serving_unit_fingerprint_creation():
    su = ServingUnit(
        model_revision="v1.0", engine="TensorRT", version="8.6", runtime_stack="CUDA12.0",
        hardware_topology="A100-80GB", accelerator_count=8, parallelism_strategy="DP",
        precision="FP16", scheduler_config="FIFO", context_limit=4096,
        caching_mode="LRU", residency="OnPrem", deployment_settings={},
    )
    fp = ServingUnitFingerprint.from_serving_unit(su)
    assert isinstance(fp, ServingUnitFingerprint)
    assert isinstance(fp.value, str)
    assert len(fp.value) == 64  # SHA-256 hash length


def test_serving_unit_fingerprint_consistency():
    su1 = ServingUnit(
        model_revision="v1.0", engine="TensorRT", version="8.6", runtime_stack="CUDA12.0",
        hardware_topology="A100-80GB", accelerator_count=8, parallelism_strategy="DP",
        precision="FP16", scheduler_config="FIFO", context_limit=4096,
        caching_mode="LRU", residency="OnPrem", deployment_settings={},
    )
    su2 = ServingUnit(
        model_revision="v1.0", engine="TensorRT", version="8.6", runtime_stack="CUDA12.0",
        hardware_topology="A100-80GB", accelerator_count=8, parallelism_strategy="DP",
        precision="FP16", scheduler_config="FIFO", context_limit=4096,
        caching_mode="LRU", residency="OnPrem", deployment_settings={},
    )
    fp1 = ServingUnitFingerprint.from_serving_unit(su1)
    fp2 = ServingUnitFingerprint.from_serving_unit(su2)
    assert fp1 == fp2


def test_serving_unit_fingerprint_change_on_identity_field_mutation():
    su1 = ServingUnit(
        model_revision="v1.0", engine="TensorRT", version="8.6", runtime_stack="CUDA12.0",
        hardware_topology="A100-80GB", accelerator_count=8, parallelism_strategy="DP",
        precision="FP16", scheduler_config="FIFO", context_limit=4096,
        caching_mode="LRU", residency="OnPrem", deployment_settings={},
    )
    su2 = ServingUnit(
        model_revision="v1.1", engine="TensorRT", version="8.6", runtime_stack="CUDA12.0",
        hardware_topology="A100-80GB", accelerator_count=8, parallelism_strategy="DP",
        precision="FP16", scheduler_config="FIFO", context_limit=4096,
        caching_mode="LRU", residency="OnPrem", deployment_settings={},
    )
    fp1 = ServingUnitFingerprint.from_serving_unit(su1)
    fp2 = ServingUnitFingerprint.from_serving_unit(su2)
    assert fp1 != fp2


# --- ServiceLevelObjective Tests ---
def test_slo_creation():
    slo = ServiceLevelObjective(
        metric_identifier="latency", comparator=">=", threshold=Decimal("100"),
        percentile=Decimal("99"), evaluation_window=timedelta(minutes=5),
        mandatory=True, failure_behavior="fail_closed",
    )
    assert slo.metric_identifier == "latency"
    assert slo.threshold == Decimal("100")


def test_slo_invalid_percentile():
    with pytest.raises(ValueError, match="percentile must be between 0 and 100"):
        ServiceLevelObjective(
            metric_identifier="latency", comparator=">=", threshold=Decimal("100"),
            percentile=Decimal("101"), evaluation_window=timedelta(minutes=5),
            mandatory=True, failure_behavior="fail_closed",
        )
    with pytest.raises(ValueError, match="percentile must be between 0 and 100"):
        ServiceLevelObjective(
            metric_identifier="latency", comparator=">=", threshold=Decimal("100"),
            percentile=Decimal("-1"), evaluation_window=timedelta(minutes=5),
            mandatory=True, failure_behavior="fail_closed",
        )


def test_slo_invalid_threshold():
    with pytest.raises(ValueError, match="threshold must be non-negative"):
        ServiceLevelObjective(
            metric_identifier="latency", comparator=">=", threshold=Decimal("-100"),
            percentile=Decimal("99"), evaluation_window=timedelta(minutes=5),
            mandatory=True, failure_behavior="fail_closed",
        )


def test_slo_invalid_evaluation_window():
    with pytest.raises(ValueError, match="evaluation_window must be positive"):
        ServiceLevelObjective(
            metric_identifier="latency", comparator=">=", threshold=Decimal("100"),
            percentile=Decimal("99"), evaluation_window=timedelta(seconds=0),
            mandatory=True, failure_behavior="fail_closed",
        )


# --- WorkloadProfile Tests ---
def test_workload_profile_creation():
    slo = ServiceLevelObjective(
        metric_identifier="latency", comparator=">=", threshold=Decimal("100"),
        percentile=Decimal("99"), evaluation_window=timedelta(minutes=5),
        mandatory=True, failure_behavior="fail_closed",
    )
    wp = WorkloadProfile(
        input_token_length_distribution={"mean": Decimal("100"), "std_dev": Decimal("10")},
        output_token_length_distribution={"mean": Decimal("200"), "std_dev": Decimal("20")},
        request_type="chat", streaming_flag=True, cache_behavior="read_through",
        batching_constraints={"max_batch_size": 32}, concurrency_shape={"max_concurrent": 100},
        service_level_objectives=(slo,),
    )
    assert wp.request_type == "chat"
    assert wp.streaming_flag is True
    assert len(wp.service_level_objectives) == 1


# --- DemandProfile Tests ---
def test_demand_profile_creation():
    dp = DemandProfile(
        average_input_tokens_per_sec=Decimal("1000"), peak_input_tokens_per_sec=Decimal("1200"),
        average_output_tokens_per_sec=Decimal("2000"), peak_output_tokens_per_sec=Decimal("2400"),
        average_requests_per_sec=Decimal("10"), peak_requests_per_sec=Decimal("12"),
        average_concurrent_requests=Decimal("50"), peak_concurrent_requests=Decimal("60"),
        source_mode="observed", observation_window=timedelta(hours=24),
        seasonality_reference=datetime(2023, 1, 1),
        accepted_assumptions=["uniform_distribution"],
    )
    assert dp.average_requests_per_sec == Decimal("10")
    assert dp.peak_concurrent_requests == Decimal("60")


def test_demand_profile_negative_rates():
    with pytest.raises(ValueError, match="average_input_tokens_per_sec must be non-negative"):
        DemandProfile(
            average_input_tokens_per_sec=Decimal("-100"), peak_input_tokens_per_sec=Decimal("1200"),
            average_output_tokens_per_sec=Decimal("2000"), peak_output_tokens_per_sec=Decimal("2400"),
            average_requests_per_sec=Decimal("10"), peak_requests_per_sec=Decimal("12"),
            average_concurrent_requests=Decimal("50"), peak_concurrent_requests=Decimal("60"),
            source_mode="observed", observation_window=timedelta(hours=24),
            seasonality_reference=None, accepted_assumptions=[],
        )


def test_demand_profile_peak_less_than_average():
    with pytest.raises(ValueError, match="peak_input_tokens_per_sec cannot be less than average_input_tokens_per_sec"):
        DemandProfile(
            average_input_tokens_per_sec=Decimal("1000"), peak_input_tokens_per_sec=Decimal("900"),
            average_output_tokens_per_sec=Decimal("2000"), peak_output_tokens_per_sec=Decimal("2400"),
            average_requests_per_sec=Decimal("10"), peak_requests_per_sec=Decimal("12"),
            average_concurrent_requests=Decimal("50"), peak_concurrent_requests=Decimal("60"),
            source_mode="observed", observation_window=timedelta(hours=24),
            seasonality_reference=None, accepted_assumptions=[],
        )


def test_demand_profile_invalid_observation_window():
    with pytest.raises(ValueError, match="observation_window must be positive"):
        DemandProfile(
            average_input_tokens_per_sec=Decimal("1000"), peak_input_tokens_per_sec=Decimal("1200"),
            average_output_tokens_per_sec=Decimal("2000"), peak_output_tokens_per_sec=Decimal("2400"),
            average_requests_per_sec=Decimal("10"), peak_requests_per_sec=Decimal("12"),
            average_concurrent_requests=Decimal("50"), peak_concurrent_requests=Decimal("60"),
            source_mode="observed", observation_window=timedelta(0),
            seasonality_reference=None, accepted_assumptions=[],
        )


# --- BenchmarkLoadPoint Tests ---
def test_benchmark_load_point_creation():
    blp = BenchmarkLoadPoint(
        offered_load=Decimal("100"), achieved_input_tokens_per_sec=Decimal("90"),
        achieved_output_tokens_per_sec=Decimal("180"), achieved_requests_per_sec=Decimal("9"),
        achieved_concurrent_requests=Decimal("45"),
        latency_percentiles_ttft={Decimal("50"): Decimal("100"), Decimal("99"): Decimal("200")},
        latency_percentiles_tpot={Decimal("50"): Decimal("50"), Decimal("99"): Decimal("150")},
        queue_metrics={"avg_queue_depth": Decimal("5")},
        error_rate=Decimal("0.01"), stability_predicate=True,
        sample_count=1000, duration=timedelta(minutes=10),
    )
    assert blp.offered_load == Decimal("100")
    assert blp.error_rate == Decimal("0.01")


def test_benchmark_load_point_negative_rates():
    with pytest.raises(ValueError, match="offered_load must be non-negative"):
        BenchmarkLoadPoint(
            offered_load=Decimal("-100"), achieved_input_tokens_per_sec=Decimal("90"),
            achieved_output_tokens_per_sec=Decimal("180"), achieved_requests_per_sec=Decimal("9"),
            achieved_concurrent_requests=Decimal("45"),
            latency_percentiles_ttft={},
            latency_percentiles_tpot={},
            queue_metrics={},
            error_rate=Decimal("0.01"), stability_predicate=True,
            sample_count=1000, duration=timedelta(minutes=10),
        )


def test_benchmark_load_point_invalid_error_rate():
    with pytest.raises(ValueError, match="error_rate must be between 0 and 1"):
        BenchmarkLoadPoint(
            offered_load=Decimal("100"), achieved_input_tokens_per_sec=Decimal("90"),
            achieved_output_tokens_per_sec=Decimal("180"), achieved_requests_per_sec=Decimal("9"),
            achieved_concurrent_requests=Decimal("45"),
            latency_percentiles_ttft={},
            latency_percentiles_tpot={},
            queue_metrics={},
            error_rate=Decimal("1.1"), stability_predicate=True,
            sample_count=1000, duration=timedelta(minutes=10),
        )
    with pytest.raises(ValueError, match="error_rate must be between 0 and 1"):
        BenchmarkLoadPoint(
            offered_load=Decimal("100"), achieved_input_tokens_per_sec=Decimal("90"),
            achieved_output_tokens_per_sec=Decimal("180"), achieved_requests_per_sec=Decimal("9"),
            achieved_concurrent_requests=Decimal("45"),
            latency_percentiles_ttft={},
            latency_percentiles_tpot={},
            queue_metrics={},
            error_rate=Decimal("-0.1"), stability_predicate=True,
            sample_count=1000, duration=timedelta(minutes=10),
        )


def test_benchmark_load_point_invalid_sample_count():
    with pytest.raises(ValueError, match="sample_count must be non-negative"):
        BenchmarkLoadPoint(
            offered_load=Decimal("100"), achieved_input_tokens_per_sec=Decimal("90"),
            achieved_output_tokens_per_sec=Decimal("180"), achieved_requests_per_sec=Decimal("9"),
            achieved_concurrent_requests=Decimal("45"),
            latency_percentiles_ttft={},
            latency_percentiles_tpot={},
            queue_metrics={},
            error_rate=Decimal("0.01"), stability_predicate=True,
            sample_count=-1, duration=timedelta(minutes=10),
        )


def test_benchmark_load_point_invalid_duration():
    with pytest.raises(ValueError, match="duration must be positive"):
        BenchmarkLoadPoint(
            offered_load=Decimal("100"), achieved_input_tokens_per_sec=Decimal("90"),
            achieved_output_tokens_per_sec=Decimal("180"), achieved_requests_per_sec=Decimal("9"),
            achieved_concurrent_requests=Decimal("45"),
            latency_percentiles_ttft={},
            latency_percentiles_tpot={},
            queue_metrics={},
            error_rate=Decimal("0.01"), stability_predicate=True,
            sample_count=1000, duration=timedelta(0),
        )


# --- BenchmarkRecord Tests ---
def test_benchmark_record_creation():
    su = ServingUnit(
        model_revision="v1.0", engine="TensorRT", version="8.6", runtime_stack="CUDA12.0",
        hardware_topology="A100-80GB", accelerator_count=8, parallelism_strategy="DP",
        precision="FP16", scheduler_config="FIFO", context_limit=4096,
        caching_mode="LRU", residency="OnPrem", deployment_settings={},
    )
    fp = ServingUnitFingerprint.from_serving_unit(su)
    blp = BenchmarkLoadPoint(
        offered_load=Decimal("100"), achieved_input_tokens_per_sec=Decimal("90"),
        achieved_output_tokens_per_sec=Decimal("180"), achieved_requests_per_sec=Decimal("9"),
        achieved_concurrent_requests=Decimal("45"),
        latency_percentiles_ttft={},
        latency_percentiles_tpot={},
        queue_metrics={},
        error_rate=Decimal("0.01"), stability_predicate=True,
        sample_count=1000, duration=timedelta(minutes=10),
    )
    br = BenchmarkRecord(
        governed_identity="test-benchmark-001", serving_unit_fingerprint=fp,
        workload_identity="chat-v1", environment_metadata={"region": "us-east-1"},
        method="throughput", load_points=(blp,),
        raw_evidence_checksum="abc123def456", reviewer="john.doe",
        approval_status="approved", validity_window=(datetime(2023, 1, 1), datetime(2024, 1, 1)),
    )
    assert br.governed_identity == "test-benchmark-001"
    assert br.serving_unit_fingerprint == fp
    assert len(br.load_points) == 1


def test_benchmark_record_invalid_validity_window_type():
    su = ServingUnit(
        model_revision="v1.0", engine="TensorRT", version="8.6", runtime_stack="CUDA12.0",
        hardware_topology="A100-80GB", accelerator_count=8, parallelism_strategy="DP",
        precision="FP16", scheduler_config="FIFO", context_limit=4096,
        caching_mode="LRU", residency="OnPrem", deployment_settings={},
    )
    fp = ServingUnitFingerprint.from_serving_unit(su)
    blp = BenchmarkLoadPoint(
        offered_load=Decimal("100"), achieved_input_tokens_per_sec=Decimal("90"),
        achieved_output_tokens_per_sec=Decimal("180"), achieved_requests_per_sec=Decimal("9"),
        achieved_concurrent_requests=Decimal("45"),
        latency_percentiles_ttft={},
        latency_percentiles_tpot={},
        queue_metrics={},
        error_rate=Decimal("0.01"), stability_predicate=True,
        sample_count=1000, duration=timedelta(minutes=10),
    )
    with pytest.raises(ValueError, match=r"validity_window must be a tuple of two datetime objects"):
        BenchmarkRecord(
            governed_identity="test-benchmark-001", serving_unit_fingerprint=fp,
            workload_identity="chat-v1", environment_metadata={},
            method="throughput", load_points=(blp,),
            raw_evidence_checksum="abc123def456", reviewer="john.doe",
            approval_status="approved", validity_window=(datetime(2023, 1, 1), "not-a-datetime"), # type: ignore
        )
    with pytest.raises(ValueError, match=r"validity_window must be a tuple of two datetime objects"):
        BenchmarkRecord(
            governed_identity="test-benchmark-001", serving_unit_fingerprint=fp,
            workload_identity="chat-v1", environment_metadata={},
            method="throughput", load_points=(blp,),
            raw_evidence_checksum="abc123def456", reviewer="john.doe",
            approval_status="approved", validity_window=(datetime(2023, 1, 1),), # type: ignore
        )
    with pytest.raises(ValueError, match=r"validity_window must be a tuple of two datetime objects"):
        BenchmarkRecord(
            governed_identity="test-benchmark-001", serving_unit_fingerprint=fp,
            workload_identity="chat-v1", environment_metadata={},
            method="throughput", load_points=(blp,),
            raw_evidence_checksum="abc123def456", reviewer="john.doe",
            approval_status="approved", validity_window="not-a-tuple", # type: ignore
        )


def test_benchmark_record_invalid_validity_window_order():
    su = ServingUnit(
        model_revision="v1.0", engine="TensorRT", version="8.6", runtime_stack="CUDA12.0",
        hardware_topology="A100-80GB", accelerator_count=8, parallelism_strategy="DP",
        precision="FP16", scheduler_config="FIFO", context_limit=4096,
        caching_mode="LRU", residency="OnPrem", deployment_settings={},
    )
    fp = ServingUnitFingerprint.from_serving_unit(su)
    blp = BenchmarkLoadPoint(
        offered_load=Decimal("100"), achieved_input_tokens_per_sec=Decimal("90"),
        achieved_output_tokens_per_sec=Decimal("180"), achieved_requests_per_sec=Decimal("9"),
        achieved_concurrent_requests=Decimal("45"),
        latency_percentiles_ttft={},
        latency_percentiles_tpot={},
        queue_metrics={},
        error_rate=Decimal("0.01"), stability_predicate=True,
        sample_count=1000, duration=timedelta(minutes=10),
    )
    with pytest.raises(ValueError, match="validity_window start datetime must be before end datetime"):
        BenchmarkRecord(
            governed_identity="test-benchmark-001", serving_unit_fingerprint=fp,
            workload_identity="chat-v1", environment_metadata={},
            method="throughput", load_points=(blp,),
            raw_evidence_checksum="abc123def456", reviewer="john.doe",
            approval_status="approved", validity_window=(datetime(2024, 1, 1), datetime(2023, 1, 1)),
        )
    with pytest.raises(ValueError, match="validity_window start datetime must be before end datetime"):
        BenchmarkRecord(
            governed_identity="test-benchmark-001", serving_unit_fingerprint=fp,
            workload_identity="chat-v1", environment_metadata={},
            method="throughput", load_points=(blp,),
            raw_evidence_checksum="abc123def456", reviewer="john.doe",
            approval_status="approved", validity_window=(datetime(2023, 1, 1), datetime(2023, 1, 1)),
        )


# --- CompatibilityPolicy Tests ---
def test_compatibility_policy_creation():
    cp = CompatibilityPolicy(
        software_patch_compatibility="minor", hardware_stepping="exact",
        cache_modes=["LRU", "FIFO"], environment=["prod", "staging"],
        minimum_sample_count=100, minimum_duration=timedelta(minutes=30),
    )
    assert cp.software_patch_compatibility == "minor"
    assert cp.minimum_sample_count == 100


def test_compatibility_policy_invalid_minimum_sample_count():
    with pytest.raises(ValueError, match="minimum_sample_count must be non-negative"):
        CompatibilityPolicy(
            software_patch_compatibility="minor", hardware_stepping="exact",
            cache_modes=[], environment=[],
            minimum_sample_count=-1, minimum_duration=timedelta(minutes=30),
        )


def test_compatibility_policy_invalid_minimum_duration():
    with pytest.raises(ValueError, match="minimum_duration must be positive"):
        CompatibilityPolicy(
            software_patch_compatibility="minor", hardware_stepping="exact",
            cache_modes=[], environment=[],
            minimum_sample_count=100, minimum_duration=timedelta(0),
        )


# --- ResiliencePolicy Tests ---
def test_resilience_policy_creation():
    rp = ResiliencePolicy(
        headroom_ratio=Decimal("0.1"), growth_ratio=Decimal("0.05"),
        maintenance_reserve_ratio=Decimal("0.02"),
        failure_domain_survival_level={"server": 1, "rack": 0},
        multi_site_mode="active_active",
    )
    assert rp.headroom_ratio == Decimal("0.1")
    assert rp.multi_site_mode == "active_active"


def test_resilience_policy_negative_ratios():
    with pytest.raises(ValueError, match="headroom_ratio must be non-negative"):
        ResiliencePolicy(
            headroom_ratio=Decimal("-0.1"), growth_ratio=Decimal("0.05"),
            maintenance_reserve_ratio=Decimal("0.02"),
            failure_domain_survival_level={},
            multi_site_mode="none",
        )


def test_resilience_policy_negative_failure_domain_count():
    with pytest.raises(ValueError, match="failure_domain_survival_level\['server'\] must be non-negative"):
        ResiliencePolicy(
            headroom_ratio=Decimal("0.1"), growth_ratio=Decimal("0.05"),
            maintenance_reserve_ratio=Decimal("0.02"),
            failure_domain_survival_level={"server": -1},
            multi_site_mode="none",
        )


# --- PackingPolicy Tests ---
def test_packing_policy_creation():
    pp = PackingPolicy(
        accelerators_per_server=8, servers_per_rack=4, racks_per_zone=2, zones_per_site=1,
        anti_affinity_allocation_constraints={"model_a": ["server"]},
    )
    assert pp.accelerators_per_server == 8
    assert pp.zones_per_site == 1


def test_packing_policy_negative_counts():
    with pytest.raises(ValueError, match="accelerators_per_server must be non-negative"):
        PackingPolicy(
            accelerators_per_server=-1, servers_per_rack=4, racks_per_zone=2, zones_per_site=1,
            anti_affinity_allocation_constraints={},
        )


# --- CapacityResult Tests ---
def test_capacity_result_creation():
    cr = CapacityResult(
        per_constraint_requirements={"gpu_memory": Decimal("1000")},
        bottleneck_dimension="gpu_memory",
        intermediate_policy_step_quantities={"raw_capacity": Decimal("1200")},
        topological_allocations={"site_0": Decimal("1")},
        capacity_classifications={"tier": "A"},
        reconciliations=["reconcile_1"],
        evidence_references=["doc_link_1"],
        certification_blockers=[],
    )
    assert cr.bottleneck_dimension == "gpu_memory"
    assert cr.topological_allocations["site_0"] == Decimal("1")


def test_capacity_result_negative_quantities():
    with pytest.raises(ValueError, match="per_constraint_requirements\['gpu_memory'\] must be non-negative"):
        CapacityResult(
            per_constraint_requirements={"gpu_memory": Decimal("-1000")},
            bottleneck_dimension=None,
            intermediate_policy_step_quantities={},
            topological_allocations={},
            capacity_classifications={},
            reconciliations=[],
            evidence_references=[],
            certification_blockers=[],
        )
    with pytest.raises(ValueError, match="intermediate_policy_step_quantities\['raw_capacity'\] must be non-negative"):
        CapacityResult(
            per_constraint_requirements={},
            bottleneck_dimension=None,
            intermediate_policy_step_quantities={"raw_capacity": Decimal("-1200")},
            topological_allocations={},
            capacity_classifications={},
            reconciliations=[],
            evidence_references=[],
            certification_blockers=[],
        )
    with pytest.raises(ValueError, match="topological_allocations\['site_0'\] must be non-negative"):
        CapacityResult(
            per_constraint_requirements={},
            bottleneck_dimension=None,
            intermediate_policy_step_quantities={},
            topological_allocations={"site_0": Decimal("-1")},
            capacity_classifications={},
            reconciliations=[],
            evidence_references=[],
            certification_blockers=[],
        )
