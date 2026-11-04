# Data Governance Policy

## Data classes

Every governed value has exactly one evidence class:

- `INVOICE`: verified commercial invoice, contract, quote, or authoritative internal ledger.
- `MEASURED`: reproducible benchmark or telemetry observation.
- `CONFIGURED`: approved organization, service, accounting, or policy decision.
- `ASSUMED`: explicit estimate accepted for a scenario.
- `DERIVED`: value produced by a versioned formula from governed inputs.

## Required metadata

Every governed record must provide, where applicable:

- Stable record identifier.
- Schema and record version.
- Evidence class.
- Value and unit.
- Currency and currency basis.
- Geography and provider region.
- Source identifier and source URI or internal reference.
- Source observation date.
- Valid-from and valid-until timestamps.
- Owning organization and responsible role.
- Confidence or quality status.
- Collection or derivation method.
- Formula identifier for derived values.
- Approval state.
- Superseded record identifier.

## Validity

- Validity periods are explicit and data-type specific.
- A record outside its validity window is `STALE`.
- A stale critical record blocks certification.
- Historical scenarios retain their original evidence snapshots.
- Updated catalogs do not silently alter a previously certified result.

## Missing data

- Missing mandatory factual data produces `INPUT_REQUIRED`.
- Missing compatible performance evidence produces `BENCHMARK_REQUIRED`.
- Missing organization policy produces `POLICY_REQUIRED`.
- An assumption may replace missing data only through explicit scenario acceptance and must remain visible in outputs.
- Zero, empty string, and null have distinct meanings.

## Units and currency

- Units use a controlled registry with dimensional validation.
- Currency values retain original currency and conversion metadata.
- FX observations identify provider, timestamp, base currency, quote currency, and rate.
- A converted amount never overwrites the original amount.

## Benchmark governance

A benchmark record must identify:

- Serving Unit fingerprint.
- Model artifact and revision.
- Engine, runtime, driver, firmware, and operating system versions.
- Hardware topology and power mode.
- Workload distribution and dataset.
- SLO definition and evaluated percentiles.
- Warm-up, duration, sample count, concurrency, and request schedule.
- Raw evidence location and checksum.
- Measurement timestamp and environment.
- Reviewer and approval state.

Derived theoretical estimates are not benchmark records.

## Pricing governance

Pricing records must identify provider, product, meter, region, purchase model, commitment, currency, effective date, taxes, discounts, included allowances, and source. Public list price and negotiated price are different records.

## Privacy and confidentiality

The platform should store aggregated demand and cost inputs by default. Customer content, prompts, credentials, personal data, and contract documents must remain outside calculation records. References may point to authorized systems without copying confidential source material.

## Immutability and replay

A completed scenario references immutable snapshots of inputs, policies, formulas, and evidence. Replay must reproduce the same canonical result or fail with a version-resolution error.
