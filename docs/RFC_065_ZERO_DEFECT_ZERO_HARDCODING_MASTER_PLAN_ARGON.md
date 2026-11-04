# RFC 065: UNIVERSAL ZERO-DEFECT & ZERO-HARDCODING IMPLEMENTATION PLAN

**Status:** RATIFIED & BINDING  
**Target Architecture:** Universal Enterprise AI Infrastructure TCO, Physics & Actuarial Engine  
**Compliance Standard:** Zero-Defect, Zero-Hardcoding, 100% Pure Technical English Codebase, IEEE 754 Exemption via Fixed-Point Decimal Arithmetic  

---

## SECTION 1: UNIVERSAL LOCALIZATION & DYNAMIC TAXONOMY ARCHITECTURE

### 1.1 Strict Linguistic Decoupling Mandate
1. **Source Code Linguistic Purity:** Every file within `src/` and `tests/`—including module names, class identifiers, method signatures, variable names, type annotations, docstrings, comments, and raised exception class names—must be written exclusively in pure Technical English.
2. **Zero Literal Strings in Domain Logic:** Domain entities, value objects, and domain services (`src/domain/`) are strictly forbidden from emitting hardcoded human-readable sentences. Every diagnostic message, gate violation reason, architectural recommendation, or error trace must emit a deterministic `i18n_key` (e.g., `"gate.phy.002.violation"`) coupled with a structured, type-safe dictionary of interpolation parameters (`Dict[str, Union[str, int, Decimal]]`).
3. **Runtime Resolution Boundary:** Translation resolution occurs exclusively at the outermost presentation adapters (`src/presentation/ui/` and `src/infrastructure/exporters/`). The domain layer remains completely agnostic of the active locale.

### 1.2 Internationalization Architecture (`config/locales.json`)
Translation keys follow a strict hierarchical dot-notation namespace: `<domain>.<subdomain>.<entity>.<attribute>`. At application bootstrap, the `LocalizationRegistry` validates that all registered locales possess 100% key-set parity and identical interpolation placeholder signatures (`{placeholder_name}`). If any key or placeholder is missing in any supported language, the system fails fast during initialization with a `LocalizationParityError`.

#### Complete Production Schema (`config/locales.json`)
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "version": "1.0.0",
  "default_locale": "en",
  "supported_locales": ["en", "es"],
  "translations": {
    "en": {
      "app.header.title": "Enterprise AI Infrastructure Actuarial & Physics Engine",
      "app.header.subtitle": "Deterministic Roofline Sizing, Open FAIR Risk Modeling & GAAP/IFRS TCO",
      "domain.questionnaire.paradigm.on_premise": "100% On-Premise Sovereign Cluster",
      "domain.questionnaire.paradigm.cloud_native": "100% Cloud-Native Elastic Serverless/Dedicated",
      "domain.questionnaire.paradigm.hybrid_burst": "Hybrid Architecture (On-Premise Base + Cloud Bursting)",
      "domain.questionnaire.deadlock.resolution": "Mutual Sovereignty/Financial Veto Deadlock Detected: Forcing Sovereign Colocation with Vendor-Managed OPEX Lease.",
      "domain.roofline.regime.compute_bound": "Compute-Bound Regime (FLOPs Limited)",
      "domain.roofline.regime.memory_bound": "Memory-Bandwidth-Bound Regime (HBM Limited)",
      "domain.roofline.oom.error": "Out-Of-Memory (OOM) across all topology permutations for model '{model_id}' requiring {required_gb} GB VRAM.",
      "gate.phy.001.violation": "GATE-PHY-001 Violation: Computed rack power density ({actual_kw} kW/rack) exceeds facility structural ceiling ({limit_kw} kW/rack).",
      "gate.phy.002.violation": "GATE-PHY-002 Violation: Rack thermal density ({actual_kw} kW/rack) exceeds 35.00 kW threshold for '{cooling_type}'. Direct-to-Chip Liquid Cooling (DLC) or Immersion is mandatory.",
      "gate.phy.003.violation": "GATE-PHY-003 Violation: Specified PUE ({actual_pue}) violates the Carnot thermodynamic floor ({min_pue}).",
      "gate.sil.001.violation": "GATE-SIL-001 Violation: Aggregate VRAM utilization ({utilization_pct}%) exceeds the mandatory 90.00% runtime safety ceiling (10.00% fragmentation/CUDA context reserve).",
      "gate.sil.002.violation": "GATE-SIL-002 Violation: HBM memory bus utilization ({bus_utilization_pct}%) exceeds the 85.00% non-linear queueing saturation ceiling.",
      "gate.fin.001.violation": "GATE-FIN-001 Violation: Computed 36-month TCO ({tco_amount}) violates the strict positive economic floor (> 0.00).",
      "gate.fin.002.violation": "GATE-FIN-002 Violation: Amortization horizon ({months} months) or salvage ratio ({salvage_pct}%) violates GAAP/IFRS accounting bounds (36-60 months, max 35.00% salvage).",
      "actuarial.risk.on_prem_sle": "Single Loss Expectancy (Silicon Field Replacement & Downtime SLA Penalty)",
      "actuarial.risk.cloud_spot_sle": "Single Loss Expectancy (Spot Instance Preemption & Cold-Start Weight Streaming)",
      "tco.breakeven.infinite": "Infinite (On-Premise Monthly OpEx Exceeds Cloud Monthly OpEx)"
    },
    "es": {
      "app.header.title": "Motor Actuarial y de Física para Infraestructura de IA Empresarial",
      "app.header.subtitle": "Dimensionamiento Determinista Roofline, Modelado de Riesgo Open FAIR y TCO GAAP/IFRS",
      "domain.questionnaire.paradigm.on_premise": "Clúster Soberano 100% On-Premise",
      "domain.questionnaire.paradigm.cloud_native": "100% Cloud-Native Elástico (Serverless/Dedicado)",
      "domain.questionnaire.paradigm.hybrid_burst": "Arquitectura Híbrida (Base On-Premise + Desborde Cloud)",
      "domain.questionnaire.deadlock.resolution": "Bloqueo Mutuo de Veto (Soberanía vs. Finanzas) Detectado: Forzando Colocación Soberana con Arrendamiento OPEX Gestionado.",
      "domain.roofline.regime.compute_bound": "Régimen Limitado por Cómputo (FLOPs)",
      "domain.roofline.regime.memory_bound": "Régimen Limitado por Ancho de Banda de Memoria (HBM)",
      "domain.roofline.oom.error": "Memoria Insuficiente (OOM) en todas las permutaciones topológicas para el modelo '{model_id}' que requiere {required_gb} GB de VRAM.",
      "gate.phy.001.violation": "Violación GATE-PHY-001: La densidad de potencia por rack calculada ({actual_kw} kW/rack) supera el límite estructural de la instalación ({limit_kw} kW/rack).",
      "gate.phy.002.violation": "Violación GATE-PHY-002: La densidad térmica del rack ({actual_kw} kW/rack) supera el umbral de 35.00 kW para '{cooling_type}'. Es obligatoria la Refrigeración Líquida Directa al Chip (DLC) o Inmersión.",
      "gate.phy.003.violation": "Violación GATE-PHY-003: El PUE especificado ({actual_pue}) vulnera el límite termodinámico de Carnot ({min_pue}).",
      "gate.sil.001.violation": "Violación GATE-SIL-001: La utilización agregada de VRAM ({utilization_pct}%) supera el techo de seguridad obligatorio del 90.00% (reserva del 10.00% para fragmentación y contexto CUDA).",
      "gate.sil.002.violation": "Violación GATE-SIL-002: La utilización del bus de memoria HBM ({bus_utilization_pct}%) supera el techo de saturación no lineal de colas del 85.00%.",
      "gate.fin.001.violation": "Violación GATE-FIN-001: El TCO calculado a 36 meses ({tco_amount}) vulnera el suelo económico estrictamente positivo (> 0.00).",
      "gate.fin.002.violation": "Violación GATE-FIN-002: El horizonte de amortización ({months} meses) o el valor residual ({salvage_pct}%) vulnera los límites contables GAAP/IFRS (36-60 meses, máx. 35.00% residual).",
      "actuarial.risk.on_prem_sle": "Expectativa de Pérdida Única (Reemplazo de Silicio en Campo y Penalización SLA por Caída)",
      "actuarial.risk.cloud_spot_sle": "Expectativa de Pérdida Única (Desalojo de Instancia Spot y Streaming de Pesos en Arranque en Frío)",
      "tco.breakeven.infinite": "Infinito (El OpEx Mensual On-Premise Supera al OpEx Mensual Cloud)"
    }
  }
}
```

### 1.3 Universal Industry Vertical Registry (`config/taxonomies/verticals.json`)
Industry verticals and regulatory compliance frameworks are injected declaratively via JSON configuration. Adding a new regulatory regime or industry vertical requires zero code modifications.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "version": "1.0.0",
  "compliance_frameworks": {
    "ENS_ALTO": {
      "i18n_name_key": "compliance.ens_alto.name",
      "forbid_public_cloud": true,
      "mandate_air_gap": true,
      "min_redundancy_n_plus": 2,
      "sla_downtime_penalty_per_hour_usd": "25000.00"
    },
    "HIPAA": {
      "i18n_name_key": "compliance.hipaa.name",
      "forbid_public_cloud": false,
      "mandate_air_gap": false,
      "min_redundancy_n_plus": 1,
      "sla_downtime_penalty_per_hour_usd": "15000.00"
    },
    "DORA": {
      "i18n_name_key": "compliance.dora.name",
      "forbid_public_cloud": false,
      "mandate_air_gap": false,
      "min_redundancy_n_plus": 2,
      "sla_downtime_penalty_per_hour_usd": "50000.00"
    },
    "FEDRAMP_HIGH": {
      "i18n_name_key": "compliance.fedramp_high.name",
      "forbid_public_cloud": true,
      "mandate_air_gap": true,
      "min_redundancy_n_plus": 2,
      "sla_downtime_penalty_per_hour_usd": "40000.00"
    },
    "PCI_DSS_4": {
      "i18n_name_key": "compliance.pci_dss_4.name",
      "forbid_public_cloud": false,
      "mandate_air_gap": false,
      "min_redundancy_n_plus": 1,
      "sla_downtime_penalty_per_hour_usd": "20000.00"
    }
  },
  "verticals": {
    "BANKING_FINANCE": {
      "i18n_key": "vertical.banking_finance",
      "default_compliance": ["DORA", "PCI_DSS_4"],
      "default_par": "3.50",
      "target_ttft_ms": "250.00",
      "target_tpot_ms": "25.00"
    },
    "DEFENSE_NATIONAL_SECURITY": {
      "i18n_key": "vertical.defense_security",
      "default_compliance": ["ENS_ALTO", "FEDRAMP_HIGH"],
      "default_par": "1.80",
      "target_ttft_ms": "200.00",
      "target_tpot_ms": "20.00"
    },
    "HEALTHCARE_LIFE_SCIENCES": {
      "i18n_key": "vertical.healthcare",
      "default_compliance": ["HIPAA"],
      "default_par": "2.20",
      "target_ttft_ms": "400.00",
      "target_tpot_ms": "35.00"
    },
    "RETAIL_ECOMMERCE": {
      "i18n_key": "vertical.retail_ecommerce",
      "default_compliance": ["PCI_DSS_4"],
      "default_par": "12.00",
      "target_ttft_ms": "180.00",
      "target_tpot_ms": "18.00"
    },
    "TELECOM_CLOUD_SP": {
      "i18n_key": "vertical.telecom_cloud",
      "default_compliance": ["DORA"],
      "default_par": "2.80",
      "target_ttft_ms": "150.00",
      "target_tpot_ms": "15.00"
    }
  }
}
```

---

## SECTION 2: MATHEMATICAL EDGE-CASE DEFENSE & DEFENSIVE INVARIANTS

### 2.1 Exact Decimal Precision & Banker's Rounding Policy
1. **Complete Prohibition of `float`:** All domain calculations use Python's `decimal.Decimal` with global context precision set to `prec = 50` (`decimal.getcontext().prec = 50`) and rounding mode set to `decimal.ROUND_HALF_EVEN` (Banker's Rounding).
2. **Intermediate vs. Presentation Quantization:**
   - **Intermediate Operations:** Unquantized `Decimal` (50 significant digits) to eliminate cascading quantization drift across multi-stage Roofline and Open FAIR pipelines.
   - **Final Presentation & Audit Quantization:**
     - Currency (`USD`, `EUR`): `Decimal("0.01")` (`2` decimal places).
     - Hourly Cloud / Token Rates: `Decimal("0.0001")` (`4` decimal places).
     - Ratios, PUE, Utilisation, Probabilities, Affinities: `Decimal("0.0001")` (`4` decimal places).
     - Hardware Node/GPU Counts & Rack Units: Ceiling integer quantization via `.to_integral_value(rounding=ROUND_CEILING)` where physical indivisibility applies.

### 2.2 Mathematical Edge-Case Guards

| Edge Case Scenario | Failure Vector Without Guard | Deterministic Mathematical Guard & Domain Invariant |
| :--- | :--- | :--- |
| **Zero Baseline Traffic ($RPS_{\text{base}} = 0$) or Single Request** | Division by zero in throughput/concurrency equations or $0$ GPU allocation when an active cluster is requested. | Enforce minimum floor $RPS_{\text{effective}} = \max\left(RPS_{\text{base}}, \text{Decimal}("0.0001")\right)$. If an architecture is evaluated, minimum physical allocation is bounded below by $\ge 1$ valid Tensor-Parallel node group ($N_{\text{GPU}} \ge TP_{\min}$). |
| **Massive Concurrency ($N_{\text{users}} > 100,000$)** | Integer overflow in batch size or KV-cache exceeding single-cluster addressability, triggering infinite loops in TP/PP search. | Cap maximum per-replica continuous batch size $B_{\text{max\_replica}}$ to the Roofline SLA knee-point $B_{\text{knee}}$ where $TPOT(B) \le TPOT_{\text{SLA}}$ and $M_{\text{VRAM}}(B) \le 0.90 \times VRAM_{\text{group}}$. Horizontal replicas scale linearly: $R_{\text{replicas}} = \lceil B_{\text{global}} / B_{\text{max\_replica}} \rceil$. |
| **Extreme Context ($L_{\text{ctx}} \in [128\text{k}, 1\text{M}]$ under GQA / MLA)** | Quadratic prefill FLOP explosion ($O(L_{\text{seq}}^2)$) or KV-Cache exceeding single-node VRAM. | Include explicit quadratic attention FLOP term $4 \cdot B \cdot L_{\text{in}}^2 \cdot n_{\text{layers}} \cdot d_{\text{model}}$ in Prefill TTFT. If $M_{\text{weights}} + M_{\text{KV}}(1, L_{\text{ctx}}) + M_{\text{act}} > 0.90 \times (8 \times VRAM_{\text{GPU}})$, automatically increment Pipeline Parallelism $PP \in \{1, 2, 4, 8, 16\}$ across multi-node InfiniBand fabrics until memory invariant `GATE-SIL-001` is satisfied. |
| **Extreme Peak-to-Average Ratio ($PAR > 50.0$)** | Over-provisioning idle On-Premise silicon by $50\times$, destroying CapEx ROI. | Whenever $PAR > \tau_{\text{PAR}}$ (default $\tau_{\text{PAR}} = \text{Decimal}("1.5000")$) and `forbid_public_cloud == False`, size On-Premise silicon strictly for $RPS_{\text{base}}$ and route $(PAR - 1.0) \times RPS_{\text{base}}$ integrated over burst duty cycle $\delta_{\text{burst}}$ to Cloud Bursting. |
| **Zero-Cost Inputs (Free Electricity / $0 CapEx Grants)** | Division by zero in ROI/Payback calculations or false-positive breach of `GATE-FIN-001`. | Individual line items ($C_{\text{elec}}, C_{\text{capex}}$) permit $\ge \text{Decimal}("0.00")$, but total 36-month TCO must strictly satisfy $TCO_{36\text{m}} > \text{Decimal}("0.00")` (`GATE-FIN-001`). In payback calculations, if $\Delta OpEx_{\text{monthly}} = OpEx_{\text{cloud}} - OpEx_{\text{onprem}} \le \text{Decimal}("0.00")$, return `BreakevenStatus.INFINITE` (`payback_months = None`) without dividing. |
| **Erlang-B Factorial Overflow ($N_{\text{nodes}} > 500$)** | Computing $E^N / N!$ directly causes overflow or extreme latency. | Compute Erlang-B iteratively via exact numerically stable recursion: $B(E, 0) = 1$, $B(E, k) = \frac{E \cdot B(E, k-1)}{k + E \cdot B(E, k-1)}$ for $k = 1 \dots N_{\text{spares}}$. |

---

## SECTION 3: PRODUCTION SPECIFICATION FOR DOMAIN SERVICES (`src/domain/services/`)

### 3.1 `QuestionnaireDecisionEngine` (`src/domain/services/questionnaire_engine.py`)

#### Mathematical Formulation
1. **Weighted Affinity Normalization:**
   Given $M$ answered questions, where question $i$ has weight $w_i \in (0, 10]$ and selected option $j$ has raw affinity scores $a_{i,j}^{\text{onprem}}, a_{i,j}^{\text{cloud}} \in [0, 100]$:
   $$S_{\text{raw}}^{\text{onprem}} = \sum_{i=1}^{M} w_i \cdot a_{i,j}^{\text{onprem}}, \quad S_{\text{raw}}^{\text{cloud}} = \sum_{i=1}^{M} w_i \cdot a_{i,j}^{\text{cloud}}$$
   $$S_{\text{total}} = \max\left(S_{\text{raw}}^{\text{onprem}} + S_{\text{raw}}^{\text{cloud}}, \text{Decimal}("0.0001")\right)$$
   $$S_{\text{onprem}} = \frac{S_{\text{raw}}^{\text{onprem}}}{S_{\text{total}}}, \quad S_{\text{cloud}} = \frac{S_{\text{raw}}^{\text{cloud}}}{S_{\text{total}}}$$

2. **Boolean Veto Algebra & Deadlock Resolution:**
   Let $V_{\text{cloud}}$ be the boolean disjunction of all `veto_cloud` flags across selected answers and active compliance frameworks (`forbid_public_cloud`). Let $V_{\text{onprem}}$ be the boolean disjunction of all `veto_onprem` flags (e.g., strict zero-CapEx mandate).
   - **Case 1 (Mutual Deadlock: $V_{\text{cloud}} \land V_{\text{onprem}} = \text{True}$):** Neither pure public cloud nor traditional CapEx on-premise is legally/financially permissible. The engine resolves the deadlock deterministically without throwing an unhandled exception: it sets `recommended_paradigm = DeploymentParadigm.ON_PREMISE`, sets `deadlock_resolved = True`, overrides financial financing mode to `SOVEREIGN_COLOCATION_OPEX_LEASE`, and emits `i18n_key = "domain.questionnaire.deadlock.resolution"`.
   - **Case 2 ($V_{\text{cloud}} = \text{True} \land V_{\text{onprem}} = \text{False}$):** Forces `DeploymentParadigm.ON_PREMISE` ($S_{\text{onprem}} = 1.0000, S_{\text{cloud}} = 0.0000$).
   - **Case 3 ($V_{\text{onprem}} = \text{True} \land V_{\text{cloud}} = \text{False}$):** Forces `DeploymentParadigm.CLOUD_NATIVE` ($S_{\text{onprem}} = 0.0000, S_{\text{cloud}} = 1.0000$).
   - **Case 4 (No Vetoes Active):** If $PAR = \frac{RPS_{\text{peak}}}{RPS_{\text{base}}} > \tau_{\text{PAR}}$ (default $1.5000$) and $|S_{\text{onprem}} - S_{\text{cloud}}| \le \text{Decimal}("0.3500")$, selects `DeploymentParadigm.HYBRID_BURST`. Otherwise selects `ON_PREMISE` if $S_{\text{onprem}} \ge S_{\text{cloud}}$, else `CLOUD_NATIVE`.

---

### 3.2 `RooflinePhysicsEngine` (`src/domain/services/roofline_physics_engine.py`)

#### Mathematical Formulation
1. **Polymorphic VRAM Sizing ($M_{\text{total}}$):**
   - **Model Weights ($M_{\text{weights}}$):**
     $$M_{\text{weights}} = P_{\text{params}} \times b_{\text{weights}} \times (1 + \alpha_{\text{quant\_overhead}})$$
     where $b_{\text{weights}} \in \{0.5, 1.0, 2.0, 4.0\}$ bytes/param and $\alpha_{\text{quant\_overhead}} = \text{Decimal}("0.0500")$ for sub-8-bit quantization scales/zero-points (else $0$).
   - **Polymorphic KV Cache ($M_{\text{KV}}$) for Concurrent Batch $B$ and Sequence Length $L_{\text{seq}} = L_{\text{in}} + L_{\text{out}}$:**
     - **Multi-Head Attention (`MHA`):**
       $$M_{\text{KV}} = 2 \cdot n_{\text{layers}} \cdot n_{\text{heads}} \cdot d_{\text{head}} \cdot L_{\text{seq}} \cdot B \cdot b_{\text{kv}}$$
     - **Grouped-Query Attention (`GQA`):**
       $$M_{\text{KV}} = 2 \cdot n_{\text{layers}} \cdot n_{\text{kv\_heads}} \cdot d_{\text{head}} \cdot L_{\text{seq}} \cdot B \cdot b_{\text{kv}}$$
     - **Multi-Head Latent Attention (`MLA` - e.g., DeepSeek-V3/R1):**
       $$M_{\text{KV}} = n_{\text{layers}} \cdot \left(d_{c\_kv} + d_{rope\_k}\right) \cdot L_{\text{seq}} \cdot B \cdot b_{\text{kv}}$$
       where $d_{c\_kv}$ is the compressed KV latent dimension (e.g., $512$) and $d_{rope\_k}$ is the decoupled RoPE key dimension (e.g., $64$).
   - **Activation & Transient Scratchpad Buffers ($M_{\text{act}}$):**
     $$M_{\text{act}} = B \cdot L_{\text{in}} \cdot d_{\text{model}} \cdot b_{\text{act}} \cdot \left(4 + 2 \cdot \frac{d_{\text{ffn}}}{d_{\text{model}}}\right) \cdot \frac{1}{TP}$$
   - **Per-GPU Memory Allocation under Tensor ($TP$) and Pipeline ($PP$) Parallelism:**
     $$M_{\text{GPU}}(TP, PP, B) = \frac{M_{\text{weights}} + M_{\text{KV}}(B)}{TP \cdot PP} + M_{\text{act}}(TP, B) + M_{\text{CUDA\_context}}$$
     Subject to `GATE-SIL-001`: $M_{\text{GPU}}(TP, PP, B) \le 0.9000 \times VRAM_{\text{GPU}}$.

2. **Exact $TP \in \{1, 2, 4, 8\}$ and $PP \in \{1, 2, 4, 8, 16\}$ Allocation Algorithm:**
   Iterate over $PP \in \{1, 2, 4, 8, 16\}$ and $TP \in \{1, 2, 4, 8\}$ in ascending order of total GPUs per replica ($G_{\text{replica}} = TP \times PP$). Select the minimal $G_{\text{replica}}$ where:
   - $M_{\text{GPU}}(TP, PP, B=1) \le 0.9000 \times VRAM_{\text{GPU}}$
   - $TP$ divides $n_{\text{kv\_heads}}$ evenly (for MHA/GQA) or divides $n_{\text{heads}}$ evenly (for MLA).
   - Determine maximum batch size per replica $B_{\text{max\_replica}} \ge 1$ that satisfies both `GATE-SIL-001` ($\le 90\%$ VRAM) and the target SLA latency equations below.
   - Compute required horizontal replicas $R_{\text{replicas}} = \max\left(1, \left\lceil \frac{RPS_{\text{target}} \cdot (TTFT + L_{\text{out}} \cdot TPOT)}{B_{\text{max\_replica}}} \right\rceil\right)$. Total cluster GPUs: $N_{\text{GPU}} = R_{\text{replicas}} \times TP \times PP$.

3. **Prefill TTFT (Compute-Bound) & Decode TPOT (Memory-Bandwidth-Bound):**
   - **Prefill FLOPs per Request ($FLOPs_{\text{prefill}}$):**
     $$FLOPs_{\text{prefill}} = 2 \cdot P_{\text{active}} \cdot L_{\text{in}} + 4 \cdot n_{\text{layers}} \cdot d_{\text{model}} \cdot L_{\text{in}}^2$$
     (where $P_{\text{active}}$ equals total parameters for Dense models, or active parameters per token for MoE models).
   - **Time To First Token ($TTFT$ in seconds):**
     $$TTFT = \frac{B \cdot FLOPs_{\text{prefill}}}{TP \cdot PP \cdot TFLOPS_{\text{GPU}} \cdot 10^{12} \cdot MFU} + \frac{2 \cdot (TP - 1) \cdot B \cdot L_{\text{in}} \cdot d_{\text{model}} \cdot b_{\text{act}} \cdot n_{\text{layers}}}{TP \cdot BW_{\text{interconnect}}}$$
   - **Time Per Output Token ($TPOT$ in seconds):**
     $$Bytes_{\text{step}}(B) = M_{\text{weights\_active}} + M_{\text{KV}}(B)$$
     $$TPOT = \frac{Bytes_{\text{step}}(B)}{TP \cdot PP \cdot BW_{\text{HBM}} \cdot 10^{12} \cdot MBU} + \frac{2 \cdot (TP - 1) \cdot B \cdot d_{\text{model}} \cdot b_{\text{act}} \cdot n_{\text{layers}}}{TP \cdot BW_{\text{interconnect}}}$$
     Subject to `GATE-SIL-002`: Effective bus saturation $MBU_{\text{effective}} \le \text{Decimal}("0.8500")$.

---

### 3.3 `OpenFairActuarialEngine` (`src/domain/services/open_fair_engine.py`)

#### Mathematical Formulation
1. **On-Premise Silicon Failure Modeling:**
   - Given device Mean Time Between Failures $MTBF_{\text{hours}}$ (or Annualized Failure Rate $AFR = 1 - \exp(-8760 / MTBF_{\text{hours}})$, linearized for small rates as $AFR = \frac{8760}{MTBF_{\text{hours}}}$):
   - Cluster Loss Event Frequency (TEF / LEF):
     $$\lambda_{\text{cluster}} = N_{\text{nodes}} \times AFR$$
   - Offered repair traffic in Erlangs ($E$) given Mean Time To Repair $MTTR_{\text{hours}}$:
     $$E = N_{\text{nodes}} \times \frac{MTTR_{\text{hours}}}{MTBF_{\text{hours}}}$$
   - Probability of Cold-Spare Depletion ($P_{\text{depletion}}$) with $K$ on-site cold spares via exact iterative Erlang-B:
     $$B(E, 0) = 1, \quad B(E, k) = \frac{E \cdot B(E, k-1)}{k + E \cdot B(E, k-1)} \quad \text{for } k = 1, \dots, K$$
     $$P_{\text{depletion}} = B(E, K)$$
   - Single Loss Expectancy ($SLE_{\text{onprem}}$) and Annualized Loss Expectancy ($ALE_{\text{onprem}}$):
     $$SLE_{\text{onprem}} = C_{\text{field\_replacement}} + P_{\text{depletion}} \cdot MTTR_{\text{hours}} \cdot C_{\text{SLA\_penalty\_per\_hour}}$$
     $$ALE_{\text{onprem}} = \lambda_{\text{cluster}} \times SLE_{\text{onprem}}$$

2. **Cloud Spot Preemption Modeling:**
   - Given daily Spot instance eviction probability $p_{\text{evict\_daily}} \in [0, 1]$ and burst duty cycle $\delta_{\text{burst}} \in [0, 1]$:
     $$LEF_{\text{spot\_annual}} = 365 \cdot p_{\text{evict\_daily}} \cdot \delta_{\text{burst}} \cdot N_{\text{spot\_instances}}$$
   - Cold Rebuild Penalty Duration ($T_{\text{rebuild\_hours}}$) for container image pull ($S_{\text{image\_GB}}$) and model weight streaming ($M_{\text{weights\_GB}}$) over network ingress bandwidth ($BW_{\text{ingress\_Gbps}}$):
     $$T_{\text{rebuild\_hours}} = \frac{\left(S_{\text{image\_GB}} + M_{\text{weights\_GB}}\right) \times 8}{BW_{\text{ingress\_Gbps}} \times 3600} + \frac{T_{\text{init\_seconds}}}{3600}$$
   - Cloud Spot $SLE_{\text{cloud}}$ and $ALE_{\text{cloud}}$:
     $$SLE_{\text{cloud}} = T_{\text{rebuild\_hours}} \times \left(C_{\text{SLA\_penalty\_per\_hour}} + C_{\text{ondemand\_fallback\_premium\_per\_hour}}\right)$$
     $$ALE_{\text{cloud}} = LEF_{\text{spot\_annual}} \times SLE_{\text{cloud}}$$

---

### 3.4 `CfoActuarialGate` (`src/domain/services/cfo_actuarial_gate.py`)

#### Seven Inviolable Constitutional Invariants
The `CfoActuarialGate` evaluates every candidate architecture against 7 deterministic constitutional invariants. Any violation returns an immutable `GateViolation` containing the `gate_id`, `i18n_key`, `severity="FATAL"`, and structured context parameters, halting financial sign-off:

| Gate ID | Domain | Mathematical Invariant Condition | Failure Trigger Condition |
| :--- | :--- | :--- | :--- |
| **`GATE-PHY-001`** | Facility Physics | $P_{\text{rack\_kW}} \le P_{\text{facility\_ceiling\_kW}}$ | Computed rack power density exceeds structural PDU/breaker rating. |
| **`GATE-PHY-002`** | Thermal Physics | $\text{If } P_{\text{rack\_kW}} > \text{Decimal}("35.00") \implies \text{Cooling} \in \{\text{DLC}, \text{IMMERSION}\}$ | Air cooling (`AIR_AISLE`) specified for $>35.00\text{ kW/rack}$ thermal density. |
| **`GATE-PHY-003`** | Thermodynamics | $PUE \ge \text{Decimal}("1.0800")$ | Specified Power Usage Effectiveness violates Carnot thermodynamic floor ($< 1.0800$). |
| **`GATE-SIL-001`** | Silicon VRAM | $\frac{M_{\text{GPU}}}{VRAM_{\text{GPU}}} \le \text{Decimal}("0.9000")$ | Aggregate VRAM utilization exceeds $90.00\%$ (violates $10.00\%$ CUDA/fragmentation buffer). |
| **`GATE-SIL-002`** | Silicon Bus | $U_{\text{HBM\_bus}} \le \text{Decimal}("0.8500")$ | Memory bandwidth utilization exceeds $85.00\%$ non-linear queuing knee-point. |
| **`GATE-FIN-001`** | Financial Floor | $TCO_{\text{horizon}} > \text{Decimal}("0.00")$ | Total Computed TCO is $\le 0.00$ (prevents corrupted zero/negative pricing models). |
| **`GATE-FIN-002`** | GAAP / IFRS | $N_{\text{amort}} \in [36, 60] \land r_{\text{salvage}} \in [\text{Decimal}("0.0000"), \text{Decimal}("0.3500")]$ | Useful life outside $36\text{--}60$ months or salvage residual value exceeds $35.00\%$. |

---

### 3.5 `HybridTcoAggregator` (`src/domain/services/hybrid_tco_aggregator.py`)

#### Mathematical Formulation
1. **CapEx Linear Depreciation with Salvage Value Recovery:**
   $$CapEx_{\text{gross}} = N_{\text{nodes}} \cdot C_{\text{node}} + N_{\text{switches}} \cdot C_{\text{switch}} + N_{\text{racks}} \cdot C_{\text{rack\_engineering}}$$
   $$V_{\text{salvage}} = CapEx_{\text{gross}} \cdot r_{\text{salvage}}$$
   $$D_{\text{monthly}} = \frac{CapEx_{\text{gross}} - V_{\text{salvage}}}{N_{\text{amort\_months}}}$$
2. **Facility OpEx (35% Static Base + 65% Dynamic Load Scaling):**
   - Effective average cluster power ($P_{\text{IT\_avg\_kW}}$) given average cluster utilization $\bar{u} \in [0, 1]$:
     $$P_{\text{IT\_avg\_kW}} = N_{\text{nodes}} \cdot P_{\text{node\_TDP\_kW}} \cdot \left(\text{Decimal}("0.3500") + \text{Decimal}("0.6500") \cdot \bar{u}\right)$$
   - Monthly Power Cost ($OpEx_{\text{power\_monthly}}$) over $730\text{ hours/month}$:
     $$OpEx_{\text{power\_monthly}} = P_{\text{IT\_avg\_kW}} \cdot PUE \cdot 730 \cdot C_{\text{kWh}}$$
   - Total Monthly On-Premise OpEx ($OpEx_{\text{onprem\_monthly}}$):
     $$OpEx_{\text{onprem\_monthly}} = OpEx_{\text{power\_monthly}} + N_{\text{racks}} \cdot C_{\text{colo\_per\_rack\_month}} + \frac{CapEx_{\text{gross}} \cdot r_{\text{oem\_carepack\_annual}} + ALE_{\text{onprem}}}{12}$$
3. **Cloud OpEx (Reserved Baseline + Spot/On-Demand Burst + Storage + Egress):**
   $$OpEx_{\text{cloud\_monthly}} = N_{\text{reserved\_GPUs}} \cdot 730 \cdot C_{\text{reserved\_hr}} + N_{\text{burst\_GPUs}} \cdot 730 \cdot \delta_{\text{burst}} \cdot C_{\text{burst\_hr}} + S_{\text{SSD\_GB}} \cdot C_{\text{SSD\_GB\_month}} + E_{\text{egress\_GB}} \cdot C_{\text{egress\_GB}} + \frac{ALE_{\text{cloud}}}{12}$$
4. **Breakeven Payback Horizon ($T_{\text{breakeven\_months}}$):**
   Comparing pure Cloud monthly spend ($OpEx_{\text{pure\_cloud\_monthly}}$) against On-Premise monthly cash outflow ($OpEx_{\text{onprem\_monthly}}$):
   $$\Delta_{\text{savings\_monthly}} = OpEx_{\text{pure\_cloud\_monthly}} - OpEx_{\text{onprem\_monthly}}$$
   $$\text{If } \Delta_{\text{savings\_monthly}} \le \text{Decimal}("0.00") \implies T_{\text{breakeven\_months}} = \text{None} \quad (\text{i18n\_key: } \texttt{"tco.breakeven.infinite"})$$
   $$\text{Else } T_{\text{breakeven\_months}} = \frac{CapEx_{\text{gross}}}{\Delta_{\text{savings\_monthly}}}$$

---

## SECTION 4: AUTOMATED TEST ORACLES & ZERO-DEFECT QUALITY GATES

### 4.1 AST Domain Purity Gate (`tests/architecture/test_domain_purity.py`)
```python
"""AST verification ensuring src/domain/ has zero external framework or I/O dependencies."""

import ast
from pathlib import Path
import pytest

FORBIDDEN_DOMAIN_IMPORTS = {
    "streamlit",
    "pandas",
    "numpy",
    "scipy",
    "plotly",
    "requests",
    "httpx",
    "sqlalchemy",
    "sqlite3",
    "os",
    "sys",
    "subprocess",
    "socket",
}


def get_domain_python_files() -> list[Path]:
    domain_root = Path("src/domain")
    return list(domain_root.rglob("*.py")) if domain_root.exists() else []


@pytest.mark.parametrize("file_path", get_domain_python_files())
def test_domain_layer_has_zero_forbidden_imports_and_zero_floats(file_path: Path) -> None:
    source_code = file_path.read_text(encoding="utf-8")
    tree = ast.parse(source_code, filename=str(file_path))

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_module = alias.name.split(".")[0]
                assert root_module not in FORBIDDEN_DOMAIN_IMPORTS, (
                    f"Forbidden import '{alias.name}' in domain file {file_path}:{node.lineno}"
                )
        elif isinstance(node, ast.ImportFrom) and node.module:
            root_module = node.module.split(".")[0]
            assert root_module not in FORBIDDEN_DOMAIN_IMPORTS, (
                f"Forbidden from-import '{node.module}' in domain file {file_path}:{node.lineno}"
            )
        elif isinstance(node, ast.Constant) and isinstance(node.value, float):
            pytest.fail(
                f"IEEE 754 float literal '{node.value}' detected in {file_path}:{node.lineno}. "
                "Use Decimal('...') string initialization exclusively."
            )
```

### 4.2 AST Zero Spanish Literals Gate (`tests/architecture/test_zero_spanish_literals.py`)
```python
"""AST & Token scanner guaranteeing 100% Pure Technical English across all files in src/."""

import ast
import re
import tokenize
from io import StringIO
from pathlib import Path
import pytest

SPANISH_DIACRITICS_REGEX = re.compile(r"[áéíóúÁÉÍÓÚñÑüÜ¡¿]")
SPANISH_LEXICON_REGEX = re.compile(
    r"\b(cálculo|calculo|configuración|configuracion|error_de|parámetro|parametro|"
    r"usuario|contraseña|empresa| coste|costo|precio|memoria|servidor|nube|"
    r"híbrido|hibrido|amortización|amortizacion|riesgo|fallo|refrigeración|"
    r"refrigeracion|potencia|ancho_de_banda|latencia|rendimiento)\b",
    re.IGNORECASE,
)


def get_all_source_files() -> list[Path]:
    src_root = Path("src")
    return list(src_root.rglob("*.py")) if src_root.exists() else []


@pytest.mark.parametrize("file_path", get_all_source_files())
def test_zero_spanish_in_identifiers_docstrings_strings_and_comments(file_path: Path) -> None:
    source_code = file_path.read_text(encoding="utf-8")
    tree = ast.parse(source_code, filename=str(file_path))

    # 1. Inspect AST Identifiers and String Constants
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            assert not SPANISH_DIACRITICS_REGEX.search(node.name), f"Spanish diacritic in identifier {node.name}"
            assert not SPANISH_LEXICON_REGEX.search(node.name), f"Spanish word in identifier {node.name}"
        elif isinstance(node, ast.Name):
            assert not SPANISH_DIACRITICS_REGEX.search(node.id), f"Spanish diacritic in variable {node.id}"
            assert not SPANISH_LEXICON_REGEX.search(node.id), f"Spanish word in variable {node.id}"
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            assert not SPANISH_DIACRITICS_REGEX.search(node.value), (
                f"Spanish diacritic in string literal at {file_path}:{node.lineno}"
            )
            assert not SPANISH_LEXICON_REGEX.search(node.value), (
                f"Spanish lexicon token in string literal at {file_path}:{node.lineno}"
            )

    # 2. Inspect All Comments via Tokenizer
    tokens = tokenize.generate_tokens(StringIO(source_code).readline)
    for tok_type, tok_string, start, _, _ in tokens:
        if tok_type == tokenize.COMMENT:
            assert not SPANISH_DIACRITICS_REGEX.search(tok_string), (
                f"Spanish diacritic in comment at {file_path}:{start[0]}"
            )
            assert not SPANISH_LEXICON_REGEX.search(tok_string), (
                f"Spanish lexicon token in comment at {file_path}:{start[0]}"
            )
```

### 4.3 Actuarial Invariants Property-Based Tests (`tests/domain/test_actuarial_invariants.py`)
- Uses `hypothesis` with `@given(...)` strategies generating `Decimal` inputs across extreme bounds:
  - Verifies `CfoActuarialGate` deterministically triggers `GATE-PHY-002` whenever `rack_power_kw > Decimal("35.00")` and `cooling_topology == CoolingTopology.AIR_AISLE`.
  - Verifies `GATE-PHY-003` triggers for all `pue < Decimal("1.0800")`.
  - Verifies `GATE-SIL-001` triggers for all `vram_utilization > Decimal("0.9000")`.
  - Verifies `OpenFairActuarialEngine.compute_erlang_b` is strictly monotonically decreasing with respect to spare count $K \in [0, 50]$ and strictly bounded within $[0.0000, 1.0000]$ without numerical overflow for $N_{\text{nodes}} = 10,000$.

### 4.4 Roofline Silicon Physics Tests (`tests/domain/test_roofline_physics.py`)
- Verifies exact polymorphic KV-cache sizing across `MHA`, `GQA`, and `MLA`: asserts $M_{\text{KV}}^{\text{MLA}} < M_{\text{KV}}^{\text{GQA}} < M_{\text{KV}}^{\text{MHA}}$ for identical layer/sequence parameters.
- Verifies $TP \in \{1, 2, 4, 8\}$ and $PP \in \{1, 2, 4, 8, 16\}$ topology solver accurately promotes a 405B FP16 model ($810\text{ GB}$ weights alone) to multi-node $TP=8, PP=2$ ($16 \times 80\text{ GB}$ H100 GPUs = $1,280\text{ GB}$ physical VRAM) to respect the $90\%$ `GATE-SIL-001` safety ceiling.
- Verifies edge-case defense for $RPS_{\text{base}} = \text{Decimal}("0.00")$ and $L_{\text{ctx}} = 1,000,000$ tokens without division by zero.

### 4.5 Playwright E2E Multi-Viewport & Multi-Locale Journey (`tests/e2e/test_ui_journeys.py`)
- Executes headless Chromium tests across 3 viewports (`1920x1080` Desktop, `1024x768` Tablet, `390x844` Mobile) and both locales (`en`, `es`):
  - Asserts zero raw `i18n_key` strings leak into the DOM (`expect(page.locator("body")).not_to_contain_text("domain.")`).
  - Asserts switching locale from `en` to `es` dynamically updates 100% of labels, gate diagnostics, and chart titles while keeping underlying numerical `Decimal` outputs bit-for-bit identical.

---

## SECTION 5: ARCHITECTURAL VERDICT

This Master Blueprint (RFC 065) is **RATIFIED**. All subsequent implementation phases must strictly adhere to the directory structure, `Decimal` fixed-point invariants, `locales.json` / `verticals.json` schemas, and AST quality gates defined herein. Zero deviations are permitted.