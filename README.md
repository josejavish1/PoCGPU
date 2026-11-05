# PoCGPU

PoCGPU is a governed foundation for a universal AI infrastructure economics calculator. The current implementation establishes strict domain contracts, provenance, policy resolution, immutable scenarios, deterministic snapshots, canonical serialization, versioned schemas, and a single evaluation boundary.

## Current status

Phase 0 established the [Engineering Constitution](docs/engineering-constitution/README.md). Phase 1 is complete with its evidence recorded in the [Phase 1 completion report](docs/engineering-constitution/PHASE_1_COMPLETION_REPORT.md). The independent plans for phases 2 through 8 are published as drafts under the [delivery roadmap](docs/engineering-constitution/DELIVERY_ROADMAP.md) and require review and acceptance before implementation.

The current foundation intentionally does not implement capacity, TCO, unit economics, pricing, or external comparison formulas. Requests for these later-phase domains fail closed with a structured `OUTPUT_DOMAIN_UNAVAILABLE` issue. Existing calculator outputs are retained only as migration evidence and are not correctness oracles.

## Canonical package

All new executable product code is under `src/pocgpu`:

- `domain`: immutable identifiers, exact numeric values, quantities, money, time, provenance, policy, organization, scenario, result, snapshot, and port contracts.
- `application`: deterministic policy resolution and the single scenario evaluation service.
- `adapters`: explicit reference adapters for contract and integration verification.
- `contracts`: strict version 1 boundary models and deterministic JSON Schema export.
- `composition.py`: the only reference composition boundary.

Canonical source is written in technical English. Presentation localization belongs at interface boundaries and is not embedded in domain or application behavior.

## Reproducible development

The repository pins Python in `.python-version`, declares dependencies and tool configuration in `pyproject.toml`, and locks the full dependency graph in `uv.lock`.

```bash
UV_CACHE_DIR=/tmp/pocgpu-uv-cache uv sync --frozen
.venv/bin/ruff check src/pocgpu tests/phase1 tests/build tests/migration
.venv/bin/mypy src/pocgpu tests/phase1
.venv/bin/pytest tests/phase1 --cov=pocgpu.domain --cov-branch
UV_CACHE_DIR=/tmp/pocgpu-uv-cache uv build --no-sources
```

The domain coverage gate requires 100 percent statement and branch coverage. Boundary schemas are checked into `schemas/v1` and tests verify that clean generation produces the same documents.

## Governance

The engineering constitution controls requirement ownership, calculation semantics, data provenance, hardcoding, internationalization, architecture, test quality, migration, and completion evidence. Later phases may add formulas only through approved, versioned formula and evidence contracts.

Legacy infrastructure material outside `src/pocgpu` is not imported by the canonical package. Its removal is governed by the evidence-first migration rules in [ADR-0010](docs/engineering-constitution/adr/0010-evidence-first-legacy-removal.md).
