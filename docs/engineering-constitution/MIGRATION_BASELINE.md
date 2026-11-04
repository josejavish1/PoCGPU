# Migration Baseline

## Purpose

Record known baseline debt that must be removed or migrated. This document grants no permanent waiver.

## Current findings

### Duplicate calculation engines

- `scripts/finops_calculator.py`
- `scripts/finops_tier1_engine.py`
- The current `src/` application and domain implementation

They use incompatible formulas, assumptions, catalogs, and output contracts.

Required action: establish the canonical engine, create migration cases, and retire duplicate operational paths after parity evidence exists.

### Benchmark substitution

The current application derives production performance from theoretical accelerator specifications and configured efficiency factors.

Required action: retain theory only as an explicitly labeled pre-flight estimate and require benchmark records for useful capacity.

### Certification gap

The current gate can certify a scenario when latency SLO flags are false.

Required action: make every mandatory SLO and evidence predicate part of certification.

### Hidden interface values

The current web interface embeds facility, traffic, token, and demand values in the request payload.

Required action: replace them with explicit governed scenario fields or assumption templates.

### Incomplete TCO boundary

The current TCO omits or simplifies several asset, labor, software, security, network, observability, one-time, financing, and lifecycle classes.

Required action: introduce explicit cost boundaries and cost-class records.

### Incorrect hybrid fixed-cost treatment

The current hybrid calculation scales private fixed cost by traffic share.

Required action: model full installed private block cost plus external overflow.

### Margin terminology

The legacy engine labels markup as commercial margin.

Required action: remove the ambiguous field and use separate gross-margin and markup formulas.

### Static, unproven catalogs

Current pricing, hardware, failure-rate, FX, efficiency, and SLO records lack complete source and validity metadata.

Required action: migrate them as unverified assumptions or replace them with governed evidence.

### Non-English executable source

Legacy executable scripts contain non-English comments, messages, or identifiers.

Required action: remove or migrate those scripts. Only locale resources and localized deliverables may contain non-English language.

Phase 0 control: thirteen exact legacy files are hash-sealed in the governance manifest. Wildcard exceptions and hash rebaselining are prohibited. The ratchet expires before Phase 1, so Phase 1 cannot pass governance until every listed file is remediated or removed.

### External-model planning artifacts

The baseline contains scripts and documents tied to external generative-model planning and self-certification workflows.

Required action: remove those scripts from the product path and replace authority claims with repository-owned engineering evidence.

### Unsupported production-readiness claims

The baseline describes the calculator as production-ready despite missing benchmark calibration, complete TCO, unit economics, and SLO certification.

Required action: use evidence-based lifecycle states defined by the Product Constitution.

### Reproducibility gap

The baseline has no canonical dependency manifest and lock for the calculator application.

Required action: establish a pinned, reproducible build and test environment in Phase 1.

## Migration constraints

- Do not delete a legacy path before preserving representative inputs and outputs for migration analysis.
- Do not preserve incorrect behavior merely to achieve parity.
- Classify differences as intentional correction, compatible migration, or unresolved defect.
- Historical artifacts may remain as localized documentation, but they cannot define product behavior.
