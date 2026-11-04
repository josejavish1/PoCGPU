# Quality and Verification Strategy

## Quality model

Quality means demonstrated correctness within an explicit scope, not the absence of observed test failures. Release evidence must cover semantics, mathematics, data, architecture, security, performance, interfaces, and operations.

## Gate order

1. Contract and schema validation.
2. Formatting, linting, and strict static typing.
3. Architecture and source-policy checks.
4. Unit and boundary tests.
5. Property and metamorphic tests.
6. Mutation and fuzz testing.
7. Adapter contract and integration tests.
8. Golden-case and external-evidence reconciliation.
9. Cross-interface parity tests.
10. Performance, load, resilience, accessibility, and security tests.
11. Reproducible build and release evidence.

A failure at an earlier gate blocks later certification.

## Test classes

### Unit tests

Verify one domain invariant or formula branch with explicit dimensions and expected results.

### Boundary tests

Cover zero, minimum, maximum, just-below, exact-boundary, just-above, empty, stale, conflicting, and dimensionally invalid inputs.

### Property tests

Examples include:

- Adding demand cannot reduce required productive capacity within the same policy and evidence set.
- Adding a required failure reserve cannot reduce installed capacity.
- Increasing a positive cost component cannot reduce TCO.
- A higher target gross margin cannot reduce target price.
- Converting currency and reversing with the same exact rate preserves the amount within the declared rounding boundary.
- Component totals reconcile with aggregate totals.
- Capacity classifications sum to installed capacity without overlap.

### Metamorphic tests

- Scaling all quantities and compatible capacity by the same factor preserves utilization.
- Reordering independent cost records does not change TCO.
- Rendering the same canonical result in another locale does not change numeric values.
- Replaying an immutable scenario produces the same canonical hash and result.

### Mutation tests

All calculation-core mutations must be killed or reviewed and documented as equivalent or invalid mutations. Unreviewed surviving mutants block completion.

### Fuzz tests

Fuzz schemas, decimal parsing, units, policy composition, locale inputs, malformed catalog records, extreme but valid quantities, and serialization round trips.

### Golden cases

Golden cases must be calculated independently from the production implementation. Critical cases require:

- Human-readable derivation.
- Source evidence.
- Expected intermediate values.
- Expected final result.
- Review by the relevant technical or financial role.

Production code must not generate its own golden expected values.

### External validation

- Capacity reconciles with approved benchmark evidence.
- Energy reconciles with meter or telemetry evidence where available.
- TCO reconciles with invoice, quote, contract, or ledger samples.
- Cloud and API pricing reconciles with dated provider or contract records.
- Workbook, API, and web outputs reconcile with the canonical result.

## Coverage

- Canonical domain and calculation services require full statement and branch coverage.
- Coverage exclusions require an accepted decision record and cannot hide calculation behavior.
- Coverage does not replace mutation, property, or external validation.

## Static quality

- Strict type checking.
- No untyped dynamic values in the domain.
- No float values in governed calculations.
- No dependency cycles.
- No framework imports in the domain.
- No source access to process environment, network, clock, randomness, or file system from calculation services.
- No prohibited literals, localized text, or organization-specific branches.
- Complexity limits and explicit decomposition for calculation functions.

## Test reliability

- Mandatory tests cannot be skipped, muted, retried into success, or marked expected failure without an approved and expiring issue.
- Flaky tests block release until the source of nondeterminism is removed.
- Test fixtures identify their provenance and do not silently share production defaults.
- Tests execute in clean environments using pinned dependencies.

## Security and supply chain

- Secret scanning.
- Dependency vulnerability scanning.
- Software bill of materials.
- Reproducible dependency lock.
- Static application security testing.
- Authorization and tenant-isolation tests.
- Input size and resource exhaustion tests.
- Export formula-injection tests.

## Completion evidence

Each phase report lists commands, versions, counts, failures, skips, coverage, mutation results, known limitations, and links to external reconciliation evidence. A green summary without underlying evidence is insufficient.
