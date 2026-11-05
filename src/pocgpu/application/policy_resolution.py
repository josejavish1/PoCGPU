"""Deterministic fail-closed policy resolution."""

from __future__ import annotations

from collections import defaultdict

from pocgpu.domain.errors import DomainIssue, IssueKind, IssueSeverity
from pocgpu.domain.identifiers import PolicyKey, PolicyPackId, SchemaId
from pocgpu.domain.policies import (
    CanonicalValue,
    PolicyPack,
    PolicyResolutionPlan,
    PolicyResolutionResult,
    ResolvedPolicySetting,
)
from pocgpu.domain.provenance import ApprovalState, GovernedRecord
from pocgpu.domain.time import UtcInstant


def _issue(code: str, path: tuple[str, ...], **parameters: str) -> DomainIssue:
    return DomainIssue(
        code=code,
        kind=IssueKind.POLICY_REQUIRED,
        severity=IssueSeverity.ERROR,
        path=path,
        parameters=tuple(sorted(parameters.items())),
        localization_key=f"error.policy.{code.lower()}",
    )


class PolicyResolver:
    """Resolve explicit policy relationships without contextual defaults."""

    def resolve(
        self,
        plan: PolicyResolutionPlan,
        records: tuple[GovernedRecord[PolicyPack], ...],
        captured_at: UtcInstant,
    ) -> PolicyResolutionResult:
        issues: list[DomainIssue] = []
        by_id: dict[PolicyPackId, GovernedRecord[PolicyPack]] = {}
        for record in records:
            pack = record.value
            if pack.pack_id in by_id:
                issues.append(
                    _issue("DUPLICATE_POLICY_PACK", ("pack_ids",), pack_id=pack.pack_id.value)
                )
                continue
            by_id[pack.pack_id] = record

        eligible: dict[PolicyPackId, GovernedRecord[PolicyPack]] = {}
        for pack_id in plan.pack_ids:
            resolved_record = by_id.get(pack_id)
            if resolved_record is None:
                issues.append(_issue("POLICY_PACK_MISSING", ("pack_ids",), pack_id=pack_id.value))
                continue
            if (
                resolved_record.value.tenant_id != plan.tenant_id
                or resolved_record.metadata.tenant_id != plan.tenant_id
            ):
                issues.append(
                    _issue("POLICY_TENANT_MISMATCH", (pack_id.value,), pack_id=pack_id.value)
                )
                continue
            if resolved_record.metadata.approval_state is not ApprovalState.APPROVED:
                issues.append(
                    _issue("POLICY_NOT_APPROVED", (pack_id.value,), pack_id=pack_id.value)
                )
                continue
            if not resolved_record.metadata.is_valid_at(captured_at):
                issues.append(_issue("POLICY_STALE", (pack_id.value,), pack_id=pack_id.value))
                continue
            eligible[pack_id] = resolved_record

        if self._has_override_cycle(eligible):
            return PolicyResolutionResult(
                (),
                (_issue("POLICY_OVERRIDE_CYCLE", ("overrides",)),),
            )

        definitions: dict[PolicyKey, list[tuple[PolicyPackId, SchemaId, CanonicalValue]]] = (
            defaultdict(list)
        )
        for pack_id, record in eligible.items():
            for setting in record.value.settings:
                definitions[setting.key].append((pack_id, setting.value_schema_id, setting.value))

        values: list[ResolvedPolicySetting] = []
        all_keys = set(definitions).union(plan.required_keys)
        for key in sorted(all_keys, key=lambda item: item.value):
            candidates = definitions.get(key, [])
            if not candidates:
                if key in plan.required_keys:
                    issues.append(_issue("POLICY_REQUIRED", (key.value,), key=key.value))
                continue
            selected = self._select_candidate(key, candidates, eligible)
            if selected is None:
                issues.append(_issue("POLICY_CONFLICT", (key.value,), key=key.value))
                continue
            source_id, schema_id, value = selected
            values.append(
                ResolvedPolicySetting(
                    key=key,
                    value_schema_id=schema_id,
                    value=value,
                    source_pack_id=source_id,
                    considered_pack_ids=tuple(
                        sorted((item[0] for item in candidates), key=lambda item: item.value)
                    ),
                )
            )

        if issues:
            return PolicyResolutionResult(
                (),
                tuple(sorted(issues, key=lambda item: (item.code, item.path))),
            )
        return PolicyResolutionResult(tuple(values), ())

    @staticmethod
    def _select_candidate(
        key: PolicyKey,
        candidates: list[tuple[PolicyPackId, SchemaId, CanonicalValue]],
        eligible: dict[PolicyPackId, GovernedRecord[PolicyPack]],
    ) -> tuple[PolicyPackId, SchemaId, CanonicalValue] | None:
        first_schema = candidates[0][1]
        first_value = candidates[0][2]
        if all(schema == first_schema and value == first_value for _, schema, value in candidates):
            return min(candidates, key=lambda item: item[0].value)

        candidate_ids = {candidate[0] for candidate in candidates}
        winners: list[tuple[PolicyPackId, SchemaId, CanonicalValue]] = []
        for candidate in candidates:
            source_id = candidate[0]
            overridden: set[PolicyPackId] = set()
            for override in eligible[source_id].value.overrides:
                if key in override.keys:
                    overridden.add(override.target_pack_id)
            if candidate_ids - {source_id} <= overridden:
                winners.append(candidate)
        return winners[0] if len(winners) == 1 else None

    @staticmethod
    def _has_override_cycle(
        eligible: dict[PolicyPackId, GovernedRecord[PolicyPack]],
    ) -> bool:
        graph = {
            pack_id: {
                override.target_pack_id
                for override in record.value.overrides
                if override.target_pack_id in eligible
            }
            for pack_id, record in eligible.items()
        }
        visiting: set[PolicyPackId] = set()
        visited: set[PolicyPackId] = set()

        def visit(pack_id: PolicyPackId) -> bool:
            if pack_id in visiting:
                return True
            if pack_id in visited:
                return False
            visiting.add(pack_id)
            if any(visit(target) for target in graph[pack_id]):
                return True
            visiting.remove(pack_id)
            visited.add(pack_id)
            return False

        return any(visit(pack_id) for pack_id in graph)
