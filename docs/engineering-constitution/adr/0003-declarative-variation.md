# ADR-0003: Declarative Variation

- Status: Accepted
- Date: 2026-11-04

## Context

The product must support organizations, industries, jurisdictions, providers, and commercial models without source forks.

## Decision

Represent contextual variation through validated, versioned data and policy packs resolved by generic services. Source branches based on customer, vertical, region, vendor, or model identifiers are prohibited.

## Consequences

- Policy schemas and precedence are product contracts.
- Conflicts fail explicitly.
- New policy behavior may require a generic rule capability, but never an unbounded code-evaluation mechanism.
