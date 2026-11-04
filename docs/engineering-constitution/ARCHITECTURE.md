# Target Architecture

## Architectural style

The product uses a modular hexagonal architecture with a deterministic functional calculation core.

## Dependency direction

`interfaces -> application -> domain`

`adapters -> ports <- application/domain`

The domain imports no web framework, database client, file system adapter, cloud SDK, spreadsheet library, localization framework, or vendor SDK.

## Target modules

### Domain

- Value objects for money, quantities, time windows, provenance, and identities.
- Organization, policy, model, Serving Unit, benchmark, workload, demand, sizing, TCO, unit economics, pricing, comparison, and scenario aggregates.
- Pure calculation services and invariants.
- Port definitions for governed external data.

### Application

- Use cases and workflow orchestration.
- Scenario state machine.
- Policy resolution.
- Certification orchestration.
- Canonical result assembly.

### Ports

- Catalog repository.
- Benchmark repository.
- Pricing provider.
- FX provider.
- Telemetry importer.
- Policy repository.
- Scenario repository.
- Audit ledger.
- Clock and identity providers.

### Adapters

- Versioned file catalogs for development.
- Database persistence.
- Cloud and API pricing integrations.
- Benchmark and telemetry ingestion.
- ERP and invoice references.
- Workbook export.
- Localization resources.

### Interfaces

- Versioned API.
- Web application.
- Command-line administration.
- Workbook and machine-readable exports.

Interfaces consume canonical results and never calculate financial or capacity metrics independently.

## Canonical scenario flow

1. Accept explicit scenario references and user inputs.
2. Resolve policy packs with deterministic precedence.
3. Resolve immutable catalog and evidence versions.
4. Validate completeness, dimensions, validity, and authorization.
5. Evaluate capacity, TCO, unit economics, pricing, and comparisons through versioned formula services.
6. Run certification gates.
7. Produce one immutable canonical result.
8. Render that result through any interface or locale.

## Determinism

Calculation functions receive all required inputs explicitly. Time, random values, identity, FX, external prices, and catalog selection enter through ports and are captured before calculation. The domain does not read process state or external systems.

## Extension model

New organizations, verticals, jurisdictions, vendors, models, currencies, languages, and pricing providers are added through validated data or adapters. They do not require branches in the canonical engine.

## Multi-tenancy

Organization data, policy, scenarios, evidence references, and permissions are tenant-scoped. Global catalogs and formulas are immutable shared versions. Tenant overrides create new governed records rather than mutating shared data.

## Security boundaries

- Calculation data is separated from credentials and customer content.
- Adapters apply least privilege.
- Scenario APIs validate tenant ownership and authorization.
- Audit integrity does not imply calculation correctness; certification evidence remains separate.

## Workbook architecture

The workbook is a generated or connected presentation of canonical inputs and results. It may expose traceable what-if controls, but it must not contain an independent hidden formula implementation. Offline mode requires a versioned portable calculation package and parity evidence.

## Versioning

- Formula versions are immutable.
- Schema changes follow explicit compatibility policy.
- Canonical results identify every input and engine version.
- Prior certified results remain replayable.
