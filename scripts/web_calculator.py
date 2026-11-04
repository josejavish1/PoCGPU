#!/usr/bin/env python3
"""
Enterprise Tier-1 Universal Hybrid FinOps Advisor Platform
==========================================================
Unified FastAPI backend & reactive Vanilla HTML5/CSS3/SVG/ES6 Single Page Application.
Features:
- Guided 5-Question Strategic Assessment Wizard (Sovereignty, Duty Cycle, Datacenter, CapEx/OpEx, SRE).
- Algorithmic Archetype Recommendation: Sovereign On-Prem vs Elastic Cloud vs Hybrid Cloud-Bursting.
- Pre-Flight CFO Constitutional Audit Gate (Physical, Thermal, Silicon, and Financial Invariants).
- Open FAIR Quantitative Actuarial Risk Engine (Hardware Silicon AFR / RMA MTTR vs Cloud Spot Preemption).
- Side-by-Side 3-Year TCO Arbitrage: Amortized On-Premises CapEx + Power/PUE vs Cloud OpEx vs OpenAI.
- Cryptographic Tamper-Evident SHA-256 Hash-Chained Audit Ledger for corporate compliance.
- 100% Language Decoupled: Dynamic i18n localization (EN/ES) powered by config/locales.json.
- Dynamic Catalogs: Zero hardcoding; loaded from config/catalogs/ and config/taxonomies/.
"""

from __future__ import annotations

import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import uvicorn

from src.application.finops_advisor_service import FinOpsAdvisorService
from src.domain.exceptions import ConstitutionalGateViolationError, DomainException, DomainLookupError
from src.domain.models.financial import CurrencyCode, MonetaryAmount
from src.domain.models.hardware import CoolingTopology, DatacenterFacilitySpec

app = FastAPI(title="Universal Hybrid LLM FinOps Advisor", version="2.0.0")

# Initialize orchestrator service
service = FinOpsAdvisorService(REPO_ROOT)


@app.exception_handler(DomainLookupError)
async def domain_lookup_exception_handler(request: Request, exc: DomainLookupError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"error_type": "DomainLookupError", "message": str(exc)})


@app.exception_handler(ConstitutionalGateViolationError)
async def constitutional_gate_exception_handler(request: Request, exc: ConstitutionalGateViolationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error_type": "ConstitutionalGateViolationError",
            "rule_code": exc.rule_code,
            "i18n_key": exc.i18n_key,
            "i18n_params": {k: str(v) for k, v in exc.i18n_params.items()},
        },
    )


@app.exception_handler(DomainException)
async def generic_domain_exception_handler(request: Request, exc: DomainException) -> JSONResponse:
    return JSONResponse(status_code=400, content={"error_type": "DomainException", "message": str(exc)})


@app.exception_handler(ValueError)
async def value_error_exception_handler(request: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"error_type": "ValueError", "message": str(exc)})


@app.exception_handler(TypeError)
async def type_error_exception_handler(request: Request, exc: TypeError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"error_type": "TypeError", "message": str(exc)})


class AssessmentEvaluationRequest(BaseModel):
    vertical_id: str
    client_responses: Dict[str, str]
    model_id: str
    concurrent_users: int = 32
    max_context_length: int = 8192
    prompt_tokens: int = 2048
    output_tokens: int = 256
    baseline_rps: Decimal = Decimal("4.0000")
    peak_burst_rps: Decimal = Decimal("8.0000")
    locale: str = "en"


class FullSimulationRequest(BaseModel):
    vertical_id: str
    client_responses: Dict[str, str]
    model_id: str
    on_prem_chassis_id: str
    cloud_instance_id: str
    amortization_months: int = 36
    currency: str = "USD"
    pue_rating: Decimal = Decimal("1.2500")
    electricity_kwh_rate: Decimal = Decimal("0.1600")
    colocation_rack_fee: Decimal = Decimal("1500.00")
    cooling_type: str = "AIR_COOLED"
    concurrent_users: int = 32
    max_context_length: int = 8192
    prompt_tokens: int = 2048
    output_tokens: int = 256
    baseline_rps: Decimal = Decimal("4.0000")
    peak_burst_rps: Decimal = Decimal("8.0000")
    chassis_per_rack: int = 1
    max_rack_units_u: int = 42
    max_rack_power_density_kw: Decimal = Decimal("35.00")


@app.get("/api/catalog")
def get_catalog() -> dict[str, Any]:
    """Exposes dynamic hardware accelerators, chassis, cloud VMs, and localized translation keys."""
    locales = service.get_locales()
    overview = service.get_catalog_overview()
    cloud_instances = service.get_cloud_instances()

    cloud_instances_list = [
        {
            "instance_id": inst.instance_id,
            "provider": inst.provider_id,
            "type": inst.instance_type,
            "region": inst.region,
            "accelerator_sku_id": inst.accelerator_sku.sku_id,
            "on_demand_hourly": str(inst.on_demand_hourly.amount),
            "spot_hourly": str(inst.spot_hourly_mean.amount),
            "currency": str(inst.on_demand_hourly.currency),
        }
        for inst in cloud_instances
    ]

    return {
        "models": overview["models"],
        "chassis": overview["chassis"],
        "cloud_instances": cloud_instances_list,
        "verticals": overview["verticals"],
        "currencies": list(service.get_available_currencies()),
        "translations": locales.get("translations", {}),
    }


@app.get("/api/questionnaire")
def get_questionnaire(vertical_id: str = "BANKING_FINANCE", locale: str = "en") -> dict[str, Any]:
    """Exposes the 5 strategic non-functional assessment questions for dynamic client rendering."""
    schema = service.get_questionnaire_schema(vertical_id, locale)
    return {
        "questions": [
            {
                "question_id": q.question_id,
                "dimension_name": q.dimension_name,
                "i18n_prompt_key": q.i18n_prompt_key,
                "weight": str(q.weight),
                "options": [
                    {
                        "option_id": opt.option_id,
                        "i18n_label_key": opt.i18n_label_key,
                        "on_prem_score": str(opt.on_prem_affinity_score),
                        "cloud_score": str(opt.cloud_affinity_score),
                        "is_hard_on_prem_veto": opt.is_hard_on_prem_veto,
                        "is_hard_cloud_veto": opt.is_hard_cloud_veto,
                    }
                    for opt in q.options
                ],
            }
            for q in schema
        ]
    }


@app.post("/api/assess")
def evaluate_assessment(req: AssessmentEvaluationRequest) -> dict[str, Any]:
    """Evaluates client responses and outputs the optimal deployment archetype."""
    workload = service.get_model_profile(
        model_id=req.model_id,
        peak_concurrent_users=req.concurrent_users,
        max_context_length=req.max_context_length,
        avg_prompt_tokens=req.prompt_tokens,
        avg_generated_tokens=req.output_tokens,
        baseline_rps=req.baseline_rps,
        peak_burst_rps=req.peak_burst_rps,
    )
    res = service.evaluate_guided_assessment(
        vertical_id=req.vertical_id,
        client_responses=req.client_responses,
        workload=workload,
        locale=req.locale,
    )
    return {
        "recommended_archetype": res.recommended_archetype.value,
        "on_prem_composite_score": str(res.on_prem_composite_score),
        "cloud_composite_score": str(res.cloud_composite_score),
        "divergence_delta": str(res.divergence_delta),
        "recommended_base_load_split_pct": str(res.recommended_base_load_split_pct),
        "recommended_burst_load_split_pct": str(res.recommended_burst_load_split_pct),
        "is_veto_enforced": res.is_veto_enforced,
        "veto_reason_i18n_key": res.veto_reason_i18n_key,
        "strategic_rationale_i18n_keys": list(res.strategic_rationale_i18n_keys),
    }


@app.post("/api/simulate")
def run_simulation(req: FullSimulationRequest) -> dict[str, Any]:
    """Executes full mathematical, physical, and financial simulation across On-Prem and Cloud."""
    curr = CurrencyCode(req.currency.upper())

    if req.cooling_type not in [c.name for c in CoolingTopology]:
        raise HTTPException(status_code=400, detail=f"Invalid cooling_type '{req.cooling_type}'.")

    usd = CurrencyCode("USD")
    converted_electricity = service.convert_currency(
        MonetaryAmount(req.electricity_kwh_rate, usd), curr
    )
    converted_colocation = service.convert_currency(
        MonetaryAmount(req.colocation_rack_fee, usd), curr
    )

    facility = DatacenterFacilitySpec(
        facility_id="CLIENT_DATACENTER",
        pue_rating=req.pue_rating,
        max_rack_power_density_kw=req.max_rack_power_density_kw,
        electricity_rate_per_kwh=converted_electricity,
        colocation_rack_monthly_fee=converted_colocation,
        cooling_topology=CoolingTopology[req.cooling_type],
        max_rack_units_u=req.max_rack_units_u,
    )

    workload = service.get_model_profile(
        model_id=req.model_id,
        peak_concurrent_users=req.concurrent_users,
        max_context_length=req.max_context_length,
        avg_prompt_tokens=req.prompt_tokens,
        avg_generated_tokens=req.output_tokens,
        baseline_rps=req.baseline_rps,
        peak_burst_rps=req.peak_burst_rps,
    )

    return service.run_full_advisory_simulation(
        vertical_id=req.vertical_id,
        client_responses=req.client_responses,
        workload=workload,
        on_prem_chassis_id=req.on_prem_chassis_id,
        cloud_instance_id=req.cloud_instance_id,
        datacenter_facility=facility,
        amortization_months=req.amortization_months,
        target_currency=curr,
        chassis_per_rack=req.chassis_per_rack,
    )


@app.get("/api/ledger/verify")
def verify_ledger() -> dict[str, Any]:
    """Cryptographically verifies audit ledger integrity."""
    is_valid = service.verify_ledger()
    return {"is_valid": is_valid, "status": "VERIFIED_TAMPER_EVIDENT" if is_valid else "TAMPERING_DETECTED"}


@app.get("/", response_class=HTMLResponse)
def serve_index() -> str:
    """Serves the reactive Single Page Application with Guided Assessment and Side-by-Side FinOps."""
    html_path = REPO_ROOT / "scripts" / "web_calculator.html"
    if html_path.is_file():
        return html_path.read_text(encoding="utf-8")
    return "<h1>Universal Hybrid FinOps Advisor Platform Active</h1>"


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
