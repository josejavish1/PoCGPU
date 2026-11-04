# ADR-0008: Explicit Policy Resolution

- Status: Accepted
- Date: 2026-11-04

## Context

A universal platform must combine organization, vertical, jurisdiction, accounting, availability, security, commercial, and scenario policies. A built-in precedence order would embed business decisions and could silently select the wrong rule.

## Decision

Require each evaluation to provide a versioned `PolicyResolutionPlan` that identifies applicable policy packs and permitted override relationships. Conflicting settings fail unless one pack explicitly supersedes the other for that setting. Input order and contextual identifiers never establish precedence.

## Consequences

- Missing mandatory policy produces `POLICY_REQUIRED`.
- Override cycles and cross-tenant references are invalid.
- Resolution evidence records selected, superseded, rejected, and conflicting sources.
- New organizations, verticals, and jurisdictions add data rather than source branches.
- A universal source default cannot resolve a business-policy conflict.
