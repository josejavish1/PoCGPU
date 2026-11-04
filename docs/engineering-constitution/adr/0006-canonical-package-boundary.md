# ADR-0006: Canonical Package and Composition Boundary

- Status: Accepted
- Date: 2026-11-04

## Context

The baseline application imports concrete adapters, reads repository files, creates domain services, applies business fallbacks, renders localized data, and writes audit records in one module. The repository also uses `src` as an import package name and has no reproducible package definition.

## Decision

Use a standard `src/pocgpu` package with explicit domain, application, contract, adapter, and composition boundaries. The domain uses the Python standard library only. Application services depend on domain contracts and ports. Concrete adapter selection occurs only in the composition root. Build metadata and an exact dependency lock define the installable product.

## Consequences

- Legacy `src.domain`, `src.application`, and `src.adapters` imports are migration paths and are not canonical package contracts.
- Application services cannot select file paths or instantiate concrete adapters.
- Boundary libraries may not leak into the domain.
- Clean wheel installation becomes a mandatory test target.
- Import compatibility may intentionally break after migration evidence is captured.
