"""Only composition boundary permitted to combine concrete adapters and services."""

from __future__ import annotations

from dataclasses import dataclass

from pocgpu.adapters.in_memory import (
    FixedClock,
    InMemoryGovernedRecordRepository,
    InMemoryPolicyRepository,
    InMemorySnapshotRepository,
    SequenceIdentityProvider,
)
from pocgpu.application.policy_resolution import PolicyResolver
from pocgpu.application.scenario_evaluation import ScenarioEvaluationService


@dataclass(frozen=True, slots=True)
class ReferenceComposition:
    """Explicit reference composition with no business-value defaults."""

    clock: FixedClock
    identity_provider: SequenceIdentityProvider
    record_repository: InMemoryGovernedRecordRepository
    policy_repository: InMemoryPolicyRepository
    snapshot_repository: InMemorySnapshotRepository

    def scenario_evaluator(self) -> ScenarioEvaluationService:
        return ScenarioEvaluationService(
            clock=self.clock,
            identity_provider=self.identity_provider,
            record_repository=self.record_repository,
            policy_repository=self.policy_repository,
            snapshot_repository=self.snapshot_repository,
            policy_resolver=PolicyResolver(),
        )
