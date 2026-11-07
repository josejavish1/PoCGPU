# Benchmark Methodology Specification: Goodput-Driven Capacity and FinOps Modeling

**Document ID:** `SPEC-BENCHMARK-METHODOLOGY-001`  
**Status:** Canonical Engineering Specification  
**Scope:** `pocs/elastic-multi-gpu-inference/` & `calculators/sizing/`  
**Authors:** Principal Infrastructure & Cognitive Architecture Team  
**Standard Compliance:** MLPerf Inference v6.1 (2026), IEEE Standard for Software Benchmarking, ISO/IEC 25010 Quality Model  

---

## 1. Executive Purpose & Strategic Alignment

Existing GPU sizing calculators across cloud vendors and consultancies rely on static, memory-only equations:
$$\text{VRAM}_{\text{total}} = \text{Model Weights} + (B \times L \times \text{KV-Cache-Per-Token})$$

This static formulation is fundamentally flawed in real-world deployments. It ignores:
1. Dynamic queuing delay and memory fragmentation under stochastic arrival patterns ($M/G/c$ queue dynamics).
2. Hardware interconnect contention during tensor-parallel all-reduce synchronization across PCIe 4.0 buses without NVLink.
3. Multi-LoRA kernel dispatch fragmentation and memory footprint degradation ($SGMV$ vs fused $GEMM$).
4. Modern engine scheduling optimizations (Chunked Prefill, Automatic Prefix Caching, and FP8 KV-Cache scaling).

This specification establishes an uncompromised, mathematically rigorous **Goodput-Driven Capacity Model**. Rather than measuring raw synthetic tokens per second, it determines the exact, certified operational boundary where user service level agreements (SLAs) are strictly satisfied without semantic degradation.

---

## 2. Mathematical Formalism: "Goodput" Under Strict SLA

In high-concurrency LLM serving, raw throughput ($\text{tok/s}$) is a vanity metric; a cluster can achieve 500 tok/s while 90% of user queries suffer 10-second queue delays. The canonical sizing engine models capacity exclusively around **Goodput** ($\lambda_{\text{SLA}}$).

### 2.1 The Goodput Definition
Let $Q$ denote the distribution of arrival requests with prompt length $L_{\text{in}}$ and target completion length $L_{\text{out}}$.  
Let $\tau_{\text{prefill}}$ denote the Time to First Token (TTFT) and $\tau_{\text{decode}}$ denote the Time Per Output Token (TPOT).

A request $i$ is defined as compliant with enterprise Tier-1 service levels if and only if:
$$\text{Compliant}(i) = \left( \text{TTFT}_i \le \tau_{\text{max\_TTFT}} \right) \land \left( \text{TPOT}_i \le \tau_{\text{max\_TPOT}} \right)$$

Where default Tier-1 enterprise thresholds are:
* $\tau_{\text{max\_TTFT}} = 1.000\text{ ms}$ (Maximum initial response latency for interactive streaming).
* $\tau_{\text{max\_TPOT}} = 60.0\text{ ms/token}$ (Reading cadence threshold; human reading speed is ~200 ms/word).

The **Goodput Capacity** $\lambda_{\text{SLA}}$ of a given GPU hardware node is the maximum arrival rate $\lambda$ (queries/second) or maximum concurrent active clients ($C_{\text{max}}$) satisfying:
$$P\left(\text{Compliant}\right) \ge 0.99 \quad (\text{P99 SLA Guarantee})$$

---

## 3. The 4 Universal Transfer Coefficients for the Sizing Calculator

The empirical benchmark suite executes not to generate isolated logs, but to calibrate the **4 universal physical coefficients** that parameterize the canonical engine in `calculators/sizing/src/sizing/domain/model.py`:

```
+---------------------------------------------------------------------------------------+
|                               CANONICAL CAPACITY ENGINE                               |
|                                                                                       |
|   N_nodes = ceil( (lambda_peak * L_out) / ( alpha_compute * beta_fabric * kappa_rt )  |
|                  + VRAM_footprint( Delta_LoRA ) )                                      |
+---------------------------------------------------------------------------------------+
        ^                       ^                      ^                     ^
        |                       |                      |                     |
  [Alpha Compute]        [Beta Fabric]           [Kappa Runtime]       [Delta LoRA]
  Tensor Core Rate       PCIe Bus Drag           Engine Tuning Tax     Adapter Weight Tax
```

### 3.1 $\alpha_{\text{compute}}(\text{Chip}, \text{Model})$: Intrinsic Compute Efficiency
* **Physical Dimension:** Useful decode tokens per second per SM processor core in memory-bandwidth-bound and compute-bound regimes.
* **Calibration Protocol:** Measured under single-stream and isolated batch runs across GPU architectures (NVIDIA L4 24GB, A100 80GB SXM4, H100 80GB SXM5).
* **Reference Baselines:**
  * NVIDIA L4 (Ada Lovelace, 300 GB/s bandwidth): $\alpha_{\text{compute}} \approx 220\text{ tok/s per 2-GPU node}$ (Mistral-7B).
  * NVIDIA A100 SXM4 (Ampere, 2,039 GB/s bandwidth): $\alpha_{\text{compute}} \approx 850\text{ tok/s per node}$.
  * NVIDIA H100 SXM5 (Hopper, 3,350 GB/s bandwidth): $\alpha_{\text{compute}} \approx 2,100\text{ tok/s per node}$.

### 3.2 $\beta_{\text{fabric}}(\text{Interconnect}, TP)$: Inter-GPU Communication Drag
* **Physical Dimension:** Dimensional multiplier ($\le 1.0$) capturing the latency tax of All-Reduce operations across transformer hidden dimensions:
  $$\beta_{\text{fabric}} = \frac{\text{Throughput}_{\text{Observed}}}{\text{Throughput}_{\text{Ideal}}}$$
* **Calibration Protocol:** Comparing Tensor Parallelism $TP=2$ across PCIe 4.0 x16 (~31.5 GB/s bidirectional) against NVLink 4 (~900 GB/s bidirectional).
* **Reference Baselines:**
  * PCIe 4.0 ($TP=2$ on dual-L4): $\beta_{\text{fabric}} \approx 0.84$ (16% penalty on dense decode batches).
  * NVLink 4 ($TP=2$ on dual-H100): $\beta_{\text{fabric}} \approx 0.98$ (2% communication overhead).

### 3.3 $\Delta_{\text{LoRA}}(r, k)$: Multi-Tenant Adapter Expansion Tax
* **Physical Dimension:** Additive latency per token and multiplicative VRAM overhead:
  $$\text{TPOT}_{\text{LoRA}} = \text{TPOT}_{\text{Base}} + \Delta_{\text{time}}(r, k)$$
  $$\text{VRAM}_{\text{LoRA}} = \sum_{j=1}^{k} \left( 2 \times d_{\text{model}} \times r_j \times N_{\text{layers}} \times 2 \text{ bytes} \right)$$
* **Calibration Protocol:** Sweeping adapter ranks ($r \in \{8, 16, 64\}$) under active concurrent adapter switching ($k \in \{1, 2, 4, 8\}$).
* **Reference Baselines:**
  * Base Mistral-7B: $\text{TPOT} = 37.8\text{ ms/tok}$.
  * Single LoRA ($r=16$): $\Delta_{\text{time}} = +3.2\text{ ms/tok}$ (8.4% latency tax).
  * Active Dual LoRA ($r=64$): $\Delta_{\text{time}} = +5.5\text{ ms/tok}$ (14.5% latency tax).

### 3.4 $\kappa_{\text{runtime}}(\text{Optimizations})$: Engine Governance Gain Multiplier
* **Physical Dimension:** Multiplier on concurrent user density per node before knee collapse:
  $$\kappa_{\text{runtime}} = \prod_{m \in \text{M}} \gamma_m$$
  Where $m$ represents runtime engine optimizations:
  * $\gamma_{\text{ChunkedPrefill}} = 1.40$ (Prevents long-prompt queue starvation).
  * $\gamma_{\text{PrefixCaching}} = 1.65$ (Reuses system prompts and RAG contexts; TTFT drops to $<30\text{ ms}$).
  * $\gamma_{\text{FP8\_KVCache}} = 1.85$ (Halves KV-Cache byte footprint, doubling concurrent capacity in VRAM).
  * **Composite Production Factor:** $\kappa_{\text{runtime}} \approx 2.10\times$ capacity gain over unoptimized default configuration.

---

## 4. Workload Representation: Realistic Trace Replay

Synthetic constant-length prompts create artificial harmonics in GPU batching engines. The benchmarking harness must execute **Trace Replay** using empirical distributions derived from global production workloads (ShareGPT and LMSYS Chatbot Arena):

### 4.1 The 4 Standard Enterprise Workload Profiles

| Workload Profile | Share of Traffic | Prompt Distribution ($L_{\text{in}}$) | Output Distribution ($L_{\text{out}}$) | Dominant Bottleneck |
| :--- | :---: | :--- | :--- | :--- |
| **1. Conversational Chat** | 50% | Log-Normal ($\mu=120, \sigma=0.6$) | Normal ($\mu=60, \sigma=15$) | Decode Bandwidth |
| **2. Code Generation (Copilot)** | 30% | Log-Normal ($\mu=650, \sigma=0.8$) | Log-Normal ($\mu=180, \sigma=0.5$) | Balanced Prefill/Decode |
| **3. Document Audit / RAG** | 15% | Bimodal ($\mu_1=1500, \mu_2=3500$) | Normal ($\mu=250, \sigma=50$) | Prefill Compute & KV-Cache |
| **4. Deep Reasoning (Chain-of-Thought)** | 5% | Normal ($\mu=400, \sigma=50$) | Log-Normal ($\mu=600, \sigma=0.7$) | Decode Compute & Time |

### 4.2 Arrival Distribution Modeling
Rather than synchronous burst injection ($t=0.000$), requests are dispatched via an asynchronous non-homogeneous **Poisson Process**:
$$P(k \text{ arrivals in interval } \Delta t) = \frac{(\lambda \Delta t)^k e^{-\lambda \Delta t}}{k!}$$
Inter-arrival delays are generated using exponentially distributed random variables:
$$\Delta t_{\text{arrival}} = -\frac{\ln(U)}{\lambda}, \quad U \sim \text{Uniform}(0, 1)$$

---

## 5. Semantic Quality Gate: The "No-Degradation" Invariant

A high-performance benchmark is scientifically invalid if runtime optimizations compromise model output accuracy. Any candidate engine configuration (e.g., FP8 KV-Cache, context window clipping, speculative draft verification) must pass an automated **Dual-Track Semantic Quality Gate**:

```
+---------------------------------------------------------------------------------------+
|                               SEMANTIC QUALITY GATE                                   |
+---------------------------------------------------------------------------------------+
         |                                                               |
         v                                                               v
  [Track A: Coding]                                             [Track B: Reasoning]
  HumanEval-Subset (25 challenges)                              GSM8K-Subset (25 problems)
  Metric: Pass@1 Python Syntax & Test Pass                      Metric: Exact Match Numerical Answer
  Threshold: Delta_Accuracy >= -0.5%                            Threshold: Delta_Accuracy >= -0.5%
```

### 5.1 Protocol Execution
1. **Baseline Evaluation ($T_{\text{idle}}$):** Execute the 50 validation problems sequentially against the unoptimized base model in FP16 precision. Record exact solutions and execution times.
2. **Stress-State Evaluation ($T_{\text{saturated}}$):** Execute the identical 50 validation problems in flight during the peak saturation step (C=40 concurrent trace clients) with candidate optimizations enabled (`--kv-cache-dtype=fp8`, `--enable-chunked-prefill`).
3. **Certification Constraint:**
   $$\text{Accuracy}_{\text{Tuned}} \ge \text{Accuracy}_{\text{Base}} - 0.01 \quad (\Delta_{\text{accuracy}} \le 1.0\%)$$
   Configurations failing this gate are discarded from sizing calculations regardless of throughput gains.

---

## 6. Factorial Design of Experiments (Orthogonal DOE Matrix)

To eliminate confounding variables, the benchmarking pipeline executes an orthogonal **$2^k$ Factorial Ablation Matrix**:

| Experiment ID | Node Topology | Engine Flags Profile | Workload Profile | Concurrency Steps | Objectives |
| :---: | :---: | :--- | :--- | :---: | :--- |
| **EXP-01** | 1 Node (2x L4) | Vanilla FP16 Default | Workload 1 (Chat) | 5, 15, 25, 35, 50 | Calibrate baseline single-node knee ($C_{\text{base}}$). |
| **EXP-02** | 2 Nodes (4x L4) | Vanilla FP16 Default | Workload 1 (Chat) | 10, 30, 50, 70, 100 | Calibrate horizontal scaling efficiency ($\eta_{\text{scale}}$). |
| **EXP-03** | 2 Nodes (4x L4) | + Chunked Prefill | Workload 3 (Long RAG) | 10, 25, 45, 60 | Isolate Head-of-Line prefill elimination gain ($\gamma_{\text{cp}}$). |
| **EXP-04** | 2 Nodes (4x L4) | + Prefix Caching (Radix) | Workload 2 (Copilot) | 10, 25, 45, 60 | Isolate prompt context reuse acceleration ($\gamma_{\text{pc}}$). |
| **EXP-05** | 2 Nodes (4x L4) | + FP8 KV-Cache | Workload 4 (Reasoning) | 10, 25, 45, 60 | Isolate VRAM memory compression capacity gain ($\gamma_{\text{fp8}}$). |
| **EXP-06** | 2 Nodes (4x L4) | Full Production Tuned | Mixed Enterprise Blend | 15, 35, 60, 85, 110 | Certify global maximum Goodput ($\lambda_{\text{SLA}}$). |

---

## 7. Mathematical Mapping to the Canonical Sizing Calculator

Every record persisted to SQLite `benchmarks.db` updates the sizing model's analytical parameter table:

### 7.1 Goodput Saturation Knee Formula
For a given hardware configuration, the Goodput Knee $C_{\text{Goodput}}$ is calculated via regression:
$$C_{\text{Goodput}} = \max \left\{ C \;\middle|\; P(\text{TTFT}_C \le 1.0\text{ s}) \ge 0.99 \land P(\text{TPOT}_C \le 60\text{ ms}) \ge 0.95 \right\}$$

### 7.2 Required Node Count Estimation
Given an enterprise tenant's peak concurrent users $U_{\text{peak}}$, target vertical peak-to-average ratio $\text{PAR}$, and selected runtime maturity profile:
$$N_{\text{nodes}} = \left\lceil \frac{U_{\text{peak}}}{C_{\text{Goodput}}(\text{Runtime Profile})} \right\rceil$$

### 7.3 Total Cost of Ownership (TCO) Amortization Formula
$$\text{Cost}_{\text{1k\_tokens}} = \frac{N_{\text{nodes}} \times \text{Cost}_{\text{hourly\_node}} + \text{Cost}_{\text{gateway\_overhead}}}{\text{Goodput}_{\text{TPS}} \times 3600} \times 1000$$

---

## 8. Summary Checklist for Execution Readiness

- [x] Schema initialized with sub-second telemetry and WAL mode in `pocs/elastic-multi-gpu-inference/data/benchmarks.db`.
- [x] Zero-Hardcoding and Language Decoupling verified with zero non-English strings.
- [x] Continuous non-blocking hardware sampling active via Prometheus exporter.
- [x] Dual-track accuracy evaluation harness ready for HumanEval and GSM8K subsets.
- [x] Cluster topology verified: 2x Spot Nodes (4x NVIDIA L4) ready in Zurich (`europe-west6-b`).
