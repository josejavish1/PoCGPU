# Phase 0 Plan: Engineering Constitution

## Objective

Define the normative product, calculation, data, architecture, internationalization, migration, and quality rules that all later implementation phases must satisfy.

## Scope

Phase 0 produces design artifacts and dependency-free governance enforcement. It does not change calculation engines, interfaces, catalogs, deployment manifests, or runtime behavior.

## Inputs

- The current repository at the audited `origin/main` baseline.
- The calculator audit dated 2026-11-04.
- The requirement to support organizations of different sizes, industries, regions, currencies, languages, deployment models, and maturity levels.
- The requirement for English-only source artifacts and externally managed localization.
- The requirement for benchmark-first capacity, fully loaded TCO, pricing, API comparison, and traceable uncertainty.

## Deliverables

1. Product Constitution.
2. Domain Glossary.
3. Requirements Traceability Matrix.
4. Calculation Constitution and initial formula registry.
5. Data Governance Policy.
6. No Hardcoding Policy.
7. Internationalization Constitution.
8. Target Architecture.
9. Quality and Verification Strategy.
10. Risk Register and FMEA.
11. Migration Baseline.
12. Definition of Done.
13. Initial Architecture Decision Records.
14. Versioned governance manifest.
15. Governance validator, negative-control tests, and CI workflow.

## Explicit exclusions

- Runtime implementation.
- User interface redesign.
- Workbook generation.
- Catalog data migration.
- Benchmark ingestion.
- Formula execution.
- Cloud or cluster deployment.

## Work sequence

1. Establish product boundaries and result states.
2. Normalize domain terminology.
3. Assign stable requirement identifiers.
4. Define formula metadata and dimensional rules.
5. Define data provenance and validity rules.
6. Define prohibited hardcoding and localization boundaries.
7. Establish architectural dependency rules.
8. Establish verification and release gates.
9. Document known migration debt.
10. Record foundational architecture decisions.
11. Validate internal cross-references and language policy.
12. Automate the document, identifier, ownership, link, and source-language gates.
13. Prove the gates with positive and negative controls.

## Failure modes addressed

- Ambiguous business terms producing incompatible formulas.
- Hidden defaults presented as facts.
- Theoretical capacity presented as measured capacity.
- Mixed units, currencies, or accounting treatments.
- Vertical-specific logic embedded in the engine.
- Localized text embedded in source code.
- Divergent results across API, web, and workbook interfaces.
- Duplicate calculation engines.
- Release claims unsupported by external evidence.

## Acceptance criteria

- All Phase 0 documents exist and are linked from the index.
- Every normative requirement has a stable identifier, phase owner, and verification method.
- Every initial formula has units, preconditions, provenance expectations, and failure behavior.
- The no-hardcoding policy distinguishes universal constants from configurable business data.
- The architecture defines a single canonical engine and dependency direction.
- The quality strategy defines static, unit, property, mutation, integration, parity, and external validation gates.
- The migration baseline identifies every known legacy exception without granting permanent waivers.
- Canonical technical artifacts contain English only.
- The repository runtime behavior remains unchanged.

## Completion evidence

- Document inventory check.
- Internal link check.
- Requirement identifier uniqueness check.
- Formula identifier uniqueness check.
- English-only lexical review for Phase 0 artifacts.
- Git diff review confirming documentation and governance-tooling changes only.
