# ADR-0010: Evidence-First Legacy Removal

- Status: Accepted
- Date: 2026-11-04

## Context

The baseline contains multiple executable calculators, non-English source, generated external-model authority claims, and tests that assert internally consistent but materially incorrect behavior. Retaining these paths permits divergence; deleting them without evidence loses migration traceability.

## Decision

Capture representative legacy inputs and serialized outputs with their exact source commit before removing an executable path. Classify each observed output as preserved, intentionally corrected, deferred, or rejected. Remove legacy modules from the distributed product after evidence capture. Preserve history in version control instead of maintaining an executable duplicate engine.

## Consequences

- Known defects never become golden expected values.
- Intentional corrections link to requirements, risks, and later formula phases.
- External-model planning and self-certification artifacts have no product authority.
- Canonical code cannot import legacy implementations.
- A phase may temporarily provide fewer calculations rather than publish unsupported results.
