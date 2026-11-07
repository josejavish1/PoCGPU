"""
FinOps, TCO & Asymmetric Chargeback Calculation Engine
======================================================
Independent financial calculator implementing the enterprise economics,
hibernation duty cycles, and asymmetric bandwidth-penalized internal chargeback
defined in `calculators/docs/09_MODELO_FINOPS_CALCULADORA.md` (Section 3).

Key Domain Capabilities:
1. True TCO with Hibernation Window (242h business-hours duty cycle vs 730h 24/7 continuous)
2. Monthly Productive Capacity with empirical duty utilization factor (default 30%)
3. Asymmetric Silicon Cost Allocation (3:1 decode-to-prefill bandwidth saturation penalty)
4. Prompt Caching Discount Rate (80% discount on Radix / KV-cache hits)
5. Departmental Margin Billing and Cost-Recovery Pricing
6. Break-Even Token Volume and ROI vs Commercial Frontier APIs (OpenAI GPT-4o, Claude 3.5 Sonnet)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class DutyCycleMode(StrEnum):
    BUSINESS_HOURS_HIBERNATED = (
        "BUSINESS_HOURS_HIBERNATED"  # 11h/day x 22 days = 242 h/month ($0 in valleys)
    )
    CONTINUOUS_24_7 = "CONTINUOUS_24_7"  # 730 h/month non-stop
    CUSTOM = "CUSTOM"


@dataclass(frozen=True)
class CommercialAPIRate:
    provider_name: str
    input_rate_per_m_usd: float
    output_rate_per_m_usd: float
    cached_input_rate_per_m_usd: float

    def compute_blended_rate_per_m(
        self, input_ratio: float = 3.0, cache_hit_rate: float = 0.20
    ) -> float:
        """
        Computes weighted blended price per 1M tokens based on traffic distribution:
        Traffic ratio 3:1 -> 75% input, 25% output.
        """
        total_parts = input_ratio + 1.0
        in_fraction = input_ratio / total_parts
        out_fraction = 1.0 / total_parts

        uncached_in_fraction = in_fraction * (1.0 - cache_hit_rate)
        cached_in_fraction = in_fraction * cache_hit_rate

        return (
            (uncached_in_fraction * self.input_rate_per_m_usd)
            + (cached_in_fraction * self.cached_input_rate_per_m_usd)
            + (out_fraction * self.output_rate_per_m_usd)
        )


# Reference Commercial Benchmarks (2026 Enterprise Rates)
COMMERCIAL_GPT4O = CommercialAPIRate(
    provider_name="OpenAI GPT-4o",
    input_rate_per_m_usd=2.50,
    output_rate_per_m_usd=10.00,
    cached_input_rate_per_m_usd=1.25,
)

COMMERCIAL_CLAUDE_35_SONNET = CommercialAPIRate(
    provider_name="Anthropic Claude 3.5 Sonnet",
    input_rate_per_m_usd=3.00,
    output_rate_per_m_usd=15.00,
    cached_input_rate_per_m_usd=0.30,
)

COMMERCIAL_GEMINI_25_FLASH = CommercialAPIRate(
    provider_name="Google Gemini 2.5 Flash",
    input_rate_per_m_usd=0.075,
    output_rate_per_m_usd=0.300,
    cached_input_rate_per_m_usd=0.01875,
)


@dataclass(frozen=True)
class ChargebackDemandRequest:
    cluster_hourly_gpu_cost: float
    cluster_hourly_mgmt_cpu_cost: float
    monthly_storage_cost: float
    monthly_egress_cost: float
    cluster_aggregate_throughput_tps: float
    duty_cycle_mode: DutyCycleMode = DutyCycleMode.BUSINESS_HOURS_HIBERNATED
    custom_active_hours_monthly: float | None = None
    duty_utilization_factor: float = 0.30  # Realistic human pauses and bursty duty cycle
    input_output_token_ratio: float = 3.0  # 3:1 input-to-output token distribution
    decode_bandwidth_penalty_ratio: float = 3.0  # Decode saturates memory bandwidth 3x more
    prompt_caching_discount_ratio: float = 0.80  # 80% discount on cache hits
    departmental_margin_pct: float = 0.0  # Cost-recovery default (0%), or e.g. 15% margin
    benchmark_commercial_api: CommercialAPIRate = COMMERCIAL_GPT4O


@dataclass(frozen=True)
class ChargebackFinancialOutput:
    duty_cycle_mode: DutyCycleMode
    monthly_active_hours: float
    monthly_tco_usd: float
    monthly_effective_tokens: float
    weighted_units_volume: float
    cost_base_input_per_m_usd: float
    cost_base_output_per_m_usd: float
    cost_cache_hit_per_m_usd: float
    billed_input_per_m_usd: float
    billed_output_per_m_usd: float
    billed_cache_hit_per_m_usd: float
    commercial_provider_name: str
    commercial_blended_rate_per_m_usd: float
    monthly_tokens_breakeven: float
    monthly_customer_savings_at_capacity_usd: float
    cost_reduction_vs_commercial_pct: float
    is_private_cluster_cost_effective: bool


# --- Core Mathematical Functions ---


def resolve_monthly_active_hours(
    duty_cycle_mode: DutyCycleMode,
    custom_hours: float | None = None,
) -> float:
    """
    Computes billable runtime hours according to enterprise hibernation schedule:
    - Business Hours: 11h/day * 22 working days/month = 242.0 hours
    - 24/7 Continuous: 730.0 hours
    """
    if duty_cycle_mode == DutyCycleMode.BUSINESS_HOURS_HIBERNATED:
        return 242.0
    elif duty_cycle_mode == DutyCycleMode.CONTINUOUS_24_7:
        return 730.0
    elif duty_cycle_mode == DutyCycleMode.CUSTOM and custom_hours is not None:
        return max(1.0, min(730.0, custom_hours))
    return 242.0


def calculate_monthly_tco_usd(
    hourly_gpu_cost: float,
    hourly_cpu_mgmt_cost: float,
    active_hours_monthly: float,
    monthly_storage_cost: float,
    monthly_egress_cost: float,
) -> float:
    """
    Calculates fully-loaded cluster monthly TCO:
    TCO = (GPU_Cost/h * Hours) + (CPU_Cost/h * Hours) + Storage_SSD + Egress
    """
    compute_cost = (hourly_gpu_cost + hourly_cpu_mgmt_cost) * active_hours_monthly
    return compute_cost + monthly_storage_cost + monthly_egress_cost


def calculate_monthly_productive_tokens(
    aggregate_throughput_tps: float,
    active_hours_monthly: float,
    duty_utilization_factor: float,
) -> float:
    """
    Calculates net productive tokens produced per month:
    Tokens_monthly = Throughput_tps * (Hours * 3600) * Utilization_Factor (default 0.30)
    """
    active_seconds = active_hours_monthly * 3600.0
    return aggregate_throughput_tps * active_seconds * duty_utilization_factor


def calculate_asymmetric_unit_costs(
    monthly_tco_usd: float,
    monthly_effective_tokens: float,
    input_output_ratio: float,
    decode_bandwidth_penalty: float,
    prompt_caching_discount: float,
    departmental_margin_pct: float,
) -> tuple[float, float, float, float, float, float, float]:
    """
    Computes asymmetric token rates reflecting memory bandwidth saturation:
    Output decode tokens consume ~3x more memory bandwidth than prefill tokens.
    """
    total_parts = input_output_ratio + 1.0
    input_fraction = input_output_ratio / total_parts
    output_fraction = 1.0 / total_parts

    # Weighted accounting units: U_weighted = (Tokens * in_frac * 1.0) + (Tokens * out_frac * penalty)
    weighted_units = (monthly_effective_tokens * input_fraction * 1.0) + (
        monthly_effective_tokens * output_fraction * decode_bandwidth_penalty
    )

    if weighted_units <= 0:
        return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

    # Base cost per 1M units
    cost_base_input_1m = (monthly_tco_usd / weighted_units) * 1_000_000.0
    cost_base_output_1m = cost_base_input_1m * decode_bandwidth_penalty
    cost_cache_hit_1m = cost_base_input_1m * (1.0 - prompt_caching_discount)

    # Departmental billed rates with margin
    margin_multiplier = 1.0 + (departmental_margin_pct / 100.0)
    billed_input_1m = cost_base_input_1m * margin_multiplier
    billed_output_1m = cost_base_output_1m * margin_multiplier
    billed_cache_hit_1m = cost_cache_hit_1m * margin_multiplier

    return (
        weighted_units,
        cost_base_input_1m,
        cost_base_output_1m,
        cost_cache_hit_1m,
        billed_input_1m,
        billed_output_1m,
        billed_cache_hit_1m,
    )


def calculate_breakeven_and_savings(
    monthly_tco_usd: float,
    monthly_effective_tokens: float,
    commercial_api: CommercialAPIRate,
    input_output_ratio: float,
) -> tuple[float, float, float, float, bool]:
    """
    Computes the break-even token volume and customer savings vs commercial APIs:
    Tokens_BreakEven = TCO_monthly / Commercial_Blended_Rate_Per_Token
    """
    blended_rate_1m = commercial_api.compute_blended_rate_per_m(
        input_ratio=input_output_ratio, cache_hit_rate=0.20
    )
    blended_rate_per_token = blended_rate_1m / 1_000_000.0

    if blended_rate_per_token <= 0:
        return 0.0, 0.0, 0.0, 0.0, False

    tokens_breakeven = monthly_tco_usd / blended_rate_per_token
    equivalent_commercial_invoice = (monthly_effective_tokens / 1_000_000.0) * blended_rate_1m
    monthly_savings = equivalent_commercial_invoice - monthly_tco_usd

    cost_reduction_pct = (
        (monthly_savings / equivalent_commercial_invoice * 100.0)
        if equivalent_commercial_invoice > 0
        else 0.0
    )
    is_cost_effective = monthly_effective_tokens >= tokens_breakeven

    return (
        blended_rate_1m,
        tokens_breakeven,
        monthly_savings,
        cost_reduction_pct,
        is_cost_effective,
    )


# --- Canonical Chargeback Engine ---


class FinOpsChargebackEngine:
    """Canonical Engine executing TCO modeling, asymmetric chargeback, and ROI analysis."""

    def evaluate_chargeback(self, request: ChargebackDemandRequest) -> ChargebackFinancialOutput:
        """Computes complete financial chargeback analysis for a cluster deployment."""
        # 1. Resolve Active Hours
        active_hours = resolve_monthly_active_hours(
            duty_cycle_mode=request.duty_cycle_mode,
            custom_hours=request.custom_active_hours_monthly,
        )

        # 2. Fully-Loaded Monthly TCO
        monthly_tco = calculate_monthly_tco_usd(
            hourly_gpu_cost=request.cluster_hourly_gpu_cost,
            hourly_cpu_mgmt_cost=request.cluster_hourly_mgmt_cpu_cost,
            active_hours_monthly=active_hours,
            monthly_storage_cost=request.monthly_storage_cost,
            monthly_egress_cost=request.monthly_egress_cost,
        )

        # 3. Monthly Productive Tokens
        monthly_tokens = calculate_monthly_productive_tokens(
            aggregate_throughput_tps=request.cluster_aggregate_throughput_tps,
            active_hours_monthly=active_hours,
            duty_utilization_factor=request.duty_utilization_factor,
        )

        # 4. Asymmetric Unit Economics
        (
            weighted_units,
            cost_in_1m,
            cost_out_1m,
            cost_cache_1m,
            billed_in_1m,
            billed_out_1m,
            billed_cache_1m,
        ) = calculate_asymmetric_unit_costs(
            monthly_tco_usd=monthly_tco,
            monthly_effective_tokens=monthly_tokens,
            input_output_ratio=request.input_output_token_ratio,
            decode_bandwidth_penalty=request.decode_bandwidth_penalty_ratio,
            prompt_caching_discount=request.prompt_caching_discount_ratio,
            departmental_margin_pct=request.departmental_margin_pct,
        )

        # 5. Break-Even & ROI vs Commercial Frontier API
        (
            comm_blended_1m,
            tokens_breakeven,
            monthly_savings,
            cost_reduction_pct,
            is_cost_effective,
        ) = calculate_breakeven_and_savings(
            monthly_tco_usd=monthly_tco,
            monthly_effective_tokens=monthly_tokens,
            commercial_api=request.benchmark_commercial_api,
            input_output_ratio=request.input_output_token_ratio,
        )

        return ChargebackFinancialOutput(
            duty_cycle_mode=request.duty_cycle_mode,
            monthly_active_hours=round(active_hours, 1),
            monthly_tco_usd=round(monthly_tco, 2),
            monthly_effective_tokens=round(monthly_tokens, 0),
            weighted_units_volume=round(weighted_units, 0),
            cost_base_input_per_m_usd=round(cost_in_1m, 4),
            cost_base_output_per_m_usd=round(cost_out_1m, 4),
            cost_cache_hit_per_m_usd=round(cost_cache_1m, 4),
            billed_input_per_m_usd=round(billed_in_1m, 4),
            billed_output_per_m_usd=round(billed_out_1m, 4),
            billed_cache_hit_per_m_usd=round(billed_cache_1m, 4),
            commercial_provider_name=request.benchmark_commercial_api.provider_name,
            commercial_blended_rate_per_m_usd=round(comm_blended_1m, 4),
            monthly_tokens_breakeven=round(tokens_breakeven, 0),
            monthly_customer_savings_at_capacity_usd=round(monthly_savings, 2),
            cost_reduction_vs_commercial_pct=round(cost_reduction_pct, 1),
            is_private_cluster_cost_effective=is_cost_effective,
        )
