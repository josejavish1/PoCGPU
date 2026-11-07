from dataclasses import dataclass, field, replace
from enum import Enum, auto
from math import ceil, floor
from typing import Dict, List, Optional, Self


class PackingResultStatus(Enum):
    SUCCESS = auto()
    REJECTED = auto()
    POLICY_REQUIRED = auto()


class FailureDomain(Enum):
    SERVER = auto()
    RACK = auto()
    ZONE = auto()
    SITE = auto()


class MultiSitePolicy(Enum):
    ACTIVE_ACTIVE = auto()
    ACTIVE_PASSIVE = auto()


@dataclass(frozen=True)
class ServingUnit:
    accelerators_per_serving_unit: int

    def __post_init__(self) -> None:
        if self.accelerators_per_serving_unit <= 0:
            raise ValueError("Accelerators per serving unit must be positive.")


@dataclass(frozen=True)
class SizingBreakdown:
    productive_units: int
    headroom_units: int
    growth_units: int
    reserved_units: int

    def __init__(
        self,
        productive_units: int = 0,
        headroom_units: int = 0,
        growth_units: int = 0,
        reserved_units: int = 0,
    ) -> None:
        object.__setattr__(self, "productive_units", productive_units)
        object.__setattr__(self, "headroom_units", headroom_units)
        object.__setattr__(self, "growth_units", growth_units)
        object.__setattr__(self, "reserved_units", reserved_units)
        if any(u < 0 for u in [productive_units, headroom_units, growth_units, reserved_units]):
            raise ValueError("Sizing breakdown units cannot be negative.")


@dataclass(frozen=True)
class AntiAffinityRule:
    failure_domain: FailureDomain
    min_separation_units: int

    def __post_init__(self) -> None:
        if self.min_separation_units <= 0:
            raise ValueError("Minimum separation units must be positive.")


@dataclass(frozen=True)
class ResiliencePolicy:
    n_plus_k: Dict[FailureDomain, int]
    failure_domains: List[FailureDomain]
    multi_site_policy: MultiSitePolicy
    anti_affinity_rules: List[AntiAffinityRule]

    def __init__(
        self,
        n_plus_k: Optional[Dict[FailureDomain, int]] = None,
        failure_domains: Optional[List[FailureDomain]] = None,
        multi_site_policy: MultiSitePolicy = MultiSitePolicy.ACTIVE_ACTIVE,
        anti_affinity_rules: Optional[List[AntiAffinityRule]] = None,
    ) -> None:
        n_plus_k_val = dict(n_plus_k) if n_plus_k is not None else {}
        failure_domains_val = list(failure_domains) if failure_domains is not None else []
        anti_affinity_val = list(anti_affinity_rules) if anti_affinity_rules is not None else []
        object.__setattr__(self, "n_plus_k", n_plus_k_val)
        object.__setattr__(self, "failure_domains", failure_domains_val)
        object.__setattr__(self, "multi_site_policy", multi_site_policy)
        object.__setattr__(self, "anti_affinity_rules", anti_affinity_val)
        if not all(k >= 0 for k in n_plus_k_val.values()):
            raise ValueError("N+k values must be non-negative.")


@dataclass(frozen=True)
class PackingPolicy:
    accelerators_per_server: int
    servers_per_rack: int
    racks_per_zone: int
    zones_per_site: int

    def __init__(
        self,
        accelerators_per_server: int = 8,
        servers_per_rack: int = 1,
        racks_per_zone: int = 1,
        zones_per_site: int = 1,
    ) -> None:
        object.__setattr__(self, "accelerators_per_server", accelerators_per_server)
        object.__setattr__(self, "servers_per_rack", servers_per_rack)
        object.__setattr__(self, "racks_per_zone", racks_per_zone)
        object.__setattr__(self, "zones_per_site", zones_per_site)
        if any(val <= 0 for val in [accelerators_per_server, servers_per_rack, racks_per_zone, zones_per_site]):
            raise ValueError("Packing policy values must be positive.")


@dataclass(frozen=True)
class CapacityClassification:
    productive: int
    headroom: int
    growth: int
    reserved: int
    resilience: int
    stranded: int
    idle: int

    def __post_init__(self) -> None:
        if any(u < 0 for u in [self.productive, self.headroom, self.growth, self.reserved, self.resilience, self.stranded, self.idle]):
            raise ValueError("Capacity classification units cannot be negative.")


@dataclass(frozen=True)
class PackingResult:
    status: PackingResultStatus
    message: str
    installed_accelerators: int
    installed_servers: int
    installed_racks: int
    installed_zones: int
    installed_sites: int
    installed_serving_unit_equivalents: int
    stranded_accelerators: int
    capacity_classification: CapacityClassification
    sellable_units: int

    def __init__(
        self,
        status: PackingResultStatus,
        message: str,
        installed_accelerators: int = 0,
        installed_servers: int = 0,
        installed_racks: int = 0,
        installed_zones: int = 0,
        installed_sites: int = 0,
        installed_serving_unit_equivalents: int = 0,
        stranded_accelerators: int = 0,
        capacity_classification: Optional[CapacityClassification] = None,
        sellable_units: int = 0,
    ) -> None:
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "message", message)
        object.__setattr__(self, "installed_accelerators", installed_accelerators)
        object.__setattr__(self, "installed_servers", installed_servers)
        object.__setattr__(self, "installed_racks", installed_racks)
        object.__setattr__(self, "installed_zones", installed_zones)
        object.__setattr__(self, "installed_sites", installed_sites)
        object.__setattr__(self, "installed_serving_unit_equivalents", installed_serving_unit_equivalents)
        object.__setattr__(self, "stranded_accelerators", stranded_accelerators)
        classification = capacity_classification or CapacityClassification(0, 0, 0, 0, 0, 0, 0)
        object.__setattr__(self, "capacity_classification", classification)
        object.__setattr__(self, "sellable_units", sellable_units)


def default_packing_policy() -> PackingPolicy:
    """Returns a default packing policy."""
    return PackingPolicy()


def calculate_resilience_accelerators(
    serving_unit: ServingUnit,
    sizing_breakdown: SizingBreakdown,
    resilience_policy: ResiliencePolicy,
    packing_policy: PackingPolicy,
) -> int:
    """Calculates the total accelerators required for resilience."""
    productive_accelerators = sizing_breakdown.productive_units * serving_unit.accelerators_per_serving_unit
    max_resilience_accelerators = productive_accelerators  # Start with base demand

    # N+k resilience
    for domain, k_value in resilience_policy.n_plus_k.items():
        if k_value < 0:
            return -1 # Should be caught by validation

        loss_accelerators = 0
        if domain == FailureDomain.SERVER:
            loss_accelerators = k_value * packing_policy.accelerators_per_server
        elif domain == FailureDomain.RACK:
            loss_accelerators = k_value * packing_policy.servers_per_rack * packing_policy.accelerators_per_server
        elif domain == FailureDomain.ZONE:
            loss_accelerators = k_value * packing_policy.racks_per_zone * packing_policy.servers_per_rack * packing_policy.accelerators_per_server
        elif domain == FailureDomain.SITE:
            loss_accelerators = k_value * packing_policy.zones_per_site * packing_policy.racks_per_zone * packing_policy.servers_per_rack * packing_policy.accelerators_per_server
        
        # To survive loss_accelerators while maintaining productive_accelerators
        required_after_loss = productive_accelerators
        total_needed_for_n_plus_k = required_after_loss + loss_accelerators
        max_resilience_accelerators = max(max_resilience_accelerators, total_needed_for_n_plus_k)

    # Failure domain (zone/site outage) resilience
    for domain in resilience_policy.failure_domains:
        if domain == FailureDomain.SITE:
            if resilience_policy.multi_site_policy == MultiSitePolicy.ACTIVE_PASSIVE:
                # Need productive capacity * number of sites to ensure one site can take over
                total_needed_for_site_outage = productive_accelerators * packing_policy.zones_per_site # zones_per_site implies number of sites if each zone is a site
                max_resilience_accelerators = max(max_resilience_accelerators, total_needed_for_site_outage)
            elif resilience_policy.multi_site_policy == MultiSitePolicy.ACTIVE_ACTIVE:
                # Active-active typically means capacity is distributed, and loss of one site means reduced capacity.
                # If we need to maintain full productive_accelerators, we need to ensure enough capacity remains.
                # This implies (productive_accelerators / (num_sites - 1)) * num_sites if one site fails.
                # For simplicity, assume if one site fails, the remaining sites must cover productive_accelerators.
                # If productive_accelerators is distributed across N sites, and 1 site fails, we need N/(N-1) * productive_accelerators total.
                # For now, let's assume active-active means productive_accelerators is the target, and resilience is handled by N+k or other means.
                # If a site outage means losing a fraction of capacity, and we need to maintain productive_accelerators, then we need more.
                # For now, let's interpret it as: if one site fails, the remaining sites must collectively provide productive_accelerators.
                # This means total capacity must be productive_accelerators * (num_sites / (num_sites - 1)) if num_sites > 1.
                # If num_sites = 1, then site outage is not possible.
                num_sites = packing_policy.zones_per_site # Assuming zones_per_site represents distinct sites for this policy
                if num_sites > 1:
                    total_needed_for_site_outage = ceil(productive_accelerators * (num_sites / (num_sites - 1)))
                    max_resilience_accelerators = max(max_resilience_accelerators, total_needed_for_site_outage)
                else:
                    # If only one site, site outage is not a resilience factor for multi-site policy
                    pass
        elif domain == FailureDomain.ZONE:
            if resilience_policy.multi_site_policy == MultiSitePolicy.ACTIVE_PASSIVE:
                # Need productive capacity * number of zones to ensure one zone can take over
                total_needed_for_zone_outage = productive_accelerators * packing_policy.racks_per_zone # racks_per_zone implies number of zones
                max_resilience_accelerators = max(max_resilience_accelerators, total_needed_for_zone_outage)
            elif resilience_policy.multi_site_policy == MultiSitePolicy.ACTIVE_ACTIVE:
                num_zones = packing_policy.racks_per_zone # Assuming racks_per_zone represents distinct zones for this policy
                if num_zones > 1:
                    total_needed_for_zone_outage = ceil(productive_accelerators * (num_zones / (num_zones - 1)))
                    max_resilience_accelerators = max(max_resilience_accelerators, total_needed_for_zone_outage)
                else:
                    pass

    # Anti-affinity rules are typically about placement, not total capacity calculation for resilience.
    # They ensure units are spread out, which is implicitly handled by the failure domain calculations if capacity is provisioned for loss.
    # For this scope, anti-affinity rules do not directly add to the total accelerator count for resilience, but rather influence placement.

    # The resilience accelerators are the additional accelerators beyond the productive ones needed to survive a failure.
    return max_resilience_accelerators


def pack_and_reconcile(
    serving_unit: ServingUnit,
    sizing_breakdown: SizingBreakdown,
    resilience_policy: ResiliencePolicy,
    packing_policy: PackingPolicy,
) -> PackingResult:
    """Maps Serving Units into discrete physical infrastructure and reconciles capacity."""

    # Validate inputs
    if serving_unit.accelerators_per_serving_unit > packing_policy.accelerators_per_server:
        return PackingResult(
            status=PackingResultStatus.REJECTED,
            message="Serving Unit accelerator count exceeds server capacity.",
        )

    # 1. Calculate base demand in accelerators
    productive_accelerators = sizing_breakdown.productive_units * serving_unit.accelerators_per_serving_unit
    headroom_accelerators = sizing_breakdown.headroom_units * serving_unit.accelerators_per_serving_unit
    growth_accelerators = sizing_breakdown.growth_units * serving_unit.accelerators_per_serving_unit
    reserved_accelerators = sizing_breakdown.reserved_units * serving_unit.accelerators_per_serving_unit

    base_demand_accelerators = productive_accelerators + headroom_accelerators + growth_accelerators + reserved_accelerators

    # 2. Calculate resilience accelerators
    resilience_accelerators_needed = calculate_resilience_accelerators(
        serving_unit, sizing_breakdown, resilience_policy, packing_policy
    )

    # The total accelerators to provision must be at least the base demand and also satisfy resilience.
    # resilience_accelerators_needed already includes productive_accelerators as a baseline.
    total_accelerators_to_provision = max(base_demand_accelerators, resilience_accelerators_needed)

    # 3. Compute discrete installed counts by rounding up to whole physical containers
    installed_servers = ceil(total_accelerators_to_provision / packing_policy.accelerators_per_server)
    installed_accelerators = installed_servers * packing_policy.accelerators_per_server

    installed_racks = ceil(installed_servers / packing_policy.servers_per_rack)
    installed_zones = ceil(installed_racks / packing_policy.racks_per_zone)
    installed_sites = ceil(installed_zones / packing_policy.zones_per_site)

    # 4. Derive installed serving unit equivalents and stranded accelerators
    installed_serving_unit_equivalents = floor(installed_accelerators / serving_unit.accelerators_per_serving_unit)
    
    # Stranded accelerators from total installed capacity not forming a full serving unit
    stranded_accelerators_from_total = installed_accelerators - (installed_serving_unit_equivalents * serving_unit.accelerators_per_serving_unit)
    
    # Additional slot fragmentation (e.g., a server has 7 acc, SU needs 4, 3 are stranded even if 1 SU fits)
    # For simplicity, if accelerators_per_server is a multiple of accelerators_per_serving_unit, this is 0.
    # If not, it's more complex. For now, assume no fragmentation within a server if a SU fits.
    # The current stranded_accelerators_from_total covers the overall fragmentation.
    stranded_accelerators = stranded_accelerators_from_total

    # 5. Classify all installed capacity
    productive_classified = sizing_breakdown.productive_units
    headroom_classified = sizing_breakdown.headroom_units
    growth_classified = sizing_breakdown.growth_units
    reserved_classified = sizing_breakdown.reserved_units

    # Calculate resilience units based on the difference between total needed and base demand
    # The resilience_accelerators_needed already includes productive_accelerators as a baseline.
    # So, the actual 'additional' resilience accelerators are resilience_accelerators_needed - productive_accelerators.
    # However, the spec says 'resilience' is physical HA/failure-domain survival reserve.
    # It's the capacity *beyond* productive, headroom, growth, reserved that is specifically for resilience.
    # Let's re-evaluate: total_accelerators_to_provision is the absolute minimum required.
    # The difference between total_accelerators_to_provision and base_demand_accelerators (excluding reserved) is for resilience.
    
    # Total accelerators needed for productive, headroom, growth, reserved, and resilience
    # The resilience_accelerators_needed is the total accelerators required to survive failures, including productive.
    # So, the resilience component is total_accelerators_to_provision - (productive_accelerators + headroom_accelerators + growth_accelerators + reserved_accelerators)
    
    # Calculate resilience units based on the difference between total provisioned and base demand (excluding reserved for now, as reserved is a separate bucket)
    # The resilience_accelerators_needed is the total accelerators required to meet resilience, including productive.
    # So, the actual resilience capacity is the difference between the total provisioned for resilience and the base demand (productive, headroom, growth).
    
    # Let's calculate the resilience accelerators that are *not* productive, headroom, growth, or reserved.
    # Total accelerators needed for productive, headroom, growth, and resilience (excluding reserved for this calculation)
    total_phg_resilience_accelerators = max(productive_accelerators + headroom_accelerators + growth_accelerators, resilience_accelerators_needed)
    
    # The resilience accelerators are the difference between this total and the productive+headroom+growth
    resilience_accelerators = total_phg_resilience_accelerators - (productive_accelerators + headroom_accelerators + growth_accelerators)
    resilience_classified = ceil(resilience_accelerators / serving_unit.accelerators_per_serving_unit) if resilience_accelerators > 0 else 0

    # Total units already classified (productive, headroom, growth, reserved, resilience, stranded)
    total_classified_units_so_far = productive_classified + headroom_classified + growth_classified + reserved_classified + resilience_classified + floor(stranded_accelerators / serving_unit.accelerators_per_serving_unit)

    idle_classified = max(0, installed_serving_unit_equivalents - total_classified_units_so_far)

    capacity_classification = CapacityClassification(
        productive=productive_classified,
        headroom=headroom_classified,
        growth=growth_classified,
        reserved=reserved_classified,
        resilience=resilience_classified,
        stranded=floor(stranded_accelerators / serving_unit.accelerators_per_serving_unit),
        idle=idle_classified,
    )

    # 6. Define sellable units
    sellable_units = capacity_classification.productive + capacity_classification.headroom + capacity_classification.growth + capacity_classification.idle

    # 7. Verify strict reconciliation invariant
    total_classified_sum = (
        capacity_classification.productive
        + capacity_classification.headroom
        + capacity_classification.growth
        + capacity_classification.reserved
        + capacity_classification.resilience
        + capacity_classification.stranded
        + capacity_classification.idle
    )

    if total_classified_sum != installed_serving_unit_equivalents:
        return PackingResult(
            status=PackingResultStatus.REJECTED,
            message=f"Reconciliation invariant failed: {total_classified_sum} != {installed_serving_unit_equivalents}",
        )

    if sellable_units != (capacity_classification.productive + capacity_classification.headroom + capacity_classification.growth + capacity_classification.idle):
        return PackingResult(
            status=PackingResultStatus.REJECTED,
            message="Sellable units invariant failed.",
        )

    return PackingResult(
        status=PackingResultStatus.SUCCESS,
        message="Packing successful.",
        installed_accelerators=installed_accelerators,
        installed_servers=installed_servers,
        installed_racks=installed_racks,
        installed_zones=installed_zones,
        installed_sites=installed_sites,
        installed_serving_unit_equivalents=installed_serving_unit_equivalents,
        stranded_accelerators=stranded_accelerators,
        capacity_classification=capacity_classification,
        sellable_units=sellable_units,
    )
