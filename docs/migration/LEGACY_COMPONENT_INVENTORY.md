# Legacy Component Inventory

- Runtime baseline: `eda8c880ba94b4922b4e70cbb0331542ae4884f9`
- Evidence schema: `1.0.0`
- Evidence file: `tests/fixtures/migration/legacy-evidence.json`

## Purpose

This inventory records representative legacy behavior before executable removal. Captured output is migration evidence only. It is not a correctness oracle, benchmark, governed price, or approved golden result.

## Calculator dispositions

| Component | Evidence case | Disposition | Reason |
|---|---|---|---|
| `scripts/finops_calculator.py` | `legacy-simple-cli-explicit-inputs` | `REJECTED` | Uses binary floats, embedded defaults, theoretical sizing, fixed calendar assumptions, and markup labeled as margin. |
| `scripts/finops_tier1_engine.py` | `legacy-tier1-cli-explicit-inputs` | `DEFERRED` | Capacity, pricing, and break-even outputs require replacement by approved Phase 2 through Phase 5 formulas and governed evidence. |
| Current `src` application | `legacy-advisor-enterprise-scenario` | `DEFERRED` | Mixes valid structural ideas with hidden fallbacks, theoretical capacity, incomplete TCO, incorrect hybrid allocation, and invalid certification behavior. |

`DEFERRED` means the behavior is retained as review evidence until its owning formula phase. It does not mean the numeric output will be preserved.

## Known intentional corrections

| Baseline behavior | Required correction | Owning phase |
|---|---|---:|
| Theoretical roofline output is treated as usable capacity. | Require compatible approved benchmark evidence. | 2 |
| Failed latency objectives may still produce a certified result. | Make every mandatory SLO and evidence gate fail closed. | 2 |
| Physical high availability is represented by financial risk reserve. | Model failure domains and installed resilience explicitly. | 2 |
| TCO omits or simplifies material cost classes. | Implement an explicit fully loaded cost boundary. | 3 |
| Private fixed cost is weighted by hybrid traffic share. | Charge the full installed private block plus external overflow. | 5 |
| Markup is labeled or accepted as gross margin. | Implement separate algebraic contracts. | 4 |
| Catalog values lack complete provenance and validity. | Treat them as unverified migration inputs until governed replacement. | 1-5 |

## External-model artifacts

The Argon planning, synthesis, audit, RFC, and self-certification files were removed from the product path during Phase 1. They have no normative authority. Git history preserves their content.

## Data classification

- The captured scenarios are synthetic.
- The fixtures contain no customer prompts, credentials, contracts, personal data, or customer identifiers.
- Legacy output text may contain localized presentation language because it records exact historical bytes.
- Nondeterministic audit entry identifiers and timestamps are excluded from stable evidence.

## Removal rule

An executable legacy component may be removed only after its source hash, representative output hash, disposition, and known corrections are recorded. Canonical source must never import a captured implementation or derive expected results from its fixture.

## Phase 1 removal outcome

After the evidence gate passed, Phase 1 removed the legacy calculators, duplicate domain and application packages, obsolete tests, external-model artifacts, and retired language-ratchet scripts listed in the approved removal set. The canonical runtime is now the `pocgpu` package. Captured fixtures remain immutable migration evidence and are never imported by production code.

The approved removal set comprised:

- `src/adapters`, `src/application`, `src/domain`, and the legacy `src/__init__.py`.
- `tests/adapters`, `tests/architecture`, `tests/domain`, and `tests/integration`.
- The legacy calculator scripts and web calculator.
- Argon planning, synthesis, audit, and RFC artifacts.
- Retired language-ratchet and legacy operational scripts.
- Obsolete observability manifests `07_observability_and_alerts.yaml` and `08_grafana_prometheus.yaml`.
