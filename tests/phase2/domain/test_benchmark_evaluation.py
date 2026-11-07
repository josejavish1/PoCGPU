import datetime
from datetime import timedelta
import pytest

from src.pocgpu.domain.capacity.benchmark_evaluation import (
    evaluate_benchmark_compatibility,
    select_useful_capacity,
    SLOMetric,
    ApprovalStatus,
    MeasurementMethod,
    BlockerReason,
    ServiceLevelObjective,
    WorkloadProfile,
    CompatibilityPolicy,
    BenchmarkLoadPoint,
    BenchmarkRecord,
    UsefulCapacityOutcome,
    BenchmarkCompatibilityOutcome,
)


@pytest.fixture
def default_policy():
    return CompatibilityPolicy(
        allowed_measurement_methods=frozenset({MeasurementMethod.STANDARD_V1}),
        min_sample_count=100,
        min_duration_seconds=60.0,
    )


@pytest.fixture
def evaluation_timestamp():
    return datetime.datetime(2023, 10, 26, 12, 0)


@pytest.fixture
def target_serving_unit():
    return "GPU_MODEL_A_V1.0"


@pytest.fixture
def target_workload():
    return WorkloadProfile(
        id="WORKLOAD_A",
        slos=[
            ServiceLevelObjective(metric_name=SLOMetric.TTFT_P99, threshold=100.0, operator="<=", is_mandatory=True),
            ServiceLevelObjective(metric_name=SLOMetric.TPOT_P99, threshold=50.0, operator="<=", is_mandatory=True),
            ServiceLevelObjective(metric_name=SLOMetric.ERROR_RATE, threshold=0.01, operator="<=", is_mandatory=True),
            ServiceLevelObjective(metric_name=SLOMetric.QUEUE_DEPTH, threshold=10.0, operator="<=", is_mandatory=False),
        ],
    )


class TestEvaluateBenchmarkCompatibility:
    def test_no_candidates_returns_failure(self, target_serving_unit, target_workload, default_policy, evaluation_timestamp):
        outcome = evaluate_benchmark_compatibility(
            target_serving_unit, target_workload, [], default_policy, evaluation_timestamp
        )
        assert outcome.status == "FAILURE"
        assert outcome.blocker == BlockerReason.BENCHMARK_REQUIRED
        assert outcome.compatible_records is None
        assert outcome.reason == "No compatible benchmark records found."
        assert outcome.rejection_reasons == {}

    def test_all_criteria_met_returns_success(self, target_serving_unit, target_workload, default_policy, evaluation_timestamp):
        record = BenchmarkRecord(
            id="REC-001",
            serving_unit_fingerprint=target_serving_unit,
            workload_profile_id=target_workload.id,
            approval_status=ApprovalStatus.APPROVED,
            valid_from=evaluation_timestamp - timedelta(days=30),
            valid_until=evaluation_timestamp + timedelta(days=30),
            raw_evidence_checksum="checksum_abc",
            measurement_method=MeasurementMethod.STANDARD_V1,
            approval_timestamp=evaluation_timestamp - timedelta(days=5),
            load_points=[],
        )
        outcome = evaluate_benchmark_compatibility(
            target_serving_unit, target_workload, [record], default_policy, evaluation_timestamp
        )
        assert outcome.status == "SUCCESS"
        assert outcome.blocker is None
        assert len(outcome.compatible_records) == 1
        assert outcome.compatible_records[0].id == "REC-001"
        assert outcome.reason == "Successfully evaluated benchmark compatibility."
        assert outcome.rejection_reasons == {}

    @pytest.mark.parametrize(
        "field, bad_value, expected_reason_part",
        [
            ("serving_unit_fingerprint", "GPU_MODEL_B_V1.0", "does not match target"),
            ("workload_profile_id", "WORKLOAD_B", "does not match target"),
            ("approval_status", ApprovalStatus.PENDING, "approval status is 'PENDING', expected 'APPROVED'"),
            ("valid_from", datetime.datetime(2024, 1, 1), "does not encompass evaluation timestamp"),
            ("valid_until", datetime.datetime(2023, 1, 1), "does not encompass evaluation timestamp"),
            ("raw_evidence_checksum", "", "Raw evidence checksum is missing."),
            ("measurement_method", MeasurementMethod.CUSTOM_V1, "is not allowed by policy"),
        ],
    )
    def test_single_criterion_failure_returns_failure_with_reason(
        self, target_serving_unit, target_workload, default_policy, evaluation_timestamp, field, bad_value, expected_reason_part
    ):
        base_record = BenchmarkRecord(
            id="REC-001",
            serving_unit_fingerprint=target_serving_unit,
            workload_profile_id=target_workload.id,
            approval_status=ApprovalStatus.APPROVED,
            valid_from=evaluation_timestamp - timedelta(days=30),
            valid_until=evaluation_timestamp + timedelta(days=30),
            raw_evidence_checksum="checksum_abc",
            measurement_method=MeasurementMethod.STANDARD_V1,
            approval_timestamp=evaluation_timestamp - timedelta(days=5),
            load_points=[],
        )
        from dataclasses import replace
        modified_record = replace(base_record, **{field: bad_value})

        outcome = evaluate_benchmark_compatibility(
            target_serving_unit, target_workload, [modified_record], default_policy, evaluation_timestamp
        )
        assert outcome.status == "FAILURE"
        assert outcome.blocker == BlockerReason.BENCHMARK_REQUIRED
        assert outcome.compatible_records is None
        assert outcome.reason == "No compatible benchmark records found."
        assert modified_record.id in outcome.rejection_reasons
        assert expected_reason_part in outcome.rejection_reasons[modified_record.id]

    def test_multiple_compatible_records_are_ranked_correctly(self, target_serving_unit, target_workload, default_policy, evaluation_timestamp):
        record_a = BenchmarkRecord(
            id="REC-A",
            serving_unit_fingerprint=target_serving_unit,
            workload_profile_id=target_workload.id,
            approval_status=ApprovalStatus.APPROVED,
            valid_from=evaluation_timestamp - timedelta(days=30),
            valid_until=evaluation_timestamp + timedelta(days=30),
            raw_evidence_checksum="checksum_a",
            measurement_method=MeasurementMethod.STANDARD_V1,
            approval_timestamp=evaluation_timestamp - timedelta(days=10), # Older approval
            load_points=[],
        )
        record_b = BenchmarkRecord(
            id="REC-B",
            serving_unit_fingerprint=target_serving_unit,
            workload_profile_id=target_workload.id,
            approval_status=ApprovalStatus.APPROVED,
            valid_from=evaluation_timestamp - timedelta(days=30),
            valid_until=evaluation_timestamp + timedelta(days=30),
            raw_evidence_checksum="checksum_b",
            measurement_method=MeasurementMethod.STANDARD_V1,
            approval_timestamp=evaluation_timestamp - timedelta(days=5), # Newer approval
            load_points=[],
        )
        record_c = BenchmarkRecord(
            id="REC-C",
            serving_unit_fingerprint=target_serving_unit,
            workload_profile_id=target_workload.id,
            approval_status=ApprovalStatus.APPROVED,
            valid_from=evaluation_timestamp - timedelta(days=30),
            valid_until=evaluation_timestamp + timedelta(days=30),
            raw_evidence_checksum="checksum_c",
            measurement_method=MeasurementMethod.STANDARD_V1,
            approval_timestamp=evaluation_timestamp - timedelta(days=5), # Same approval as B
            load_points=[],
        )

        candidates = [record_a, record_b, record_c]
        outcome = evaluate_benchmark_compatibility(
            target_serving_unit, target_workload, candidates, default_policy, evaluation_timestamp
        )

        assert outcome.status == "SUCCESS"
        assert outcome.blocker is None
        assert len(outcome.compatible_records) == 3
        # Expected order: REC-B (newer approval), REC-C (same approval as B, but C > B lexicographically), REC-A (oldest approval)
        assert outcome.compatible_records[0].id == "REC-B"
        assert outcome.compatible_records[1].id == "REC-C"
        assert outcome.compatible_records[2].id == "REC-A"


class TestSelectUsefulCapacity:
    def test_all_slos_and_policy_met_returns_success(self, target_workload, default_policy, evaluation_timestamp):
        record = BenchmarkRecord(
            id="REC-001",
            serving_unit_fingerprint="GPU_MODEL_A_V1.0",
            workload_profile_id="WORKLOAD_A",
            approval_status=ApprovalStatus.APPROVED,
            valid_from=evaluation_timestamp - timedelta(days=30),
            valid_until=evaluation_timestamp + timedelta(days=30),
            raw_evidence_checksum="checksum_abc",
            measurement_method=MeasurementMethod.STANDARD_V1,
            approval_timestamp=evaluation_timestamp - timedelta(days=5),
            load_points=[
                BenchmarkLoadPoint(
                    offered_load=100.0,
                    metrics={
                        SLOMetric.TTFT_P99: 90.0,
                        SLOMetric.TPOT_P99: 40.0,
                        SLOMetric.ERROR_RATE: 0.005,
                        SLOMetric.QUEUE_DEPTH: 5.0,
                    },
                    sample_count=150,
                    duration_seconds=90.0,
                ),
                BenchmarkLoadPoint(
                    offered_load=200.0,
                    metrics={
                        SLOMetric.TTFT_P99: 95.0,
                        SLOMetric.TPOT_P99: 45.0,
                        SLOMetric.ERROR_RATE: 0.008,
                        SLOMetric.QUEUE_DEPTH: 8.0,
                    },
                    sample_count=200,
                    duration_seconds=120.0,
                ),
            ],
        )
        outcome = select_useful_capacity(record, target_workload, default_policy)
        assert outcome.status == "SUCCESS"
        assert outcome.blocker is None
        assert outcome.selected_load_point is not None
        assert outcome.selected_load_point.offered_load == 200.0
        assert outcome.reason == "Successfully selected useful capacity."

    def test_no_load_points_returns_failure(self, target_workload, default_policy, evaluation_timestamp):
        record = BenchmarkRecord(
            id="REC-NO-LP",
            serving_unit_fingerprint="GPU_MODEL_A_V1.0",
            workload_profile_id="WORKLOAD_A",
            approval_status=ApprovalStatus.APPROVED,
            valid_from=evaluation_timestamp - timedelta(days=30),
            valid_until=evaluation_timestamp + timedelta(days=30),
            raw_evidence_checksum="checksum_abc",
            measurement_method=MeasurementMethod.STANDARD_V1,
            approval_timestamp=evaluation_timestamp - timedelta(days=5),
            load_points=[],
        )
        outcome = select_useful_capacity(record, target_workload, default_policy)
        assert outcome.status == "FAILURE"
        assert outcome.blocker == BlockerReason.SLO_VIOLATION
        assert outcome.selected_load_point is None
        assert outcome.reason == "No load point satisfied all mandatory SLOs and policy predicates."

    def test_load_point_fails_slo_threshold_returns_failure(self, target_workload, default_policy, evaluation_timestamp):
        record_failing_slo = BenchmarkRecord(
            id="REC-FAIL-SLO",
            serving_unit_fingerprint="GPU_MODEL_A_V1.0",
            workload_profile_id="WORKLOAD_A",
            approval_status=ApprovalStatus.APPROVED,
            valid_from=evaluation_timestamp - timedelta(days=30),
            valid_until=evaluation_timestamp + timedelta(days=30),
            raw_evidence_checksum="checksum_fs",
            measurement_method=MeasurementMethod.STANDARD_V1,
            approval_timestamp=evaluation_timestamp - timedelta(days=5),
            load_points=[
                BenchmarkLoadPoint(
                    offered_load=100.0,
                    metrics={
                        SLOMetric.TTFT_P99: 110.0,  # Fails TTFT_P99 <= 100.0
                        SLOMetric.TPOT_P99: 40.0,
                        SLOMetric.ERROR_RATE: 0.005,
                        SLOMetric.QUEUE_DEPTH: 5.0,
                    },
                    sample_count=150,
                    duration_seconds=90.0,
                ),
            ],
        )
        outcome = select_useful_capacity(record_failing_slo, target_workload, default_policy)
        assert outcome.status == "FAILURE"
        assert outcome.blocker == BlockerReason.SLO_VIOLATION
        assert outcome.selected_load_point is None
        assert "SLO 'ttft_p99' failed: 110.0 <= 100.0." in outcome.reason

    def test_load_point_fails_min_sample_count_returns_failure(self, target_workload, default_policy, evaluation_timestamp):
        record_failing_sample_count = BenchmarkRecord(
            id="REC-FAIL-SAMPLE",
            serving_unit_fingerprint="GPU_MODEL_A_V1.0",
            workload_profile_id="WORKLOAD_A",
            approval_status=ApprovalStatus.APPROVED,
            valid_from=evaluation_timestamp - timedelta(days=30),
            valid_until=evaluation_timestamp + timedelta(days=30),
            raw_evidence_checksum="checksum_fsc",
            measurement_method=MeasurementMethod.STANDARD_V1,
            approval_timestamp=evaluation_timestamp - timedelta(days=5),
            load_points=[
                BenchmarkLoadPoint(
                    offered_load=100.0,
                    metrics={
                        SLOMetric.TTFT_P99: 90.0,
                        SLOMetric.TPOT_P99: 40.0,
                        SLOMetric.ERROR_RATE: 0.005,
                    },
                    sample_count=50,  # Fails min_sample_count=100
                    duration_seconds=90.0,
                ),
            ],
        )
        outcome = select_useful_capacity(record_failing_sample_count, target_workload, default_policy)
        assert outcome.status == "FAILURE"
        assert outcome.blocker == BlockerReason.SLO_VIOLATION
        assert outcome.selected_load_point is None
        assert "Sample count 50 is less than minimum required 100." in outcome.reason

    def test_load_point_fails_min_duration_returns_failure(self, target_workload, default_policy, evaluation_timestamp):
        record_failing_duration = BenchmarkRecord(
            id="REC-FAIL-DURATION",
            serving_unit_fingerprint="GPU_MODEL_A_V1.0",
            workload_profile_id="WORKLOAD_A",
            approval_status=ApprovalStatus.APPROVED,
            valid_from=evaluation_timestamp - timedelta(days=30),
            valid_until=evaluation_timestamp + timedelta(days=30),
            raw_evidence_checksum="checksum_fd",
            measurement_method=MeasurementMethod.STANDARD_V1,
            approval_timestamp=evaluation_timestamp - timedelta(days=5),
            load_points=[
                BenchmarkLoadPoint(
                    offered_load=100.0,
                    metrics={
                        SLOMetric.TTFT_P99: 90.0,
                        SLOMetric.TPOT_P99: 40.0,
                        SLOMetric.ERROR_RATE: 0.005,
                    },
                    sample_count=150,
                    duration_seconds=30.0,  # Fails min_duration_seconds=60.0
                ),
            ],
        )
        outcome = select_useful_capacity(record_failing_duration, target_workload, default_policy)
        assert outcome.status == "FAILURE"
        assert outcome.blocker == BlockerReason.SLO_VIOLATION
        assert outcome.selected_load_point is None
        assert "Duration 30.0s is less than minimum required 60.0s." in outcome.reason

    def test_load_point_missing_mandatory_metric_fails(self, target_workload, default_policy, evaluation_timestamp):
        record_missing_metric = BenchmarkRecord(
            id="REC-MISSING-METRIC",
            serving_unit_fingerprint="GPU_MODEL_A_V1.0",
            workload_profile_id="WORKLOAD_A",
            approval_status=ApprovalStatus.APPROVED,
            valid_from=evaluation_timestamp - timedelta(days=30),
            valid_until=evaluation_timestamp + timedelta(days=30),
            raw_evidence_checksum="checksum_mm",
            measurement_method=MeasurementMethod.STANDARD_V1,
            approval_timestamp=evaluation_timestamp - timedelta(days=5),
            load_points=[
                BenchmarkLoadPoint(
                    offered_load=100.0,
                    metrics={
                        SLOMetric.TTFT_P99: 90.0,
                        SLOMetric.ERROR_RATE: 0.001,
                        # Missing SLOMetric.TPOT_P99 which is mandatory
                    },
                    sample_count=150,
                    duration_seconds=90.0,
                ),
            ],
        )
        outcome = select_useful_capacity(record_missing_metric, target_workload, default_policy)
        assert outcome.status == "FAILURE"
        assert outcome.blocker == BlockerReason.SLO_VIOLATION
        assert outcome.selected_load_point is None
        assert "Mandatory SLO metric 'tpot_p99' not found in load point metrics." in outcome.reason

    def test_multiple_load_points_only_one_useful_selects_correct_one(self, target_workload, default_policy, evaluation_timestamp):
        record = BenchmarkRecord(
            id="REC-MULTI-LP",
            serving_unit_fingerprint="GPU_MODEL_A_V1.0",
            workload_profile_id="WORKLOAD_A",
            approval_status=ApprovalStatus.APPROVED,
            valid_from=evaluation_timestamp - timedelta(days=30),
            valid_until=evaluation_timestamp + timedelta(days=30),
            raw_evidence_checksum="checksum_ml",
            measurement_method=MeasurementMethod.STANDARD_V1,
            approval_timestamp=evaluation_timestamp - timedelta(days=5),
            load_points=[
                BenchmarkLoadPoint( # Fails TTFT_P99
                    offered_load=100.0,
                    metrics={
                        SLOMetric.TTFT_P99: 110.0,
                        SLOMetric.TPOT_P99: 40.0,
                        SLOMetric.ERROR_RATE: 0.005,
                    },
                    sample_count=150,
                    duration_seconds=90.0,
                ),
                BenchmarkLoadPoint( # Useful
                    offered_load=200.0,
                    metrics={
                        SLOMetric.TTFT_P99: 95.0,
                        SLOMetric.TPOT_P99: 45.0,
                        SLOMetric.ERROR_RATE: 0.008,
                    },
                    sample_count=200,
                    duration_seconds=120.0,
                ),
                BenchmarkLoadPoint( # Fails sample count
                    offered_load=300.0,
                    metrics={
                        SLOMetric.TTFT_P99: 90.0,
                        SLOMetric.TPOT_P99: 40.0,
                        SLOMetric.ERROR_RATE: 0.001,
                    },
                    sample_count=50,
                    duration_seconds=90.0,
                ),
            ],
        )
        outcome = select_useful_capacity(record, target_workload, default_policy)
        assert outcome.status == "SUCCESS"
        assert outcome.blocker is None
        assert outcome.selected_load_point is not None
        assert outcome.selected_load_point.offered_load == 200.0
        assert outcome.reason == "Successfully selected useful capacity."

    def test_multiple_useful_load_points_selects_greatest_offered_load(self, target_workload, default_policy, evaluation_timestamp):
        record = BenchmarkRecord(
            id="REC-MULTI-USEFUL",
            serving_unit_fingerprint="GPU_MODEL_A_V1.0",
            workload_profile_id="WORKLOAD_A",
            approval_status=ApprovalStatus.APPROVED,
            valid_from=evaluation_timestamp - timedelta(days=30),
            valid_until=evaluation_timestamp + timedelta(days=30),
            raw_evidence_checksum="checksum_mu",
            measurement_method=MeasurementMethod.STANDARD_V1,
            approval_timestamp=evaluation_timestamp - timedelta(days=5),
            load_points=[
                BenchmarkLoadPoint(
                    offered_load=100.0,
                    metrics={
                        SLOMetric.TTFT_P99: 90.0,
                        SLOMetric.TPOT_P99: 40.0,
                        SLOMetric.ERROR_RATE: 0.005,
                    },
                    sample_count=150,
                    duration_seconds=90.0,
                ),
                BenchmarkLoadPoint(
                    offered_load=300.0, # Greatest offered load
                    metrics={
                        SLOMetric.TTFT_P99: 95.0,
                        SLOMetric.TPOT_P99: 45.0,
                        SLOMetric.ERROR_RATE: 0.008,
                    },
                    sample_count=200,
                    duration_seconds=120.0,
                ),
                BenchmarkLoadPoint(
                    offered_load=200.0,
                    metrics={
                        SLOMetric.TTFT_P99: 92.0,
                        SLOMetric.TPOT_P99: 42.0,
                        SLOMetric.ERROR_RATE: 0.006,
                    },
                    sample_count=180,
                    duration_seconds=100.0,
                ),
            ],
        )
        outcome = select_useful_capacity(record, target_workload, default_policy)
        assert outcome.status == "SUCCESS"
        assert outcome.blocker is None
        assert outcome.selected_load_point is not None
        assert outcome.selected_load_point.offered_load == 300.0
        assert outcome.reason == "Successfully selected useful capacity."

    def test_all_load_points_fail_returns_failure_with_specific_reason(self, target_workload, default_policy, evaluation_timestamp):
        record_all_fail = BenchmarkRecord(
            id="REC-ALL-FAIL",
            serving_unit_fingerprint="GPU_MODEL_A_V1.0",
            workload_profile_id="WORKLOAD_A",
            approval_status=ApprovalStatus.APPROVED,
            valid_from=evaluation_timestamp - timedelta(days=30),
            valid_until=evaluation_timestamp + timedelta(days=30),
            raw_evidence_checksum="checksum_af",
            measurement_method=MeasurementMethod.STANDARD_V1,
            approval_timestamp=evaluation_timestamp - timedelta(days=5),
            load_points=[
                BenchmarkLoadPoint( # Fails TTFT_P99
                    offered_load=100.0,
                    metrics={
                        SLOMetric.TTFT_P99: 110.0,
                        SLOMetric.TPOT_P99: 40.0,
                        SLOMetric.ERROR_RATE: 0.005,
                    },
                    sample_count=150,
                    duration_seconds=90.0,
                ),
                BenchmarkLoadPoint( # Fails missing TPOT_P99
                    offered_load=200.0,
                    metrics={
                        SLOMetric.TTFT_P99: 95.0,
                        SLOMetric.ERROR_RATE: 0.008,
                    },
                    sample_count=200,
                    duration_seconds=120.0,
                ),
            ],
        )
        outcome = select_useful_capacity(record_all_fail, target_workload, default_policy)
        assert outcome.status == "FAILURE"
        assert outcome.blocker == BlockerReason.SLO_VIOLATION
        assert outcome.selected_load_point is None
        assert "SLO 'ttft_p99' failed: 110.0 <= 100.0." in outcome.reason

    def test_all_load_points_fail_with_different_reasons_returns_first_specific_reason(self, target_workload, default_policy, evaluation_timestamp):
        record_all_fail_diff_reasons = BenchmarkRecord(
            id="REC-ALL-FAIL-DIFF",
            serving_unit_fingerprint="GPU_MODEL_A_V1.0",
            workload_profile_id="WORKLOAD_A",
            approval_status=ApprovalStatus.APPROVED,
            valid_from=evaluation_timestamp - timedelta(days=30),
            valid_until=evaluation_timestamp + timedelta(days=30),
            raw_evidence_checksum="checksum_afdr",
            measurement_method=MeasurementMethod.STANDARD_V1,
            approval_timestamp=evaluation_timestamp - timedelta(days=5),
            load_points=[
                BenchmarkLoadPoint( # Fails min_sample_count
                    offered_load=100.0,
                    metrics={
                        SLOMetric.TTFT_P99: 90.0,
                        SLOMetric.TPOT_P99: 40.0,
                        SLOMetric.ERROR_RATE: 0.005,
                    },
                    sample_count=50,
                    duration_seconds=90.0,
                ),
                BenchmarkLoadPoint( # Fails missing TPOT_P99
                    offered_load=200.0,
                    metrics={
                        SLOMetric.TTFT_P99: 95.0,
                        SLOMetric.ERROR_RATE: 0.008,
                    },
                    sample_count=200,
                    duration_seconds=120.0,
                ),
            ],
        )
        outcome = select_useful_capacity(record_all_fail_diff_reasons, target_workload, default_policy)
        assert outcome.status == "FAILURE"
        assert outcome.blocker == BlockerReason.SLO_VIOLATION
        assert outcome.selected_load_point is None
        assert "Sample count 50 is less than minimum required 100." in outcome.reason
