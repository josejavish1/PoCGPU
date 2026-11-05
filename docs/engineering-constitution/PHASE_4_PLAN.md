# Phase 4 Plan: Unit Economics and Gross-Margin Pricing

## Status

- Lifecycle state: `DRAFT FOR REVIEW`
- Implementation authority: `BLOCKED` until semantic, evidence, and engineering reviews accept this plan.
- Owning requirements: `CAL-010`, `CAL-011`, `ARC-004`, and `QLT-001` through `QLT-004`.
- Owning formulas: `ECO-001`, `ECO-002`, `PRC-001`, and `PRC-002` version `0.1.0`.

## Objective

Convert a compatible Phase 3 cost boundary and Phase 2 workload/capacity boundary into transparent unit economics and policy-driven target prices. The implementation must distinguish cost, price, gross margin, markup, utilization, productive capacity, and sellable capacity and must expose every allocation basis.

## Entry conditions

- Phases 1-3 are complete and all regression gates pass.
- Finance and commercial reviewers accept unit definitions, cost-allocation boundaries, margin policy, precision, and independent golden cases.
- Workload, capacity, TCO, currency, service, and period identities are compatible and immutable.
- No critical Phase 4 risk lacks preventive and detection controls.

## Scope

- Blended cost per million total tokens for one declared workload profile.
- Separate informational input-token, output-token, request, and capacity-unit views only when an accepted allocation policy defines them.
- Utilization sensitivity across an explicit scenario grid supplied as governed input.
- Gross-margin target price and separately reported markup.
- Price-component reconciliation and declared rounding boundaries.
- Policy-driven commercial treatment, without embedded target margins or discount assumptions.
- Versioned unit-economics and pricing result sections with evidence references and blockers.

## Exclusions

- External provider prices, competitive benchmarking, break-even, hybrid routing, tax advice, demand forecasting, and contract generation.
- Inferring separate input and output costs from blended infrastructure cost without an accepted causal allocation policy.
- Hidden utilization, demand, margin, discount, or price defaults.
- Business-value, willingness-to-pay, or market-demand claims.

## Decisions required before implementation

Reviewers must accept:

1. The service boundary and workload identity required for cost allocation.
2. The denominator definitions for tokens, requests, concurrency, and capacity units.
3. Whether reserved resilience and idle capacity remain in the cost pool and how they are disclosed.
4. Which utilization grid is scenario input and how capacity steps are represented.
5. Gross-margin policy scope, valid domain, precision, and final price rounding.
6. Whether discounts, taxes, credits, and channel costs are inside or outside each price view.
7. Rules for zero volume, zero cost, and currencies with different minor-unit conventions.

Any unresolved commercial choice produces `POLICY_REQUIRED`.

## Domain contracts

- `EconomicBoundary`: service, workload, capacity, TCO, currency, period, cost pool, and allocation-policy identities.
- `VolumeMeasure`: dimension, period, governed value, workload reference, and provenance.
- `CostAllocation`: cost pool, driver, denominator, allocated amount, residual, and policy reference.
- `UtilizationScenario`: explicit ratio or demand point with identity and source classification.
- `MarginPolicy`: target gross margin, applicable scope, price precision, rounding mode, and approval.
- `UnitEconomicsResult`: denominators, allocated costs, unit costs, utilization sensitivity, and reconciliation.
- `PricingResult`: cost basis, target gross margin, target price, implied markup, rounding delta, currency, and blockers.

## Formula contracts

### ECO-001 blended cost per million tokens

`total_million_tokens = (monthly_input_tokens + monthly_output_tokens) / 1_000_000`

`blended_cost_per_million = allocated_monthly_tco / total_million_tokens`

The TCO and token demand must cover the same service, workload, and period. Zero volume cannot produce a finite unit cost and yields `INPUT_REQUIRED` or an explicitly non-computable result.

### ECO-002 utilization sensitivity

`tokens_at_utilization = useful_monthly_token_capacity * utilization_ratio`

`cost_per_million_at_utilization = monthly_tco / (tokens_at_utilization / 1_000_000)`

Valid utilization ratios and scenario points are supplied by governed policy or scenario input. Sensitivity does not rewrite the baseline result.

### PRC-001 gross-margin price

`price = cost / (1 - target_gross_margin)`

Valid domain: `0 <= target_gross_margin < 1`. Price rounding occurs only at the declared presentation or billing boundary and the rounding delta is visible.

### PRC-002 markup reporting

`markup = (price - cost) / cost`

When cost is zero, markup is undefined rather than infinite. Markup remains informational and is never labeled gross margin.

## Invariants and failure behavior

- Cost and denominator boundaries have identical service and period identities.
- Allocated components and residual reconcile to the selected cost pool.
- Increasing positive cost cannot reduce unit cost under an unchanged denominator.
- Increasing target gross margin cannot reduce target price.
- Recomputed gross margin from unrounded values equals the target within declared exact precision.
- Gross margin and markup are separate typed fields and localization keys.
- Missing allocation or commercial policy yields `POLICY_REQUIRED`; zero or incompatible denominator yields a fail-closed state.

## Ports and adapters

- Add commercial-policy and allocation-policy ports if Phase 1 policy storage is insufficient.
- Consume immutable Phase 2 capacity and Phase 3 TCO results; do not duplicate their formulas.
- Use in-memory policy adapters and synthetic reviewed commercial fixtures.
- External billing, CRM, and price-book integrations are deferred to adapter work after canonical completion.

## Planned implementation boundary

- `src/pocgpu/domain/economics/`: boundaries, allocation, unit economics, sensitivity, margin, markup, and reconciliation.
- `src/pocgpu/application/`: compatible-result resolution and economics orchestration.
- `src/pocgpu/contracts/v4/` and `schemas/v4/`: strict versioned boundaries.
- `tests/phase4/`: formula, property, mutation, compatibility, reconciliation, and independent golden suites.

## Test-first verification matrix

| Area | Required evidence |
|---|---|
| Boundary matching | Service, workload, period, currency, and version mismatch negatives. |
| Blended unit cost | Independently derived token and allocation goldens. |
| Sensitivity | Zero boundary, explicit grid, monotonic behavior within a capacity step, and baseline preservation. |
| Gross margin | Zero, representative, near-one, invalid-negative, and one-or-greater cases. |
| Markup | Algebraic relation, zero-cost undefined behavior, and label separation. |
| Rounding | Currency precision, rounding delta, and no intermediate rounding. |
| Properties | Cost monotonicity, margin-price monotonicity, and allocation conservation. |
| Mutation | All calculation mutations killed or formally adjudicated. |
| External review | Finance-reviewed derivation with intermediates and policy references. |

Canonical Phase 4 calculation services require 100 percent statement and branch coverage.

## Migration and compatibility

- Legacy markup labeled as margin is an intentional correction and must not be preserved.
- No prior phase result is mutated; Phase 4 adds versioned references and result sections.
- Existing unsupported output states become evaluable only with compatible Phase 2 and Phase 3 results plus approved policies.
- Migration evidence records every changed label, denominator, and rounding behavior.

## Delivery increments

1. Accept boundaries, denominators, allocation rules, commercial policies, and independent goldens.
2. Implement economic boundary and allocation reconciliation.
3. Implement ECO-001 and ECO-002.
4. Implement PRC-001 and PRC-002 with explicit rounding.
5. Integrate policy resolution, canonical results, and failure states.
6. Complete mutation, external reconciliation, migration evidence, and completion report.

## Requirements traceability

- `CAL-010` maps to compatible workload allocation and unit-cost goldens.
- `CAL-011` maps to separate gross-margin and markup contracts and algebraic properties.
- `PRD-006`, `DAT-003` through `DAT-005`, `ARC-004`, `QLT-001` through `QLT-004`, and `SEC-001` apply throughout.

## Risk controls

- `RSK-006`: separate types, schemas, formulas, labels, and property tests for margin and markup.
- `RSK-007`: compatible dimensions and periods.
- `RSK-018`: independent commercial goldens and mutation testing.
- `RSK-020`: no default volume, utilization, or margin in DTOs or source.
- `RSK-022`: immutable formula versions and replay.

## Acceptance criteria

- ECO-001, ECO-002, PRC-001, and PRC-002 have accepted records, dimensional analysis, independent goldens, and negative tests.
- Every unit cost identifies its cost pool, denominator, workload, period, currency, and policy.
- Allocation components and residual reconcile exactly.
- Margin and markup remain algebraically and semantically distinct across schemas and outputs.
- No governed commercial value is embedded in source or public DTO defaults.
- Phases 1-3 regression suites pass.
- Coverage, mutation, typing, architecture, language, schema, security, and governance gates pass.
- A Phase 4 completion report records evidence and limitations.

## Stop conditions

Stop if cost and volume boundaries differ, an allocation rule is implicit, margin policy is unresolved, zero denominators produce misleading values, intermediate rounding changes results, margin and markup labels can be confused, or an independent golden disagrees.
