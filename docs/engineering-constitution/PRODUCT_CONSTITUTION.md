# Product Constitution

## Mission

Provide a universal, evidence-based platform for AI inference capacity planning, fully loaded cost analysis, unit economics, pricing, deployment comparison, and scenario governance.

The platform must support organizations ranging from medium-sized enterprises to globally distributed regulated enterprises without embedding organization, industry, geography, language, vendor, model, or deployment assumptions in source code.

## Primary decisions supported

The platform must answer:

1. What does an AI inference platform cost to acquire, operate, support, secure, and renew?
2. What useful capacity can a specific Serving Unit provide while meeting a defined SLO?
3. How many Serving Units, replicas, servers, accelerators, racks, and sites are required for a demand profile?
4. What capacity is installed, productive, resilient, sellable, reserved, stranded, and idle?
5. What is the effective cost per unit of demand at expected and alternative utilization levels?
6. What price meets a target gross margin without confusing margin and markup?
7. When is private infrastructure economically preferable to an external API or cloud deployment?
8. What is the cost of a hybrid private-baseload and external-burst strategy?
9. Which outputs are measured facts, invoices, configured values, assumptions, or derived values?

## Product users

- Chief Financial Officer and finance teams.
- Chief Technology Officer and architecture teams.
- Infrastructure, platform, SRE, MLOps, networking, security, and datacenter teams.
- FinOps, procurement, commercial, pricing, and managed service teams.
- Auditors, risk owners, and compliance teams.

## Product principles

### Evidence before precision

The platform must not display unjustified decimal precision. Measured capacity requires a compatible approved benchmark. Missing evidence produces an explicit unresolved state.

### One canonical result

API, web, command-line tools, exports, and workbooks must consume the same versioned calculation result. Interfaces must not reimplement formulas.

### Fail closed

Missing critical input, invalid provenance, expired pricing, incompatible units, or failed SLO must block certification. The system must not substitute a hidden default.

### Separation of concerns

Cost, capacity, demand, utilization, price, risk, and accounting treatment are separate concepts. A result may connect them only through a documented formula.

### Universal core, declarative variation

Organization, vertical, jurisdiction, accounting, availability, locale, vendor, and commercial variation belongs in validated policy or data packs.

### Reproducibility

Every result must identify engine version, formula version, policy versions, catalog versions, benchmark identifiers, source dates, scenario inputs, and rounding rules.

## Result states

Every scenario has exactly one primary state:

- `DRAFT`: incomplete scenario that has not requested evaluation.
- `INPUT_REQUIRED`: a mandatory configured or factual value is missing.
- `BENCHMARK_REQUIRED`: no compatible approved benchmark supports capacity claims.
- `POLICY_REQUIRED`: an organization or jurisdiction decision is unresolved.
- `ASSUMPTION_BASED`: calculation completed using explicitly accepted assumptions.
- `VALID`: calculation completed with valid inputs and evidence.
- `CERTIFIED`: valid result that passed all required technical, financial, provenance, and approval gates.
- `REJECTED`: at least one mandatory gate failed.
- `STALE`: evidence or pricing exceeded its validity period.

`CERTIFIED` is impossible when an SLO is missed, a critical source is stale, a benchmark is absent, reconciliation fails, or an unaccepted critical assumption remains.

## V1 boundary

V1 supports:

- Always-warm model residency.
- One canonical workload profile per scenario.
- Benchmark-backed Serving Units.
- Actual telemetry mode and estimation mode for demand.
- Multi-constraint sizing and physical high availability.
- Fully loaded private and cloud TCO.
- Blended unit economics tied to a workload profile.
- Gross-margin pricing.
- Equivalent external API comparison.
- Utilization and sensitivity scenarios.

Dynamic residency, arbitrary multi-model pooling, discrete-event simulation, stochastic optimization, and advanced queueing simulation are later-version capabilities.

## Non-goals

- Predict model quality or business value without evidence.
- Infer prices, benchmarks, or contractual terms from vendor names.
- Treat theoretical accelerator specifications as production throughput.
- Replace accounting, legal, tax, procurement, or regulatory approval.
- Provide a universal fixed threshold at which private infrastructure always wins.

## Ownership

Each organization must assign owners for business assumptions, technical benchmarks, financial inputs, security policies, and release certification. The platform records ownership but does not invent it.
