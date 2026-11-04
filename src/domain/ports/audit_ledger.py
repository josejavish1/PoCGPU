"""Domain Port for Immutable Transactional Audit and Provenance Recording."""

from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Mapping, Union

from src.domain.models.assessment import ArchetypeRecommendationResult
from src.domain.models.financial import ActuarialRiskMetrics, ComputedTcoBreakdown
from src.domain.models.workload import RooflineSimulationResult

AuditMetadataPrimitive = Union[str, int, Decimal, bool]


class AuditLedgerPort(ABC):
    """Driven Port for recording cryptographic, tamper-evident FinOps audit records."""

    @abstractmethod
    def append_audit_entry(
        self,
        recommendation: ArchetypeRecommendationResult,
        roofline: RooflineSimulationResult,
        tco_breakdown: ComputedTcoBreakdown,
        actuarial_metrics: ActuarialRiskMetrics,
        provenance_metadata: Mapping[str, AuditMetadataPrimitive],
    ) -> str:
        """Appends a new immutable ledger record. Returns the generated SHA-256 integrity seal."""
        raise NotImplementedError

    @abstractmethod
    def verify_ledger_chain_integrity(self) -> bool:
        """Cryptographically verifies the entire hash chain of historical audit records."""
        raise NotImplementedError
