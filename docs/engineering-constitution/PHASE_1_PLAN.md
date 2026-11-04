# Phase 1 Plan: Canonical Foundation and Governed Contracts

- Status: `READY_FOR_IMPLEMENTATION`
- Plan date: 2026-11-04
- Baseline commit: `d21d6d4`
- Planning branch: `codex/phase-1-foundation-plan`

## Objective

Create the reproducible, typed, deterministic, fail-closed foundation on which every later calculation phase will depend. Phase 1 replaces implicit defaults and mixed architectural boundaries with one canonical package, immutable governed records, explicit policy resolution, stable result states, canonical serialization, and replayable scenario snapshots.

Phase 1 does not claim that capacity, TCO, unit economics, pricing, or deployment comparison is implemented. Unsupported calculations remain unavailable until their owning phases provide approved formulas, tests, and evidence.

## Required outcome

At Phase 1 completion, the repository must provide:

1. A reproducible Python package and dependency lock.
2. One canonical package rooted at `src/pocgpu`.
3. A domain that has no framework, file system, network, environment, clock, randomness, vendor, or adapter dependency.
4. Strict immutable value objects for identifiers, decimals, quantities, money, time, provenance, versions, and content hashes.
5. Governed organization, policy, scenario, snapshot, issue, and result-state contracts.
6. Explicit policy resolution with no implicit global precedence or hidden fallback.
7. Canonical serialization and deterministic snapshot hashing.
8. Ports for time, identity, units, governed records, scenarios, snapshots, and audit integrity.
9. In-memory reference adapters and contract tests for every Phase 1 port.
10. Versioned boundary schemas generated from one contract definition and verified against domain mappings.
11. Migration evidence for legacy calculators before their executable paths are removed or quarantined from distribution.
12. Removal of external-model planning and self-certification artifacts from the product path.
13. English-only executable source with no remaining Phase 0 language ratchet.
14. Evidence-based repository status with no unsupported production-readiness claim.

## Scope

### In scope

- Package, build, lock, test, lint, type-check, coverage, property-test, mutation-test, and clean-build configuration.
- Canonical package dependency boundaries and a composition root.
- Stable technical errors with codes, paths, structured parameters, and localization keys.
- Strict decimal parsing that rejects binary floating-point values, booleans, non-finite values, and ambiguous strings.
- Data-driven unit definitions and dimension-safe quantities.
- Currency identity, money, FX observations, and preservation of original monetary values.
- UTC instants, validity intervals, explicit time windows, and injected clocks.
- Evidence classification and complete provenance metadata.
- Tenant and organization identity without organization-size or vertical branches.
- Versioned policy packs and explicit resolution plans.
- Immutable scenario drafts, accepted assumptions, evidence references, snapshots, issues, and canonical result envelopes.
- Result-state invariants for `DRAFT`, `INPUT_REQUIRED`, `BENCHMARK_REQUIRED`, `POLICY_REQUIRED`, `ASSUMPTION_BASED`, `VALID`, `CERTIFIED`, `REJECTED`, and `STALE`.
- Canonical JSON serialization and SHA-256 content identity.
- Legacy component inventory, representative migration fixtures, and disposition records.
- Source-language and architectural fitness gates.

### Explicitly out of scope

- Useful-capacity and Serving Unit formulas, which belong to Phase 2.
- Fully loaded TCO and accounting calculations, which belong to Phase 3.
- Unit economics and pricing formulas, which belong to Phase 4.
- API comparison, break-even, and hybrid-cost formulas, which belong to Phase 5.
- Production catalogs and benchmark ingestion.
- Web, API, command-line, workbook, or localized presentation interfaces.
- Database, cloud-provider, ERP, invoice, or telemetry production adapters.
- Production authentication, authorization, deployment, and tenant administration.
- Product certification. Phase 1 defines certification contracts and invariants but cannot certify a financial or capacity result.

## Baseline findings that drive the design

- `src/application/finops_advisor_service.py` imports concrete adapters, reads files, constructs services, resolves policies, applies business fallbacks, calculates outputs, localizes responses, and writes audit records in one class.
- Required governed inputs are frequently read with fallback values, including currency, facility, workload, allocation, accounting, and policy values.
- The existing money type quantizes during construction with an embedded precision instead of preserving the original governed amount until a declared rounding boundary.
- The current domain combines theoretical roofline outputs, risk, TCO, questionnaires, catalogs, and certification contracts that have different owning phases.
- The repository has no canonical build metadata or dependency lock.
- Multiple calculator paths and generated authority claims remain executable or prominent.
- Thirteen exact source or manifest files remain under the Phase 0 language ratchet.

These findings are migration inputs. They do not define the new contracts.

## Architectural decisions

Phase 1 implementation is governed by:

- ADR-0001 through ADR-0005 from Phase 0.
- ADR-0006 for the canonical package and composition boundary.
- ADR-0007 for immutable governed records.
- ADR-0008 for explicit policy resolution.
- ADR-0009 for canonical serialization and snapshot identity.
- ADR-0010 for evidence-first legacy removal.

## Target repository structure

```text
pyproject.toml
uv.lock
.python-version
schemas/
  v1/
    canonical-result.schema.json
    governed-record.schema.json
    organization-profile.schema.json
    policy-pack.schema.json
    scenario.schema.json
src/
  pocgpu/
    __init__.py
    composition.py
    contracts/
      __init__.py
      v1.py
      schema_export.py
    domain/
      __init__.py
      errors.py
      identifiers.py
      numeric.py
      quantities.py
      money.py
      time.py
      provenance.py
      organizations.py
      policies.py
      scenarios.py
      results.py
      snapshots.py
      serialization.py
      ports/
        clock.py
        identity.py
        records.py
        scenarios.py
        snapshots.py
        units.py
        audit.py
    application/
      __init__.py
      policy_resolution.py
      scenario_evaluation.py
      snapshot_service.py
    adapters/
      __init__.py
      in_memory.py
tests/
  architecture/
  contracts/
  domain/
  property/
  integration/
  migration/
  governance/
```

The implementation may split a listed module when complexity limits require it. It may not merge domain, application, adapter, contract, or composition responsibilities.

## Dependency rules

The allowed dependency direction is:

```text
composition -> adapters + application + domain
adapters -> domain ports + domain contracts
application -> domain contracts + domain ports
contracts -> domain mapping boundary
domain -> Python standard library only
```

The following imports are prohibited:

- Domain importing application, adapters, contracts, composition, file system, network, process environment, localization, or vendor libraries.
- Application importing concrete adapters.
- Contracts or interfaces invoking calculation services.
- Any canonical module importing a legacy calculator.
- Any interface or adapter constructing business defaults.

Only `composition.py` may select concrete adapters. Selection inputs are explicit configuration references, never governed business values.

## Build and dependency contract

- Use PEP 621 metadata in `pyproject.toml` and a standard `src` package layout.
- Declare `requires-python = ">=3.12,<3.14"`, use Python 3.12.14 for reproducible Phase 1 evidence, and run the compatibility suite on the latest available Python 3.12 and 3.13 patch releases.
- Use Hatchling only as the build backend and isolate Pydantic to strict versioned boundary contracts; neither dependency may enter the domain.
- Use `uv.lock` as the exact cross-platform dependency lock and require frozen synchronization in CI.
- Use uv 0.13.4 for Phase 1 lock and clean-build evidence.
- Keep the domain standard-library-only.
- Limit the initial development toolchain to pytest, pytest-cov, Hypothesis, mypy, Ruff, mutmut, and pip-audit. Every direct and transitive dependency must be declared or locked.
- Configure strict static typing, deterministic formatting, linting, branch coverage, property testing, and mutation testing in versioned project configuration.
- Build both source and wheel artifacts in a clean temporary environment and install the wheel before the clean-environment test suite.
- Fail if lock metadata and declared dependencies diverge.

Dependency versions are build configuration, not business policy. Exact versions belong in the lock, never in domain code.

## Domain contracts

### Identifiers and versions

Opaque identifiers are validated technical values. They never encode organization size, vertical, vendor, geography, language, or deployment decisions. Their protocol form is one to 128 ASCII characters from letters, digits, dot, underscore, colon, and hyphen, beginning with a letter or digit. The length limit is a named input-security constant.

The foundation defines distinct types for tenant, organization, record, policy pack, scenario, snapshot, formula, schema, and engine identifiers. Schema, engine, and formula versions use Semantic Versioning 2.0.0. Record revisions are positive integers scoped to a stable record identifier. Identifier generation enters through an `IdentityProvider` port; the domain never reads randomness or a system clock.

### Decimal values and rounding

- Governed numeric values enter as `Decimal` or canonical decimal strings.
- `float`, `bool`, NaN, infinity, locale-formatted text, and implicit coercion are rejected.
- Construction preserves the exact finite decimal value.
- Rounding requires an explicit policy containing scale and rounding mode.
- Rounding never occurs merely because a value object was constructed.
- Ratio bounds belong to the consuming contract and are not applied globally.

### Quantities and units

- A quantity contains an exact decimal magnitude, unit identifier, and dimension identifier.
- Unit definitions are versioned governed data resolved through a `UnitRegistry` port.
- Unit conversion requires compatible dimensions and an explicit versioned conversion definition.
- Exact mathematical conversions may be named universal constants with rationale and tests.
- A missing unit, unknown unit, dimension mismatch, or incompatible time basis fails before calculation.
- Rates identify numerator, denominator, and time window; monthly, annual, hourly, and instantaneous values are never interchangeable.

### Money and FX

- Money contains an exact amount and validated ISO 4217 currency identity.
- Currency identity validation does not invent support, exchange rates, precision, or rounding rules.
- An FX observation contains base currency, quote currency, exact rate, provider reference, observation time, validity, and provenance.
- Conversion produces a record containing both original and converted money plus the FX observation identifier.
- Original money is immutable and is never overwritten by a converted value.

### Time and validity

- Machine timestamps are timezone-aware UTC instants.
- Validity intervals define inclusive start and exclusive end semantics.
- Time windows carry explicit start, end, and aggregation meaning.
- Current time is supplied through a `Clock` port and captured before domain evaluation.
- Staleness is evaluated against the captured instant and preserved in the result evidence.

### Provenance

Every governed record must carry applicable metadata from the Data Governance Policy. The contract distinguishes:

- `INVOICE`
- `MEASURED`
- `CONFIGURED`
- `ASSUMED`
- `DERIVED`

Conditional invariants include:

- `DERIVED` requires formula identity and source-record references.
- `ASSUMED` requires explicit acceptance, owner, scope, and acceptance time.
- `INVOICE` and `MEASURED` require a source reference and observation time.
- Critical stale evidence cannot support `VALID` or `CERTIFIED`.
- Supersession creates a new record and never mutates the prior record.
- Integrity hashes prove byte-level snapshot integrity, not factual correctness.

### Organization profiles

An organization profile identifies tenant scope, organization identity, policy references, locale preferences, jurisdictions, and evidence ownership. Organization size, vertical, regulated status, provider preference, and geography remain governed data identifiers. No source branch may compare their concrete values.

The reference scenario matrix will use data fixtures representing different scales and contexts. Fixture names and values are test data, not production defaults.

### Policy packs and resolution

A policy pack is immutable, versioned, tenant-scoped governed data. It contains typed settings and declares the packs it intentionally supersedes.

Policy settings use a closed canonical value union: null, boolean, integer, decimal string, text, identifier, quantity, money, instant, or recursively typed immutable lists and objects tied to a schema identifier. Arbitrary Python objects, executable expressions, callbacks, and untyped dynamic values are prohibited.

A `PolicyResolutionPlan` explicitly lists applicable pack references and their permitted override relationships. Resolution follows these rules:

1. Validate identity, tenant, version, approval, and validity for every pack.
2. Reject missing referenced packs.
3. Reject cycles in override relationships.
4. Reject conflicting values unless one pack explicitly supersedes the other for that setting.
5. Preserve every selected and rejected source in the resolution evidence.
6. Produce `POLICY_REQUIRED` when a mandatory setting is absent or unresolved.

Input order, dictionary order, organization name, vertical identifier, and a built-in global precedence never resolve a conflict.

### Scenarios, assumptions, and snapshots

- A scenario draft contains explicit input records, requested output domains, policy references, evidence references, and accepted assumptions.
- A missing mandatory reference remains missing; it never becomes zero, an empty record, or a selected catalog item.
- Updating a scenario produces a new version.
- Evaluation first resolves every referenced immutable record, then creates a snapshot, then invokes available services.
- A snapshot contains canonical copies or immutable content-addressed references sufficient for replay.
- Unsupported requested output domains produce a structured issue and cannot be presented as calculated.

### Issues and result states

A domain issue contains a stable code, severity, field or record path, structured parameters, and localization key. It does not contain a user-facing fallback sentence.

State derivation is deterministic and ordered by explicit rules:

1. Invalid or failed mandatory controls produce `REJECTED`.
2. Expired critical evidence produces `STALE`.
3. Missing factual or configured inputs produce `INPUT_REQUIRED`.
4. Missing policy decisions produce `POLICY_REQUIRED`.
5. Missing compatible benchmark evidence for a requested capacity claim produces `BENCHMARK_REQUIRED`.
6. Completed calculations containing accepted assumptions produce `ASSUMPTION_BASED` unless a later certification policy explicitly permits the assumption class.
7. Completed calculations with valid evidence produce `VALID`.
8. `CERTIFIED` requires a prior valid result and successful evidence from every mandatory certification gate.
9. A scenario that has not requested evaluation remains `DRAFT`.

Phase 1 tests the state machinery and the impossibility of invalid certification. It does not create passing capacity or financial certification evidence.

## Canonical serialization and hashing

Canonical serialization is a protocol contract:

- UTF-8 JSON.
- Unicode strings normalized to NFC.
- Object keys sorted lexicographically.
- No insignificant whitespace.
- Exact decimals serialized in non-exponent fixed-point form, with insignificant trailing fractional zeros removed and every signed zero represented as `0`. Reported precision is separate metadata when it is evidence-bearing.
- UTC instants serialized with an explicit `Z` suffix.
- Enums and identifiers serialized as stable strings.
- Ordered collections preserve declared semantic order.
- Unordered collections are normalized by their stable identity before serialization.
- Binary floating-point values, non-finite values, arbitrary objects, and unknown fields are rejected.
- The schema identifier and schema version are part of the serialized document.
- Snapshot identity is lowercase SHA-256 over the canonical UTF-8 bytes.

UTC timestamps use RFC 3339 form. Fractional seconds are omitted when zero and otherwise have trailing zeros removed. JSON object keys are NFC-normalized strings and sorted by Unicode code point. Serialization uses Unicode characters directly rather than environment-dependent ASCII escaping.

Serialization and replay tests must run in separate processes and under reordered input mappings. Equal semantic inputs must produce identical bytes and hashes. A content hash never changes a result state or implies certification.

## Boundary schema strategy

- Boundary contracts are versioned independently from internal domain classes.
- Strict boundary models accept governed decimals as strings and reject unknown fields.
- JSON Schema files are generated deterministically from the versioned boundary models.
- CI fails if checked-in schemas differ from clean regeneration.
- Mapping tests cover every boundary field, enum member, required field, and error code.
- Schema evolution requires compatibility fixtures and an explicit migration path.

## Port and adapter contracts

Phase 1 defines ports for:

- Captured time.
- Generated identity.
- Versioned unit definitions.
- Governed record retrieval.
- Organization and policy retrieval.
- Scenario storage.
- Snapshot storage.
- Audit integrity append and verification.

Reference in-memory adapters exist only to prove contracts and deterministic orchestration. They accept explicit records and have no embedded organizations, policies, prices, units, currencies, timestamps, or defaults. Production persistence and provider adapters remain out of scope.

## No-hardcoding and language controls

Automated gates must reject:

- Governed numeric defaults in constructors, DTOs, adapters, or application services.
- Required-field parsing through fallback operators.
- Organization, vertical, jurisdiction, provider, model, region, locale, or currency branches in the domain or application layer.
- User-facing strings outside declared language resources.
- Non-English identifiers, comments, docstrings, technical logs, schemas, tests, and migration scripts.
- Numeric literals in governed domain modules outside named mathematical, protocol, schema, or security constants.
- Direct time, randomness, environment, file, or network access from the domain.
- Application imports of concrete adapters.
- Shared mutable global state.

Language detection vocabulary, when needed for a lexical gate, is non-executable versioned language data. It cannot be embedded in Python source and cannot affect product calculations.

## Migration plan

### Evidence before removal

Before changing or deleting a legacy execution path:

1. Record the exact source commit.
2. Capture representative inputs and serialized outputs as migration fixtures.
3. Record which outputs are preserved, intentionally corrected, deferred to a later phase, or rejected as unsupported.
4. Verify that fixtures contain no credentials, prompts, personal data, or customer-confidential content.
5. Link every intentional correction to a requirement and risk.

Legacy output is evidence of prior behavior, not a golden expected result. Known defects must not be preserved for parity.

### Legacy engine disposition

- Preserve representative behavior from `scripts/finops_calculator.py`, `scripts/finops_tier1_engine.py`, and the current `src` application in migration fixtures.
- Remove the old modules from the distributed package after the fixtures and disposition records exist.
- Prevent all canonical modules, tests, and composition code from importing legacy implementations.
- Keep calculation corrections deferred to their owning phases rather than implementing substitute formulas in Phase 1.
- Mark current catalogs as unverified migration inputs; the canonical foundation must not load them as governed facts.

### External-model artifact removal

Remove the Argon planning, synthesis, audit, RFC, and self-certification artifacts from the product path. Git history preserves their historical content. Repository-owned plans, tests, ADRs, manifests, and completion evidence replace their authority claims.

### Language-ratchet closure

- Remediate or remove every exact file in the Phase 0 legacy language ratchet.
- Move user-facing localized text to declared locale resources with stable keys.
- Keep operational manifests and technical log events in English.
- Replace the legacy source-language test with an English implementation and external versioned language data where lexical detection is required.
- Set `governance_phase` to `1` only when the ratchet list is empty and every language gate passes.
- Rebaselining a changed legacy hash is prohibited.

### Documentation status

- Rewrite the primary repository documentation as evidence-based English technical documentation.
- Preserve Spanish as a supported localized documentation output, clearly separated from canonical technical authority.
- Remove quality scores, production-ready labels, and certification claims not backed by the current completion evidence.

## Delivery increments

Each increment starts by adding or updating the tests named below. Production implementation follows only after those tests fail for the intended missing behavior.

### Increment 1A: Reproducible toolchain

Deliver `pyproject.toml`, `uv.lock`, Python version metadata, strict type and lint configuration, build configuration, and frozen CI setup.

Tests and evidence:

- Lock consistency.
- Clean source and wheel build.
- Wheel installation in a new environment.
- Test discovery from the installed package.
- No undeclared runtime import.

### Increment 1B: Migration evidence and package boundary

Capture legacy scenarios and dispositions, create `src/pocgpu`, establish the composition root, and add dependency-direction tests.

Tests and evidence:

- Canonical package imports without repository-relative paths.
- Domain and application import graph gates.
- No canonical import of legacy modules.
- Exactly one canonical scenario-evaluation entry point.
- Migration fixtures reproduce the recorded legacy bytes without asserting their correctness.

### Increment 1C: Primitive value contracts

Implement identifiers, versions, strict decimals, explicit rounding, quantities, unit definitions, money, FX observations, instants, validity intervals, and time windows.

Tests and evidence:

- Boundary tests for zero, sign, scale, non-finite values, bool, float, malformed text, and extreme valid decimals.
- Dimension and time-basis mismatch tests.
- Currency mismatch and original-value preservation tests.
- Property tests for exact round trips and compatible conversions.
- Mutation score with no unreviewed surviving invariant mutation.

### Increment 1D: Provenance and governed records

Implement evidence classes, ownership, source references, validity, approval, supersession, assumption acceptance, and derived-record lineage.

Tests and evidence:

- Schema completeness matrix for each evidence class.
- Stale-boundary tests at just before, exactly at, and just after validity end.
- Immutability and supersession tests.
- Missing metadata and incompatible evidence negative tests.

### Increment 1E: Organizations and policies

Implement tenant-scoped organization profiles, policy packs, resolution plans, explicit overrides, and conflict evidence.

Tests and evidence:

- Organization profiles for different scales and vertical data with identical code paths.
- Reordered input invariance.
- Missing pack, tenant mismatch, invalid version, stale pack, conflict, cycle, and unauthorized override tests.
- Static scan for contextual identifier branches.

### Increment 1F: Scenarios, issues, and result states

Implement immutable scenario drafts and versions, accepted assumptions, requested domains, structured issues, result envelopes, and state derivation.

Tests and evidence:

- Complete transition and precedence table.
- Every unresolved state has positive and negative cases.
- `CERTIFIED` construction fails without complete mandatory gate evidence.
- Unsupported calculation domains never produce calculated numeric outputs.
- No missing input is converted to zero or an empty record.

### Increment 1G: Canonical snapshots and replay

Implement canonical serialization, snapshot hashing, replay validation, and content-addressed references.

Tests and evidence:

- Golden canonical bytes produced independently from the serializer implementation.
- Mapping-order, process, and repeated-run determinism.
- Unicode normalization, decimal string, UTC timestamp, unknown-field, and float rejection tests.
- Tamper detection and explicit proof that valid integrity does not change correctness state.

### Increment 1H: Ports, reference adapters, and schemas

Implement ports, in-memory contract adapters, strict boundary models, schema export, and mapping parity.

Tests and evidence:

- Shared contract suite executed against every reference adapter.
- Alternate adapter test for each port.
- Clean schema regeneration.
- Unknown-field and missing-field schema tests.
- Tenant-isolation and immutable-version tests.

### Increment 1I: Legacy closure and phase evidence

Remove or remediate external-model artifacts, duplicate executable paths, language-ratchet files, misleading claims, and obsolete tests. Activate governance Phase 1 and publish the completion report.

Tests and evidence:

- Empty legacy language ratchet.
- No external-model artifact in the product path.
- No duplicate engine import or executable entry point.
- Full clean-environment suite with no failure, skip, expected failure, retry, or warning.
- Coverage, mutation, property, architecture, schema, build, replay, language, secret, and governance reports.

## Requirements traceability

| Requirement | Phase 1 disposition | Primary evidence |
|---|---|---|
| PRD-001 | Complete organization-profile contract without organization branches. | Organization matrix and branch scan. |
| PRD-002 | Complete declarative policy-pack and resolution foundation. | Policy contract and conflict tests. |
| PRD-003 | Establish representative scale matrix; calculation evidence remains later-phase. | Data-driven organization fixtures. |
| PRD-004 | Complete result-state and certification-construction invariants. | State table and negative certification tests. |
| PRD-006 | Establish separate typed output-domain requests and result sections. | Result schema and dependency tests. |
| DAT-001 | Complete governed metadata contract. | Evidence-class schema matrix. |
| DAT-002 | Complete evidence classification. | Enum and conditional invariant tests. |
| DAT-003 | Complete immutable snapshots and replay identity. | Cross-process replay tests. |
| DAT-004 | Complete foundational validity and dimension rejection. | Boundary, stale, and mismatch tests. |
| DAT-005 | Complete fail-closed missing-data behavior. | Missing-field and no-fallback gates. |
| ARC-001 | Establish one canonical package and evaluation boundary. | Repository engine inventory gate. |
| ARC-002 | Complete domain dependency isolation. | AST and import-graph tests. |
| ARC-003 | Complete Phase 1 ports and alternate reference adapters. | Shared adapter contract suite. |
| ARC-004 | Complete deterministic foundation and serialization. | Repeatability and canonical-byte tests. |
| ARC-005 | Complete strict quantity and currency types. | Runtime, type, and property tests. |
| ARC-006 | Complete immutability and global-state prohibition. | Static and mutation tests. |
| I18N-001 | Complete English-only canonical source gate. | Source-language and schema scans. |
| QLT-001 | Tests precede every increment. | Commit and change evidence. |
| QLT-002 | Full statement and branch coverage for Phase 1 domain. | Coverage report. |
| QLT-003 | Apply property, metamorphic, boundary, mutation, fuzz, and golden tests to Phase 1. | Test inventory and reports. |
| QLT-005 | Block incomplete mandatory tests. | CI result and collection audit. |
| SEC-001 | Exclude credentials and confidential content from scenario contracts and fixtures. | Schema allowlist, secret scan, fixture review. |
| SEC-002 | Separate integrity evidence from correctness and certification. | Tamper and state-independence tests. |
| MIG-001 | Capture and isolate legacy engines; retire executable duplicates after evidence. | Migration inventory and import gate. |
| MIG-002 | Remove external-model planning and authority artifacts. | Repository inventory gate. |
| MIG-003 | Close the Phase 0 language ratchet. | Empty ratchet and source scan. |
| MIG-004 | Replace unsupported readiness claims. | Documentation claim scan. |
| MIG-005 | Complete reproducible build and dependency lock. | Frozen clean build. |

## Risk controls

| Risk | Preventive control | Detection evidence |
|---|---|---|
| RSK-003 | Required fields have no defaults or fallback parsing. | Missing-data matrix and fallback AST scan. |
| RSK-007 | Typed dimensions, units, rates, and time windows. | Property, fuzz, and mismatch tests. |
| RSK-008 | Immutable original money and governed FX observations. | Currency round-trip and staleness tests. |
| RSK-014 | Context variation only through policy and data. | Identifier-branch scan and scenario matrix. |
| RSK-016 | Single packaged evaluation boundary and legacy import prohibition. | Engine inventory and dependency tests. |
| RSK-017 | Immutable versions and content-addressed snapshots. | Catalog-change replay test. |
| RSK-018 | Independently authored canonical-byte fixtures and mutation tests. | Golden provenance and mutation report. |
| RSK-019 | Integrity fields cannot produce a valid or certified state. | State-independence negative tests. |
| RSK-020 | No governed defaults; assumptions require acceptance records. | DTO scan and assumption tests. |
| RSK-022 | Immutable schema and engine versions in results. | Replay and compatibility tests. |
| RSK-023 | Aggregated allowlisted scenario fields and reviewed fixtures. | Secret scan and schema rejection tests. |
| RSK-025 | One canonical serialization protocol with cross-process tests. | Canonical bytes and hash golden cases. |
| RSK-026 | Explicit override graph and conflict rejection. | Reordering, conflict, and cycle tests. |
| RSK-027 | Migration fixtures and dispositions precede removal. | Migration inventory gate. |
| RSK-028 | Strict decimal-string boundary and typed unit mapping. | Float, bool, implicit-unit, and malformed-input tests. |
| RSK-029 | Tenant identity on governed records and repositories. | Cross-tenant negative contract tests. |
| RSK-030 | Frozen lock, clean build, and wheel-install tests. | Lock drift and undeclared-import tests. |
| RSK-031 | Hash rebaselining prohibited; Phase 1 requires an empty ratchet. | Governance manifest validation. |

No critical Phase 1 risk lacks both a preventive and a detection control.

## Mandatory test inventory

Before Phase 1 completion, the suite must contain:

- Manifest and schema contract tests.
- Architecture and dependency-direction tests.
- English-only source and user-facing literal tests.
- No-hardcoding and no-fallback static tests.
- Strict decimal, money, quantity, unit, rate, and time boundary tests.
- Provenance conditional-invariant tests.
- Organization and policy resolution property tests.
- Scenario state precedence and certification negative tests.
- Canonical serialization golden and metamorphic tests.
- Snapshot replay and tamper tests.
- Port contract tests with alternate adapters.
- Tenant-isolation and confidential-field rejection tests.
- Legacy migration inventory and repository-claim tests.
- Clean build, installed-wheel, lock consistency, coverage, and mutation gates.

Test fixtures must identify whether they are synthetic, legacy-captured, or independently derived. No production catalog value becomes a test oracle merely because it already exists in the repository.

## Implementation gate order

Every increment runs gates in this order:

1. Manifest and schema validation.
2. Formatter and linter check.
3. Strict static typing.
4. Architecture, language, hardcoding, and secret scans.
5. Unit and boundary tests.
6. Property and metamorphic tests.
7. Mutation tests for changed domain modules.
8. Adapter contracts and integration tests.
9. Canonical golden and replay tests.
10. Branch and statement coverage.
11. Frozen clean build and installed-wheel tests.

Later gates do not convert an earlier failure into success.

## Acceptance criteria

Phase 1 is complete only when all conditions below are true:

- Every in-scope requirement has implementation, tests, and completion evidence.
- All Phase 1 ADRs are accepted and reflected in code.
- The canonical package has one composition root and one scenario-evaluation boundary.
- Domain and application dependency rules pass.
- All governed numeric inputs reject float and implicit units.
- No required governed field has a source-code or parsing fallback.
- Organization and policy variation is data-driven and conflict-safe.
- All governed records are immutable, versioned, tenant-scoped where applicable, and provenance-complete.
- Scenario snapshots serialize and hash identically across processes and mapping order.
- Result states follow the declared precedence and invalid certification is unconstructable.
- Boundary schemas regenerate cleanly and reject unknown fields.
- Legacy behavior is captured and classified before executable removal.
- The Phase 0 language ratchet is empty and `governance_phase` is `1`.
- External-model planning, synthesis, audit, and authority artifacts are absent from the product path.
- Documentation contains no unsupported production-ready, certified, or quality-score claim.
- The source and wheel build reproducibly from the frozen lock in a clean environment.
- Mandatory gates contain no failure, skip, expected failure, flaky retry, or unexplained warning.
- The Phase 1 domain has full statement and branch coverage.
- Mutation testing has no unreviewed surviving domain mutation.
- A Phase 1 completion report records commands, tool versions, counts, evidence, corrections, and limitations.

## Stop conditions

Implementation must stop and return to planning if:

- A domain contract requires a hidden default to remain compatible.
- A legacy output cannot be classified as preserved, corrected, deferred, or rejected.
- A critical risk loses either its preventive or detection control.
- A dependency would enter the domain layer.
- Canonical serialization cannot be specified independently from its implementation.
- A calculation formula is required before its owning phase has an approved plan and evidence contract.
- A source-language exception would need to be extended or rebaselined.

## Completion report requirements

The Phase 1 completion report must include:

- Final commit and clean-tree evidence.
- Package, Python, and tool versions.
- Requirement and risk status.
- File and migration disposition inventory.
- Test counts by class.
- Coverage and mutation results.
- Static typing, lint, architecture, language, schema, and secret-scan results.
- Clean-build and installed-wheel evidence.
- Snapshot reproducibility evidence.
- Intentional corrections and deferred formulas.
- Known limitations that do not contradict the completion claim.
