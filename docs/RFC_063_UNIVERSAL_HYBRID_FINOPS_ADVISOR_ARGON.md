# RFC 063: Universal Hybrid LLM FinOps Advisor — Architectural Blueprint

| Metadata | Details |
| :--- | :--- |
| **Document ID** | RFC-063-HYBRID-FINOPS |
| **Status** | RATIFIED / CONSTITUTIONAL MANDATE |
| **Authors** | Chief Systems Architect & Principal Actuary |
| **Target Audience** | Tier-1 Infrastructure Engineers (OpenAI/Anthropic/Google Core), Enterprise CIOs, CFOs |
| **Architecture Pattern** | Strict Hexagonal Architecture (Ports & Adapters), Zero-Hardcoding, Open FAIR Actuarial Engine |

---

## SECTION 1: DOMAIN ARCHITECTURE & PORTS (HEXAGONAL ARCHITECTURE)

### 1.1 Pure Domain Layer Boundaries & Isolation Rules
The core engine resides in `src/domain/`. It is governed by an absolute **Zero-Side-Effect Mandate**. The domain layer represents pure mathematical, physical, and actuarial state transitions.

```
                      +-------------------------------------------------------+
                      |                   PRIMARY ADAPTERS                    |
                      |   UI (Streamlit/React) | CLI | REST/gRPC API Gateways |
                      +-------------------------------------------------------+
                                                  |
                                                  v (Calls Inbound Ports)
+--------------------+      +-------------------------------------------+      +--------------------+
| SECONDARY ADAPTERS |      |             PURE DOMAIN CORE              |      | SECONDARY ADAPTERS |
| (Driven / Infra)   |      |                                           |      | (Driven / Infra)   |
|                    |      |  +-------------------------------------+  |      |                    |
| - Live Cloud APIs  | <--- |  |       Domain Services & Gates       |  | ---> | - Crypto Ledger DB |
| - OEM ERP Catalogs |      |  | - CfoActuarialGate (Pre-Flight)     |  |      | - OpenTelemetry    |
| - Currency FX APIs |      |  | - RooflinePhysicsEngine             |  |      | - I18n Locales     |
| - JSON/YAML Schemas|      |  | - OpenFairActuarialEngine           |  |      | - Redis TTL Cache  |
+--------------------+      |  | - HybridTcoAggregator               |  |      +--------------------+
                            |  +-------------------------------------+  |
                            |  |    Immutable Value Objects (VOs)    |  |
                            |  +-------------------------------------+  |
                            +-------------------------------------------+
```

#### Forbidden Imports in `src/domain/**`:
The following packages are strictly banned in the domain layer and enforced via automated Abstract Syntax Tree (AST) pre-commit hooks:
* **I/O & Filesystem:** `os`, `sys`, `pathlib`, `shutil`, `io`, `glob`, `pickle`, `sqlite3`.
* **Network & IPC:** `requests`, `urllib`, `httpx`, `aiohttp`, `socket`, `grpc`, `boto3`, `google.cloud`.
* **UI & Presentation:** `streamlit`, ` dash`, `flask`, `fastapi`, `jinja2`, `plotly`, `matplotlib`.
* **Data Manipulation Frameworks (Heavy):** `pandas`, `polars`, `sqlalchemy` (Domain uses pure Python `dataclasses`, `typing`, `decimal.Decimal`, and `math`).

### 1.2 Domain Value Objects & Ports Specification

All financial calculations must use `decimal.Decimal` with `ROUND_HALF_EVEN` (Banker's Rounding) to eliminate IEEE 754 floating-point drift across multi-million-dollar 60-month TCO projections.

```python
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Callable, Dict, Generic, List, Optional, Sequence, Tuple, TypeVar
from uuid import UUID

# ============================================================================
# IMMUTABLE DOMAIN VALUE OBJECTS (VOs)
# ============================================================================

class CurrencyCode(str):
    """ISO 4217 Currency Code validated dynamically via external registry."""
    pass

class IndustryVertical(str):
    """Dynamic industry taxonomy identifier (e.g., 'DEFENSE', 'TIER1_BANKING', 'RETAIL')."""
    pass

class DeploymentArchetype(str, Enum):
    SOVEREIGN_ON_PREM = "SOVEREIGN_ON_PREM_BARE_METAL"
    ELASTIC_CLOUD = "ELASTIC_PUBLIC_CLOUD_DEDICATED"
    HYBRID_CLOUD_BURST = "TIERED_HYBRID_SOVEREIGN_BURST"

@dataclass(frozen=True)
class MonetaryAmount:
    amount: Decimal
    currency: CurrencyCode

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            object.__setattr__(self, "amount", Decimal(str(self.amount)))

@dataclass(frozen=True)
class HardwareAcceleratorSpec:
    sku_id: str
    vendor: str
    architecture: str
    fp16_tflops: Decimal
    fp8_tflops: Decimal
    int8_tops: Decimal
    vram_gb: Decimal
    memory_bandwidth_gbps: Decimal
    interconnect_bandwidth_gbps: Decimal
    tdp_watts: Decimal
    annualized_failure_rate_pct: Decimal  # Silicon AFR (e.g., 0.025 for 2.5%)
    mttr_hours: Decimal                   # Mean Time To Repair/Replace for RMA

@dataclass(frozen=True)
class ServerChassisSpec:
    chassis_id: str
    accelerator_sku: HardwareAcceleratorSpec
    accelerators_per_chassis: int
    base_system_power_watts: Decimal      # CPU, NICs, NVMe, Fans
    rack_units_u: int
    capex_unit_price: MonetaryAmount
    oem_warranty_annual_pct: Decimal      # 24/7 Mission-Critical Care Pack % of CapEx
    salvage_value_pct_36m: Decimal
    salvage_value_pct_60m: Decimal

    @property
    def total_chassis_tdp_kw(self) -> Decimal:
        accel_watts = self.accelerator_sku.tdp_watts * Decimal(self.accelerators_per_chassis)
        return (accel_watts + self.base_system_power_watts) / Decimal("1000.0")

@dataclass(frozen=True)
class CloudInstancePricingSpec:
    provider_id: str
    region: str
    instance_type: str
    accelerator_sku: HardwareAcceleratorSpec
    accelerators_per_instance: int
    on_demand_hourly: MonetaryAmount
    reserved_1yr_hourly: MonetaryAmount
    reserved_3yr_hourly: MonetaryAmount
    spot_hourly_mean: MonetaryAmount
    spot_hourly_volatility_std: Decimal
    spot_preemption_probability_daily: Decimal  # Open FAIR LEF input
    cold_boot_rebuild_seconds: Decimal
    storage_gb_monthly: MonetaryAmount
    egress_gb_price: MonetaryAmount

@dataclass(frozen=True)
class DatacenterFacilitySpec:
    facility_id: str
    pue_rating: Decimal
    max_rack_power_density_kw: Decimal
    electricity_rate_per_kwh: MonetaryAmount
    colocation_rack_monthly_fee: MonetaryAmount
     cooling_topology: str  # "AIR_COOLED", "DIRECT_LIQUID_COOLED", "IMMERSION"

@dataclass(frozen=True)
class LlmWorkloadProfile:
    model_id: str
    parameter_count_billions: Decimal
    quantization_bits: int
    kv_cache_bits: int
    avg_input_tokens: int
    avg_output_tokens: int
    baseline_rps: Decimal
    peak_burst_rps: Decimal
    burst_duty_cycle_pct: Decimal  # % of time spent in peak burst state
    target_ttft_ms: Decimal        # Time To First Token SLA
    target_tpot_ms: Decimal        # Time Per Output Token SLA

# ============================================================================
# DOMAIN PORTS (INTERFACES)
# ============================================================================

class HardwareRegistryPort(ABC):
    """Driven Port for JIT resolution of hardware physics and chassis topologies."""
    
    @abstractmethod
    def get_accelerator_spec(self, sku_id: str) -> HardwareAcceleratorSpec:
        """Resolves silicon specs dynamically. Raises DomainLookupError if absent."""
        raise NotImplementedError

    @abstractmethod
    def list_compatible_chassis(
        self, min_vram_gb: Decimal, max_rack_kw: Decimal, target_currency: CurrencyCode
    ) -> Sequence[ServerChassisSpec]:
        """Queries catalog with TTL caching for on-premise chassis matching physical bounds."""
        raise NotImplementedError


class PricingProviderPort(ABC):
    """Driven Port for live cloud Spot/On-Demand pricing, Colocation rates, and FX conversion."""

    @abstractmethod
    def get_cloud_pricing(
        self, sku_id: str, region: Optional[str], target_currency: CurrencyCode
    ) -> Sequence[CloudInstancePricingSpec]:
        """Fetches live market rates with TTL expiration enforcement."""
        raise NotImplementedError

    @abstractmethod
    def convert_currency(
        self, amount: MonetaryAmount, target_currency: CurrencyCode
    ) -> MonetaryAmount:
        """Performs JIT institutional FX conversion."""
        raise NotImplementedError


@dataclass(frozen=True)
class QuestionnaireCriterionOption:
    option_key: str
    i18n_label_key: str
    on_prem_affinity_score: Decimal  # Normalized [0.0, 100.0]
    cloud_affinity_score: Decimal    # Normalized [0.0, 100.0]
    risk_ aversion_multiplier: Decimal

@dataclass(frozen=True)
class QuestionnaireItemSchema:
    question_id: str
    i18n_prompt_key: str
    weight: Decimal
    options: Sequence[QuestionnaireCriterionOption]

class AssessmentQuestionnairePort(ABC):
    """Driven Port loading dynamic, localized questionnaire schemas without static code dicts."""

    @abstractmethod
    def fetch_questionnaire_schema(
        self, industry: IndustryVertical, locale: str
    ) -> Sequence[QuestionnaireItemSchema]:
        raise NotImplementedError


@dataclass(frozen=True)
class ArchetypeRecommendationResult:
    recommended_archetype: DeploymentArchetype
    on_prem_composite_score: Decimal
    cloud_composite_score: Decimal
    divergence_delta: Decimal
    recommended_base_load_split_pct: Decimal  # e.g., 100% On-Prem for Base, 0% Cloud
    recommended_burst_load_split_pct: Decimal # e.g., 0% On-Prem for Burst, 100% Cloud
    strategic_rationale_i18n_keys: Sequence[str]

class ArchetypeRecommendationPort(ABC):
    """Inbound/Internal Domain Port executing the strategic decision matrix."""

    @abstractmethod
    def evaluate_responses(
        self,
        schema: Sequence[QuestionnaireItemSchema],
        user_selections: Dict[str, str],
        workload: LlmWorkloadProfile
    ) -> ArchetypeRecommendationResult:
        raise NotImplementedError


@dataclass(frozen=True)
class RooflineSimulationResult:
    chassis_or_instance_id: str
    tensor_parallel_degree: int
    pipeline_parallel_degree: int
    model_weights_vram_gb: Decimal
    kv_cache_vram_gb_per_seq: Decimal
    activation_buffer_vram_gb: Decimal
    max_concurrent_sequences: int
    achieved_ttft_ms: Decimal
    achieved_tpot_ms: Decimal
    memory_bus_utilization_pct: Decimal
    compute_utilization_pct: Decimal
    bottleneck_regime: str  # "MEMORY_BANDWIDTH_BOUND" | "COMPUTE_BOUND" | "INTERCONNECT_BOUND"
    required_cluster_nodes_baseline: int
    required_cluster_nodes_peak: int

class RooflineSimulationPort(ABC):
    """Domain Port for physical silicon performance & cluster sizing simulation."""

    @abstractmethod
    def simulate_workload_physics(
        self,
        workload: LlmWorkloadProfile,
        hardware: HardwareAcceleratorSpec,
        nodes_count: int
    ) -> RooflineSimulationResult:
        raise NotImplementedError


@dataclass(frozen=True)
class OpenFairRiskExposure:
    loss_event_frequency_annual: Decimal
    loss_magnitude_per_event: MonetaryAmount
    annualized_loss_expectancy_mean: MonetaryAmount
    value_at_risk_95_percentile: MonetaryAmount
    value_at_risk_99_percentile: MonetaryAmount
    downtime_hours_expected_annual: Decimal

class ActuarialRiskPort(ABC):
    """Domain Port executing Open FAIR Monte Carlo / parametric risk calculations."""

    @abstractmethod
    def compute_on_premise_risk(
        self,
        chassis: ServerChassisSpec,
        node_count: int,
        sla_breach_penalty_hourly: MonetaryAmount,
        spare_nodes_on_site: int
    ) -> OpenFairRiskExposure:
        raise NotImplementedError

    @abstractmethod
    def compute_cloud_spot_risk(
        self,
        instance: CloudInstancePricingSpec,
        instance_count: int,
        workload: LlmWorkloadProfile,
        sla_breach_penalty_hourly: MonetaryAmount
    ) -> OpenFairRiskExposure:
        raise NotImplementedError


@dataclass(frozen=True)
class ConstitutionalAuditRecord:
    record_id: UUID
    timestamp_utc: datetime
    tenant_id: str
    industry: IndustryVertical
    input_hash_sha256: str
    recommendation: ArchetypeRecommendationResult
    passed_cfo_gate: bool
    gate_violations: Sequence[str]
    previous_record_hash_sha256: str
    cryptographic_signature: str

class AuditLedgerPort(ABC):
    """Driven Port for immutable, hash-chained cryptographic compliance logging."""

    @abstractmethod
    def append_audit_record(self, record: ConstitutionalAuditRecord) -> str:
        """Persists record to append-only ledger and returns new chain tip SHA-256."""
        raise NotImplementedError
```

---

## SECTION 2: QUESTIONNAIRE DECISION MATRIX & ARCHETYPE TAXONOMY

To serve non-technical executives (CIOs, CFOs, Chief Risk Officers), the platform abstracts raw silicon parameters behind a **5-Vector Strategic Assessment Matrix**. None of these weights or strings are hardcoded in Python; they are hydrated at runtime via `AssessmentQuestionnairePort` from external signed configuration stores.

### 2.1 The 5 Strategic Assessment Vectors & Scoring Weights

Let $Q = \{q_1, q_2, q_3, q_4, q_5\}$ be the set of strategic questions, where each question $q_i$ has a normalized strategic weight $w_i \in [0, 1]$ such that $\sum_{i=1}^{5} w_i = 1.00$.

| Vector ID | Strategic Dimension | Default Weight ($w_i$) | Option Key | Option Description (I18n Abstracted) | On-Prem Affinity ($S_{i, \text{onprem}}$) | Cloud Affinity ($S_{i, \text{cloud}}$) |
| :--- | :--- | :---: | :--- | :--- | :---: | :---: |
| **`Q1_SOVEREIGNTY`** | **Data Sovereignty & Regulatory Jurisdiction** | `0.30` | `AIR_GAPPED` | Classified / ITAR / Strict Air-Gapped Mandate | `100.0` | `0.0` |
| | | | `STRICT_PII` | Regulated Banking/Healthcare (On-Soil Residency) | `85.0` | `25.0` |
| | | | `COMMERCIAL` | Standard Enterprise GDPR/SOC2 Compliance | `50.0` | `75.0` |
| | | | `PUBLIC_DATA` | Unregulated Public / Synthetic Data | `10.0` | `100.0` |
| **`Q2_DUTY_CYCLE`** | **Workload Temporal Profile & Duty Cycle** | `0.25` | `BASELOAD_24_7` | Continuous 24/7 High-Utilization (>75% steady) | `95.0` | `15.0` |
| | | | `PREDICTABLE_DIURNAL` | Business Hours Peak + Nightly Batch Processing | `75.0` | `50.0` |
| | | | `HIGH_VARIANCE_SPIKY` | Unpredictable Viral Spikes (Peak > 4x Baseline) | `30.0` | `95.0` |
| | | | `EPHEMERAL_RND` | Ad-hoc R&D / Sporadic Fine-Tuning (<20% duty) | `5.0` | `100.0` |
| **`Q3_FACILITY`** | **Datacenter & Cooling Readiness** | `0.20` | `DLC_READY` | Owned/Colo Tier-3+ with Direct Liquid Cooling (>40kW/rack) | `100.0` | `10.0` |
| | | | `HIGH_DENSITY_AIR` | Enterprise Colo with High-Density Air (15kW–30kW/rack) | `80.0` | `30.0` |
| | | | `LEGACY_CLOSET` | Legacy Enterprise Server Room (<8kW/rack) | `15.0` | `90.0` |
| | | | `NO_FOOTPRINT` | Zero Datacenter Footprint / Cloud-First Mandate | `0.0` | `100.0` |
| **`Q4_FINANCE`** | **Capital Structure & Accounting Preference** | `0.15` | `CAPEX_HEAVY` | Strong Balance Sheet / EBITDA Optimization via CapEx Amortization | `100.0` | `10.0` |
| | | | `BALANCED_HYBRID` | Balanced CapEx Baseline + OpEx Burst Flexibility | `65.0` | `65.0` |
| | | | `STRICT_OPEX` | Zero CapEx Mandate / Pure Pay-As-You-Go OpEx | `0.0` | `100.0` |
| **`Q5_SRE_MATURITY`**| **In-House Infrastructure & SRE Maturity** | `0.10` | `TIER1_INFRA_TEAM` | Dedicated Bare-Metal Kernel/InfiniBand/Kubernetes SREs | `100.0` | `20.0` |
| | | | `MANAGED_COLO_OPS` | General DevOps + OEM Remote Hands Reliance | `65.0` | `60.0` |
| | | | `APP_DEVS_ONLY` | Application Developers Only (Zero Hardware Ops) | `5.0` | `100.0` |

### 2.2 Mathematical Decision Function & Archetype Classification

Given a vector of user selections $u = (u_1, u_2, u_3, u_4, u_5)$, the engine calculates two primary affinity coordinates: the **Sovereign On-Premise Score ($A_{\text{onprem}}$)** and the **Elastic Cloud Score ($A_{\text{cloud}}$)**:

$$A_{\text{onprem}} = \sum_{i=1}^{5} w_i \cdot S_{i, \text{onprem}}(u_i), \quad A_{\text{cloud}} = \sum_{i=1}^{5} w_i \cdot S_{i, \text{cloud}}(u_i)$$

Next, we define the **Normalized Affinity Divergence ($\Delta_A$)** and the **Workload Peak-to-Average Ratio ($\text{PAR}$)**:

$$\Delta_A = A_{\text{onprem}} - A_{\text{cloud}} \in [-100, +100]$$

$$\text{PAR} = \frac{\text{RPS}_{\text{peak}}}{\text{RPS}_{\text{baseline}}}$$

#### Hard Veto Overrides (Boundary Constraints):
Before applying continuous scoring thresholds, the decision engine evaluates three non-compensatory **Boolean Vetoes**:
1. **Air-Gapped Veto ($V_{\text{airgap}}$):** If $u_1 = \text{AIR\_GAPPED}$, Cloud is legally impossible. Force **Archetype 1** ($100\%$ On-Premise).
2. **Zero-Footprint / Zero-CapEx Veto ($V_{\text{nocapex}}$):** If $(u_3 = \text{NO\_FOOTPRINT} \lor u_4 = \text{STRICT\_OPEX}) \land u_1 \neq \text{AIR\_GAPPED}$, On-Premise hardware acquisition is blocked. Force **Archetype 2** ($100\%$ Public Cloud).

#### Continuous Classification Function $\Phi(\Delta_A, \text{PAR}, V)$:

$$\Phi(\Delta_A, \text{PAR}, V) = \begin{cases} 
\text{Archetype 1: Sovereign On-Premise Bare-Metal} & \text{if } V_{\text{airgap}} = \text{True} \lor \left(\Delta_A \ge +25.0 \land \text{PAR} \le 1.5\right) \\[8pt]
\text{Archetype 2: Elastic Public Cloud Dedicated} & \text{if } V_{\text{nocapex}} = \text{True} \lor \Delta_A \le -25.0 \\[8pt]
\text{Archetype 3: Tiered Hybrid Sovereign + Burst} & \text{if } \left|\Delta_A\right| < 25.0 \lor \left(\Delta_A \ge +25.0 \land \text{PAR} > 1.5 \land \neg V_{\text{airgap}}\right)
\end{cases}$$

* **Archetype 1 (Sovereign On-Premise Bare-Metal Cluster):** Sizes bare-metal chassis to cover $100\%$ of $\text{RPS}_{\text{peak}}$ plus $N+K$ hardware redundancy. Zero cloud egress or spot dependency.
* **Archetype 2 (Elastic Public Cloud Dedicated Cluster):** Sizes Reserved/Committed-Use instances for $\text{RPS}_{\text{baseline}}$ and scales elastically using Spot/On-Demand instances for $\Delta \text{RPS}_{\text{burst}} = \text{RPS}_{\text{peak}} - \text{RPS}_{\text{baseline}}$.
* **Archetype 3 (Tiered Hybrid Sovereign Base with Cloud-Bursting):** Sizes amortized On-Premise Bare-Metal to run at $>85\%$ continuous utilization handling $\text{RPS}_{\text{baseline}}$, while routing overflow traffic ($\Delta \text{RPS}_{\text{burst}}$) over encrypted VPN/DirectConnect to Public Cloud GPU instances during peak duty cycles ($\tau_{\text{burst}}$).

---

## SECTION 3: ON-PREMISE VS CLOUD FINANCIAL MODELING INVARIANTS

All financial comparisons are evaluated over a customizable planning horizon $T \in [36, 60]$ months.

### 3.1 On-Premise Capital Expenditure (CapEx) & Amortization Invariants

Let $N_{\text{chassis}}$ be the number of physical server chassis required to satisfy the workload physics (plus $N_{\text{spare}}$ cold/warm spares). Let $C_{\text{unit}}$ be the unit CapEx price of a chassis, and $\alpha_{\text{net}} \in [0.10, 0.25]$ be the networking/storage fabric overhead multiplier (InfiniBand/RoCEv2 leaf-spine switches, optical transceivers, NVMe storage appliances).

**Total Initial Capital Outlay ($\text{CapEx}_{\text{initial}}$):**
$$\text{CapEx}_{\text{initial}} = N_{\text{chassis}} \cdot C_{\text{unit}} \cdot (1 + \alpha_{\text{net}})$$

**Salvage Value & Net Depreciable Base:**
Given a residual salvage value percentage $\gamma_T \in [0.05, 0.25]$ at month $T$ (e.g., $15\%$ at 36 months, $5\%$ at 60 months):
$$V_{\text{salvage}}(T) = \text{CapEx}_{\text{initial}} \cdot \gamma_T$$

**Monthly Amortized CapEx Charge ($\text{CapEx}_{\text{monthly}}$) Incorporating Cost of Capital (WACC):**
Using the Weighted Average Cost of Capital $r_{\text{wacc}}$ (monthly rate $r_m = r_{\text{wacc}} / 12$), the annuity-adjusted monthly capital charge is:
$$\text{CapEx}_{\text{monthly}} = \frac{\left(\text{CapEx}_{\text{initial}} - \frac{V_{\text{salvage}}(T)}{(1 + r_m)^T}\right) \cdot r_m}{1 - (1 + r_m)^{-T}}$$
*(Note: When $r_{\text{wacc}} = 0$, this simplifies by L'Hôpital's rule to straight-line depreciation: $\frac{\text{CapEx}_{\text{initial}} - V_{\text{salvage}}(T)}{T}$.)*

### 3.2 On-Premise Datacenter Operational Expenditure (OpEx) Invariants

Let $H_m = 730.5$ be the average hours per month ($365.25 \times 24 / 12$).

1. **Facility Power & Thermal Dissipation Cost ($\text{OpEx}_{\text{power}, m}$):**
   Each chassis draws $P_{\text{chassis\_kw}}$ under load. With datacenter Power Usage Effectiveness $\text{PUE} \in [1.08, 2.00]$ and electricity tariff $E_{\text{kwh}}$:
   $$\text{OpEx}_{\text{power}, m} = N_{\text{chassis}} \cdot P_{\text{chassis\_kw}} \cdot \text{PUE} \cdot H_m \cdot E_{\text{kwh}}$$

2. **High-Density Colocation Rack Rental ($\text{OpEx}_{\text{colo}, m}$):**
   Physical rack allocation is constrained by **both** spatial height ($U_{\text{max}}$, typically $42\text{U}$ usable) and rack power delivery ceiling ($P_{\text{rack\_max\_kw}}$, e.g., $20\text{kW}$ or $40\text{kW}$):
   $$N_{\text{racks}} = \max \left( \left\lceil \frac{N_{\text{chassis}} \cdot U_{\text{chassis}}}{U_{\text{max}}} \right\rceil, \, \left\lceil \frac{N_{\text{chassis}} \cdot P_{\text{chassis\_kw}}}{P_{\text{rack\_max\_kw}}} \right\rceil \right)$$
   $$\text{OpEx}_{\text{colo}, m} = N_{\text{racks}} \cdot R_{\text{rack\_monthly}}$$

3. **OEM 24/7 Mission-Critical Care Pack Warranty ($\text{OpEx}_{\text{oem}, m}$):**
   Given annual OEM support rate $\omega_{\text{oem}}$ (typically $8\%$ to $12\%$ of hardware CapEx per annum):
   $$\text{OpEx}_{\text{oem}, m} = \frac{\text{CapEx}_{\text{initial}} \cdot \omega_{\text{oem}}}{12}$$

4. **SRE Staffing Allocation ($\text{OpEx}_{\text{sre}, m}$):**
   $$\text{OpEx}_{\text{sre}, m} = \text{FTE}_{\text{count}} \cdot \frac{C_{\text{fte\_annual}}}{12}$$

**Total Monthly On-Premise Baseline Run-Rate:**
$$\text{TCO}_{\text{onprem}, m} = \text{CapEx}_{\text{monthly}} + \text{OpEx}_{\text{power}, m} + \text{OpEx}_{\text{colo}, m} + \text{OpEx}_{\text{oem}, m} + \text{OpEx}_{\text{sre}, m}$$

### 3.3 Public Cloud Operational Expenditure (OpEx) Invariants

Let $N_{\text{base\_inst}}$ be the instance count required for baseline load, and $N_{\text{burst\_inst}}$ be the additional instances required during peak bursts occurring for fraction $\tau_{\text{burst}} \in [0, 1]$ of the month.

1. **Compute Cost ($\text{OpEx}_{\text{cloud\_compute}, m}$):**
   Baseline instances use Reserved/Committed hourly rate $C_{\text{res\_hr}}$, while burst instances use either On-Demand ($C_{\text{od\_hr}}$) or Spot ($C_{\text{spot\_hr}}$) rate:
   $$\text{OpEx}_{\text{cloud\_compute}, m} = H_m \cdot \left( N_{\text{base\_inst}} \cdot C_{\text{res\_hr}} + N_{\text{burst\_inst}} \cdot \tau_{\text{burst}} \cdot C_{\text{burst\_hr}} \right)$$

2. **Block Storage & High-Speed Ephemeral NVMe ($\text{OpEx}_{\text{storage}, m}$):**
   $$\text{OpEx}_{\text{storage}, m} = \left(N_{\text{base\_inst}} + N_{\text{burst\_inst}}\right) \cdot D_{\text{gb\_per\_inst}} \cdot C_{\text{gb\_month}}$$

3. **Network Egress Cost ($\text{OpEx}_{\text{egress}, m}$):**
   Let $B_{\text{token}}$ be bytes per UTF-8 token ($\approx 4\text{ bytes}$). Total monthly outbound token traffic generates egress volume $V_{\text{egress\_gb}}$:
   $$V_{\text{egress\_gb}} = \frac{H_m \cdot 3600 \cdot \left(\text{RPS}_{\text{base}} + \tau_{\text{burst}} \cdot \Delta\text{RPS}_{\text{burst}}\right) \cdot L_{\text{out\_tokens}} \cdot B_{\text{token}}}{10^9}$$
   $$\text{OpEx}_{\text{egress}, m} = V_{\text{egress\_gb}} \cdot C_{\text{egress\_gb}}$$

### 3.4 Open FAIR Quantitative Actuarial Risk Modeling

Standard TCO calculators fail CFO scrutiny because they ignore **Availability Risk**. We integrate the **Open FAIR (Factor Analysis of Information Risk)** standard, where **Annualized Loss Expectancy ($\text{ALE}$)** is the product of **Loss Event Frequency ($\text{LEF}$)** and **Loss Magnitude ($\text{LM}$)**.

#### A. On-Premise Silicon AFR & RMA MTTR Penalty ($\text{ALE}_{\text{onprem}}$)
Each physical GPU has an Annualized Failure Rate $\lambda_{\text{afr}}$ (e.g., $2.5\%$ to $4.0\%$ per year in high-thermal density clusters). For a cluster of $N_{\text{chassis}}$ with $G$ GPUs per chassis:
$$\text{LEF}_{\text{onprem}} = N_{\text{chassis}} \cdot G \cdot \lambda_{\text{afr}}$$

When a GPU fails without an available warm spare ($N_{\text{spare}}$), the node goes offline or degrades cluster throughput for the OEM RMA Mean Time To Repair ($\text{MTTR}_{\text{rma}}$, typically $4\text{ to }48\text{ hours}$). Using the Erlang-B / Poisson spare depletion probability $P_{\text{depletion}}(N_{\text{spare}}, \text{LEF}_{\text{onprem}}, \text{MTTR}_{\text{rma}})$:
$$\text{LM}_{\text{onprem}} = \text{MTTR}_{\text{rma}} \cdot \left( \frac{C_{\text{sla\_penalty\_hr}}}{N_{\text{chassis}}} + C_{\text{eng\_remediation\_hr}} \right)$$
$$\text{ALE}_{\text{onprem}} = \text{LEF}_{\text{onprem}} \cdot P_{\text{depletion}} \cdot \text{LM}_{\text{onprem}}$$

#### B. Cloud Spot Preemption & Cold-Boot Penalty ($\text{ALE}_{\text{cloud\_spot}}$)
When utilizing Cloud Spot instances for burst capacity ($N_{\text{burst\_inst}}$), the cloud provider can preempt instances with daily probability $p_{\text{preempt\_daily}}$.
$$\text{LEF}_{\text{spot}} = 365.25 \cdot \tau_{\text{burst}} \cdot N_{\text{burst\_inst}} \cdot p_{\text{preempt\_daily}}$$

Each preemption triggers a **Cold Rebuild Penalty**: provisioning a replacement node, pulling container images, and loading multi-hundred-gigabyte LLM weights from object storage into GPU VRAM over PCIe/NVLink ($t_{\text{cold\_boot}}$ seconds). During $t_{\text{cold\_boot}}$, requests are dropped or violate SLA latency bounds:
$$\text{LM}_{\text{spot}} = \left(\frac{t_{\text{cold\_boot}}}{3600}\right) \cdot \left( C_{\text{od\_hr}} + \frac{C_{\text{sla\_penalty\_hr}}}{N_{\text{burst\_inst}}} \right)$$
$$\text{ALE}_{\text{cloud\_spot}} = \text{LEF}_{\text{spot}} \cdot \text{LM}_{\text{spot}}$$

**Risk-Adjusted Monthly TCO ($\text{TCO}^*$):**
$$\text{TCO}^*_{\text{monthly}} = \text{TCO}_{\text{monthly}} + \frac{\text{ALE}}{12}$$

---

## SECTION 4: PRE-FLIGHT CFO CONSTITUTIONAL AUDIT GATE (`CfoActuarialGate`)

No simulation or financial recommendation may reach the presentation layer without passing through the **`CfoActuarialGate`**. This gate enforces inviolable laws of thermodynamics, electrical engineering, silicon memory architecture, and institutional economics.

```python
class ConstitutionalGateViolationError(Exception):
    """Raised when a proposed configuration violates physical or actuarial invariants."""
    def __init__(self, code: str, message: str, offending_value: Decimal, limit_value: Decimal):
        self.code = code
        self.message = message
        self.offending_value = offending_value
        self.limit_value = limit_value
        super().__init__(f"[{code}] {message} (Observed: {offending_value}, Limit: {limit_value})")
```

### 4.1 Inviolable Gate Invariants

| Rule Code | Invariant Name | Mathematical Boundary Condition | Violation Trigger Example |
| :--- | :--- | :--- | :--- |
| **`GATE-PHY-001`** | **Rack Power Density Ceiling** | $P_{\text{chassis\_kw}} \cdot N_{\text{chassis\_per\_rack}} \le P_{\text{rack\_max\_kw}}$ | Attempting to deploy an $10.2\text{ kW}$ 8xH100 chassis inside a legacy $5.0\text{ kW}$ uncooled enterprise rack. |
| **`GATE-PHY-002`** | **Cooling Topology Thermal Ceiling** | If $P_{\text{rack\_actual\_kw}} > 35.0\text{ kW} \implies \text{Cooling} \in \{\text{DLC}, \text{IMMERSION}\}$ | Specifying $50\text{ kW}$ rack density with standard `AIR_COOLED` CRAC units. |
| **`GATE-PHY-003`** | **Thermodynamic Carnot PUE Floor** | $\text{PUE} \ge 1.08$ | User or adapter injecting $\text{PUE} = 1.00$ or $0.95$ (violates 2nd Law of Thermodynamics for power transformation + cooling). |
| **`GATE-SIL-001`** | **VRAM Allocation Hard Ceiling (10% Runtime Buffer)** | $\frac{M_{\text{weights}} + M_{\text{kv\_cache}} + M_{\text{activations}}}{M_{\text{total\_vram}}} \le 0.90$ | Allocating $76\text{ GB}$ of weights + KV cache on an $80\text{ GB}$ GPU ($95\%$ utilization), leaving insufficient headroom for CUDA kernels and PyTorch memory fragmentation (OOM risk). |
| **`GATE-SIL-002`** | **Memory Bandwidth Saturation Ceiling** | $\frac{\text{BW}_{\text{required\_decode}}}{\text{BW}_{\text{hbm\_spec}}} \le 0.85$ | Sizing token decode throughput requiring $>85\%$ of theoretical HBM3e pin bandwidth, where non-contiguous memory access and bus contention cause exponential TPOT latency spikes. |
| **`GATE-FIN-001`** | **Strict Positive Economic Floor** | $\forall x \in \{\text{CapEx}, E_{\text{kwh}}, C_{\text{hourly}}\}, \, x > 0$ | Injecting $\$0.00$ electricity cost, $\$0.00$ hardware CapEx, or negative WACC/discount rates. |
| **`GATE-FIN-002`** | **Depreciation & Salvage Sanity Bound** | $36 \le T_{\text{months}} \le 60 \land 0.0 \le \gamma_T \le 0.35$ | Amortizing rapidly obsolescing AI silicon over $120\text{ months}$ or claiming $80\%$ residual salvage value after 5 years. |

### 4.2 Reference Implementation of `CfoActuarialGate`

```python
class CfoActuarialGate:
    """Constitutional Pre-Flight Audit Gate enforcing physical, silicon, and economic laws."""

    PUE_PHYSICAL_FLOOR: Decimal = Decimal("1.08")
    AIR_COOLING_MAX_RACK_KW: Decimal = Decimal("35.0")
    VRAM_UTILIZATION_CEILING: Decimal = Decimal("0.90")
    MEMORY_BUS_SATURATION_CEILING: Decimal = Decimal("0.85")
    MIN_AMORTIZATION_MONTHS: int = 36
    MAX_AMORTIZATION_MONTHS: int = 60
    MAX_SALVAGE_VALUE_PCT: Decimal = Decimal("0.35")

    @classmethod
    def validate_on_premise_deployment(
        cls,
        chassis: ServerChassisSpec,
        facility: DatacenterFacilitySpec,
        roofline: RooflineSimulationResult,
        amortization_months: int
    ) -> List[ConstitutionalGateViolationError]:
        violations: List[ConstitutionalGateViolationError] = []

        # 1. GATE-PHY-001: Single chassis cannot exceed rack maximum power delivery
        if chassis.total_chassis_tdp_kw > facility.max_rack_power_density_kw:
            violations.append(ConstitutionalGateViolationError(
                code="GATE-PHY-001",
                message="Server chassis thermal dissipation exceeds datacenter rack power delivery ceiling.",
                offending_value=chassis.total_chassis_tdp_kw,
                limit_value=facility.max_rack_power_density_kw
            ))

        # 2. GATE-PHY-002: High-density racks (>35kW) require Direct Liquid or Immersion Cooling
        if (facility.max_rack_power_density_kw > cls.AIR_COOLING_MAX_RACK_KW 
                and facility.cooling_topology == "AIR_COOLED"):
            violations.append(ConstitutionalGateViolationError(
                code="GATE-PHY-002",
                message="Rack power density above 35 kW physically requires Direct Liquid or Immersion Cooling.",
                offending_value=facility.max_rack_power_density_kw,
                limit_value=cls.AIR_COOLING_MAX_RACK_KW
            ))

        # 3. GATE-PHY-003: PUE Physical Floor
        if facility.pue_rating < cls.PUE_PHYSICAL_FLOOR:
            violations.append(ConstitutionalGateViolationError(
                code="GATE-PHY-003",
                message="Facility PUE violates thermodynamic floor for electrical transformation and heat rejection.",
                offending_value=facility.pue_rating,
                limit_value=cls.PUE_PHYSICAL_FLOOR
            ))

        # 4. GATE-SIL-001: Mandatory 10% VRAM Runtime Buffer
        total_cluster_vram = chassis.accelerator_sku.vram_gb * Decimal(
            chassis.accelerators_per_chassis * roofline.required_cluster_nodes_baseline
        )
        allocated_vram = (
            roofline.model_weights_vram_gb 
            + (roofline.kv_cache_vram_gb_per_seq * Decimal(roofline.max_concurrent_sequences))
            + roofline.activation_buffer_vram_gb
        )
        vram_ratio = allocated_vram / total_cluster_vram if total_cluster_vram > 0 else Decimal("1.0")
        if vram_ratio > cls.VRAM_UTILIZATION_CEILING:
            violations.append(ConstitutionalGateViolationError(
                code="GATE-SIL-001",
                message="VRAM allocation exceeds 90% hard ceiling (missing mandatory 10% CUDA runtime buffer).",
                offending_value=vram_ratio,
                limit_value=cls.VRAM_UTILIZATION_CEILING
            ))

        # 5. GATE-SIL-002: Memory Bandwidth Saturation Ceiling (85%)
        bus_util_ratio = roofline.memory_bus_utilization_pct / Decimal("100.0")
        if bus_util_ratio > cls.MEMORY_BUS_SATURATION_CEILING:
            violations.append(ConstitutionalGateViolationError(
                code="GATE-SIL-002",
                message="Decode memory bandwidth exceeds 85% HBM bus saturation ceiling.",
                offending_value=bus_util_ratio,
                limit_value=cls.MEMORY_BUS_SATURATION_CEILING
            ))

        # 6. GATE-FIN-001 & GATE-FIN-002: Economic Floors & Amortization Bounds
        if chassis.capex_unit_price.amount <= Decimal("0") or facility.electricity_rate_per_kwh.amount <= Decimal("0"):
            violations.append(ConstitutionalGateViolationError(
                code="GATE-FIN-001",
                message="Zero or negative infrastructure cost detected. Free hardware/electricity is prohibited.",
                offending_value=min(chassis.capex_unit_price.amount, facility.electricity_rate_per_kwh.amount),
                limit_value=Decimal("0.0001")
            ))

        if not (cls.MIN_AMORTIZATION_MONTHS <= amortization_months <= cls.MAX_AMORTIZATION_MONTHS):
            violations.append(ConstitutionalGateViolationError(
                code="GATE-FIN-002",
                message="Amortization period outside institutional accounting bounds (36-60 months).",
                offending_value=Decimal(amortization_months),
                limit_value=Decimal(cls.MAX_AMORTIZATION_MONTHS)
            ))

        return violations
```

---

## SECTION 5: VERIFIABLE IMPLEMENTATION ROADMAP & TEST ORACLES

### 5.1 Phased Implementation Order

1. **Phase 1: Pure Domain Foundation (`src/domain/models/` & `src/domain/ports/`)**
   * Implement all frozen `Decimal`-backed Value Objects (`HardwareAcceleratorSpec`, `ServerChassisSpec`, `CloudInstancePricingSpec`, `DatacenterFacilitySpec`, `LlmWorkloadProfile`).
   * Implement all Abstract Base Class Ports (`HardwareRegistryPort`, `PricingProviderPort`, `AssessmentQuestionnairePort`, `RooflineSimulationPort`, `ActuarialRiskPort`, `AuditLedgerPort`).
2. **Phase 2: Physics, Actuarial & Decision Engines (`src/domain/services/`)**
   * Implement `QuestionnaireDecisionEngine` (evaluating $\Delta_A$, $\text{PAR}$, and hard vetoes).
   * Implement `RooflinePhysicsEngine` (computing KV cache sizing, tensor/pipeline parallelism, TTFT, TPOT, and HBM bandwidth saturation).
   * Implement `OpenFairActuarialEngine` (computing Silicon AFR Erlang-B spare depletion and Spot Preemption Cold-Rebuild ALE).
   * Implement `HybridTcoAggregator` and `CfoActuarialGate`.
3. **Phase 3: Driven Secondary Adapters (`src/adapters/outbound/`)**
   * Implement `DynamicJsonCatalogAdapter` with configurable TTL cache for hardware/pricing resolution and live FX conversion.
   * Implement `I18nQuestionnaireLoaderAdapter` supporting dynamic locales and industry verticals.
   * Implement `SqliteHashChainAuditLedgerAdapter` generating SHA-256 tamper-evident audit chains.
4. **Phase 4: Driving Primary Adapters & Executive UI (`src/adapters/inbound/`)**
   * Build the Guided Executive Assessment Wizard UI (5 strategic questions $\to$ Automated Archetype Recommendation $\to$ Side-by-Side 3-Archetype Financial & Risk Comparison Matrix $\to$ Cryptographic Audit Certificate Export).

### 5.2 Automated Verification Oracles

#### Oracle 1: AST Domain Purity Verification (`tests/architecture/test_domain_purity.py`)
An automated test parses every `.py` file under `src/domain/` using Python's `ast` module and fails the build if any forbidden module is imported:

```python
import ast
from pathlib import Path

FORBIDDEN_DOMAIN_IMPORTS = {
    "os", "sys", "pathlib", "shutil", "requests", "httpx", "urllib",
    "boto3", "streamlit", "pandas", "sqlalchemy", "sqlite3", "plotly"
}

def test_domain_hexagonal_purity() -> None:
    domain_dir = Path("src/domain")
    for py_file in domain_dir.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root_pkg = alias.name.split(".")[0]
                    assert root_pkg not in FORBIDDEN_DOMAIN_IMPORTS, (
                        f"Hexagonal Purity Violation in {py_file}: import '{root_pkg}' is banned."
                    )
            elif isinstance(node, ast.ImportFrom) and node.module:
                root_pkg = node.module.split(".")[0]
                assert root_pkg not in FORBIDDEN_DOMAIN_IMPORTS, (
                    f"Hexagonal Purity Violation in {py_file}: from '{root_pkg}' is banned."
                )
```

#### Oracle 2: Mathematical & Actuarial Property-Based Oracles (`tests/domain/test_actuarial_invariants.py`)
* **Idempotency & Zero Floating-Point Drift:** Running a 60-month TCO aggregation 10,000 times across JPY, USD, EUR, and KWD must yield bit-identical `Decimal` outputs to 4 decimal places.
* **Boundary Rejection Oracle:** Feeding a $10.2\text{ kW}$ DGX/HGX-class server into a $5.0\text{ kW}$ rack must deterministically raise `GATE-PHY-001`. Feeding $\text{PUE} = 1.02$ must deterministically raise `GATE-PHY-003`.
* **Veto Determinism Oracle:** Selecting `AIR_GAPPED` in `Q1_SOVEREIGNTY` must return `SOVEREIGN_ON_PREM_BARE_METAL` even if `Q2` through `Q5` are set to maximum cloud affinity.

#### Oracle 3: Playwright End-to-End Executive Journey (`tests/e2e/test_wizard_flow.py`)
* **Test Scenario A (Defense / Air-Gapped CIO):** User selects Defense Vertical $\to$ Air-Gapped Sovereignty $\to$ 24/7 Baseload $\to$ DLC Ready Facility. Playwright verifies the UI recommends **Archetype 1 (Sovereign On-Premise)**, renders 36/60-month CapEx depreciation schedules, displays Silicon AFR risk metrics, and records a valid SHA-256 audit hash.
* **Test Scenario B (Retail / Spiky Traffic CFO):** User selects Retail Vertical $\to$ Commercial Compliance $\to$ High-Variance Spiky Workload ($\text{PAR} = 5.0$) $\to$ Balanced CapEx/OpEx. Playwright verifies the UI recommends **Archetype 3 (Tiered Hybrid Cloud-Bursting)**, sizing bare-metal for baseline RPS and Cloud Spot/On-Demand for burst RPS.

---

### 5.3 Architectural Verdict

**VERDICT: APPROVED FOR IMPLEMENTATION.**

This blueprint eliminates all static hardcoding, elevates On-Premise Bare-Metal to first-class mathematical parity with Public Cloud, shields non-technical executives from raw silicon complexity via a rigorous 5-vector decision matrix, embeds Open FAIR quantitative risk modeling, and enforces physical and economic reality through the `CfoActuarialGate`. Programming may proceed strictly adhering to Phase 1 through Phase 4.