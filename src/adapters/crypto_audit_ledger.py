"""Cryptographic Tamper-Evident Hash-Chained Audit Ledger Adapter."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

from src.domain.models.assessment import ArchetypeRecommendationResult
from src.domain.models.financial import ActuarialRiskMetrics, ComputedTcoBreakdown
from src.domain.models.workload import RooflineSimulationResult
from src.domain.ports.audit_ledger import AuditLedgerPort, AuditMetadataPrimitive

GENESIS_PREVIOUS_HASH = "0" * 64


class CryptographicAuditLedgerAdapter(AuditLedgerPort):
    """Appends tamper-evident, SHA-256 hash-chained JSONL audit records for executive FinOps compliance."""

    def __init__(self, ledger_file_path: Path) -> None:
        self._ledger_path = ledger_file_path
        self._ledger_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._ledger_path.exists():
            self._ledger_path.touch()

    def _get_last_entry_hash(self) -> str:
        if not self._ledger_path.is_file() or self._ledger_path.stat().st_size == 0:
            return GENESIS_PREVIOUS_HASH

        lines = self._ledger_path.read_text(encoding="utf-8").strip().splitlines()
        if not lines:
            return GENESIS_PREVIOUS_HASH

        last_line = lines[-1].strip()
        if not last_line:
            return GENESIS_PREVIOUS_HASH

        try:
            last_entry = json.loads(last_line)
            return last_entry.get("entry_hash", GENESIS_PREVIOUS_HASH)
        except json.JSONDecodeError:
            return GENESIS_PREVIOUS_HASH

    def append_audit_entry(
        self,
        recommendation: ArchetypeRecommendationResult,
        roofline: RooflineSimulationResult,
        tco_breakdown: ComputedTcoBreakdown,
        actuarial_metrics: ActuarialRiskMetrics,
        provenance_metadata: Mapping[str, AuditMetadataPrimitive],
    ) -> str:
        """Appends a new immutable ledger record. Returns the generated SHA-256 integrity seal."""
        record_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        previous_hash = self._get_last_entry_hash()

        payload = {
            "record_id": record_id,
            "timestamp": timestamp,
            "previous_hash": previous_hash,
            "recommendation": {
                "archetype": recommendation.recommended_archetype.value,
                "on_prem_score": str(recommendation.on_prem_composite_score),
                "cloud_score": str(recommendation.cloud_composite_score),
                "divergence_delta": str(recommendation.divergence_delta),
                "base_split_pct": str(recommendation.recommended_base_load_split_pct),
                "burst_split_pct": str(recommendation.recommended_burst_load_split_pct),
                "is_veto_enforced": recommendation.is_veto_enforced,
            },
            "roofline": {
                "candidate_id": roofline.chassis_or_instance_id,
                "required_nodes": roofline.required_cluster_nodes_baseline,
                "tp_degree": roofline.tensor_parallel_degree,
                "pp_degree": roofline.pipeline_parallel_degree,
                "vram_utilization_ratio": str(roofline.vram_utilization_ratio),
                "memory_bus_utilization_ratio": str(roofline.memory_bus_utilization_ratio),
                "tpot_ms": str(roofline.tpot_ms_per_token),
                "ttft_seconds": str(roofline.ttft_seconds),
            },
            "tco": {
                "monthly_nominal": str(tco_breakdown.total_monthly_nominal_tco.amount),
                "currency": str(tco_breakdown.total_monthly_nominal_tco.currency),
                "amortization_months": tco_breakdown.amortization_period_months,
                "is_on_premise": tco_breakdown.is_on_premise,
            },
            "actuarial": {
                "annual_lef": str(actuarial_metrics.loss_event_frequency_annual),
                "sle_amount": str(actuarial_metrics.single_loss_expectancy.amount),
                "ale_amount": str(actuarial_metrics.annualized_loss_expectancy.amount),
                "monthly_reserve": str(actuarial_metrics.monthly_risk_adjusted_reserve.amount),
            },
            "provenance": {k: str(v) for k, v in provenance_metadata.items()},
        }

        canonical_serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        entry_hash = hashlib.sha256(canonical_serialized.encode("utf-8")).hexdigest()
        payload["entry_hash"] = entry_hash

        with self._ledger_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, sort_keys=True) + "\n")

        return entry_hash

    def verify_ledger_chain_integrity(self) -> bool:
        """Cryptographically verifies the entire hash chain of historical audit records."""
        if not self._ledger_path.is_file() or self._ledger_path.stat().st_size == 0:
            return True

        lines = self._ledger_path.read_text(encoding="utf-8").strip().splitlines()
        expected_prev_hash = GENESIS_PREVIOUS_HASH

        for idx, line in enumerate(lines):
            line_str = line.strip()
            if not line_str:
                continue
            try:
                record = json.loads(line_str)
            except json.JSONDecodeError:
                return False

            if record.get("previous_hash") != expected_prev_hash:
                return False

            stored_hash = record.get("entry_hash")
            payload_copy = dict(record)
            payload_copy.pop("entry_hash", None)

            canonical_serialized = json.dumps(payload_copy, sort_keys=True, separators=(",", ":"))
            computed_hash = hashlib.sha256(canonical_serialized.encode("utf-8")).hexdigest()

            if stored_hash != computed_hash:
                return False

            expected_prev_hash = stored_hash

        return True
