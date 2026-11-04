# 10_BACKLOG_FINOPS_INSTITUCIONAL.md: Institutional FinOps Architecture Backlog

> **ENGINEERING ROADMAP & TIER-1 NEUROSYMBOLIC BACKLOG**  
> Strategic evolution plan transferring the institutional primitives of `assessment_engine` into the PoCGPU FinOps Platform. Structured into 4 sequential Epics designed for iterative execution under `gemini-4-argon`, prioritizing a **Guided Assessment Wizard (Questionnaire Decision Matrix)** to recommend and compare **On-Premise Private Datacenter** vs. **Public Cloud** vs. **Hybrid Cloud-Bursting**.

---

## Executive Assessment Architecture: From Questions to Hardware & TCO

```
                      [ ENTERPRISE EXECUTIVE / CTO / CFO ]
                                        │
                                        ▼
                  ┌───────────────────────────────────────────┐
                  │    GUIDED ARCHITECTURAL ASSESSMENT WIZARD │
                  │  (5 Strategic Non-Functional Questions)  │
                  └─────────────────────┬─────────────────────┘
                                        │
                                        ▼
                  ┌───────────────────────────────────────────┐
                  │     ALGORITHMIC DECISION MATRIX ENGINE    │
                  │   Weights: Compliance, Traffic, CapEx/OpEx│
                  └─────────────────────┬─────────────────────┘
                                        │
              ┌─────────────────────────┼─────────────────────────┐
              ▼                         ▼                         ▼
   [ ARCHETYPE 1: ON-PREM ]    [ ARCHETYPE 2: CLOUD ]    [ ARCHETYPE 3: HYBRID ]
   100% Sovereign Private      Elastic Cloud Dedicated   Sovereign Base + Bursting
   (CPD / Rack / CapEx)        (Zero Upfront / OpEx)     (PoCGPU Native Pattern)
              │                         │                         │
              └─────────────────────────┼─────────────────────────┘
                                        │
                                        ▼
                  ┌───────────────────────────────────────────┐
                  │      SIDE-BY-SIDE TCO ARBITRAGE REPORT    │
                  │ 3-Year Amortization vs Monthly Cloud Bill │
                  │        vs OpenAI GPT-4o Invoicing         │
                  └───────────────────────────────────────────┘
```

---

## The 5 Strategic Assessment Questions (Decision Vector)

| Question Dimension | Client Scenario A (Points to On-Premise) | Client Scenario B (Points to Cloud) |
| :--- | :--- | :--- |
| **1. Data Sovereignty & Regulatory Compliance** | Restricted by law (ENS Alto, Defense, GDPR Banking secrecy, Patient Health Data). | General business data, public RAG, no strict residency constraints. |
| **2. Workload Predictability & Duty Cycle** | Continuous 24/7 sustained baseline (>50M tokens/month, high diurnal saturation). | Bursty, seasonal, experimental R&D, unpredictable adoption. |
| **3. Datacenter Infrastructure Readiness** | Existing owned/rented datacenter with available kW power and cooling capacity. | No physical datacenter space; zero tolerance for physical rack management. |
| **4. Financial Model & Accounting Preference** | CFO prefers **CapEx** (depreciated asset over 3-5 years with lower unit token cost). | CFO prefers **OpEx** (monthly operating expense, zero upfront capital investment). |
| **5. Operational Engineering Maturity** | In-house SRE / Linux / Hardware infrastructure team capable of managing hardware RMA. | Lean software development team; requires fully managed orchestration. |

### Algorithmic Recommendation Archetypes:
1. **Archetype 1: Sovereign On-Premise Cluster:** Recommended when Sovereignty is CRITICAL or Continuous Traffic > 60% with existing datacenter space.
2. **Archetype 2: Elastic Public Cloud Cluster:** Recommended when Traffic is highly seasonal or zero physical datacenter infrastructure exists.
3. **Archetype 3: Hybrid Tier-1 (Cloud-Bursting Architecture):** The native PoCGPU blueprint: On-premise / private nodes absorb 80% of routine corporate traffic at near-zero marginal cost, with transparent failover to Gemini/Cloud GPU during demand spikes.

---

## EPIC 1: JIT Hardware & Hybrid Sourcing Resolver (On-Premise & Cloud)
*Origin: `assessment_engine/src/assessment_engine/infrastructure/evidence_engine.py`*

### Objective
Eliminate static silicon and pricing dictionaries. Provide a unified resolver capable of discovering both **On-Premise Server BOMs (Bill of Materials)** from enterprise OEMs (Supermicro, Dell PowerEdge, HPE ProLiant, Lenovo) and **Cloud Virtual Machines** (GCP, AWS, Azure, RunPod, CoreWeave).

### Technical Deliverables
1. **Unified `HardwareCatalogPort` & `DeploymentModel`:**
   - Supports two distinct financial modalities:
     - **`DeploymentType.ON_PREMISE`:** Models capital expenditure (CapEx) for physical chassis, GPUs, NVMe storage, InfiniBand switches, and transceivers.
     - **`DeploymentType.PUBLIC_CLOUD`:** Models hourly operational expenditure (OpEx) for Spot and On-Demand instances.
2. **`PlaywrightEvidenceHarvester`:**
   - Crawls official manufacturer datasheets and enterprise distributor quotes (NVIDIA, Supermicro, Dell, Arrow, TD Synnex) and cloud pricing endpoints.
   - Captures local SHA-256 evidence snapshots in `working/evidence_snapshots/`.
3. **On-Premise Physical Parameter Extractor:**
   - Targets:
     - Chassis form factor (2U, 4U, 8U), socket configuration, PCIe Gen5 / NVLink switchboards.
     - Total chassis thermal power consumption (TDP in Watts, e.g. 10.2 kW for an 8x H100 8U server).
     - Purchase acquisition cost (CapEx in EUR/USD, e.g. ~€280,000 for 8x H100 SXM5 node).

### Acceptance Criteria
- [ ] Guided Wizard guides the user through the 5 questions and recommends the optimal archetype automatically.
- [ ] User can inspect the side-by-side financial breakdown (CapEx amortized + Power vs Cloud VM $/h) with 1 click.

---

## EPIC 2: Open FAIR Actuarial Risk: On-Premise Hardware RMA vs Spot Preemption
*Origin: `assessment_engine/src/assessment_engine/domain/actuarial_calculator.py`*

### Objective
Provide actuarial loss modeling customized for both deployment regimes: **Physical Component Failure (AFR / MTBF / RMA)** in On-Premise environments and **Node Eviction (Preemption)** in Public Cloud Spot clusters.

### Technical Deliverables
1. **On-Premise Actuarial Risk Engine:**
   - **Annualized Failure Rate (AFR) & Mean Time Between Failures (MTBF):**
     - GPU silicon failure rate ($\text{AFR} \approx 3.2\% - 4.5\%$ per year under continuous thermal load).
     - Power supply unit (PSU) and NVMe drive failure probability.
   - **Single Loss Expectancy (SLE - Physical RMA):**
     $$\text{SLE}_{\text{onprem}} = (\text{Hardware Replacement MTTR (24h - 72h)} \times \text{Degraded Throughput Penalty}) + \text{On-Site Field Engineer Cost}$$
   - **Annualized Loss Expectancy (ALE):**
     $$\text{ALE}_{\text{onprem}} = \text{AFR} \times \text{Number of GPUs} \times \text{SLE}_{\text{onprem}}$$
2. **Cloud Spot Preemption Risk Engine:**
   - Preemption Loss Event Frequency ($\text{LEF}_{\text{spot}} \approx 2.5\% - 5.8\%$ monthly eviction rate) with Cold Rebuild token regeneration penalties.
3. **Institutional 3-Year TCO Arbitrage Comparison:**
   - Renders the definitive 3-year Total Cost of Ownership:
     - **Scenario A (On-Premise):** $\text{CapEx Amortized} + \text{Power (PUE)} + \text{Colo/Rack} + \text{OEM Care Pack} + \text{ALE}_{\text{onprem}}$.
     - **Scenario B (Cloud Spot):** $\text{Hourly Spot} + \text{Storage} + \text{Egress} + \text{ALE}_{\text{spot}}$.
     - **Scenario C (Cloud On-Demand / Reserved):** $\text{Hourly On-Demand} + \text{Storage} + \text{Egress}$.

### Acceptance Criteria
- [ ] Displays the exact 3-year TCO comparison curve between On-Premise, Cloud Spot, and Cloud On-Demand.
- [ ] Incorporates electricity price per kWh (e.g. €0.15/kWh), PUE (e.g. 1.25), and colocation rack costs (€1,500/month per 20kW rack).

---

## EPIC 3: Pre-Flight CFO Constitutional Gate (`CfoActuarialGate`)
*Origin: `assessment_engine/src/assessment_engine/domain/cfo_actuarial_gate.py`*

### Objective
Enforce physical and economic boundary invariants for both on-premise datacenters and cloud infrastructures, preventing unfeasible capacity allocations or invalid financial models.

### Technical Deliverables
1. **On-Premise Datacenter Invariants:**
   - **Rack Power Density Ceiling:** Rejects configurations where total node power exceeds the maximum rack power capacity (e.g. >20kW on standard racks or >40kW on direct-to-chip liquid cooled racks).
   - **Cooling & Thermal Invariant (PUE Floor):** Rejects PUE assumptions below physical limits ($\text{PUE} < 1.08$ for liquid cooling, $\text{PUE} < 1.25$ for air cooling).
   - **Amortization Horizon Floor:** Validates that hardware depreciation follows corporate GAAP/IFRS standards (minimum 36 months, maximum 60 months).
2. **Silicon & Roofline Invariants:**
   - **Memory Bandwidth Saturation:** Rejects decode loads exceeding 85% of memory bus bandwidth.
   - **VRAM Hard Ceiling:** Blocks any topology where $M_{total} > 0.90 \times \text{VRAM}_{\text{cluster}}$.
   - **RMA Replacement Floor:** Enforces a minimum physical component replacement MTTR of 4 hours (Mission Critical 24/7 OEM contract) or 24 hours (Next Business Day).

### Acceptance Criteria
- [ ] Entering an on-premise cluster with 8x H100 (10.2 kW) on an uncooled 5 kW rack triggers an immediate `ActuarialAuditGateViolationError` with clear datacenter power ceiling diagnostics.
- [ ] 100% test coverage over all thermal, electrical, and physical boundaries in `tests/test_cfo_actuarial_gate.py`.

---

## EPIC 4: Immutable Transactional Audit & Provenance Ledger (`EpistemicLedger`)
*Origin: `assessment_engine/src/assessment_engine/application/build_evidence_ledger.py`*

### Objective
Record every sizing simulation, CapEx/OpEx quote, and architectural audit into an append-only, cryptographically verified ledger (`epistemic_ledger.jsonl`) for enterprise procurement committees, board presentations, and internal chargeback compliance.

### Technical Deliverables
1. **`EpistemicLedgerWriter`:**
   - Append-only transactional logger recording:
     - `record_id`: UUIDv4.
     - `assessment_answers`: Exact client responses to the 5 strategic questions.
     - `recommended_archetype`: `ON_PREMISE`, `PUBLIC_CLOUD`, or `HYBRID_BURSTING`.
     - `capex_breakdown`: Server chassis, GPUs, networking, and cabling costs.
     - `opex_breakdown`: Power consumption (kWh), cooling PUE, rack rental, and OEM maintenance.
     - `actuarial_metrics`: AFR, MTBF, SLE, ALE, and CFO Gate verification status.
     - `git_commit_hash` & `cryptographic_signature`: SHA-256 integrity seal.
2. **LiteLLM PostgreSQL Synchronization:**
   - Stores corporate department chargeback tariffs directly into PostgreSQL, enabling automated billing whether models run on bare-metal racks or in GKE.

### Acceptance Criteria
- [ ] Every calculation produces an auditable ledger entry with its cryptographic hash and input provenance.
- [ ] Built-in CLI `python3 scripts/verify_ledger_integrity.py` validates that no historical financial calculation has been tampered with.

---

## Implementation Sequence (Step-by-Step Roadmap)

```
        [ STEP 1 ]                 [ STEP 2 ]                [ STEP 3 ]                [ STEP 4 ]
    Implement EPIC 1           Implement EPIC 2          Implement EPIC 3          Implement EPIC 4
 Guided Assessment Wizard    Open FAIR Risk Engine      CFO Actuarial Gate       Epistemic Ledger
& Hybrid Hardware Resolver  (On-Prem RMA & Spot ALE)   (Power/Thermal Limits)   (Cryptographic Seal)
```

1. **Step 1 (Immediate Next Task):** Implement **EPIC 1** (`scripts/guided_assessment_wizard.py` and `scripts/jit_hardware_resolver.py`), establishing the 5-question decision wizard and dynamic grounding for **On-Premise Servers (CapEx, Power/kW, PUE)** and **Cloud VMs**.
2. **Step 2:** Implement **EPIC 2** (`scripts/actuarial_risk_engine.py`), adding physical hardware failure (AFR/RMA) and Spot eviction actuarial models.
3. **Step 3:** Implement **EPIC 3** (`scripts/cfo_constitutional_gate.py`), enforcing datacenter power, cooling, and latency invariants.
4. **Step 4:** Implement **EPIC 4** (`scripts/epistemic_ledger.py`), connecting the audit ledger to the web UI and LiteLLM database.
