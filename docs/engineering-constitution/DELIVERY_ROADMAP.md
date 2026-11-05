# Delivery Roadmap: Phases 0-8

## Status

- Roadmap version: `1.0.0`
- Lifecycle state: `DRAFT FOR REVIEW`
- Planning boundary: phases 0 through 8
- Implementation authority: an individual phase plan becomes executable only after review changes its lifecycle state to `ACCEPTED`.

## Purpose

This roadmap divides the product mission into independently reviewable implementation phases. It prevents a coding agent from inventing formulas, evidence, policy, scope, or acceptance criteria while implementing a phase. Every phase has one primary responsibility, explicit entry and exit gates, and an independent plan.

## Global execution protocol

For every phase, the implementing agent must:

1. Read the Engineering Constitution, this roadmap, and the phase plan.
2. Produce a requirement-to-test matrix before production code.
3. List every unresolved decision and stop before implementation if any decision can affect semantics, mathematics, evidence, security, or compatibility.
4. Implement only the accepted scope and preserve dependency direction.
5. Keep executable source, identifiers, comments, docstrings, logs, schemas, and technical documentation in English.
6. Store business variation in validated governed records; never introduce contextual source branches or hidden defaults.
7. Run the full regression suite and every phase-specific gate.
8. Publish a completion report containing commands, versions, counts, reconciliations, limitations, and migration outcomes.

An agent must not interpret a green test suite as authority to expand scope or certify unsupported outputs.

## Phase sequence

| Phase | Primary outcome | Plan | Depends on |
|---:|---|---|---|
| 0 | Engineering constitution and automated governance | `PHASE_0_PLAN.md` | None |
| 1 | Canonical deterministic foundation and governed contracts | `PHASE_1_PLAN.md` | 0 |
| 2 | Benchmark-backed useful capacity and physical sizing | `PHASE_2_PLAN.md` | 1 |
| 3 | Fully loaded TCO and accounting views | `PHASE_3_PLAN.md` | 2 |
| 4 | Unit economics, gross-margin pricing, and utilization sensitivity | `PHASE_4_PLAN.md` | 3 |
| 5 | Equivalent external comparison, piecewise break-even, and hybrid cost | `PHASE_5_PLAN.md` | 4 |
| 6 | Scenario comparison, sensitivity orchestration, approvals, and certification | `PHASE_6_PLAN.md` | 2-5 |
| 7 | Versioned API, web, export, workbook, and internationalization parity | `PHASE_7_PLAN.md` | 6 |
| 8 | Production security, operations, supply chain, recovery, and release evidence | `PHASE_8_PLAN.md` | 7 |

## Dependency rules

- A phase may consume only completed outputs from prior phases.
- Formula ownership never moves to an interface or later orchestration phase.
- A later phase may identify a defect in an earlier contract, but correction requires a versioned change in the owning phase with regression and migration evidence.
- Phase 3 may use Phase 2 topology and quantities but cannot reinterpret useful capacity.
- Phase 4 may allocate Phase 3 cost only across a compatible Phase 2 workload and period.
- Phase 5 must compare the exact Phase 2-4 workload, service boundary, currency basis, and period.
- Phase 6 composes immutable results and gates; it does not duplicate formulas from phases 2-5.
- Phase 7 renders and transports the Phase 6 canonical result; interfaces never calculate it.
- Phase 8 hardens and releases the same product; operational controls never change calculation semantics.

## Cross-phase invariants

- One canonical calculation engine serves every interface.
- Identical immutable inputs and versions produce identical canonical bytes and hash.
- Missing critical facts, evidence, policy, or approvals fail closed.
- `CERTIFIED` is impossible while any required technical, financial, provenance, SLO, reconciliation, authorization, or approval gate is unresolved or failed.
- Original evidence, currency, unit, period, and provenance remain traceable through derived outputs.
- Capacity, cost, price, risk, accounting, and cash-flow views remain separate.
- Tenant scope is checked at every repository and application boundary.
- Historical certified results remain replayable with their original versions.

## Common phase-plan contract

Every phase plan must contain:

- Status and implementation authority.
- Objective and measurable outcome.
- Entry conditions.
- Scope and explicit exclusions.
- Required decisions that must be resolved before coding.
- Domain, formula, data, port, and schema contracts.
- Planned file and dependency boundaries.
- Test-first verification matrix.
- Migration and compatibility plan.
- Delivery increments with review checkpoints.
- Requirements and risk traceability.
- Acceptance criteria, completion evidence, and stop conditions.

## Review gates

Each phase receives four explicit reviews:

1. `SEMANTIC REVIEW`: domain meaning, formulas, units, periods, and failure behavior.
2. `EVIDENCE REVIEW`: provenance, compatibility, validity, independent examples, and reconciliation sources.
3. `ENGINEERING REVIEW`: architecture, schemas, security, migration, tests, and operational impact.
4. `ACCEPTANCE REVIEW`: every plan criterion has objective evidence and no mandatory gate is bypassed.

The first three reviews are required before implementation. The acceptance review closes the phase.

## Program completion

The nine-phase program is complete only when Phase 8 publishes a release report proving all Product Release Completion conditions from the Definition of Done. Completion does not imply universal correctness outside the declared formulas, evidence, scenarios, versions, and limitations.
