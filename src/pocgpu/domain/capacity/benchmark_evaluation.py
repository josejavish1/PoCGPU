from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Literal, Optional, Sequence


# Enums
class SLOMetric(str, Enum):
    TTFT_P99 = "ttft_p99"
    TPOT_P99 = "tpot_p99"
    ERROR_RATE = "error_rate"
    QUEUE_DEPTH = "queue_depth"
    STABILITY_SCORE = "stability_score"


class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class MeasurementMethod(str, Enum):
    STANDARD_V1 = "STANDARD_V1"
    CUSTOM_V1 = "CUSTOM_V1"


class BlockerReason(str, Enum):
    BENCHMARK_REQUIRED = "BENCHMARK_REQUIRED"
    SLO_VIOLATION = "SLO_VIOLATION"
    POLICY_VIOLATION = "POLICY_VIOLATION"
    INVALID_RECORD = "INVALID_RECORD"


# Core Data Models
@dataclass(frozen=True)
class ServiceLevelObjective:
    metric_name: SLOMetric
    threshold: float
    operator: Literal["<=", ">=", "<", ">", "=="]
    is_mandatory: bool


@dataclass(frozen=True)
class WorkloadProfile:
    id: str
    slos: Sequence[ServiceLevelObjective]


@dataclass(frozen=True)
class CompatibilityPolicy:
    allowed_measurement_methods: frozenset[MeasurementMethod]
    min_sample_count: int
    min_duration_seconds: float


@dataclass(frozen=True)
class BenchmarkLoadPoint:
    offered_load: float
    metrics: dict[SLOMetric, float]
    sample_count: int
    duration_seconds: float


@dataclass(frozen=True)
class BenchmarkRecord:
    id: str
    serving_unit_fingerprint: str
    workload_profile_id: str
    approval_status: ApprovalStatus
    valid_from: datetime
    valid_until: datetime
    raw_evidence_checksum: str
    measurement_method: MeasurementMethod
    approval_timestamp: datetime
    load_points: Sequence[BenchmarkLoadPoint]


@dataclass(frozen=True)
class UsefulCapacityOutcome:
    status: Literal["SUCCESS", "FAILURE"]
    selected_load_point: Optional[BenchmarkLoadPoint]
    blocker: Optional[BlockerReason]
    reason: Optional[str]


@dataclass(frozen=True)
class BenchmarkCompatibilityOutcome:
    status: Literal["SUCCESS", "FAILURE"]
    compatible_records: Optional[Sequence[BenchmarkRecord]]
    blocker: Optional[BlockerReason]
    rejection_reasons: Optional[dict[str, str]]
    reason: Optional[str]


# Helper Functions
def _evaluate_slo_condition(
    value: float, operator: Literal["<=", ">=", "<", ">", "=="], threshold: float
) -> bool:
    """Evaluates a single Service Level Objective condition."""
    if operator == "<=":
        return value <= threshold
    elif operator == ">=":
        return value >= threshold
    elif operator == "<":
        return value < threshold
    elif operator == ">":
        return value > threshold
    elif operator == "==":
        return value == threshold
    else:
        raise ValueError(f"Unsupported SLO operator: {operator}")


# CAP-001 Implementation
def evaluate_benchmark_compatibility(
    serving_unit: str,
    workload: WorkloadProfile,
    candidates: Sequence[BenchmarkRecord],
    policy: CompatibilityPolicy,
    evaluation_timestamp: datetime,
) -> BenchmarkCompatibilityOutcome:
    """
    Filters and ranks a sequence of BenchmarkRecord candidates based on compatibility rules.
    """
    compatible_records: list[BenchmarkRecord] = []
    all_rejection_reasons: dict[str, str] = {}

    for record in candidates:
        reasons_for_rejection: list[str] = []

        # 1. ServingUnitFingerprint match
        if record.serving_unit_fingerprint != serving_unit:
            reasons_for_rejection.append(
                f"Serving unit fingerprint '{record.serving_unit_fingerprint}' does not match target '{serving_unit}'."
            )

        # 2. Workload identity match
        if record.workload_profile_id != workload.id:
            reasons_for_rejection.append(
                f"Workload profile ID '{record.workload_profile_id}' does not match target '{workload.id}'."
            )

        # 3. Approval status is approved
        if record.approval_status != ApprovalStatus.APPROVED:
            reasons_for_rejection.append(
                f"Record approval status is '{record.approval_status.value}', expected '{ApprovalStatus.APPROVED.value}'."
            )

        # 4. Validity window encompasses evaluation_timestamp
        if not (record.valid_from <= evaluation_timestamp <= record.valid_until):
            reasons_for_rejection.append(
                f"Record validity window [{record.valid_from}, {record.valid_until}] does not encompass evaluation timestamp {evaluation_timestamp}."
            )

        # 5. Raw evidence checksum is present
        if not record.raw_evidence_checksum:
            reasons_for_rejection.append("Raw evidence checksum is missing.")

        # 6. Measurement method satisfies policy rules
        if record.measurement_method not in policy.allowed_measurement_methods:
            reasons_for_rejection.append(
                f"Measurement method '{record.measurement_method.value}' is not allowed by policy."
            )

        if not reasons_for_rejection:
            compatible_records.append(record)
        else:
            all_rejection_reasons[record.id] = "; ".join(reasons_for_rejection)

    if not compatible_records:
        return BenchmarkCompatibilityOutcome(
            status="FAILURE",
            compatible_records=None,
            blocker=BlockerReason.BENCHMARK_REQUIRED,
            rejection_reasons=all_rejection_reasons,
            reason="No compatible benchmark records found.",
        )

    # Tie-breaking:
    # 1. Exact fingerprint match first (handled by initial filtering)
    # 2. Latest approval timestamp second (descending)
    # 3. Canonical lexicographical record ID third (ascending)
    compatible_records.sort(
        key=lambda r:
            (r.approval_timestamp.timestamp() * -1,  # Sort by timestamp descending
             r.id)                                   # Sort by ID ascending for ties
    )

    return BenchmarkCompatibilityOutcome(
        status="SUCCESS",
        compatible_records=compatible_records,
        blocker=None,
        rejection_reasons=all_rejection_reasons,
        reason="Successfully evaluated benchmark compatibility.",
    )


# CAP-002 Implementation
def select_useful_capacity(
    benchmark_record: BenchmarkRecord,
    workload: WorkloadProfile,
    policy: CompatibilityPolicy,
) -> UsefulCapacityOutcome:
    """
    Selects the single BenchmarkLoadPoint with the greatest offered_load that satisfies
    all mandatory ServiceLevelObjectives and policy predicates.
    Interpolation and extrapolation between load points are strictly prohibited.
    """
    useful_load_points: list[BenchmarkLoadPoint] = []
    # Store the first specific reason encountered for a load point's rejection.
    # This helps provide a more targeted error message if no load point is useful.
    first_specific_rejection_reason: Optional[str] = None

    mandatory_slos = [slo for slo in workload.slos if slo.is_mandatory]

    for load_point in benchmark_record.load_points:
        is_useful = True
        current_load_point_reasons: list[str] = []

        # Check policy predicates
        if load_point.sample_count < policy.min_sample_count:
            is_useful = False
            current_load_point_reasons.append(
                f"Sample count {load_point.sample_count} is less than minimum required {policy.min_sample_count}."
            )
        if load_point.duration_seconds < policy.min_duration_seconds:
            is_useful = False
            current_load_point_reasons.append(
                f"Duration {load_point.duration_seconds}s is less than minimum required {policy.min_duration_seconds}s."
            )

        # Evaluate mandatory SLOs
        for slo in mandatory_slos:
            metric_name = slo.metric_name
            if metric_name not in load_point.metrics:
                is_useful = False
                current_load_point_reasons.append(
                    f"Mandatory SLO metric '{metric_name.value}' not found in load point metrics."
                )
                # No need to check threshold if metric is missing, move to next SLO
                continue

            metric_value = load_point.metrics[metric_name]
            if not _evaluate_slo_condition(metric_value, slo.operator, slo.threshold):
                is_useful = False
                current_load_point_reasons.append(
                    f"SLO '{metric_name.value}' failed: {metric_value} {slo.operator} {slo.threshold}."
                )

        if is_useful:
            useful_load_points.append(load_point)
        else:
            # If this load point was rejected and we haven't captured a specific reason yet,
            # take the first reason from this load point.
            if not first_specific_rejection_reason and current_load_point_reasons:
                first_specific_rejection_reason = current_load_point_reasons[0]

    if not useful_load_points:
        # If no useful load points, return failure.
        # Use the specific reason if available, otherwise a general message.
        final_reason = first_specific_rejection_reason if first_specific_rejection_reason else \
                       "No load point satisfied all mandatory SLOs and policy predicates."

        return UsefulCapacityOutcome(
            status="FAILURE",
            selected_load_point=None,
            blocker=BlockerReason.SLO_VIOLATION,
            reason=final_reason,
        )

    # Sort by offered_load in descending order to pick the greatest
    useful_load_points.sort(key=lambda lp: lp.offered_load, reverse=True)
    selected_load_point = useful_load_points[0]

    return UsefulCapacityOutcome(
        status="SUCCESS",
        selected_load_point=selected_load_point,
        blocker=None,
        reason="Successfully selected useful capacity.",
    )
