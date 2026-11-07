"""
Unit Tests for the FinOps, TCO & Asymmetric Chargeback Calculator
================================================================
Verifies mathematical models, duty cycle hibernation savings,
asymmetric bandwidth rate allocations, and commercial API break-even.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add calculators/chargeback/src to path for testing
CHARGEBACK_SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(CHARGEBACK_SRC))

import pytest  # noqa: E402
from chargeback import (  # type: ignore # noqa: E402
    COMMERCIAL_GPT4O,
    ChargebackDemandRequest,
    DutyCycleMode,
    FinOpsChargebackEngine,
    calculate_asymmetric_unit_costs,
    calculate_breakeven_and_savings,
    calculate_monthly_productive_tokens,
    calculate_monthly_tco_usd,
    resolve_monthly_active_hours,
)


class TestTCOAndDutyCyclePhysics:
    """Verifies monthly runtime hours and fully-loaded TCO calculations."""

    def test_duty_cycle_hours_resolution(self) -> None:
        # Hibernated business hours = 11h/day * 22 days = 242.0 hours
        assert resolve_monthly_active_hours(DutyCycleMode.BUSINESS_HOURS_HIBERNATED) == 242.0
        # Continuous 24/7 = 730.0 hours
        assert resolve_monthly_active_hours(DutyCycleMode.CONTINUOUS_24_7) == 730.0
        # Custom hours
        assert resolve_monthly_active_hours(DutyCycleMode.CUSTOM, custom_hours=350.0) == 350.0

    def test_hibernation_tco_savings_factor(self) -> None:
        gpu_rate = 1.40  # 2x L4 Spot ($0.70/h each = $1.40/h)
        mgmt_rate = 0.10  # e2-standard-2 CPU node ($0.10/h)
        storage = 15.0  # 100GB persistent disks
        egress = 10.0

        # Hibernated TCO: (1.50 * 242) + 25 = 363.0 + 25 = $388.00
        tco_hibernated = calculate_monthly_tco_usd(
            hourly_gpu_cost=gpu_rate,
            hourly_cpu_mgmt_cost=mgmt_rate,
            active_hours_monthly=242.0,
            monthly_storage_cost=storage,
            monthly_egress_cost=egress,
        )
        assert tco_hibernated == 388.0

        # Continuous 24/7 TCO: (1.50 * 730) + 25 = 1095.0 + 25 = $1120.00
        tco_continuous = calculate_monthly_tco_usd(
            hourly_gpu_cost=gpu_rate,
            hourly_cpu_mgmt_cost=mgmt_rate,
            active_hours_monthly=730.0,
            monthly_storage_cost=storage,
            monthly_egress_cost=egress,
        )
        assert tco_continuous == 1120.0

        # Hibernation delivers 65.3% net TCO savings
        savings_pct = (tco_continuous - tco_hibernated) / tco_continuous * 100.0
        assert 65.0 < savings_pct < 66.0

    def test_monthly_productive_tokens_duty_cycle(self) -> None:
        # Cluster throughput = 450 tokens/s, 242 active hours, 30% duty factor
        # 450 * (242 * 3600) * 0.30 = 450 * 871,200 * 0.30 = 117,612,000 tokens (117.6M tokens)
        tokens = calculate_monthly_productive_tokens(
            aggregate_throughput_tps=450.0,
            active_hours_monthly=242.0,
            duty_utilization_factor=0.30,
        )
        assert tokens == 117612000.0


class TestAsymmetricBandwidthEconomics:
    """Verifies memory bandwidth penalty and prompt caching discount allocations."""

    def test_asymmetric_unit_rates(self) -> None:
        tco = 388.0  # $388 monthly TCO
        tokens = 117612000.0  # 117.6M tokens
        # Ratio 3:1 -> in_fraction = 0.75, out_fraction = 0.25
        # Weighted units = (117.6M * 0.75 * 1.0) + (117.6M * 0.25 * 3.0) = 88.2M + 88.2M = 176.418M units
        # Cost base input = 388 / 176.418M * 1M ≈ $2.1993 per 1M tokens
        (
            units,
            cost_in,
            cost_out,
            cost_cache,
            billed_in,
            billed_out,
            _billed_cache,
        ) = calculate_asymmetric_unit_costs(
            monthly_tco_usd=tco,
            monthly_effective_tokens=tokens,
            input_output_ratio=3.0,
            decode_bandwidth_penalty=3.0,
            prompt_caching_discount=0.80,
            departmental_margin_pct=0.0,
        )

        assert pytest.approx(units, rel=1e-3) == 176418000.0
        assert 2.19 < cost_in < 2.21
        # Decode output is exactly 3x input rate
        assert pytest.approx(cost_out, rel=1e-3) == cost_in * 3.0
        # Cache hit is exactly 20% of input rate (80% discount)
        assert pytest.approx(cost_cache, rel=1e-3) == cost_in * 0.20
        # With 0% margin, billed equals cost
        assert billed_in == cost_in
        assert billed_out == cost_out

    def test_departmental_margin_markup(self) -> None:
        # With 15% departmental margin markup
        (
            _,
            cost_in,
            cost_out,
            _,
            billed_in,
            billed_out,
            _,
        ) = calculate_asymmetric_unit_costs(
            monthly_tco_usd=500.0,
            monthly_effective_tokens=100_000_000.0,
            input_output_ratio=3.0,
            decode_bandwidth_penalty=3.0,
            prompt_caching_discount=0.80,
            departmental_margin_pct=15.0,
        )
        assert pytest.approx(billed_in, rel=1e-3) == cost_in * 1.15
        assert pytest.approx(billed_out, rel=1e-3) == cost_out * 1.15


class TestCommercialAPIBreakEven:
    """Verifies break-even thresholds and customer savings vs OpenAI and Anthropic."""

    def test_gpt4o_blended_rate_and_breakeven(self) -> None:
        # GPT-4o: $2.50 in, $10.00 out, $1.25 cached in
        # 3:1 ratio (75% in, 25% out), 20% cache hit rate on input
        # In uncached = 75% * 80% = 60% * $2.50 = $1.50
        # In cached = 75% * 20% = 15% * $1.25 = $0.1875
        # Out = 25% * $10.00 = $2.50
        # Blended rate = 1.50 + 0.1875 + 2.50 = $4.1875 / 1M tokens
        blended = COMMERCIAL_GPT4O.compute_blended_rate_per_m(input_ratio=3.0, cache_hit_rate=0.20)
        assert pytest.approx(blended, rel=1e-3) == 4.1875

        # With monthly TCO = $388.00:
        # Break-even tokens = 388 / (4.1875 / 1M) = 92,656,716 tokens (~92.6M tokens)
        (
            comm_rate,
            tokens_be,
            savings,
            cost_reduct_pct,
            is_cost_effective,
        ) = calculate_breakeven_and_savings(
            monthly_tco_usd=388.0,
            monthly_effective_tokens=117612000.0,
            commercial_api=COMMERCIAL_GPT4O,
            input_output_ratio=3.0,
        )

        assert pytest.approx(comm_rate, rel=1e-3) == 4.1875
        assert 92_000_000.0 < tokens_be < 93_000_000.0
        # At full 117.6M token capacity, customer saves positive money
        assert savings > 100.0
        assert is_cost_effective is True
        assert cost_reduct_pct > 20.0


class TestFinOpsChargebackEngineIntegration:
    """Verifies end-to-end chargeback evaluation."""

    def test_complete_enterprise_chargeback_report(self) -> None:
        engine = FinOpsChargebackEngine()
        request = ChargebackDemandRequest(
            cluster_hourly_gpu_cost=1.40,
            cluster_hourly_mgmt_cpu_cost=0.10,
            monthly_storage_cost=15.0,
            monthly_egress_cost=10.0,
            cluster_aggregate_throughput_tps=450.0,
            duty_cycle_mode=DutyCycleMode.BUSINESS_HOURS_HIBERNATED,
            duty_utilization_factor=0.30,
            departmental_margin_pct=10.0,
            benchmark_commercial_api=COMMERCIAL_GPT4O,
        )
        result = engine.evaluate_chargeback(request)

        assert result.monthly_active_hours == 242.0
        assert result.monthly_tco_usd == 388.0
        assert result.monthly_effective_tokens == 117612000.0
        assert result.cost_base_input_per_m_usd > 2.0
        assert result.billed_output_per_m_usd > result.billed_input_per_m_usd * 2.9
        assert result.commercial_provider_name == "OpenAI GPT-4o"
        assert result.is_private_cluster_cost_effective is True
        assert result.monthly_customer_savings_at_capacity_usd > 100.0
