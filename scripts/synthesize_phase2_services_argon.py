#!/usr/bin/env python3
"""
Meta-Intelligence Synthesis: Autonomous Phase 2 Domain Services Generation
==========================================================================
Delegates the complete, zero-defect implementation of Phase 2 domain calculation
engines and test oracles to gemini-4-argon, enforcing zero-hardcoding, strict Decimal
arithmetic, and 100% pure Technical English compliance.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ASSESSMENT_ENGINE_SRC = Path("/home/jsanchhi/assessment_engine/src")
if str(ASSESSMENT_ENGINE_SRC) not in sys.path:
    sys.path.insert(0, str(ASSESSMENT_ENGINE_SRC))

from assessment_engine.infrastructure.genai_client import (
    ModelTier,
    create_genai_client,
    get_model,
)

SERVICES_DIR = REPO_ROOT / "src/domain/services"
TESTS_DOMAIN_DIR = REPO_ROOT / "tests/domain"
SERVICES_DIR.mkdir(parents=True, exist_ok=True)
TESTS_DOMAIN_DIR.mkdir(parents=True, exist_ok=True)


def load_domain_context() -> str:
    files = [
        REPO_ROOT / "src/domain/exceptions.py",
        REPO_ROOT / "src/domain/models/financial.py",
        REPO_ROOT / "src/domain/models/hardware.py",
        REPO_ROOT / "src/domain/models/workload.py",
        REPO_ROOT / "src/domain/models/assessment.py",
        REPO_ROOT / "src/domain/ports/hardware_registry.py",
        REPO_ROOT / "src/domain/ports/pricing_provider.py",
        REPO_ROOT / "src/domain/ports/assessment_questionnaire.py",
        REPO_ROOT / "src/domain/ports/roofline_simulation.py",
        REPO_ROOT / "src/domain/ports/actuarial_risk.py",
        REPO_ROOT / "src/domain/ports/constitutional_gate.py",
        REPO_ROOT / "src/domain/ports/hybrid_tco.py",
        REPO_ROOT / "src/domain/ports/audit_ledger.py",
        REPO_ROOT / "config/taxonomies/verticals.json",
        REPO_ROOT / "config/locales.json",
    ]
    parts = []
    for f in files:
        if f.is_file():
            parts.append(f"### FILE: `{f.relative_to(REPO_ROOT)}`\n```python\n{f.read_text(encoding='utf-8')}\n```\n")
    return "\n".join(parts)


def extract_code_block(text: str, filename_hint: str) -> str:
    """Extracts python code block from model response."""
    # Look for ```python ... ```
    pattern = r"```(?:python)?\s*\n(.*?)\n```"
    matches = re.findall(pattern, text, re.DOTALL)
    if matches:
        # Return the longest matching block or the one containing filename_hint
        for m in matches:
            if filename_hint in m or "class " in m or "def " in m:
                return m.strip() + "\n"
        return matches[0].strip() + "\n"
    return text.strip() + "\n"


SERVICES_TO_GENERATE = [
    {
        "name": "QuestionnaireDecisionEngine",
        "service_file": SERVICES_DIR / "questionnaire_engine.py",
        "test_file": TESTS_DOMAIN_DIR / "test_questionnaire_engine.py",
        "prompt": """
Implement `src/domain/services/questionnaire_engine.py` containing `QuestionnaireDecisionEngine` implementing `ArchetypeRecommendationPort`.
And implement `tests/domain/test_questionnaire_engine.py`.

Requirements:
- Class `QuestionnaireDecisionEngine(ArchetypeRecommendationPort)`
- Method: `evaluate_assessment(self, schema: Sequence[QuestionnaireItemSchema], client_responses: Mapping[str, str], workload: LlmWorkloadProfile, policy: AssessmentDecisionPolicy) -> ArchetypeRecommendationResult`
- Algorithm:
  * Iterate over schema questions and match selected option_id from `client_responses`.
  * Calculate weighted affinity scores:
    on_prem_score = (sum(weight * option.on_prem_affinity_score)) / total_weight
    cloud_score = (sum(weight * option.cloud_affinity_score)) / total_weight
    Normalized in [0.0000, 100.0000] using Decimal Banker's Rounding (precision 4).
  * Hard Veto Enforcement:
    If any selected option has `is_hard_on_prem_veto`, on-prem is prohibited -> recommend ELASTIC_CLOUD with veto reason.
    If any selected option has `is_hard_cloud_veto`, cloud is prohibited -> recommend SOVEREIGN_ON_PREM with veto reason.
    If mutual veto occurs -> resolve via deadlock policy (SOVEREIGN_ON_PREM with colocation lease note).
  * If no veto:
    divergence_delta = abs(on_prem_score - cloud_score)
    Check Peak-to-Average Ratio: par = workload.peak_burst_rps / workload.baseline_rps
    If divergence_delta <= policy.hybrid_divergence_threshold and par >= Decimal("1.5"):
      Recommend HYBRID_CLOUD_BURST.
      Calculate base_split = clamp(Decimal("1.0") / par, policy.min_base_load_split_pct, policy.max_base_load_split_pct)
      burst_split = Decimal("1.0") - base_split
    Elif on_prem_score >= cloud_score:
      Recommend SOVEREIGN_ON_PREM (base_split=1.0, burst_split=0.0)
    Else:
      Recommend ELASTIC_CLOUD (base_split=0.0, burst_split=1.0)
- Zero Spanish literals anywhere in code. 100% Technical English.
- Pure Hexagonal Domain: zero I/O, zero network, zero forbidden imports.

OUTPUT FORMAT:
Generate TWO distinct markdown code blocks:
Block 1 with header `# FILE: src/domain/services/questionnaire_engine.py`:
```python
...
```
Block 2 with header `# FILE: tests/domain/test_questionnaire_engine.py`:
```python
...
```
"""
    },
    {
        "name": "RooflinePhysicsEngine",
        "service_file": SERVICES_DIR / "roofline_engine.py",
        "test_file": TESTS_DOMAIN_DIR / "test_roofline_engine.py",
        "prompt": """
Implement `src/domain/services/roofline_engine.py` containing `RooflinePhysicsEngine` implementing `RooflineSimulationPort`.
And implement `tests/domain/test_roofline_engine.py`.

Requirements:
- Class `RooflinePhysicsEngine(RooflineSimulationPort)`
- Method: `simulate_roofline(self, candidate_id: str, workload: LlmWorkloadProfile, accelerator: HardwareAcceleratorSpec, accelerators_per_node: int, max_vram_utilization_ratio: Decimal) -> RooflineSimulationResult`
- Mathematical Algorithm:
  * Weights VRAM: M_weights_gb = (workload.total_params_billion * Decimal("1000000000") * workload.weights_bytes_per_param) / Decimal("1073741824")
  * KV Cache VRAM: bytes_per_token = workload.compute_kv_cache_bytes_per_token()
    total_tokens = workload.peak_concurrent_users * (workload.avg_prompt_tokens + workload.avg_generated_tokens)
    M_kv_gb = (Decimal(total_tokens) * bytes_per_token) / Decimal("1073741824")
  * Activation buffer VRAM: M_act_gb = (Decimal(workload.peak_concurrent_users) * Decimal(workload.max_context_length) * Decimal(workload.hidden_size) * Decimal("2.0")) / Decimal("1073741824")
  * Total Required VRAM: M_total_gb = M_weights_gb + M_kv_gb + M_act_gb
  * Distributed Parallelism:
    Derive Tensor Parallelism TP in {1, 2, 4, 8} such that TP <= accelerators_per_node and workload.num_query_heads % TP == 0.
    Calculate single accelerator effective VRAM = accelerator.vram_gb * max_vram_utilization_ratio
    Single node usable VRAM = single accelerator effective VRAM * Decimal(accelerators_per_node)
    required_nodes = max(1, math.ceil(M_total_gb / single_node_usable_VRAM))
    cluster_total_vram_pool_gb = accelerator.vram_gb * Decimal(required_nodes * accelerators_per_node)
    vram_utilization_ratio = M_total_gb / cluster_total_vram_pool_gb
  * Latency & Throughput (Roofline):
    arithmetic_intensity_prefill = workload.active_params_billion * Decimal("2.0")
    effective_tflops = accelerator.fp16_tflops * accelerator.tensor_parallel_efficiency_factor * Decimal(required_nodes * accelerators_per_node)
    prefill_flops = Decimal(workload.avg_prompt_tokens) * workload.active_params_billion * Decimal("2000000000")
    ttft_seconds = prefill_flops / (effective_tflops * Decimal("1000000000000") * Decimal("0.45")) # 45% MFU
    effective_bw_gbps = accelerator.memory_bandwidth_gbps * accelerator.tensor_parallel_efficiency_factor * Decimal(required_nodes * accelerators_per_node)
    bytes_moved_per_token = (workload.active_params_billion * Decimal("1000000000") * workload.weights_bytes_per_param) + (Decimal(workload.peak_concurrent_users) * bytes_per_token)
    tpot_seconds = bytes_moved_per_token / (effective_bw_gbps * Decimal("1000000000") * Decimal("0.65")) # 65% MBU
    tpot_ms_per_token = tpot_seconds * Decimal("1000")
    tokens_per_second_per_user = Decimal("1000") / max(Decimal("0.001"), tpot_ms_per_token)
    aggregate_throughput = tokens_per_second_per_user * Decimal(workload.peak_concurrent_users)
    memory_bus_utilization_ratio = min(Decimal("1.0"), (bytes_moved_per_token / (effective_bw_gbps * Decimal("1000000000") * tpot_seconds)).quantize(Decimal("0.0001")))
    model_flops_utilization_ratio = Decimal("0.4500")
    is_memory_bound = True
- Zero Spanish literals anywhere in code. 100% Technical English.
- Pure Hexagonal Domain: zero I/O, zero network, zero forbidden imports.

OUTPUT FORMAT:
Generate TWO distinct markdown code blocks:
Block 1 with header `# FILE: src/domain/services/roofline_engine.py`:
```python
...
```
Block 2 with header `# FILE: tests/domain/test_roofline_engine.py`:
```python
...
```
"""
    },
    {
        "name": "OpenFairActuarialEngine",
        "service_file": SERVICES_DIR / "actuarial_engine.py",
        "test_file": TESTS_DOMAIN_DIR / "test_actuarial_engine.py",
        "prompt": """
Implement `src/domain/services/actuarial_engine.py` containing `OpenFairActuarialEngine` implementing `ActuarialRiskPort`.
And implement `tests/domain/test_actuarial_engine.py`.

Requirements:
- Class `OpenFairActuarialEngine(ActuarialRiskPort)`
- Methods:
  1. `evaluate_on_premise_hardware_risk(self, chassis: ServerChassisSpec, cluster_node_count: int, hourly_sla_penalty: MonetaryAmount, spare_chassis_count: int = 0) -> ActuarialRiskMetrics`
     * Total GPUs = cluster_node_count * chassis.accelerators_per_chassis
     * Loss Event Frequency (LEF) annual = chassis.accelerator_sku.annualized_failure_rate_pct * Decimal(total_GPUs)
     * Expected MTBF hours = (Decimal("8760") / max(Decimal("0.0001"), LEF_annual)).quantize(Decimal("0.01"))
     * MTTR hours = chassis.accelerator_sku.mttr_replacement_hours
     * Single Loss Expectancy (SLE) = hourly_sla_penalty.multiply(MTTR_hours)
     * Annualized Loss Expectancy (ALE) = SLE.multiply(LEF_annual)
     * Monthly reserve = ALE.divide(Decimal("12"))
  2. `evaluate_cloud_spot_preemption_risk(self, cloud_spec: CloudInstancePricingSpec, cluster_instance_count: int, hourly_sla_penalty: MonetaryAmount, roofline: RooflineSimulationResult) -> ActuarialRiskMetrics`
     * Daily preemption prob = cloud_spec.spot_preemption_probability_daily
     * LEF annual = (Decimal("365") * daily_preemption_prob * Decimal(cluster_instance_count)).quantize(Decimal("0.0001"))
     * Recovery MTTR hours = (cloud_spec.cold_boot_rebuild_seconds / Decimal("3600")).quantize(Decimal("0.0001"))
     * SLE = hourly_sla_penalty.multiply(Recovery_MTTR_hours)
     * ALE = SLE.multiply(LEF_annual)
     * Monthly reserve = ALE.divide(Decimal("12"))
- Zero Spanish literals anywhere in code. 100% Technical English.
- Pure Hexagonal Domain: zero I/O, zero network, zero forbidden imports.

OUTPUT FORMAT:
Generate TWO distinct markdown code blocks:
Block 1 with header `# FILE: src/domain/services/actuarial_engine.py`:
```python
...
```
Block 2 with header `# FILE: tests/domain/test_actuarial_engine.py`:
```python
...
```
"""
    },
    {
        "name": "CfoActuarialGate",
        "service_file": SERVICES_DIR / "cfo_gate.py",
        "test_file": TESTS_DOMAIN_DIR / "test_cfo_gate.py",
        "prompt": """
Implement `src/domain/services/cfo_gate.py` containing `CfoActuarialGate` implementing `ConstitutionalGatePort`.
And implement `tests/domain/test_cfo_gate.py`.

Requirements:
- Class `CfoActuarialGate(ConstitutionalGatePort)`
- Methods:
  1. `validate_physical_invariants(self, chassis: ServerChassisSpec, facility: DatacenterFacilitySpec, chassis_count_per_rack: int, policy: ConstitutionalGatePolicy) -> None`
     * Rack power = chassis.total_chassis_tdp_kw * Decimal(chassis_count_per_rack)
     * If rack_power > facility.max_rack_power_density_kw or rack_power > policy.max_rack_power_kw:
       raise ConstitutionalGateViolationError("GATE-PHY-001", "gate.phy.001.violation", {"actual_kw": rack_power, "limit_kw": min(facility.max_rack_power_density_kw, policy.max_rack_power_kw)})
     * Thermal cooling limit: max_cool_kw = policy.max_power_kw_by_cooling_topology.get(facility.cooling_topology, Decimal("20.00"))
       If rack_power > max_cool_kw:
         raise ConstitutionalGateViolationError("GATE-PHY-002", "gate.phy.002.violation", {"actual_kw": rack_power, "limit_kw": max_cool_kw, "cooling_type": facility.cooling_topology.value})
     * Carnot PUE floor: If facility.pue_rating < policy.min_carnot_pue:
       raise ConstitutionalGateViolationError("GATE-PHY-003", "gate.phy.003.violation", {"actual_pue": facility.pue_rating, "min_pue": policy.min_carnot_pue})
  2. `validate_silicon_invariants(self, roofline: RooflineSimulationResult, policy: ConstitutionalGatePolicy) -> None`
     * If roofline.vram_utilization_ratio > policy.max_vram_utilization_ratio:
       raise ConstitutionalGateViolationError("GATE-SIL-001", "gate.sil.001.violation", {"utilization_pct": (roofline.vram_utilization_ratio * Decimal("100")).quantize(Decimal("0.01")), "max_utilization_pct": (policy.max_vram_utilization_ratio * Decimal("100")).quantize(Decimal("0.01")), "reserve_pct": Decimal("10.00")})
     * If roofline.memory_bus_utilization_ratio > policy.max_memory_bus_utilization_ratio:
       raise ConstitutionalGateViolationError("GATE-SIL-002", "gate.sil.002.violation", {"bus_utilization_pct": (roofline.memory_bus_utilization_ratio * Decimal("100")).quantize(Decimal("0.01")), "max_bus_utilization_pct": (policy.max_memory_bus_utilization_ratio * Decimal("100")).quantize(Decimal("0.01"))})
  3. `validate_financial_invariants(self, tco: ComputedTcoBreakdown, salvage_value_pct: Decimal, policy: ConstitutionalGatePolicy) -> None`
     * If tco.total_monthly_nominal_tco.amount <= Decimal("0"):
       raise ConstitutionalGateViolationError("GATE-FIN-001", "gate.fin.001.violation", {"horizon_months": tco.amortization_period_months, "tco_amount": str(tco.total_monthly_nominal_tco.amount)})
     * If not (policy.min_amortization_months <= tco.amortization_period_months <= policy.max_amortization_months) or salvage_value_pct > policy.max_salvage_value_ratio:
       raise ConstitutionalGateViolationError("GATE-FIN-002", "gate.fin.002.violation", {"months": tco.amortization_period_months, "min_months": policy.min_amortization_months, "max_months": policy.max_amortization_months, "salvage_pct": (salvage_value_pct * Decimal("100")).quantize(Decimal("0.01")), "max_salvage_pct": (policy.max_salvage_value_ratio * Decimal("100")).quantize(Decimal("0.01"))})
- Zero Spanish literals anywhere in code. 100% Technical English.
- Pure Hexagonal Domain: zero I/O, zero network, zero forbidden imports.

OUTPUT FORMAT:
Generate TWO distinct markdown code blocks:
Block 1 with header `# FILE: src/domain/services/cfo_gate.py`:
```python
...
```
Block 2 with header `# FILE: tests/domain/test_cfo_gate.py`:
```python
...
```
"""
    },
    {
        "name": "HybridTcoAggregator",
        "service_file": SERVICES_DIR / "tco_aggregator.py",
        "test_file": TESTS_DOMAIN_DIR / "test_tco_aggregator.py",
        "prompt": """
Implement `src/domain/services/tco_aggregator.py` containing `HybridTcoAggregator` implementing `HybridTcoAggregatorPort`.
And implement `tests/domain/test_tco_aggregator.py`.

Requirements:
- Class `HybridTcoAggregator(HybridTcoAggregatorPort)`
- Methods:
  1. `compute_on_premise_tco(self, chassis: ServerChassisSpec, facility: DatacenterFacilitySpec, roofline: RooflineSimulationResult, amortization_months: int, chassis_per_rack: int, management_plane_monthly: MonetaryAmount, persistent_storage_monthly: MonetaryAmount, network_egress_monthly: MonetaryAmount) -> ComputedTcoBreakdown`
     * Total nodes = roofline.required_cluster_nodes_baseline
     * Total chassis CapEx = chassis.capex_unit_price.multiply(Decimal(total_nodes))
     * salvage_pct = chassis.get_salvage_value_pct(amortization_months)
     * Net CapEx = total chassis CapEx.multiply(Decimal("1.0") - salvage_pct)
     * Monthly hardware compute = Net CapEx.divide(Decimal(amortization_months))
     * Total power kW = chassis.total_chassis_tdp_kw * Decimal(total_nodes) * facility.pue_rating
     * Monthly power kWh = Total power kW * Decimal("730")
     * Monthly power cost = facility.electricity_rate_per_kwh.multiply(monthly_power_kwh)
     * Racks required = max(1, math.ceil(total_nodes / chassis_per_rack))
     * Monthly rack cost = facility.colocation_rack_monthly_fee.multiply(Decimal(racks_required))
     * Monthly OEM support = (total chassis CapEx.multiply(chassis.oem_warranty_annual_pct)).divide(Decimal("12"))
     * Total monthly nominal = compute + management + storage + power + rack + oem + egress
  2. `compute_cloud_tco(self, cloud_spec: CloudInstancePricingSpec, workload: LlmWorkloadProfile, roofline: RooflineSimulationResult, amortization_months: int, spot_allocation_ratio: Decimal, reserved_allocation_ratio: Decimal, persistent_storage_gb: Decimal, monthly_egress_gb: Decimal, management_plane_monthly: MonetaryAmount, hours_per_month: Decimal) -> ComputedTcoBreakdown`
     * Total instances = roofline.required_cluster_nodes_baseline
     * Blended hourly = (cloud_spec.spot_hourly_mean.multiply(spot_allocation_ratio)
                         .add(cloud_spec.reserved_1yr_hourly.multiply(reserved_allocation_ratio))
                         .add(cloud_spec.on_demand_hourly.multiply(Decimal("1.0") - spot_allocation_ratio - reserved_allocation_ratio)))
     * Monthly compute = blended_hourly.multiply(Decimal(total_instances)).multiply(hours_per_month)
     * Monthly storage = cloud_spec.storage_gb_monthly.multiply(persistent_storage_gb)
     * Monthly egress = cloud_spec.egress_gb_price.multiply(monthly_egress_gb)
     * Total monthly nominal = compute + management + storage + egress
  3. `compute_hybrid_tco(self, on_prem_tco: ComputedTcoBreakdown, cloud_tco: ComputedTcoBreakdown, recommendation: ArchetypeRecommendationResult) -> ComputedTcoBreakdown`
     * Weighted synthesis based on recommendation.recommended_base_load_split_pct and recommended_burst_load_split_pct.
- Zero Spanish literals anywhere in code. 100% Technical English.
- Pure Hexagonal Domain: zero I/O, zero network, zero forbidden imports.

OUTPUT FORMAT:
Generate TWO distinct markdown code blocks:
Block 1 with header `# FILE: src/domain/services/tco_aggregator.py`:
```python
...
```
Block 2 with header `# FILE: tests/domain/test_tco_aggregator.py`:
```python
...
```
"""
    },
]


def parse_two_blocks(text: str) -> tuple[str, str]:
    pattern = r"```(?:python)?\s*\n(.*?)\n```"
    matches = re.findall(pattern, text, re.DOTALL)
    if len(matches) >= 2:
        return matches[0].strip() + "\n", matches[1].strip() + "\n"
    elif len(matches) == 1:
        return matches[0].strip() + "\n", ""
    return text.strip() + "\n", ""


def main() -> None:
    client = create_genai_client()
    model_name = get_model(ModelTier.REASONING)
    print(f"[+] Consulting Cognitive Arbiter: {model_name}")
    print("[+] Loading Phase 1 domain context...")
    context = load_domain_context()

    for item in SERVICES_TO_GENERATE:
        service_name = item["name"]
        print(f"\n{'='*70}\n[+] Synthesizing Service: {service_name}\n{'='*70}")

        full_prompt = f"""
You are the Principal AI Systems Architect & Core Infrastructure Engineer.
We need you to generate production-grade Python code for Phase 2 of the Universal Hybrid FinOps Advisor.
Follow all user directives:
1. 100% PURE TECHNICAL ENGLISH (Zero Spanish words, identifiers, comments, or docstrings).
2. ZERO HARDCODED CONSTANTS: all thresholds and rates are passed via models/ports/policy.
3. HEXAGONAL PURITY: pure standard library only (dataclasses, decimal, math, typing, abc).
4. STRICT INVARIANT DEFENSE against all edge cases.

DOMAIN CONTEXT FROM PHASE 1:
{context}

TASK SPECIFICATION:
{item['prompt']}
"""
        response = client.models.generate_content(
            model=model_name,
            contents=full_prompt,
        )

        service_code, test_code = parse_two_blocks(response.text)

        item["service_file"].write_text(service_code, encoding="utf-8")
        print(f"[✓] Generated {item['service_file'].relative_to(REPO_ROOT)} ({len(service_code)} chars)")

        if test_code:
            item["test_file"].write_text(test_code, encoding="utf-8")
            print(f"[✓] Generated {item['test_file'].relative_to(REPO_ROOT)} ({len(test_code)} chars)")

        # Validate syntax immediately
        res = subprocess.run([sys.executable, "-m", "py_compile", str(item["service_file"])], capture_output=True, text=True)
        if res.returncode != 0:
            print(f"[!] Syntax error in {item['service_file']}:\n{res.stderr}")
            sys.exit(1)
        if test_code:
            res_t = subprocess.run([sys.executable, "-m", "py_compile", str(item["test_file"])], capture_output=True, text=True)
            if res_t.returncode != 0:
                print(f"[!] Syntax error in {item['test_file']}:\n{res_t.stderr}")
                sys.exit(1)

    # Write src/domain/services/__init__.py
    init_services = SERVICES_DIR / "__init__.py"
    init_services.write_text(
        '"""Pure Domain Calculation Services for Universal Hybrid FinOps Advisor."""\n\n'
        "from src.domain.services.questionnaire_engine import QuestionnaireDecisionEngine\n"
        "from src.domain.services.roofline_engine import RooflinePhysicsEngine\n"
        "from src.domain.services.actuarial_engine import OpenFairActuarialEngine\n"
        "from src.domain.services.cfo_gate import CfoActuarialGate\n"
        "from src.domain.services.tco_aggregator import HybridTcoAggregator\n\n"
        "__all__ = [\n"
        '    "QuestionnaireDecisionEngine",\n'
        '    "RooflinePhysicsEngine",\n'
        '    "OpenFairActuarialEngine",\n'
        '    "CfoActuarialGate",\n'
        '    "HybridTcoAggregator",\n'
        "]\n",
        encoding="utf-8",
    )
    print(f"\n[✓] Generated {init_services.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
