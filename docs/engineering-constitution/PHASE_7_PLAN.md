# Phase 7 Plan: Interfaces, Exports, and Internationalization

## Status

- Lifecycle state: `DRAFT FOR REVIEW`
- Implementation authority: `BLOCKED` until product, accessibility, security, semantic, and engineering reviews accept this plan.
- Owning requirements: `PRD-003`, `PRD-005`, `I18N-002` through `I18N-004`, `SEC-003`, and `QLT-001` through `QLT-005`.
- Formula ownership: interfaces consume canonical results and implement no calculation formulas.

## Objective

Deliver a versioned API, accessible web workflow, administrative CLI, machine-readable exports, and workbook output that all consume the same canonical application services and produce semantically identical results in any supported locale. The interfaces must support medium-sized through globally distributed enterprises without embedding organization, vertical, vendor, geography, currency, or language behavior in source branches.

## Entry conditions

- Phases 1-6 are complete and all regression gates pass.
- API compatibility, authentication, authorization, pagination, idempotency, and error contracts are accepted.
- Product and accessibility reviewers accept the end-to-end user journeys and information architecture.
- Source locale and at least one additional locale pack have approved key and placeholder contracts.
- Export and workbook security models are accepted.
- No critical Phase 7 risk lacks preventive and detection controls.

## Scope

- Versioned scenario, evidence-reference, evaluation, decision-analysis, certification, and replay APIs.
- Tenant-scoped authentication and authorization at every use-case boundary.
- Accessible web journeys for creating, validating, evaluating, comparing, reviewing, and exporting scenarios.
- Administrative CLI for governed import, validation, replay, and diagnostics.
- Canonical JSON and CSV exports plus a generated workbook presentation.
- Stable localization keys, versioned locale packs, BCP 47 locale negotiation, and CLDR-compatible formatting.
- ISO 4217 currency display, IANA time zones, pluralization, Unicode, pseudolocalization, and RTL layout.
- Cross-interface and cross-locale parity against canonical result hashes.
- Safe input limits, rate and resource boundaries, error mapping, and export formula-injection protection.

## Exclusions

- Interface-specific formulas, workbook-only calculations, localized canonical values, and ambiguous locale inference.
- Customer-specific UI forks or organization names in source.
- Storing prompts, credentials, contracts, or personal data in scenario or diagnostic payloads.
- Production deployment, disaster recovery, full operational observability, and release certification, which belong to Phase 8.

## Decisions required before implementation

Reviewers must accept:

1. API resource model, compatibility policy, idempotency semantics, concurrency control, and error envelope.
2. Authentication mechanism interfaces and authorization policy inputs.
3. User journeys, role capabilities, accessibility target, and browser support policy.
4. Locale negotiation, parent fallback, source locale, supported-locale release policy, and translation review roles.
5. Input parsing rules for numbers, currencies, dates, units, and time zones.
6. Export schemas, workbook structure, formula-free guarantee, signing/checksum options, and size limits.
7. Pagination, filtering, sorting, asynchronous evaluation, and cancellation semantics.
8. Retention and redaction policy for request metadata, diagnostics, and audit references.

Missing authorization or locale policy fails explicitly; an interface cannot invent a fallback display sentence or business value.

## Interface contracts

- `Scenario API`: create immutable draft/version, validate, evaluate, retrieve, and replay through application use cases.
- `Evidence API`: register references and metadata without copying confidential source content.
- `Analysis API`: request explicit variant sets and retrieve canonical decision packages.
- `Certification API`: submit approvals, evaluate gates, revoke approval, and retrieve certification evidence under authorization.
- `Export API`: produce versioned renderings from one canonical result identity.
- `ErrorEnvelope`: stable code, path, structured parameters, localization key, correlation identifier, and documentation reference.
- `LocalePack`: locale, parent, version, direction, review status, translations, plural variants, and typed placeholders.
- `ExportManifest`: source result hash, schema, renderer version, locale, generated timestamp, file checksums, and warnings.

## User experience contract

The user experience must:

1. Ask only for facts, evidence, policies, or accepted assumptions required by the selected outputs.
2. Explain every unresolved state with stable actionable issue keys.
3. Preserve source values and show assumptions, units, periods, currencies, and provenance.
4. Show capacity, cost, price, risk, accounting, and cash views separately.
5. Present scenario comparisons without hiding incompatibility or unresolved trade-offs.
6. Display certification gates and approvals without implying that audit integrity proves correctness.
7. Produce the same canonical result regardless of interface or locale.

## Internationalization contracts

- Canonical serialization remains locale-neutral.
- Input parsing requires an explicit locale when syntax is locale-dependent.
- Currency formatting never performs conversion; time-zone formatting never changes the machine timestamp.
- All supported packs preserve mandatory key and typed-placeholder parity.
- Missing mandatory translations block that locale release.
- Parent fallback is explicit, versioned, and observable; source code contains no display-text fallback.
- RTL direction affects layout only and never field meaning or result ordering.

## Security and authorization

- Every resource lookup validates tenant and subject authorization.
- Authorization decisions are explicit application inputs and auditable references.
- API bodies, query parameters, uploads, and exports have policy-driven resource limits.
- CSV and workbook cells that could trigger formulas are escaped or rejected under an explicit export policy.
- Logs use stable English event keys and exclude secrets and confidential payload content.
- Authentication adapters remain outside the domain and are replaceable.

## Planned implementation boundary

- `src/pocgpu/interfaces/api/`: transport mapping and versioned endpoints.
- `src/pocgpu/interfaces/cli/`: administrative commands using application services.
- `src/pocgpu/interfaces/export/`: canonical JSON, CSV, and workbook renderers.
- `src/pocgpu/interfaces/web/` or a separately declared web package: presentation consuming the API contract.
- `src/pocgpu/localization/`: locale contracts, negotiation, and formatting adapters.
- `locales/`: versioned locale resources only.
- `tests/phase7/`: contract, authorization, accessibility, locale, export, parity, performance, and security suites.

Framework selection is a review decision and must not move transport dependencies into domain or application calculation modules.

## Test-first verification matrix

| Area | Required evidence |
|---|---|
| API | Schema, compatibility, malformed input, idempotency, concurrency, pagination, and error contracts. |
| Authorization | Role, tenant, object, action, confused-deputy, and cross-tenant negative matrix. |
| Parity | API, web, CLI, JSON, CSV, and workbook reference the same result hash and values. |
| Localization | Key and placeholder parity, pseudolocale, non-Latin, plural, number, currency, date, time-zone, and RTL matrix. |
| Accessibility | Automated and manual keyboard, focus, semantics, contrast, zoom, screen-reader, and error-flow evidence. |
| Exports | Deterministic schemas, checksums, injection defense, large values, Unicode, and round-trip references. |
| Performance | Policy-defined payload, export, and concurrent-request budgets without changing calculations. |
| Security | Input fuzzing, resource exhaustion, secret/privacy scan, and authorization bypass tests. |
| Mutation | Interface mapping and localization logic mutations killed or adjudicated where meaningful. |

Cross-interface parity is mandatory for representative organization, vertical, currency, deployment, and locale scenarios.

## Migration and compatibility

- Existing strict contracts remain canonical; transport DTOs map explicitly and never widen governed values silently.
- API and export versions are immutable after release; breaking changes require a new version and migration guide.
- Any retained legacy UI screenshot is historical evidence only and does not define expected behavior.
- Workbook consumers receive a generated presentation with result identity, not an independent calculator.

## Delivery increments

1. Accept framework-neutral API, authorization, UX, locale, accessibility, and export decisions.
2. Implement versioned API mapping and authorization boundaries.
3. Implement CLI and canonical JSON/CSV exports.
4. Implement locale-pack validation, negotiation, formatting, pseudolocale, and RTL foundations.
5. Implement accessible web journeys against the API.
6. Implement generated workbook and export security.
7. Complete cross-interface parity, security, accessibility, performance, migration evidence, and completion report.

## Requirements traceability

- `PRD-003` maps to representative organization-size scenarios.
- `PRD-005` maps to canonical cross-interface parity.
- `I18N-002` through `I18N-004` map to locale resources, standards, and semantic parity.
- `SEC-003` maps to authorization and least-privilege integration contracts.
- `QLT-001` through `QLT-005` apply to all interface and localization paths.

## Risk controls

- `RSK-014`: no organization or vertical branches.
- `RSK-015`: cross-locale canonical parity.
- `RSK-016`: interfaces cannot implement formulas.
- `RSK-019`: certification and audit labels remain distinct.
- `RSK-020`: templates are explicit assumptions, never facts.
- `RSK-021`: workbook contains no independent formula engine.
- `RSK-023`, `RSK-024`, and `RSK-029`: privacy, locale safety, authorization, and tenant isolation.

## Acceptance criteria

- API, web, CLI, JSON, CSV, and workbook all consume canonical use cases and preserve result identity.
- No interface or export contains an independent calculation implementation.
- Representative parity scenarios match across interfaces and locales.
- Locale packs satisfy key, placeholder, plural, Unicode, formatting, pseudolocale, and RTL gates.
- Authentication and authorization negative matrices prove tenant isolation and least privilege.
- Accessibility, export injection, input fuzzing, and resource limits meet accepted policies.
- Phases 1-6 regression suites pass.
- Typing, architecture, language, schema, security, governance, and applicable mutation gates pass.
- A Phase 7 completion report records supported interfaces, locales, compatibility, evidence, and limitations.

## Stop conditions

Stop if an interface reimplements a formula, tenant authorization is uncertain, locale changes canonical values, ambiguous input can be silently interpreted, a workbook calculates independently, accessibility blockers remain, confidential content enters logs, or parity differs for the same result identity.
