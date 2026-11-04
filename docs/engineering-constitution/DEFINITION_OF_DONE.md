# Definition of Done

## Phase readiness

A phase may begin implementation only when:

- Its plan is published.
- Scope and exclusions are explicit.
- Requirements and risks are mapped.
- Domain contracts and formulas are resolved for the phase.
- Data and migration impacts are known.
- Tests and acceptance evidence are defined.
- No critical risk lacks a preventive and detection control.

## Implementation completion

A phase is complete only when:

- Every in-scope requirement has implementation, tests, and evidence.
- All mandatory gates pass in a clean environment.
- No mandatory test is skipped, disabled, flaky, or unexplained.
- Domain and calculation coverage meets the Quality Strategy.
- Mutation survivors are killed or formally adjudicated.
- Static typing and architecture boundaries pass.
- No prohibited hardcoding or localized source text exists.
- Every governed value has required provenance metadata.
- Formula and unit reconciliations pass.
- Migration behavior and intentional corrections are documented.
- Documentation and schemas match implementation.
- Known limitations are explicit and do not contradict certification.
- A phase completion report is published.

## Product release completion

The product is release-ready only when:

- One canonical calculation engine serves every interface.
- Representative organization, vertical, locale, currency, and deployment scenarios pass.
- Capacity outputs reconcile with approved benchmark evidence.
- Financial outputs reconcile with approved external examples.
- API, web, export, and workbook parity passes.
- Security, privacy, tenant isolation, accessibility, performance, and resilience gates pass.
- Dependency lock, software bill of materials, vulnerability report, and reproducible build evidence exist.
- Upgrade, rollback, backup, and recovery procedures are tested.
- Release status uses the Product Constitution states and contains no unsupported quality score.

## Certification rule

No person, interface, script, test summary, or audit ledger may label a result `CERTIFIED` unless the certification service has recorded successful completion of every required technical, financial, provenance, SLO, and approval gate for the exact immutable scenario.
