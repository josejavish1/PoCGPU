# Risk Register and FMEA

## Rating definitions

- Severity: `CRITICAL`, `HIGH`, `MEDIUM`, or `LOW` impact if the failure occurs.
- Likelihood: `HIGH`, `MEDIUM`, or `LOW` before controls.
- Detection: `WEAK`, `MODERATE`, or `STRONG` ability of planned controls to detect the failure before release.

Numeric risk scores are intentionally omitted until an organization risk policy defines their scales and acceptance thresholds.

## Failure modes

| ID | Failure mode | Effect | Severity | Likelihood | Preventive control | Detection control | Owning phase |
|---|---|---|---|---|---|---|---:|
| RSK-001 | Theoretical throughput is presented as measured useful capacity. | Under-sizing, SLO failure, invalid pricing. | CRITICAL | HIGH | Benchmark-first capacity contract. | Benchmark compatibility and certification gate. | 2 |
| RSK-002 | A scenario is certified while TTFT, TPOT, queue, or error SLO fails. | Contract breach and operational failure. | CRITICAL | HIGH | SLO predicates are mandatory certification inputs. | Negative golden case and state-machine test. | 2 |
| RSK-003 | Hidden fallback replaces missing critical data. | False precision and unauditable decisions. | CRITICAL | HIGH | Fail-closed missing-data states. | Source scan and missing-data test matrix. | 1 |
| RSK-004 | Fixed private cost is scaled by traffic share in a hybrid scenario. | Material TCO understatement. | CRITICAL | HIGH | Installed-block cost model. | Conservation and golden hybrid tests. | 5 |
| RSK-005 | Risk reserve substitutes for physical high availability. | Service cannot survive declared failure. | CRITICAL | HIGH | Separate resilience topology and risk views. | Failure-domain simulation tests. | 2-3 |
| RSK-006 | Gross margin is implemented as markup. | Underpricing and margin loss. | CRITICAL | MEDIUM | Separate named formulas and types. | Algebraic property tests. | 4 |
| RSK-007 | Unit or time-window mismatch passes calculation. | Orders-of-magnitude error. | CRITICAL | MEDIUM | Typed quantities and explicit periods. | Compile/runtime dimension tests and fuzzing. | 1-5 |
| RSK-008 | Currency conversion loses source currency or uses stale FX. | Incorrect financial comparison. | HIGH | MEDIUM | Immutable FX observations and original values. | Round-trip and stale-data tests. | 1-3 |
| RSK-009 | PUE, cooling, energy, or colocation is counted twice. | TCO overstatement. | HIGH | HIGH | Cost-boundary inclusion metadata. | Cost-class reconciliation tests. | 3 |
| RSK-010 | TDP is used as average measured power without disclosure. | Energy and facility distortion. | HIGH | HIGH | Power evidence class and scenario status. | Provenance gate and meter reconciliation. | 3 |
| RSK-011 | Benchmark identity does not match runtime configuration. | Invalid capacity claim. | CRITICAL | MEDIUM | Serving Unit fingerprint and compatibility rules. | Compatibility negative tests. | 2 |
| RSK-012 | Benchmark selection favors a faster but SLO-incompatible point. | Unusable sellable capacity. | CRITICAL | MEDIUM | Useful-capacity predicate. | Ordered benchmark golden cases. | 2 |
| RSK-013 | Capacity packing counts unusable or stranded accelerators. | Cost and capacity mismatch. | HIGH | MEDIUM | Explicit allocation and packing model. | Capacity reconciliation invariant. | 2 |
| RSK-014 | Vertical-specific behavior enters source code. | Forks, inconsistent behavior, global scaling failure. | HIGH | HIGH | Declarative policy packs. | AST and identifier branch scan. | 1-8 |
| RSK-015 | Localized text changes calculation semantics. | Locale-dependent results. | CRITICAL | LOW | Localization boundary. | Cross-locale parity tests. | 7 |
| RSK-016 | Duplicate engines diverge. | Conflicting decisions across interfaces. | CRITICAL | HIGH | Single canonical engine. | Repository dependency and parity gates. | 1-7 |
| RSK-017 | Catalog updates change prior certified scenarios. | Loss of reproducibility. | HIGH | MEDIUM | Immutable evidence snapshots. | Replay tests. | 1 |
| RSK-018 | Tests mirror implementation defects. | False confidence. | HIGH | HIGH | Independent golden cases and mutation testing. | External reconciliation review. | 1-8 |
| RSK-019 | Audit integrity is treated as calculation correctness. | Incorrect result appears trusted. | HIGH | MEDIUM | Separate integrity and certification states. | Output-contract and UI tests. | 1-7 |
| RSK-020 | User-facing defaults appear as organization facts. | Unaccepted assumptions drive decisions. | HIGH | HIGH | Templates labeled as assumptions. | DTO and UI hardcoding scan. | 1-7 |
| RSK-021 | Spreadsheet interface reimplements formulas. | Workbook and API divergence. | CRITICAL | MEDIUM | Canonical result export architecture. | Cross-interface parity suite. | 7 |
| RSK-022 | Formula change silently alters historical meaning. | Invalid comparisons and audit history. | HIGH | MEDIUM | Immutable formula versions. | Replay and migration tests. | 1-8 |
| RSK-023 | Confidential prompts, credentials, or contracts enter logs. | Security and privacy incident. | CRITICAL | MEDIUM | Aggregated data contracts and secret boundaries. | Secret, privacy, and log scans. | 1-8 |
| RSK-024 | Unsupported locale, number format, or right-to-left layout corrupts input or output. | Wrong values or unusable interface. | HIGH | MEDIUM | Canonical parsing and locale boundary. | Locale compatibility matrix. | 7 |
| RSK-025 | Snapshot serialization changes with process, mapping order, Unicode form, or environment. | Replay identity and audit evidence become unreliable. | CRITICAL | MEDIUM | Versioned canonical serialization protocol. | Independent golden bytes and cross-process metamorphic tests. | 1 |
| RSK-026 | Policy conflict is resolved by incidental input order or a built-in contextual precedence. | Wrong organization or jurisdiction policy silently controls a decision. | CRITICAL | HIGH | Explicit versioned resolution plans and override relationships. | Reordering, conflict, and cycle tests. | 1 |
| RSK-027 | A legacy engine is removed before representative behavior and known defects are classified. | Migration evidence is lost and corrections cannot be reviewed. | HIGH | MEDIUM | Evidence-first legacy disposition workflow. | Migration inventory and fixture gate. | 1 |
| RSK-028 | A public contract accepts binary float, implicit unit, or ambiguous numeric text. | Precision or dimensional error enters every later formula. | CRITICAL | MEDIUM | Strict decimal-string and typed-unit boundary. | Boundary, property, and malformed-input tests. | 1 |
| RSK-029 | A governed record or repository lookup crosses tenant scope. | Confidentiality breach and incorrect scenario evidence. | CRITICAL | MEDIUM | Tenant identity on governed records and repository contracts. | Cross-tenant negative contract tests. | 1 |
| RSK-030 | Dependency lock, build metadata, and installed artifact resolve different code or dependencies. | Tests cannot reproduce the delivered product. | HIGH | MEDIUM | Frozen lock and installed-wheel test path. | Lock drift, clean build, and undeclared-import gates. | 1 |
| RSK-031 | A legacy language exception is rebaselined instead of remediated. | Non-English executable debt becomes permanent or expands silently. | HIGH | MEDIUM | Phase 1 requires an empty expiring ratchet. | Hash-ratchet and source-language validation. | 1 |

## FMEA workflow

Before each implementation phase:

1. Review existing risks assigned to the phase.
2. Add phase-specific failure modes.
3. Map every critical and high risk to preventive and detection tests.
4. Reject implementation if a critical risk has no effective control.
5. Update residual risk after verification.
