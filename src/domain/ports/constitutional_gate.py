"""Domain Port for Physical, Silicon, and Financial Constitutional Invariant Gates."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType
from typing import Mapping

from src.domain.models.financial import ComputedTcoBreakdown
from src.domain.models.hardware import CoolingTopology, DatacenterFacilitySpec, ServerChassisSpec
from src.domain.models.validation import assert_strict_decimal
from src.domain.models.workload import RooflineSimulationResult


@dataclass(frozen=True)
class ConstitutionalGatePolicy:
    """Configurable constitutional gate limit thresholds loaded strictly from declarative policy."""

    max_rack_power_kw: Decimal
    max_power_kw_by_cooling_topology: Mapping[CoolingTopology, Decimal]
    min_carnot_pue: Decimal
    max_vram_utilization_ratio: Decimal
    max_memory_bus_utilization_ratio: Decimal
    min_amortization_months: int
    max_amortization_months: int
    max_salvage_value_ratio: Decimal
    max_rack_units_u: int = 42

    def __post_init__(self) -> None:
        assert_strict_decimal(self.max_rack_power_kw, "max_rack_power_kw")
        assert_strict_decimal(self.min_carnot_pue, "min_carnot_pue")
        assert_strict_decimal(self.max_vram_utilization_ratio, "max_vram_utilization_ratio")
        assert_strict_decimal(self.max_memory_bus_utilization_ratio, "max_memory_bus_utilization_ratio")
        assert_strict_decimal(self.max_salvage_value_ratio, "max_salvage_value_ratio")

        if isinstance(self.max_rack_units_u, bool) or not isinstance(self.max_rack_units_u, int) or self.max_rack_units_u <= 0:
            raise ValueError(f"max_rack_units_u must be positive integer, got {self.max_rack_units_u}.")

        if isinstance(self.min_amortization_months, bool) or not isinstance(self.min_amortization_months, int) or self.min_amortization_months <= 0:
            raise ValueError(f"min_amortization_months must be positive integer, got {self.min_amortization_months}.")
        if isinstance(self.max_amortization_months, bool) or not isinstance(self.max_amortization_months, int) or self.max_amortization_months <= self.min_amortization_months:
            raise ValueError(
                f"max_amortization_months ({self.max_amortization_months}) must be > min_amortization_months ({self.min_amortization_months})."
            )

        if self.min_carnot_pue < Decimal("1.0000"):
            raise ValueError(f"min_carnot_pue cannot violate thermodynamic floor (>= 1.0), got {self.min_carnot_pue}.")

        if not (Decimal("0") < self.max_vram_utilization_ratio <= Decimal("1.0")):
            raise ValueError(f"max_vram_utilization_ratio must be in (0, 1], got {self.max_vram_utilization_ratio}.")

        if not self.max_power_kw_by_cooling_topology:
            raise ValueError("ConstitutionalGatePolicy must define thermal limits per CoolingTopology.")

        for topology, limit_kw in self.max_power_kw_by_cooling_topology.items():
            assert_strict_decimal(limit_kw, f"cooling_limit_{topology.name}")
            if limit_kw <= Decimal("0"):
                raise ValueError(f"Cooling limit for {topology.name} must be positive, got {limit_kw}.")

        object.__setattr__(
            self,
            "max_power_kw_by_cooling_topology",
            MappingProxyType(dict(self.max_power_kw_by_cooling_topology)),
        )


class ConstitutionalGatePort(ABC):
    """Domain Port enforcing inviolable physical, thermodynamic, and financial invariants."""

    @abstractmethod
    def validate_physical_invariants(
        self,
        chassis: ServerChassisSpec,
        facility: DatacenterFacilitySpec,
        chassis_count_per_rack: int,
        policy: ConstitutionalGatePolicy,
    ) -> None:
        """Validates rack power density and cooling topology limits.
        Raises ConstitutionalGateViolationError if any invariant is breached.
        """
        raise NotImplementedError

    @abstractmethod
    def validate_silicon_invariants(
        self,
        roofline: RooflineSimulationResult,
        policy: ConstitutionalGatePolicy,
    ) -> None:
        """Validates 10% VRAM safety headroom and HBM memory bus saturation ceilings.
        Raises ConstitutionalGateViolationError if any invariant is breached.
        """
        raise NotImplementedError

    @abstractmethod
    def validate_financial_invariants(
        self,
        tco: ComputedTcoBreakdown,
        salvage_value_pct: Decimal,
        policy: ConstitutionalGatePolicy,
    ) -> None:
        """Validates positive TCO floor, amortization bounds, and salvage value limits.
        Raises ConstitutionalGateViolationError if any invariant is breached.
        """
        raise NotImplementedError
