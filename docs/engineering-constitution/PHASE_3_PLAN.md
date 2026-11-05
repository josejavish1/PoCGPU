# Phase 3 Plan: Fully Loaded TCO and Accounting Views

## Status

- Lifecycle state: `DRAFT FOR REVIEW`
- Implementation authority: `BLOCKED` until semantic, evidence, and engineering reviews accept this plan.
- Owning requirements: `CAL-007` through `CAL-009`, `DAT-004`, `ARC-004`, `QLT-001` through `QLT-004`.
- Owning formulas: `TCO-001` through `TCO-003` version `0.1.0`.

## Objective

Implement a fully loaded, explicitly bounded cost model for the physical capacity produced by Phase 2. The phase must separate depreciation, economic capital cost, cash flow, fixed and variable operating cost, one-off allocation, and risk views while preserving original invoices, currencies, periods, and evidence classifications.

## Entry conditions

- Phases 1 and 2 are complete and their regression suites pass.
- Capacity topology and installed quantities are immutable Phase 2 outputs.
- Finance reviewers accept the cost-class taxonomy, accounting view definitions, allocation rules, and independent golden cases.
- Every required price, FX, power, facility, labor, support, network, storage, software, tax-treatment, and asset-life input has a governed schema.
- No critical Phase 3 risk lacks preventive and detection controls.

## Scope

- Explicit cost boundaries with included, excluded, and not-applicable classes.
- Asset acquisition, installation, useful life, residual value, depreciation, and cash-flow schedules.
- Economic capital-charge view separated from accounting depreciation.
- Measured or explicitly assumed power, active hours, PUE, energy price, and facility energy.
- Facility, colocation, network, storage, software, support, maintenance, labor, security, compliance, insurance, and decommissioning classes.
- One-off allocation policies and recurring fixed and variable operating cost.
- Original-currency preservation and governed FX conversion.
- Nominal, accounting, cash, and risk-adjusted views as separate outputs.
- Monthly and annual result periods with explicit conversion rules.
- Cost-class reconciliation to fully loaded TCO.

## Exclusions

- Unit cost allocation across tokens or requests.
- Customer pricing, gross margin, markup, external API comparison, break-even, and hybrid decisions.
- Organization-specific tax advice or embedded accounting policy.
- Forecasting inflation, exchange rates, or energy prices without governed scenario inputs.
- Using TDP as measured power or inventing missing commercial terms.

## Decisions required before implementation

Reviewers must accept:

1. The canonical cost-class hierarchy and rules preventing overlap.
2. Accounting, economic, cash-flow, and risk-view semantics.
3. Period normalization, partial-period treatment, allocation start and end rules, and rounding boundaries.
4. Capitalized-cost composition, asset-class useful-life policy, residual value, and disposal treatment.
5. Capital-charge method and whether nominal or real rates are used for each policy pack.
6. Power aggregation, active-hour definitions, PUE boundary, and cooling exclusion rules.
7. FX observation selection, conversion direction, triangulation policy, and stale-data behavior.
8. Treatment of taxes, recoverable taxes, commitments, credits, shared services, and one-off costs.

Unresolved accounting policy produces `POLICY_REQUIRED`; missing factual cost produces `INPUT_REQUIRED`.

## Domain contracts

- `CostBoundary`: service, topology, period, included classes, excluded classes, allocation scope, currency basis, and policy versions.
- `CostRecord`: governed amount, class, recurrence, quantity basis, original currency, period, source, owner, validity, and allocation reference.
- `AssetRecord`: asset class, quantity, acquisition and installation components, in-service date, useful life, residual value, and evidence.
- `PowerObservation`: measured or assumed average IT power, quantity, active window, source, and confidence.
- `FacilityPolicy`: PUE observation, included facility overhead, allocation basis, and validity.
- `AllocationPolicy`: named driver, numerator, denominator, applicable period, precision, and residual treatment.
- `AccountingPolicy`: depreciation and recognition choices represented as governed data.
- `TcoResult`: component ledger, subtotals, reconciliations, original and converted values, view-specific totals, assumptions, and blockers.

## Formula contracts

### TCO-001 monthly depreciation

For each asset class:

`monthly_depreciation = (capitalized_cost - residual_value) / useful_life_months`

The valid domain requires non-negative capitalized cost and residual value, residual value not greater than capitalized cost, and strictly positive useful life. Partial-period convention is policy-driven and explicit.

### TCO-002 facility energy

`monthly_facility_kwh = sum(average_it_kw_i * quantity_i * active_hours_i) * pue`

`monthly_energy_cost = monthly_facility_kwh * electricity_price_per_kwh`

Every factor uses compatible period and location. PUE includes facility overhead; additional cooling energy is rejected unless the boundary proves it is excluded from PUE.

### TCO-003 fully loaded monthly TCO

`monthly_tco = depreciation + capital_charge + fixed_opex + variable_opex + allocated_one_off + risk_view_adjustments`

Nominal TCO excludes risk-view adjustments. Cash outflow and accounting expense remain separately reconciled views and never reuse the same label.

## Invariants and failure behavior

- Every required cost class is explicitly included, excluded with reason, or not applicable.
- Component totals equal subtotals and the declared aggregate exactly at the calculation precision.
- Reordering independent records does not change results.
- Increasing a positive included cost cannot reduce TCO.
- Original monetary amounts and FX observations remain available after conversion.
- One source record cannot enter overlapping cost classes for the same boundary.
- Energy dimensions reconcile from power and time; PUE is dimensionless and valid under policy.
- Missing or stale critical evidence blocks certification; accepted assumptions produce `ASSUMPTION_BASED`.

## Ports and adapters

- Add governed asset, invoice, price, FX, power, facility, labor, contract, and ledger ports.
- Provide in-memory contract adapters and synthetic versioned evidence fixtures.
- External ERP, cloud billing, energy, and FX integrations remain replaceable adapters and are not required for core completion.
- Snapshot every selected record and policy before calculation.

## Planned implementation boundary

- `src/pocgpu/domain/tco/`: cost boundaries, assets, energy, allocation, accounting views, and reconciliation.
- `src/pocgpu/domain/ports/`: financial evidence, FX, asset, power, and pricing protocols.
- `src/pocgpu/application/`: evidence resolution and TCO orchestration.
- `src/pocgpu/contracts/v3/` and `schemas/v3/`: strict versioned boundaries.
- `tests/phase3/`: unit, property, mutation, adapter, reconciliation, and independently derived golden suites.

## Test-first verification matrix

| Area | Required evidence |
|---|---|
| Depreciation | Zero residual, non-zero residual, invalid life, invalid residual, and partial-period goldens. |
| Energy | Dimensional derivation, multiple devices, active windows, PUE boundary, and double-count rejection. |
| Cost classes | Complete boundary, missing class, exclusion rationale, and duplicate attribution. |
| Currency | Direct conversion, reverse round trip, stale FX, original-value preservation, and multi-currency aggregation. |
| Accounting views | Depreciation, capital charge, and cash flow remain distinct and reconcile. |
| Properties | Positive-cost monotonicity, record-order invariance, and period scaling where policy permits. |
| Reconciliation | Component, class, period, currency, and total ledgers balance exactly. |
| Mutation | All calculation mutations killed or formally adjudicated. |
| External review | At least one independently prepared fully loaded TCO case with source references and intermediates. |

Canonical Phase 3 calculation services require 100 percent statement and branch coverage.

## Migration and compatibility

- Legacy TCO outputs remain unverified evidence and cannot become golden expectations.
- Phase 2 quantities and topology are consumed by immutable reference; Phase 3 never rewrites sizing.
- Phase 3 adds versioned result sections without changing historical Phase 1 or Phase 2 canonical bytes.
- Every corrected legacy omission or double count is listed in migration evidence.

## Delivery increments

1. Accept cost taxonomy, accounting semantics, policies, and independent derivations.
2. Implement boundaries, cost records, assets, periods, and currencies.
3. Implement depreciation and accounting/cash views.
4. Implement power, PUE, facility energy, and variable costs.
5. Implement fixed cost, allocations, capital charge, risk views, and reconciliation.
6. Integrate governed evidence resolution and canonical results.
7. Complete mutation, external reconciliation, migration evidence, and completion report.

## Requirements traceability

- `CAL-007` maps to the explicit boundary, taxonomy, and reconciliation ledger.
- `CAL-008` maps to separate depreciation, economic capital, and cash-flow views.
- `CAL-009` maps to power evidence, PUE, energy dimensions, and double-count controls.
- `DAT-001` through `DAT-005`, `ARC-004`, `QLT-001` through `QLT-004`, `SEC-001`, and `SEC-002` apply throughout.

## Risk controls

- `RSK-005`: physical resilience remains a Phase 2 topology, not a financial reserve.
- `RSK-007`: typed quantities and periods.
- `RSK-008`: immutable FX evidence and original values.
- `RSK-009`: cost-boundary inclusion metadata and cooling/PUE rejection tests.
- `RSK-010`: measured-versus-assumed power and provenance gates.
- `RSK-018`: independent financial goldens and mutation testing.
- `RSK-023`: references to contracts and invoices without confidential document content.

## Acceptance criteria

- TCO-001 through TCO-003 have accepted formula records, dimensional analysis, independent goldens, and failure tests.
- Every cost class has an explicit boundary disposition and all totals reconcile.
- Depreciation, capital charge, cash flow, nominal TCO, and risk-adjusted TCO remain distinct.
- Energy calculations prove PUE and cooling are not double counted.
- Multi-currency results retain original values and valid FX provenance.
- Phase 1 and Phase 2 regression suites pass.
- Coverage, mutation, typing, architecture, language, security, schema, and governance gates pass.
- A Phase 3 completion report records external reconciliation and limitations.

## Stop conditions

Stop if cost boundaries overlap, an accounting choice is unresolved, critical evidence is missing or stale, power provenance is ambiguous, PUE treatment can double count, currency originals are lost, a reconciliation fails, or an independent golden disagrees.
