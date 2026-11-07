from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
import hashlib
import json
from typing import Any, Literal, Mapping, Sequence, Self, Tuple


def _check_non_negative(value: Decimal | int, field_name: str) -> None:
    """Checks if a numeric value is non-negative."""
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative, got {value}")


def _check_positive(value: Decimal | int, field_name: str) -> None:
    """Checks if a numeric value is positive."""
    if value <= 0:
        raise ValueError(f"{field_name} must be positive, got {value}")


@dataclass(frozen=True, kw_only=True)
class ServingUnit:
    """Represents an immutable domain value object for a serving unit configuration."""
    model_revision: str
    engine: str
    version: str
    runtime_stack: str
    hardware_topology: str
    accelerator_count: int
    parallelism_strategy: str
    precision: str
    scheduler_config: str
    context_limit: int
    caching_mode: str
    residency: str
    deployment_settings: Mapping[str, Any]

    def __post_init__(self) -> None:
        _check_positive(self.accelerator_count, "accelerator_count")
        _check_positive(self.context_limit, "context_limit")


@dataclass(frozen=True, kw_only=True)
class ServingUnitFingerprint:
    """Computes the canonical SHA-256 hash over every identity-defining field of ServingUnit."""
    value: str

    @classmethod
    def from_serving_unit(cls, unit: ServingUnit) -> Self:
        """Computes the canonical SHA-256 hash for a given ServingUnit."""
        # Convert ServingUnit to a dictionary, ensuring consistent key ordering for canonical serialization
        unit_dict = {
            "model_revision": unit.model_revision,
            "engine": unit.engine,
            "version": unit.version,
            "runtime_stack": unit.runtime_stack,
            "hardware_topology": unit.hardware_topology,
            "accelerator_count": unit.accelerator_count,
            "parallelism_strategy": unit.parallelism_strategy,
            "precision": unit.precision,
            "scheduler_config": unit.scheduler_config,
            "context_limit": unit.context_limit,
            "caching_mode": unit.caching_mode,
            "residency": unit.residency,
            "deployment_settings": unit.deployment_settings,
        }
        # Canonical JSON serialization: sorted keys, no whitespace
        canonical_json = json.dumps(unit_dict, sort_keys=True, separators=(',', ':'))
        sha256_hash = hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
        return cls(value=sha256_hash)


@dataclass(frozen=True, kw_only=True)
class ServiceLevelObjective:
    """Defines a service level objective with a metric, comparator, and threshold."""
    metric_identifier: str
    comparator: Literal[">", "<", ">=", "<=", "=="]
    threshold: Decimal
    percentile: Decimal
    evaluation_window: timedelta
    mandatory: bool
    failure_behavior: Literal["fail_closed", "warn_only"]

    def __post_init__(self) -> None:
        _check_non_negative(self.threshold, "threshold")
        if not (Decimal("0") <= self.percentile <= Decimal("100")):
            raise ValueError(f"percentile must be between 0 and 100, got {self.percentile}")
        if self.evaluation_window <= timedelta(0):
            raise ValueError(f"evaluation_window must be positive, got {self.evaluation_window}")


@dataclass(frozen=True, kw_only=True)
class WorkloadProfile:
    """Describes the characteristics of a workload, including token distributions and SLOs."""
    input_token_length_distribution: Mapping[str, Decimal]
    output_token_length_distribution: Mapping[str, Decimal]
    request_type: str
    streaming_flag: bool
    cache_behavior: str
    batching_constraints: Mapping[str, Any]
    concurrency_shape: Mapping[str, Any]
    service_level_objectives: Tuple[ServiceLevelObjective, ...]


@dataclass(frozen=True, kw_only=True)
class DemandProfile:
    """Captures average and peak rates for various demand dimensions."""
    average_input_tokens_per_sec: Decimal
    peak_input_tokens_per_sec: Decimal
    average_output_tokens_per_sec: Decimal
    peak_output_tokens_per_sec: Decimal
    average_requests_per_sec: Decimal
    peak_requests_per_sec: Decimal
    average_concurrent_requests: Decimal
    peak_concurrent_requests: Decimal
    source_mode: Literal["observed", "projected", "simulated"]
    observation_window: timedelta
    seasonality_reference: datetime | None
    accepted_assumptions: Sequence[str]

    def __post_init__(self) -> None:
        _check_non_negative(self.average_input_tokens_per_sec, "average_input_tokens_per_sec")
        _check_non_negative(self.peak_input_tokens_per_sec, "peak_input_tokens_per_sec")
        _check_non_negative(self.average_output_tokens_per_sec, "average_output_tokens_per_sec")
        _check_non_negative(self.peak_output_tokens_per_sec, "peak_output_tokens_per_sec")
        _check_non_negative(self.average_requests_per_sec, "average_requests_per_sec")
        _check_non_negative(self.peak_requests_per_sec, "peak_requests_per_sec")
        _check_non_negative(self.average_concurrent_requests, "average_concurrent_requests")
        _check_non_negative(self.peak_concurrent_requests, "peak_concurrent_requests")

        if self.peak_input_tokens_per_sec < self.average_input_tokens_per_sec:
            raise ValueError("peak_input_tokens_per_sec cannot be less than average_input_tokens_per_sec")
        if self.peak_output_tokens_per_sec < self.average_output_tokens_per_sec:
            raise ValueError("peak_output_tokens_per_sec cannot be less than average_output_tokens_per_sec")
        if self.peak_requests_per_sec < self.average_requests_per_sec:
            raise ValueError("peak_requests_per_sec cannot be less than average_requests_per_sec")
        if self.peak_concurrent_requests < self.average_concurrent_requests:
            raise ValueError("peak_concurrent_requests cannot be less than average_concurrent_requests")

        if self.observation_window <= timedelta(0):
            raise ValueError(f"observation_window must be positive, got {self.observation_window}")


@dataclass(frozen=True, kw_only=True)
class BenchmarkLoadPoint:
    """Represents a single load point within a benchmark, capturing offered load and achieved metrics."""
    offered_load: Decimal
    achieved_input_tokens_per_sec: Decimal
    achieved_output_tokens_per_sec: Decimal
    achieved_requests_per_sec: Decimal
    achieved_concurrent_requests: Decimal
    latency_percentiles_ttft: Mapping[Decimal, Decimal]
    latency_percentiles_tpot: Mapping[Decimal, Decimal]
    queue_metrics: Mapping[str, Decimal]
    error_rate: Decimal
    stability_predicate: bool
    sample_count: int
    duration: timedelta

    def __post_init__(self) -> None:
        _check_non_negative(self.offered_load, "offered_load")
        _check_non_negative(self.achieved_input_tokens_per_sec, "achieved_input_tokens_per_sec")
        _check_non_negative(self.achieved_output_tokens_per_sec, "achieved_output_tokens_per_sec")
        _check_non_negative(self.achieved_requests_per_sec, "achieved_requests_per_sec")
        _check_non_negative(self.achieved_concurrent_requests, "achieved_concurrent_requests")

        if not (Decimal("0") <= self.error_rate <= Decimal("1")):
            raise ValueError(f"error_rate must be between 0 and 1, got {self.error_rate}")

        _check_non_negative(self.sample_count, "sample_count")
        if self.duration <= timedelta(0):
            raise ValueError(f"duration must be positive, got {self.duration}")


@dataclass(frozen=True, kw_only=True)
class BenchmarkRecord:
    """A comprehensive record of a benchmark run, including identity, environment, and load points."""
    governed_identity: str
    serving_unit_fingerprint: ServingUnitFingerprint
    workload_identity: str
    environment_metadata: Mapping[str, Any]
    method: str
    load_points: Tuple[BenchmarkLoadPoint, ...]
    raw_evidence_checksum: str
    reviewer: str
    approval_status: Literal["approved", "pending", "rejected"]
    validity_window: Tuple[datetime, datetime]

    def __post_init__(self) -> None:
        if not isinstance(self.validity_window, tuple) or len(self.validity_window) != 2:
            raise ValueError("validity_window must be a tuple of two datetime objects")
        if not all(isinstance(ts, datetime) for ts in self.validity_window):
            raise ValueError("validity_window must be a tuple of two datetime objects")
        if self.validity_window[0] >= self.validity_window[1]:
            raise ValueError("validity_window start datetime must be before end datetime")


@dataclass(frozen=True, kw_only=True)
class CompatibilityPolicy:
    """Defines rules for software, hardware, and environment compatibility."""
    software_patch_compatibility: Literal["major", "minor", "patch", "exact"]
    hardware_stepping: Literal["major", "minor", "exact"]
    cache_modes: Sequence[str]
    environment: Sequence[str]
    minimum_sample_count: int
    minimum_duration: timedelta

    def __post_init__(self) -> None:
        _check_non_negative(self.minimum_sample_count, "minimum_sample_count")
        if self.minimum_duration <= timedelta(0):
            raise ValueError(f"minimum_duration must be positive, got {self.minimum_duration}")


@dataclass(frozen=True, kw_only=True)
class ResiliencePolicy:
    """Specifies resilience requirements, including headroom, growth, and failure domain survival."""
    headroom_ratio: Decimal
    growth_ratio: Decimal
    maintenance_reserve_ratio: Decimal
    failure_domain_survival_level: Mapping[Literal["accelerator", "server", "rack", "zone", "site"], int]
    multi_site_mode: Literal["active_active", "active_passive", "none"]

    def __post_init__(self) -> None:
        _check_non_negative(self.headroom_ratio, "headroom_ratio")
        _check_non_negative(self.growth_ratio, "growth_ratio")
        _check_non_negative(self.maintenance_reserve_ratio, "maintenance_reserve_ratio")

        for level, count in self.failure_domain_survival_level.items():
            _check_non_negative(count, f"failure_domain_survival_level['{level}']")


@dataclass(frozen=True, kw_only=True)
class PackingPolicy:
    """Defines how resources are packed into a topological hierarchy and anti-affinity constraints."""
    accelerators_per_server: int
    servers_per_rack: int
    racks_per_zone: int
    zones_per_site: int
    anti_affinity_allocation_constraints: Mapping[str, Any]

    def __post_init__(self) -> None:
        _check_non_negative(self.accelerators_per_server, "accelerators_per_server")
        _check_non_negative(self.servers_per_rack, "servers_per_rack")
        _check_non_negative(self.racks_per_zone, "racks_per_zone")
        _check_non_negative(self.zones_per_site, "zones_per_site")


@dataclass(frozen=True, kw_only=True)
class CapacityResult:
    """Encapsulates the outcome of a capacity modeling exercise."""
    per_constraint_requirements: Mapping[str, Decimal]
    bottleneck_dimension: str | None
    intermediate_policy_step_quantities: Mapping[str, Decimal]
    topological_allocations: Mapping[str, Decimal]
    capacity_classifications: Mapping[str, str]
    reconciliations: Sequence[str]
    evidence_references: Sequence[str]
    certification_blockers: Sequence[str]

    def __post_init__(self) -> None:
        for key, value in self.per_constraint_requirements.items():
            _check_non_negative(value, f"per_constraint_requirements['{key}']")
        for key, value in self.intermediate_policy_step_quantities.items():
            _check_non_negative(value, f"intermediate_policy_step_quantities['{key}']")
        for key, value in self.topological_allocations.items():
            _check_non_negative(value, f"topological_allocations['{key}']")
