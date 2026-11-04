# No Hardcoding Policy

## Purpose

Ensure that the platform can support different organizations, industries, jurisdictions, languages, vendors, models, deployment patterns, and commercial agreements without source changes.

## Prohibited source content

Executable source must not embed:

- Vendor prices or commercial discounts.
- Benchmark results or efficiency ratios.
- Hardware, model, provider, region, or vertical catalogs.
- Organization names or customer-specific identifiers.
- Electricity, labor, facility, network, storage, or software rates.
- SLO thresholds or availability policies.
- Accounting lives, residual values, tax rules, or capital rates.
- Gross-margin targets or commercial markups.
- API token prices, cache discounts, or batch discounts.
- Locale-specific display text.
- Default demand, token, concurrency, or utilization profiles.
- Silent fallback selections.
- Vertical-specific decision branches.

## Allowed source constants

Only the following categories may exist as named source constants:

- Mathematical identities and exact conversion definitions.
- Protocol and schema tokens required for interoperability.
- Stable enumeration members that describe domain categories rather than organization policy.
- Security limits required to protect the runtime, when they are not business calculation inputs.

Allowed constants must have a descriptive name, type, unit where relevant, documentation, and tests. Unexplained numeric literals are prohibited in the canonical domain and calculation services.

## Configuration rules

- Configurable values live in validated, versioned records.
- A configuration source must expose provenance and validity metadata.
- Configuration resolution is explicit and visible in the canonical result.
- Environment variables select deployments or credentials; they do not carry complex business policy.
- A missing configuration value does not activate a source-code fallback.
- Suggested templates are data packs labeled as assumptions, not defaults.

## Policy packs

Variation is expressed through composable policy packs:

- Organization policy.
- Vertical policy.
- Jurisdiction policy.
- Accounting policy.
- Availability policy.
- Security policy.
- Commercial policy.
- Localization policy.

Policy precedence must be deterministic, documented, and recorded in each result. Conflicting mandatory policies produce `POLICY_REQUIRED` or `REJECTED` rather than arbitrary precedence.

## Detection gates

Automated checks must detect:

- Numeric literals in governed calculation modules outside an approved constant registry.
- User-facing string literals outside localization adapters and locale resources.
- Known vendor, model, region, vertical, and currency identifiers inside the domain engine.
- Default values in public request DTOs for governed business fields.
- Direct file reads from the domain layer.
- Conditional branches based on organization or vertical identifiers.
- Fallback operators that substitute governed values.

## Exception process

An exception requires an Architecture Decision Record that explains why the value is universal, why configuration would be incorrect, its unit and valid domain, and how it is tested. Temporary migration exceptions require an owner and removal phase. Permanent customer-specific exceptions are forbidden.
