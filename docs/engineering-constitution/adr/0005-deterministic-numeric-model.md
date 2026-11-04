# ADR-0005: Deterministic Decimal and Quantity Model

- Status: Accepted
- Date: 2026-11-04

## Context

Financial and capacity calculations are vulnerable to binary floating-point error, mixed units, implicit time windows, and premature rounding.

## Decision

Use decimal arithmetic for governed numeric calculations and explicit typed quantities for physical dimensions, rates, ratios, time windows, and currencies. Apply rounding only at declared formula or presentation boundaries.

## Consequences

- Public contracts use canonical decimal strings for governed values.
- Unit conversion is explicit and tested.
- Floats are prohibited in the canonical calculation core.
- Dimensional mismatches fail before calculation.
