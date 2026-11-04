# ADR-0004: Localization Boundary

- Status: Accepted
- Date: 2026-11-04

## Context

The product must support any language while preserving one stable technical vocabulary and preventing localized text from affecting calculations.

## Decision

Use English for executable source and canonical technical artifacts. Store user-facing language in versioned locale packs referenced by semantic keys. Perform formatting only at interface boundaries.

## Consequences

- Source and literal scans become release gates.
- Locale packs require schema, parity, placeholder, and layout tests.
- Localized deliverables are generated from canonical results.
