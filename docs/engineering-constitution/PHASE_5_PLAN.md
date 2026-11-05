# Phase 5 Plan: External Comparison, Break-Even, and Hybrid Cost

## Status

- Lifecycle state: `DRAFT FOR REVIEW`
- Implementation authority: `BLOCKED` until semantic, evidence, and engineering reviews accept this plan.
- Owning requirements: `CAL-012` through `CAL-014`, `ARC-004`, and `QLT-001` through `QLT-004`.
- Owning formulas: `API-001`, `API-002`, and `HYB-001` version `0.1.0`.

## Objective

Compare private infrastructure with external API or cloud services on an equivalent workload, service level, geography, currency, contract, cache, and period basis. Compute discrete piecewise break-even and hybrid private-baseload plus external-overflow cost without scaling already purchased private fixed cost by traffic share.

## Entry conditions

- Phases 1-4 are complete and all regression gates pass.
- Procurement, finance, and technical reviewers accept equivalence, external-meter, commitment, discount, tax, and hybrid-allocation semantics.
- At least one dated external price fixture and one independently derived comparison case are approved.
- No critical Phase 5 risk lacks preventive and detection controls.

## Scope

- External service offer and immutable price-card contracts.
- Input, output, cached-input, request, storage, network, provisioned-capacity, and other explicit meters.
- Region, currency, effective period, purchase model, commitment, allowance, discount, tax, batch, and cache treatment.
- Workload and SLO equivalence gate before economic comparison.
- Equivalent external monthly cost.
- Private capacity-step generation from Phase 2 sizing and Phase 3-4 economics.
- Piecewise break-even with zero, one, multiple, or no valid crossings.
- Hybrid cost using full installed private-block cost plus external overflow.
- Comparison result with assumptions, evidence, invalidity reasons, and sensitivity inputs.

## Exclusions

- Vendor recommendation, model-quality ranking, contract negotiation, demand forecasting, and stochastic routing optimization.
- Inferring missing price meters, cache ratios, discounts, taxes, egress, or service equivalence.
- Treating public list prices and negotiated prices as interchangeable.
- Scaling private fixed cost by the percentage of traffic routed privately.

## Decisions required before implementation

Reviewers must accept:

1. The exact equivalence dimensions for workload, model/service capability, SLO, geography, availability, support, security, and compliance.
2. External meter taxonomy and aggregation order.
3. Allowance, tier, commitment, minimum-spend, discount, tax, and credit semantics.
4. Cache and batch treatment and their compatibility with the private scenario.
5. Construction of discrete private capacity intervals and variable cost inside each interval.
6. Break-even root inclusion at interval boundaries and reporting when multiple crossings exist.
7. Hybrid routing input, overflow definition, private saturation policy, and external fallback constraints.

Missing commercial facts yield `INPUT_REQUIRED`; unresolved equivalence yields `POLICY_REQUIRED`; incompatible offers yield `REJECTED` for comparison.

## Domain contracts

- `ExternalServiceOffer`: provider-neutral service identity, capabilities, SLO, region, purchase model, and evidence.
- `PriceCard`: immutable effective period, currency, meters, tiers, commitments, allowances, discounts, taxes, and provenance.
- `MeteredUsage`: compatible workload-derived quantity for one named meter and period.
- `EquivalenceAssessment`: dimension-by-dimension status, evidence, policy, and blockers.
- `CapacityStep`: inclusive/exclusive volume interval, installed private block, fixed cost, variable unit cost, and capacity evidence.
- `BreakEvenPoint`: volume, interval, cost equality evidence, precision, and boundary status.
- `HybridAllocation`: installed private block, privately served demand, overflow demand, and routing policy.
- `ComparisonResult`: private, external, hybrid, differences, break-even points, equivalence, evidence, and blockers.

## Formula contracts

### API-001 equivalent external cost

`api_cost = input_millions * input_price + output_millions * output_price + cached_input_millions * cached_input_price + other_metered_costs`

Every meter is expanded into a reconciled component ledger. Workload, period, currency, region, discount, batch, cache, allowance, and commitment treatment must match the declared comparison.

### API-002 piecewise break-even

Within private capacity interval `i`:

`break_even_volume_i = fixed_private_cost_i / (api_unit_cost_i - private_variable_unit_cost_i)`

A candidate is valid only when the denominator is positive and the resulting volume lies inside interval `i` under accepted boundary rules. All intervals are evaluated; multiple valid points remain visible.

### HYB-001 hybrid monthly cost

`hybrid_cost = full_installed_private_block_cost + external_overflow_cost`

The installed private block cost is charged in full. Private variable components and external overflow meters are reconciled separately. Traffic share never scales private fixed cost.

## Invariants and failure behavior

- No economic comparison is valid before equivalence passes every mandatory dimension.
- External component costs reconcile to the price-card rules and total.
- Break-even candidates never escape their capacity interval.
- Every discrete capacity step is evaluated and ordered deterministically.
- Hybrid private and overflow demand reconcile to total demand without overlap or loss.
- Zero overflow yields the full installed private cost; zero private traffic does not erase installed private cost.
- Stale price cards produce `STALE`; missing meters produce `INPUT_REQUIRED`; failed equivalence blocks certification.

## Ports and adapters

- Add external offer and pricing-provider ports with immutable record retrieval.
- Provide in-memory and versioned-file adapters using synthetic reviewed evidence.
- Provider APIs remain adapters; provider names and meter identifiers never enter domain branches.
- Capture exact offers, price cards, FX, policies, and comparison inputs in the scenario snapshot.

## Planned implementation boundary

- `src/pocgpu/domain/comparison/`: equivalence, metering, external cost, capacity steps, break-even, hybrid allocation, and reconciliation.
- `src/pocgpu/domain/ports/`: external offer and pricing protocols.
- `src/pocgpu/application/`: comparison evidence resolution and orchestration.
- `src/pocgpu/contracts/v5/` and `schemas/v5/`: strict versioned boundaries.
- `tests/phase5/`: formula, tier, boundary, property, mutation, equivalence, and independent golden suites.

## Test-first verification matrix

| Area | Required evidence |
|---|---|
| Equivalence | Exact match, every single-dimension mismatch, unresolved policy, and evidence expiry. |
| External cost | Separate meters, allowances, tiers, commitments, cache, batch, discounts, tax, and reconciliation. |
| Break-even | Positive, zero, and negative denominators; boundary roots; no root; and multiple crossings. |
| Capacity steps | Ordered discrete intervals with no gap or overlap under declared policy. |
| Hybrid | Zero overflow, full overflow with installed block, partial overflow, and conservation. |
| Properties | Cost-component monotonicity and demand-allocation conservation. |
| Determinism | Price-record reordering and replay preserve canonical output. |
| Mutation | All calculation mutations killed or formally adjudicated. |
| External review | Procurement and finance reviewed comparison with dated evidence and intermediates. |

Canonical Phase 5 calculation services require 100 percent statement and branch coverage.

## Migration and compatibility

- Legacy cloud-share multiplication of private fixed cost is an intentional correction and is prohibited.
- Legacy break-even based on one continuous capacity function is not preserved.
- Phase 5 consumes immutable prior results and adds versioned comparison sections.
- Migration evidence records differences caused by equivalent-workload enforcement, complete metering, and discrete capacity steps.

## Delivery increments

1. Accept equivalence, meter, pricing, capacity-step, and hybrid decisions plus independent goldens.
2. Implement offers, price cards, meters, and equivalence.
3. Implement API-001 with tier and component reconciliation.
4. Implement capacity steps and API-002.
5. Implement hybrid allocation and HYB-001.
6. Integrate provider-neutral ports, snapshots, canonical results, and failure states.
7. Complete mutation, external reconciliation, migration evidence, and completion report.

## Requirements traceability

- `CAL-012` maps to equivalence and API-001.
- `CAL-013` maps to capacity steps and API-002.
- `CAL-014` maps to hybrid allocation, HYB-001, and conservation.
- `PRD-006`, `DAT-003` through `DAT-005`, `ARC-004`, `QLT-001` through `QLT-004`, and `SEC-001` apply throughout.

## Risk controls

- `RSK-004`: full installed-block cost and hybrid conservation tests.
- `RSK-007`: compatible dimensions, meters, and periods.
- `RSK-018`: independent procurement/finance goldens and mutation testing.
- `RSK-020`: no default discount, cache, batch, commitment, or traffic share.
- `RSK-022`: immutable formula and price-card versions.

## Acceptance criteria

- API-001, API-002, and HYB-001 have accepted records, dimensional analysis, independent goldens, and negative tests.
- Comparison is impossible without explicit mandatory equivalence.
- External meter components and totals reconcile to an immutable dated price card.
- Every capacity interval is evaluated and every break-even point is interval-valid.
- Hybrid allocation conserves demand and charges the full installed private block.
- Phases 1-4 regression suites pass.
- Coverage, mutation, typing, architecture, language, schema, security, and governance gates pass.
- A Phase 5 completion report records evidence and limitations.

## Stop conditions

Stop if equivalence is unresolved, a price meter is missing, a provider rule enters the domain as a branch, capacity intervals overlap, a break-even root lies outside its interval, hybrid demand fails to reconcile, private fixed cost is traffic-weighted, or an independent golden disagrees.
