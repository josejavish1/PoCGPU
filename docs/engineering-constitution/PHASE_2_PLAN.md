# Phase 2 Plan: Benchmark-Backed Capacity and Physical Sizing

## Status

- Lifecycle state: `DRAFT FOR REVIEW`
- Implementation authority: `BLOCKED` until semantic, evidence, and engineering reviews accept this plan.
- Owning requirements: `CAL-001` through `CAL-006`, `DAT-004`, `ARC-004`, `QLT-001` through `QLT-004`.
- Owning formulas: `CAP-001` through `CAP-005` version `0.1.0`.

## Objective

Implement deterministic, benchmark-backed sizing that identifies the minimum physical deployment able to serve a declared workload while satisfying every mandatory SLO, headroom rule, growth allowance, maintenance policy, and failure-domain requirement. The result must reconcile installed, productive, resilient, sellable, stranded, reserved, and idle capacity without using theoretical hardware throughput as measured capacity.

## Entry conditions

- Phase 1 completion report is accepted and all regression gates pass.
- Serving Unit, benchmark, workload, SLO, topology, and capacity-classification terms are accepted by technical reviewers.
- At least one independently reviewable benchmark fixture includes raw-evidence references and all required metadata.
- Required unit dimensions and time windows are registered.
- No critical Phase 2 risk lacks a preventive and detection control.

## Scope

- Immutable Serving Unit identity and fingerprint.
- Workload profile and demand profile contracts for actual telemetry and explicit estimation modes.
- SLO definitions for TTFT, TPOT, error rate, queue behavior, throughput, concurrency, stability, and evaluation windows.
- Benchmark records, load points, approval, validity, and exact compatibility evaluation.
- Useful-capacity selection from measured SLO-passing points.
- Independent sizing by input-token rate, output-token rate, request rate, and concurrency.
- Bottleneck selection, operational headroom, growth allowance, maintenance reserve, and physical high availability.
- Discrete packing across accelerators, servers, racks, zones, and sites using explicit topology data.
- Capacity classification and reconciliation.
- Versioned capacity result section and certification blockers.

## Exclusions

- Hardware purchase cost, depreciation, energy cost, and TCO.
- Queueing simulation, stochastic optimization, dynamic model residency, and arbitrary multi-model pooling.
- Inference quality claims and theoretical FLOPS-to-throughput conversion.
- Vendor selection, catalog recommendations, or embedded model and hardware catalogs.
- Financial risk reserve as a substitute for physical resilience.

## Decisions required before implementation

Reviewers must accept:

1. The complete Serving Unit fingerprint fields and which changes invalidate benchmark compatibility.
2. Exact compatibility rules for software patch versions, hardware stepping, workload distributions, cache modes, and environmental differences.
3. Metric definitions, percentile method, measurement window, minimum sample rules, warm-up rules, and stability predicates.
4. The policy schema for headroom, growth, maintenance, failure domains, anti-affinity, and packing.
5. The representation of multi-site and active-active versus active-passive capacity.
6. How demand distributions become simultaneous peak constraints without inventing correlation.
7. Tie-breaking when multiple approved benchmark records are compatible.

Any unresolved item blocks coding; it cannot become a source default.

## Domain contracts

- `ServingUnit`: immutable model revision, engine and version, runtime stack, hardware topology, accelerator count, parallelism, precision, scheduler, context, caching, residency, and deployment settings.
- `ServingUnitFingerprint`: canonical hash of every identity-defining field.
- `WorkloadProfile`: input/output length distributions, request type, streaming, cache behavior, batching constraints, concurrency shape, and SLO references.
- `DemandProfile`: average and peak rates with source mode, observation window, seasonality reference, and accepted assumptions.
- `ServiceLevelObjective`: metric, comparator, threshold, percentile, evaluation window, mandatory flag, and failure behavior.
- `BenchmarkRecord`: governed identity, Serving Unit fingerprint, workload identity, environment, method, load points, raw evidence checksum, reviewer, approval, and validity.
- `BenchmarkLoadPoint`: offered load, achieved rates, latency percentiles, queue metrics, errors, stability, sample count, and duration.
- `ResiliencePolicy`: declared failures to survive and topology constraints.
- `PackingPolicy`: resource capacities and allocation restrictions supplied as governed data.
- `CapacityResult`: per-constraint requirements, bottleneck, allocations, classifications, reconciliations, evidence references, and blockers.

## Formula contracts

### CAP-001 compatible benchmark

Compatibility is a pure predicate over versioned identities and an explicit compatibility policy. A missing, stale, unapproved, or incompatible record produces `BENCHMARK_REQUIRED`. Selection order is deterministic and recorded.

### CAP-002 useful capacity

For each measured load point:

`useful = ttft_pass AND tpot_pass AND error_rate_pass AND queue_pass AND stability_pass`

The selected useful point is the greatest offered load satisfying all mandatory predicates. Interpolation and extrapolation are prohibited in version `0.1.0`.

### CAP-003 constraint-specific Serving Units

For each dimension `d`:

`required_d = ceil(peak_demand_d / useful_capacity_per_serving_unit_d)`

Demand and capacity must share the same dimension, workload identity, and time window.

### CAP-004 productive Serving Units

`productive = max(required_input, required_output, required_requests, required_concurrency)`

Headroom, growth, maintenance, and resilience are applied as separately named policy steps after the bottleneck calculation. Each intermediate quantity remains visible.

### CAP-005 utilization

`utilization_d = demand_d / sellable_capacity_d`

`bottleneck_utilization = max(utilization_d)`

Zero sellable capacity with positive demand is rejected; zero demand remains a verified value and does not imply capacity is unnecessary when policy requires installed resilience.

## Invariants and failure behavior

- Every useful-capacity claim references an approved compatible benchmark and exact load point.
- Every mandatory SLO passes at the selected point.
- Increasing demand cannot reduce required productive capacity under identical evidence and policy.
- Adding a declared failure cannot reduce installed resources.
- Capacity classes are non-negative, non-overlapping, and reconcile to installed capacity.
- Packing never allocates fractional indivisible resources.
- Stranded capacity is explicit and never counted as sellable.
- Missing benchmark yields `BENCHMARK_REQUIRED`; missing topology or policy yields `INPUT_REQUIRED` or `POLICY_REQUIRED`; failed mandatory SLO yields `REJECTED`.

## Ports and adapters

- Add benchmark, Serving Unit catalog, workload, topology, and telemetry ports.
- Provide in-memory contract adapters and versioned file fixtures for development evidence.
- Do not add vendor APIs in this phase; provider-specific ingestion belongs behind future adapters.
- Capture all selected records in the immutable scenario snapshot before evaluation.

## Planned implementation boundary

- `src/pocgpu/domain/capacity/`: contracts, compatibility, useful capacity, sizing, packing, reconciliation.
- `src/pocgpu/domain/ports/`: benchmark, catalog, topology, and telemetry protocols.
- `src/pocgpu/application/`: evidence resolution and capacity orchestration.
- `src/pocgpu/contracts/v2/`: strict request, evidence, and result schemas.
- `tests/phase2/`: domain, application, adapter, property, mutation, and golden evidence suites.
- `schemas/v2/`: deterministic exported boundary schemas.

Exact filenames may change during review, but dependency direction and single-engine ownership may not.

## Test-first verification matrix

| Area | Required evidence |
|---|---|
| Identity | Fingerprint golden bytes; every identity field mutation changes identity. |
| Compatibility | Valid, missing, stale, unapproved, and one-field mismatch cases. |
| SLO selection | Ordered load-point goldens including faster but failing points. |
| Sizing | Boundary cases around every ceiling and each independent bottleneck. |
| Properties | Demand monotonicity, scale invariance, and resilience monotonicity. |
| Packing | Fragmentation, indivisibility, anti-affinity, zone loss, and stranded capacity. |
| Reconciliation | Every capacity class sums exactly without overlap. |
| Determinism | Input reordering and cross-process replay preserve canonical output. |
| Mutation | All calculation mutations killed or formally adjudicated. |
| External review | At least one human-derived benchmark and sizing case with intermediate values. |

Canonical Phase 2 domain and formula services require 100 percent statement and branch coverage.

## Migration and compatibility

- Legacy theoretical roofline outputs remain migration evidence and are never accepted as benchmarks.
- No Phase 1 schema changes silently alter stored snapshots; Phase 2 adds versioned contracts.
- Unsupported capacity output changes from `OUTPUT_DOMAIN_UNAVAILABLE` to an evaluated result only when all Phase 2 evidence is resolvable.
- Intentional differences from legacy sizing are documented per fixture.

## Delivery increments

1. Accept terminology, decisions, schemas, and independent golden derivations.
2. Implement Serving Unit, workload, SLO, benchmark, and fingerprint contracts.
3. Implement compatibility and useful-capacity selection.
4. Implement multi-constraint sizing and utilization.
5. Implement resilience topology, packing, and reconciliation.
6. Integrate snapshot resolution, canonical results, and failure states.
7. Complete mutation, external reconciliation, migration evidence, and completion report.

Each increment must pass existing regression gates before the next begins.

## Requirements traceability

- `CAL-001` to identity contracts and fingerprint tests.
- `CAL-002` and `CAL-003` to compatibility, SLO, and useful-capacity evidence.
- `CAL-004` to independent constraint sizing.
- `CAL-005` to headroom, growth, maintenance, resilience, and packing.
- `CAL-006` to classification and reconciliation.
- `DAT-004`, `ARC-004`, `QLT-001` through `QLT-004`, `SEC-001`, and `SEC-002` apply across all increments.

## Risk controls

- `RSK-001`, `RSK-002`, `RSK-011`, and `RSK-012`: benchmark-first predicates and negative certification tests.
- `RSK-005`: physical failure-domain modeling separated from financial risk.
- `RSK-007`: typed dimensions and explicit periods.
- `RSK-013`: allocation reconciliation and stranded-capacity tests.
- `RSK-018`: independently derived goldens and mutation testing.
- `RSK-023`: aggregated evidence references without prompts or credentials.

## Acceptance criteria

- All Phase 2 decisions are accepted and recorded.
- CAP-001 through CAP-005 have versioned records, dimensional analysis, golden derivations, and failure tests.
- No result claims useful capacity without compatible approved benchmark evidence.
- Multi-constraint sizing, physical resilience, packing, and capacity reconciliation pass all mandatory tests.
- Phase 1 regressions pass unchanged.
- Required schemas are deterministic and backward compatibility is documented.
- Coverage, mutation, typing, lint, architecture, secret, language, and governance gates pass.
- A Phase 2 completion report records exact evidence and limitations.

## Stop conditions

Stop implementation immediately if benchmark semantics are unresolved, an SLO can be bypassed, a topology rule requires an embedded vendor assumption, capacity fails to reconcile, an independent golden disagrees, or a critical risk lacks an effective control.
