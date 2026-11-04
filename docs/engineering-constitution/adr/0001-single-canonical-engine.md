# ADR-0001: Single Canonical Calculation Engine

- Status: Accepted
- Date: 2026-11-04

## Context

The baseline contains multiple calculators with incompatible formulas and outputs. Independent implementations in API, web, command-line tools, or workbooks would create uncontrolled divergence.

## Decision

Maintain one canonical calculation engine. Every interface consumes its versioned canonical result. Interfaces may validate presentation input but must not reimplement governed formulas.

## Consequences

- Duplicate engines must be retired after migration evidence exists.
- Workbook output requires parity tests.
- Interface changes cannot change calculation semantics.
- Formula versions become explicit dependencies of results.
