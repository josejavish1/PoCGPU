# Requirements Traceability Matrix

## Requirement categories

- `PRD`: product behavior.
- `CAL`: calculation behavior.
- `DAT`: data and provenance.
- `ARC`: architecture.
- `I18N`: internationalization.
- `QLT`: quality and verification.
- `SEC`: security and auditability.
- `MIG`: migration.

## Normative requirements

| ID | Requirement | Planned phase | Verification |
|---|---|---:|---|
| PRD-001 | Support organization profiles without organization-specific source branches. | 1 | Schema and property tests across organization profiles. |
| PRD-002 | Support vertical variation through versioned policy packs. | 1 | Policy-pack contract tests and source scan for vertical branches. |
| PRD-003 | Support medium-sized through globally distributed enterprise scenarios. | 1-7 | Reference scenario matrix. |
| PRD-004 | Expose explicit result states and block certification on unresolved critical conditions. | 1 | State-machine tests. |
| PRD-005 | Provide identical canonical results to API, web, exports, and workbook consumers. | 7 | Cross-interface parity suite. |
| PRD-006 | Separate cost, capacity, demand, utilization, price, risk, and accounting views. | 1-5 | Domain dependency and output-contract tests. |
| CAL-001 | Define Serving Units as immutable deployable configurations. | 2 | Domain validation and identity tests. |
| CAL-002 | Require compatible approved benchmarks for useful capacity. | 2 | Missing, incompatible, stale, and valid benchmark tests. |
| CAL-003 | Evaluate TTFT, TPOT, error rate, queueing, and throughput against declared SLOs. | 2 | Golden and boundary cases. |
| CAL-004 | Size independently by input throughput, output throughput, RPS, and concurrency. | 2 | Multi-constraint property tests. |
| CAL-005 | Model operational headroom, growth, maintenance, and physical high availability separately. | 2 | Failure-domain and packing tests. |
| CAL-006 | Distinguish installed, productive, resilient, sellable, stranded, and idle capacity. | 2 | Capacity reconciliation invariant. |
| CAL-007 | Calculate fully loaded TCO using an explicit cost boundary. | 3 | Cost-class reconciliation suite. |
| CAL-008 | Separate depreciation, economic capital cost, and cash flow. | 3 | Accounting-view golden cases. |
| CAL-009 | Use measured or explicitly assumed power, with PUE treatment that prevents double counting. | 3 | Dimensional and inclusion tests. |
| CAL-010 | Calculate blended unit cost for a declared workload profile. | 4 | Golden unit-economics cases. |
| CAL-011 | Calculate target price from gross margin and report markup separately. | 4 | Algebraic property tests. |
| CAL-012 | Compare private and external API cost with the same workload profile. | 5 | Workload-equivalence tests. |
| CAL-013 | Compute piecewise break-even across discrete capacity steps. | 5 | Boundary and multiple-crossing tests. |
| CAL-014 | Calculate hybrid cost as full private block cost plus external overflow cost. | 5 | Hybrid conservation tests. |
| DAT-001 | Attach source, classification, owner, unit, currency, region, version, and validity metadata to governed values. | 1 | Schema completeness tests. |
| DAT-002 | Classify values as invoice, measured, configured, assumed, or derived. | 1 | Provenance-state tests. |
| DAT-003 | Preserve immutable scenario and evidence snapshots for reproducibility. | 1 | Hash and replay tests. |
| DAT-004 | Reject incompatible, expired, or dimensionally invalid data. | 1-3 | Negative contract tests. |
| DAT-005 | Never infer missing price, benchmark, policy, or contractual data silently. | 1 | Missing-data tests. |
| ARC-001 | Maintain one canonical calculation engine. | 1 | Repository architecture test. |
| ARC-002 | Keep domain logic independent from frameworks, storage, UI, and vendors. | 1 | Import-boundary test. |
| ARC-003 | Expose external systems through ports with replaceable adapters. | 1 | Contract tests with alternate adapters. |
| ARC-004 | Make calculations deterministic for identical versioned inputs. | 1-5 | Repeatability and serialization tests. |
| ARC-005 | Use explicit quantity and currency types rather than untyped numeric values. | 1 | Type and runtime validation tests. |
| ARC-006 | Prohibit shared mutable global calculation state. | 1 | Static architecture test. |
| I18N-001 | Keep executable source, identifiers, comments, docstrings, technical logs, and schemas in English. | 1-8 | AST and lexical source gate. |
| I18N-002 | Keep user-facing text in locale packs referenced by stable keys. | 7 | Literal scan and locale-key tests. |
| I18N-003 | Support BCP 47 locales, ISO 4217 currencies, CLDR formatting, pluralization, and right-to-left presentation. | 7 | Locale compatibility matrix. |
| I18N-004 | Preserve semantic and placeholder parity across supported locale packs. | 7 | Locale schema and placeholder tests. |
| QLT-001 | Define tests before implementing every calculation branch. | 1-8 | Phase-plan and pull-request evidence. |
| QLT-002 | Achieve full statement and branch coverage for the canonical calculation core. | 1-8 | Coverage gate. |
| QLT-003 | Use property, metamorphic, boundary, mutation, fuzz, and golden-case testing. | 1-8 | Test inventory and gate reports. |
| QLT-004 | Reconcile critical formulas with independently reviewed examples and external evidence. | 2-5 | Signed calculation evidence. |
| QLT-005 | Block release for skipped, disabled, flaky, or unexplained failing mandatory tests. | 1-8 | CI policy gate. |
| QLT-006 | Produce a versioned software bill of materials and vulnerability report. | 8 | Release evidence. |
| SEC-001 | Avoid storing credentials or confidential customer data in scenarios, logs, or ledgers. | 1-8 | Secret and privacy scans. |
| SEC-002 | Record tamper-evident result provenance without treating integrity as correctness. | 1-8 | Ledger and replay tests. |
| SEC-003 | Apply least privilege and explicit authorization to external integrations. | 7-8 | Threat-model verification. |
| MIG-001 | Retire duplicate calculation engines after parity and migration evidence exists. | 1-5 | Dependency scan and archival decision. |
| MIG-002 | Remove external-model planning scripts and generated authority claims from the product path. | 1 | Repository inventory gate. |
| MIG-003 | Remove non-English executable source outside approved locale resources. | 1-7 | English-only source gate. |
| MIG-004 | Replace unproven production-readiness claims with evidence-based release status. | 1 | Documentation and release metadata review. |
| MIG-005 | Introduce a reproducible dependency and build manifest. | 1 | Clean-environment build test. |

## Traceability rule

Each implementation change must reference one or more requirement identifiers. Each requirement must map to tests and release evidence before it may be marked complete.
