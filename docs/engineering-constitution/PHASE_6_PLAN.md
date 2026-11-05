# Phase 6 Plan: Decision Analysis and Result Certification

## Status

- Lifecycle state: `DRAFT FOR REVIEW`
- Implementation authority: `BLOCKED` until semantic, evidence, and engineering reviews accept this plan.
- Primary requirements: `PRD-003`, `PRD-004`, `PRD-006`, `DAT-003` through `DAT-005`, `ARC-004`, `SEC-002`, and `QLT-001` through `QLT-005`.
- Formula ownership: Phase 6 introduces no replacement capacity or financial formulas; it composes versioned Phase 2-5 outputs.

## Objective

Turn immutable Phase 2-5 outputs into a decision-ready scenario analysis with deterministic alternatives, sensitivity views, explicit trade-offs, approval evidence, and a fail-closed certification decision. Certification must prove every applicable technical, financial, provenance, SLO, reconciliation, policy, authorization, and approval gate for the exact scenario snapshot.

## Entry conditions

- Phases 1-5 are complete and all regression gates pass.
- Certification authorities, approval roles, gate applicability, expiry, revocation, and separation-of-duty rules are accepted as policy contracts.
- Scenario-comparison and sensitivity dimensions are accepted and cannot change formula semantics.
- At least one positive and multiple negative end-to-end certification cases have independent review.
- No critical Phase 6 risk lacks preventive and detection controls.

## Scope

- Deterministic scenario variants over explicitly supplied input sets.
- Side-by-side comparison of capacity, TCO, unit economics, price, external, break-even, and hybrid result sections.
- Sensitivity orchestration that re-evaluates canonical formulas rather than approximating them in presentation code.
- Named decision criteria, trade-off evidence, and policy-driven ranking only when an approved decision policy exists.
- Certification gate registry, applicability resolution, gate evidence, approval records, expiry, and revocation.
- Tamper-evident audit events distinct from correctness evidence.
- Canonical decision package containing the exact scenario, alternatives, results, gates, approvals, limitations, and hash.
- Replay and recertification behavior after evidence, policy, formula, or approval expiry.

## Exclusions

- New capacity, TCO, pricing, comparison, or hybrid formulas.
- Universal weighted scoring, recommendation thresholds, risk appetite, or automatic winner selection.
- Probabilistic forecasting, Monte Carlo analysis, stochastic optimization, or portfolio optimization.
- Treating audit-ledger integrity, an approver signature, or a green test run as calculation correctness.
- User interfaces and localized presentation, which belong to Phase 7.

## Decisions required before implementation

Reviewers must accept:

1. Scenario variant identity, permitted dimensions, maximum governed size, and ordering.
2. Baseline selection and rules for declaring two results comparable.
3. Decision-criterion schema and behavior when criteria conflict or remain unweighted.
4. Complete certification gate taxonomy and applicability policy.
5. Approval roles, authority scope, separation of duties, quorum, expiry, withdrawal, and supersession.
6. Recertification triggers for changes in scenarios, formulas, evidence, policy, engine, approvals, or time.
7. Audit event canonicalization, chaining, storage boundary, and verification behavior.
8. Which limitations are certification blockers versus mandatory disclosures.

No built-in role, threshold, score, quorum, or gate applicability may substitute for these policies.

## Domain contracts

- `ScenarioVariantSet`: baseline snapshot and an ordered set of explicit governed changes.
- `ComparableResultSet`: result identities plus compatibility assessment across formula, boundary, currency, period, and workload dimensions.
- `DecisionCriterion`: stable key, direction, applicable metric, policy source, mandatory flag, and optional governed weight.
- `DecisionAnalysis`: alternatives, comparable measures, deltas, Pareto information where defined, criteria outcomes, and unresolved trade-offs.
- `CertificationGateDefinition`: gate key, category, applicability rule reference, required evidence type, failure severity, and validity policy.
- `CertificationGateResult`: exact subject hash, status, evidence references, evaluator version, timestamp, and structured reason.
- `ApprovalRecord`: subject hash, authorized role, actor reference, decision, scope, timestamp, expiry, and supersession.
- `CertificationDecision`: state, exact subject hash, complete gate set, approval set, blockers, validity window, and policy versions.
- `AuditEvent`: previous hash, event identity, tenant, subject, action, actor reference, timestamp, and canonical payload hash.

## Orchestration contracts

- Every variant is a complete immutable scenario evaluated through the same canonical services used by the baseline.
- Deltas are derived only between compatible typed result fields; incompatible fields remain non-comparable.
- Ranking is absent unless a governed policy completely defines criteria, direction, missing-value treatment, and weights.
- Certification resolves all applicable gates before approvals can complete the decision.
- A gate result is bound to the exact canonical subject hash and cannot be reused after any relevant change.
- `CERTIFIED` requires every mandatory applicable gate to pass and every required valid approval to exist.
- Certification expiry or evidence staleness transitions the presented result to `STALE` without mutating historical records.

## Certification gate categories

- Input completeness and policy resolution.
- Benchmark compatibility and mandatory SLO outcomes.
- Capacity, cost, allocation, currency, and demand reconciliation.
- Provenance, evidence approval, and validity.
- Formula and schema version support.
- Tenant authorization and approval authority.
- Technical, finance, procurement, risk, and release approvals as required by policy.
- Known limitation and assumption acceptance.
- Replay identity and audit-chain integrity.

The category list is stable domain vocabulary; applicability and required roles are governed policy.

## Invariants and failure behavior

- Variant order does not change individual result hashes or analysis semantics.
- An increase in variant count cannot mutate earlier variant results.
- Every comparison delta references both immutable source values.
- No missing or failed mandatory gate can coexist with `CERTIFIED`.
- Approval for one subject hash cannot approve another hash.
- Revoked, expired, unauthorized, or self-conflicting approvals do not satisfy policy.
- Audit integrity is reported separately from certification correctness.
- Unresolved criteria produce a transparent non-ranked analysis, never an arbitrary winner.

## Ports and adapters

- Add certification policy, approval, authorization, decision-package, and audit-ledger ports.
- Provide in-memory adapters with contract tests for concurrency, idempotency, tenant scope, and append-only behavior.
- Identity-provider, signing, ticketing, and durable-ledger integrations remain adapters.
- Clock and identity remain injected Phase 1 ports and are captured in certification records.

## Planned implementation boundary

- `src/pocgpu/domain/decision/`: comparability, criteria, analyses, gates, approvals, certification, and audit records.
- `src/pocgpu/application/`: variant evaluation, analysis assembly, certification orchestration, replay, and recertification.
- `src/pocgpu/domain/ports/`: authorization, approval, certification, decision-package, and ledger protocols.
- `src/pocgpu/contracts/v6/` and `schemas/v6/`: strict versioned boundaries.
- `tests/phase6/`: scenario matrix, state machine, authorization, approval, audit, mutation, and end-to-end certification suites.

## Test-first verification matrix

| Area | Required evidence |
|---|---|
| Variants | Deterministic expansion, ordering invariance, size limits, and no hidden values. |
| Comparability | Exact compatible cases and every boundary/version mismatch. |
| Decision analysis | Typed deltas, unresolved trade-offs, governed ranking, and absent-policy behavior. |
| Gates | Complete applicability matrix and one-failure-at-a-time negative cases. |
| Approvals | Authority, tenant, scope, quorum, separation, expiry, revocation, and subject binding. |
| Certification | Positive case plus missing benchmark, failed SLO, stale price, reconciliation failure, and unaccepted assumption. |
| Audit | Chain verification, tamper detection, append idempotency, and correctness separation. |
| Replay | Same snapshot reproduces result and certification subject hash; changed evidence forces recertification. |
| Mutation | All canonical decision and certification mutations killed or adjudicated. |

Canonical Phase 6 domain services require 100 percent statement and branch coverage.

## Migration and compatibility

- Existing result states remain stable; Phase 6 makes certification construction reachable only through the governed service.
- Prior results without Phase 6 certification evidence remain valid calculation records but are not certified decisions.
- Audit entries created by legacy systems are external references unless they satisfy the new contract.
- Scenario and result hashes are never rewritten during migration.

## Delivery increments

1. Accept comparability, variant, criteria, gate, approval, and audit decisions.
2. Implement variants, comparable result sets, and deterministic sensitivity orchestration.
3. Implement decision criteria and transparent analysis.
4. Implement certification gate registry and applicability resolution.
5. Implement approvals, authorization, expiry, revocation, and separation of duties.
6. Implement certification decision, audit chain, replay, and recertification.
7. Complete mutation, end-to-end negative matrix, migration evidence, and completion report.

## Requirements traceability

- `PRD-003`, `PRD-004`, and `PRD-006` map to universal scenarios, states, and separated views.
- `DAT-003` through `DAT-005` map to immutable evidence, validity, and fail-closed resolution.
- `ARC-004` maps to deterministic variants, replay, and subject identity.
- `SEC-002` maps to tamper evidence separated from correctness.
- `QLT-001` through `QLT-005` govern all decision and certification branches.

## Risk controls

- `RSK-002`: mandatory SLO gate cannot be bypassed.
- `RSK-014`: criteria and gate applicability are declarative policies.
- `RSK-018`: independently reviewed positive and negative certification cases.
- `RSK-019`: separate audit-integrity and correctness fields and tests.
- `RSK-020`: no default criteria, weights, approvals, or thresholds.
- `RSK-022`: exact formula and subject version binding.
- `RSK-023` and `RSK-029`: confidential-data exclusion, authorization, and tenant isolation.

## Acceptance criteria

- Every scenario variant is explicit, immutable, deterministic, and evaluated by canonical services.
- Comparisons expose incompatibility rather than coercing unlike boundaries.
- Ranking exists only under a complete accepted decision policy.
- The certification service is the only construction path for `CERTIFIED`.
- Every mandatory failure case proves certification is impossible.
- Approvals are authorized, subject-bound, tenant-scoped, expiring, and revocable under policy.
- Audit-chain integrity is verifiable and never presented as correctness.
- Phases 1-5 regression suites pass.
- Coverage, mutation, typing, architecture, language, security, schema, and governance gates pass.
- A Phase 6 completion report records the full certification matrix and limitations.

## Stop conditions

Stop if any certification gate can be bypassed, approval authority is ambiguous, a result can be ranked without complete policy, comparisons mix incompatible boundaries, audit integrity is conflated with correctness, tenant scope is uncertain, or an end-to-end negative case reaches `CERTIFIED`.
