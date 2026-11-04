# Domain Glossary

The terms in this glossary are normative. Interfaces and implementation must use these meanings consistently.

| Term | Definition |
|---|---|
| Accelerator | A physical compute device used for inference, such as a GPU or another AI accelerator. |
| Adapter | A parameter-efficient model extension, such as a LoRA, associated with a base model without being counted as a full duplicate model unless it has an independent memory footprint. |
| Assumption | A value accepted for analysis without invoice, measurement, or authoritative configuration evidence. |
| Base Model | The shared model weights from which one or more logical models or adapters are served. |
| Benchmark | A versioned, reproducible measurement of one Serving Unit under a defined workload, software stack, hardware topology, and environment. |
| Capacity, Installed | The technical capacity represented by all installed resources before operational reservations. |
| Capacity, Productive | Capacity assigned to normal production service. |
| Capacity, Resilient | Capacity reserved to survive a declared failure or maintenance event. |
| Capacity, Sellable | Capacity that may be committed to demand while preserving SLO, headroom, and resilience policy. |
| Capacity, Useful | The maximum measured load that satisfies all required SLO and error constraints. |
| Certified Result | A valid result that passed every required evidence, formula, SLO, reconciliation, and approval gate. |
| Cost | Economic or accounting consumption attributable to a service. Cost is distinct from price. |
| Demand Profile | A normalized description of expected and peak requests, tokens, concurrency, timing, and growth. |
| Gross Margin | `(Price - Cost) / Price`. It is distinct from markup. |
| Headroom | Deliberately uncommitted capacity for uncertainty, growth, fragmentation, or operational safety. |
| Logical Model | A customer-visible model identity that may map to a base model, an adapter, or a routing policy. |
| Markup | `(Price - Cost) / Cost`. It is distinct from gross margin. |
| Model Revision | An immutable model artifact and architecture version used by a Serving Unit. |
| Policy Pack | Versioned declarative rules for an organization, vertical, jurisdiction, accounting treatment, availability class, or other variable context. |
| Price | The amount charged to a customer or internal consumer. Price is distinct from cost. |
| Scenario | An immutable set of versioned inputs, policies, evidence references, and requested outputs. |
| Serving Unit | The smallest independently deployable inference unit defined by model revision, engine and version, hardware, accelerator count, parallelism, precision, scheduler, context, caching, and residency configuration. |
| SLO | A measurable service objective with a metric, threshold, percentile, evaluation window, and failure rule. |
| TCO | Fully loaded cost over a declared boundary and period. The boundary must state included and excluded cost classes. |
| Utilization | Demand divided by useful or sellable capacity for the same metric and time window. Multiple constraints produce multiple utilization values. |
| Workload Profile | A normalized distribution of prompt length, output length, request type, streaming, caching, batching, concurrency, and SLO requirements. |

## Prohibited semantic substitutions

- Registered users must not be used as concurrent users without a documented conversion model.
- Peak throughput must not be called useful capacity unless it passes the required SLO.
- Accelerator utilization must not be used as business utilization.
- Risk reserve must not be used as a substitute for physical redundancy.
- Markup must not be labeled gross margin.
- Amortization must not be labeled cash flow.
- Cloud allocation percentage must not scale already purchased private fixed cost.
- A theoretical estimate must not be labeled benchmark data.
