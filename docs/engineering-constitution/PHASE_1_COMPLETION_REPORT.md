# Phase 1 Completion Report

## Status

Phase 1 is complete. The repository now provides one reproducible canonical foundation with governed contracts, deterministic serialization, replayable scenario snapshots, explicit policy resolution, strict boundary schemas, and no executable legacy calculator path.

The phase does not implement capacity, TCO, unit economics, pricing, break-even, or hybrid formulas. Those calculations remain unavailable until their owning phases provide approved formulas and evidence.

## Delivered foundation

- Python 3.12.14 and uv 0.13.4 project declaration with a frozen dependency lock.
- One installable `pocgpu` package and one reference composition boundary.
- Strict identifiers, decimals, rounding, time, units, quantities, money, and FX evidence.
- Immutable tenant-scoped governed records with conditional provenance rules.
- Organization profiles and versioned policy packs without contextual source branches.
- Immutable scenario drafts, explicit output domains, deterministic result states, and certification invariants.
- Canonical JSON bytes, SHA-256 content identity, snapshots, and policy-sensitive replay identity.
- Ports for clocks, identities, governed records, policies, snapshots, units, and audit integrity.
- In-memory reference adapters and a single scenario evaluation service.
- Strict Pydantic boundary contracts and five deterministic version 1 JSON Schemas.
- Captured migration evidence for three representative legacy execution paths.
- English-only canonical source, empty language ratchet, and no external-model authority artifact in the product path.

## Evidence

The final clean verification recorded:

- Full repository tests: 91 passed with warnings treated as errors.
- Phase 1 tests: 82 passed with warnings treated as errors.
- Domain statements: 665 of 665 covered.
- Domain branches: 174 of 174 covered.
- Domain statement and branch coverage: 100 percent.
- Mutation testing: 870 generated, 849 killed, and 21 equivalent survivors formally adjudicated.
- Strict typing: no issues across the canonical source and Phase 1 tests.
- Lint and formatting: passed.
- Dependency audit: no known vulnerabilities in resolvable third-party packages.
- Build: source distribution and universal wheel produced from declared sources.
- Installed-wheel smoke test: package import, version, identifier behavior, and five schema exports passed outside the repository.
- Migration fixtures: all recorded SHA-256 identities passed.
- Governance phase: 1 with an empty legacy language ratchet.

The verified toolchain was PoCGPU 0.1.0, Python 3.12.14, uv 0.13.4, Pydantic 2.14.2, pytest 9.2.0, coverage.py 7.17.2, Ruff 0.14.14, mypy 1.20.2, mutmut 3.8.1, and pip-audit 2.10.1. Mutation details are in [PHASE_1_MUTATION_REPORT.md](PHASE_1_MUTATION_REPORT.md).

## Corrections made during implementation

- Removed binary-float and hidden-default calculator paths after capturing migration evidence.
- Removed duplicate engines, obsolete tests, external-model planning artifacts, and expired language exceptions.
- Replaced embedded deployment credentials with Kubernetes Secret references and translated executable manifest content to English.
- Made policy-pack content part of snapshot identity so a policy change changes the replay hash.
- Added invariant checks for duplicate policy settings, override keys, result sections, snapshot records, and canonical object fields.
- Replaced unreachable decimal parsing branches with the strict grammar-backed parser.
- Added exact protocol fixtures and host-timezone-independent UTC normalization tests.
- Replaced unsupported readiness claims in the primary README with evidence-based phase status.

## Acceptance review

- Canonical package and single evaluation boundary: passed.
- Domain and application dependency direction: passed.
- Strict numeric, unit, currency, time, and provenance contracts: passed.
- Missing input and unsupported output fail closed: passed.
- Data-driven organization and policy variation: passed.
- Immutable scenario and policy-sensitive snapshot identity: passed.
- Deterministic schemas and serialization: passed.
- Result-state and certification construction invariants: passed.
- Source language, no-hardcoding, confidential-field, and context-branch gates: passed.
- Legacy evidence captured before executable removal: passed.
- Frozen lock, clean build, installed wheel, and vulnerability audit: passed.
- Full statement and branch coverage: passed.
- Mutation survivors killed or formally adjudicated: passed.
- No mandatory skip, expected failure, retry, or warning: passed.

Phase 2 may be planned. It must define benchmark-backed Serving Units and useful-capacity calculations before implementation begins.
