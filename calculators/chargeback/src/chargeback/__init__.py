"""
FinOps, TCO & Asymmetric Chargeback Calculator
==============================================
Independent financial calculator implementing true TCO under hibernation duty cycles,
asymmetric bandwidth-penalized internal chargeback rates, and commercial API break-even.
"""

from __future__ import annotations

from .domain.model import (
    COMMERCIAL_CLAUDE_35_SONNET,
    COMMERCIAL_GEMINI_25_FLASH,
    COMMERCIAL_GPT4O,
    ChargebackDemandRequest,
    ChargebackFinancialOutput,
    CommercialAPIRate,
    DutyCycleMode,
    FinOpsChargebackEngine,
    calculate_asymmetric_unit_costs,
    calculate_breakeven_and_savings,
    calculate_monthly_productive_tokens,
    calculate_monthly_tco_usd,
    resolve_monthly_active_hours,
)

__all__ = [
    "COMMERCIAL_CLAUDE_35_SONNET",
    "COMMERCIAL_GEMINI_25_FLASH",
    "COMMERCIAL_GPT4O",
    "ChargebackDemandRequest",
    "ChargebackFinancialOutput",
    "CommercialAPIRate",
    "DutyCycleMode",
    "FinOpsChargebackEngine",
    "calculate_asymmetric_unit_costs",
    "calculate_breakeven_and_savings",
    "calculate_monthly_productive_tokens",
    "calculate_monthly_tco_usd",
    "resolve_monthly_active_hours",
]
