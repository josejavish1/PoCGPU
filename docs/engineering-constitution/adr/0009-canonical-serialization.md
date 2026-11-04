# ADR-0009: Canonical Serialization and Snapshot Identity

- Status: Accepted
- Date: 2026-11-04

## Context

Reproducible scenarios require byte-stable serialization across processes, input mapping order, and supported environments. Ordinary JSON serialization permits ambiguous decimals, inconsistent Unicode, unordered mappings, and environment-specific timestamp representations.

## Decision

Define one versioned canonical JSON protocol for snapshots and canonical results. Normalize Unicode to NFC, sort object keys, encode exact decimals as strings, encode UTC instants with `Z`, reject floats and unknown values, and include schema identity. Calculate snapshot identity as lowercase SHA-256 over the canonical UTF-8 bytes.

## Consequences

- Golden canonical bytes are authored independently from the production serializer.
- A protocol change requires a new schema version and compatibility decision.
- Unordered semantic collections require stable identity sorting before serialization.
- Hash equality proves identical canonical content only.
- Audit integrity cannot change validity or certification state.
