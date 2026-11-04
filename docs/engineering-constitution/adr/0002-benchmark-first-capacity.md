# ADR-0002: Benchmark-First Useful Capacity

- Status: Accepted
- Date: 2026-11-04

## Context

Theoretical roofline models are useful for plausibility and memory feasibility but cannot establish production capacity under latency and reliability objectives.

## Decision

Only compatible approved benchmarks may establish useful or sellable capacity. Theoretical estimates remain separately labeled planning aids and cannot support certification or commercial pricing.

## Consequences

- Missing evidence produces `BENCHMARK_REQUIRED`.
- Benchmark identity and compatibility rules are part of the domain.
- SLO failure blocks certification.
- Roofline calculations remain optional pre-flight evidence.
