# ADR-0007: Immutable Governed Records

- Status: Accepted
- Date: 2026-11-04

## Context

Calculation inputs currently mix values, defaults, catalog identity, and partial metadata. Updating a catalog can change later evaluation without preserving the exact evidence previously used.

## Decision

Represent governed inputs as immutable versioned records with evidence class, source, ownership, validity, approval, tenant scope where applicable, and lineage. A change creates a new record version. Scenario evaluation resolves records into an immutable snapshot before any calculation service runs.

## Consequences

- Missing required metadata fails closed.
- Assumptions require explicit acceptance records.
- Derived values identify their formula and source records.
- Superseded records remain replayable.
- Adapters cannot mutate a record after retrieval.
- A content hash demonstrates snapshot integrity and identity but never demonstrates correctness.
