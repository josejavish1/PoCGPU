# PoCGPU

PoCGPU is a governed foundation for a universal AI infrastructure economics calculator. The current implementation establishes strict domain contracts, provenance, policy resolution, immutable scenarios, deterministic snapshots, canonical serialization, versioned schemas, and a single evaluation boundary.

## Current status

| Domain | Directory | Primary Scope | Operational / Implementation Status |
| :--- | :--- | :--- | :--- |
| **Cloud Infrastructure PoC** | `pocs/elastic-multi-gpu-inference/` | GKE Zurich (`europe-west6-b`), 4x NVIDIA L4 GPUs, vLLM TP=2 + Multi-LoRA, LiteLLM Gateway, OpenWebUI | **Operational & Hibernated ($0.00/h):** Tracks A, B, C, and D-Step 1 (Active-Active at 689 tok/s) certified. Pending: D-Step 2 (Chaos failover). |
| **Calculadora A (Sizing)** | `calculators/sizing/` | Silicon physics, static weights VRAM, dynamic KV cache (GQA), roofline bandwidth saturation | **Specified & Modeled:** Formulas approved in `09_MODELO_FINOPS_CALCULADORA.md`; implemented in `pocgpu.domain.capacity`. |
| **Calculadora B (Chargeback)** | `calculators/chargeback/` | Fully-loaded TCO (hardware, energy, PUE cooling, datacenter), $/1M tokens rate card, break-even vs cloud APIs | **Specified & Modeled:** Formulas approved in `09_MODELO_FINOPS_CALCULADORA.md`; implemented in `pocgpu.domain.tco` and `economics`. |
| **Canonical Engine / Shared Kernel** | `src/pocgpu/` | Exact numeric models, immutable types (`Money`), deterministic policy resolution, schemas v1 | **Phase 1 Certified:** Governed by [Engineering Constitution](docs/engineering-constitution/README.md) with 100% formal CI quality gates. |

## Repository structure

- `pocs/`: Declarative cloud PoC infrastructure environments (e.g. `pocs/elastic-multi-gpu-inference/` containing Kubernetes manifests, runbooks, and load testing scripts).
- `calculators/`: Decoupled calculators for Silicon Sizing (`calculators/sizing/`) and Chargeback/TCO (`calculators/chargeback/`), with domain specifications under `calculators/docs/`.
- `src/pocgpu/`: Canonical calculation engine and shared kernel (domain primitives, exact numeric models, and evaluation pipelines).
- `config/`: Governed catalogs for hardware, pricing, models, and taxonomies.
- `schemas/`: Versioned canonical boundary schemas.
- `docs/`: Engineering constitution and architecture decision records.
- `tests/`: Governed verification suites across delivery phases.

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
