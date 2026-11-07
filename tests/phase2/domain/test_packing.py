import pytest
from dataclasses import replace
from src.pocgpu.domain.capacity.packing import (
    ServingUnit,
    SizingBreakdown,
    ResiliencePolicy,
    PackingPolicy,
    PackingResultStatus,
    CapacityClassification,
    FailureDomain,
    MultiSitePolicy,
    AntiAffinityRule,
    pack_and_reconcile,
    default_packing_policy,
)


def test_serving_unit_validation():
    """Tests ServingUnit validation."""
    with pytest.raises(ValueError, match="Accelerators per serving unit must be positive."):
        ServingUnit(accelerators_per_serving_unit=0)
    with pytest.raises(ValueError, match="Accelerators per serving unit must be positive."):
        ServingUnit(accelerators_per_serving_unit=-1)
    assert ServingUnit(accelerators_per_serving_unit=10)


def test_sizing_breakdown_validation():
    """Tests SizingBreakdown validation."""
    with pytest.raises(ValueError, match="Sizing breakdown units cannot be negative."):
        SizingBreakdown(productive_units=-1)
    with pytest.raises(ValueError, match="Sizing breakdown units cannot be negative."):
        SizingBreakdown(headroom_units=-1)
    with pytest.raises(ValueError, match="Sizing breakdown units cannot be negative."):
        SizingBreakdown(growth_units=-1)
    with pytest.raises(ValueError, match="Sizing breakdown units cannot be negative."):
        SizingBreakdown(reserved_units=-1)
    assert SizingBreakdown(productive_units=1, headroom_units=1, growth_units=1, reserved_units=1)


def test_anti_affinity_rule_validation():
    """Tests AntiAffinityRule validation."""
    with pytest.raises(ValueError, match="Minimum separation units must be positive."):
        AntiAffinityRule(failure_domain=FailureDomain.SERVER, min_separation_units=0)
    with pytest.raises(ValueError, match="Minimum separation units must be positive."):
        AntiAffinityRule(failure_domain=FailureDomain.SERVER, min_separation_units=-1)
    assert AntiAffinityRule(failure_domain=FailureDomain.SERVER, min_separation_units=1)


def test_resilience_policy_validation():
    """Tests ResiliencePolicy validation."""
    with pytest.raises(ValueError, match=r"N\+k values must be non-negative\."):
        ResiliencePolicy(n_plus_k={FailureDomain.SERVER: -1})
    assert ResiliencePolicy(n_plus_k={FailureDomain.SERVER: 0})
    assert ResiliencePolicy(n_plus_k={FailureDomain.SERVER: 1})


def test_packing_policy_validation():
    """Tests PackingPolicy validation."""
    with pytest.raises(ValueError, match="Packing policy values must be positive."):
        PackingPolicy(accelerators_per_server=0)
    with pytest.raises(ValueError, match="Packing policy values must be positive."):
        PackingPolicy(servers_per_rack=0)
    with pytest.raises(ValueError, match="Packing policy values must be positive."):
        PackingPolicy(racks_per_zone=0)
    with pytest.raises(ValueError, match="Packing policy values must be positive."):
        PackingPolicy(zones_per_site=0)
    assert PackingPolicy(accelerators_per_server=1, servers_per_rack=1, racks_per_zone=1, zones_per_site=1)


def test_capacity_classification_validation():
    """Tests CapacityClassification validation."""
    with pytest.raises(ValueError, match="Capacity classification units cannot be negative."):
        CapacityClassification(productive=-1, headroom=0, growth=0, reserved=0, resilience=0, stranded=0, idle=0)
    with pytest.raises(ValueError, match="Capacity classification units cannot be negative."):
        CapacityClassification(productive=0, headroom=-1, growth=0, reserved=0, resilience=0, stranded=0, idle=0)
    # ... and so on for all fields
    assert CapacityClassification(productive=1, headroom=1, growth=1, reserved=1, resilience=1, stranded=1, idle=1)


def test_pack_and_reconcile_basic_productive():
    """Tests basic packing for productive units only."""
    serving_unit = ServingUnit(accelerators_per_serving_unit=4)
    sizing_breakdown = SizingBreakdown(productive_units=1)
    resilience_policy = ResiliencePolicy()
    packing_policy = default_packing_policy()

    result = pack_and_reconcile(serving_unit, sizing_breakdown, resilience_policy, packing_policy)

    assert result.status == PackingResultStatus.SUCCESS
    assert result.installed_accelerators == 8  # 1 SU (4 acc) needs 1 server (8 acc)
    assert result.installed_servers == 1
    assert result.installed_racks == 1
    assert result.installed_zones == 1
    assert result.installed_sites == 1
    assert result.installed_serving_unit_equivalents == 2  # floor(8/4) = 2
    assert result.stranded_accelerators == 0
    assert result.capacity_classification == CapacityClassification(productive=1, headroom=0, growth=0, reserved=0, resilience=0, stranded=0, idle=1)
    assert result.sellable_units == 2


def test_pack_and_reconcile_multiple_productive_units():
    """Tests packing for multiple productive units."""
    serving_unit = ServingUnit(accelerators_per_serving_unit=4)
    sizing_breakdown = SizingBreakdown(productive_units=3)
    resilience_policy = ResiliencePolicy()
    packing_policy = default_packing_policy()

    result = pack_and_reconcile(serving_unit, sizing_breakdown, resilience_policy, packing_policy)

    assert result.status == PackingResultStatus.SUCCESS
    # 3 SU * 4 acc/SU = 12 acc needed. 1 server = 8 acc. ceil(12/8) = 2 servers.
    # 2 servers * 8 acc/server = 16 acc installed.
    assert result.installed_accelerators == 16
    assert result.installed_servers == 2
    assert result.installed_racks == 2 # 2 servers, 1 server/rack
    assert result.installed_zones == 2 # 2 racks, 1 rack/zone
    assert result.installed_sites == 2 # 2 zones, 1 zone/site
    assert result.installed_serving_unit_equivalents == 4 # floor(16/4) = 4
    assert result.stranded_accelerators == 0
    assert result.capacity_classification == CapacityClassification(productive=3, headroom=0, growth=0, reserved=0, resilience=0, stranded=0, idle=1)
    assert result.sellable_units == 4


def test_pack_and_reconcile_with_headroom_and_growth():
    """Tests packing with headroom and growth units."""
    serving_unit = ServingUnit(accelerators_per_serving_unit=4)
    sizing_breakdown = SizingBreakdown(productive_units=1, headroom_units=1, growth_units=1)
    resilience_policy = ResiliencePolicy()
    packing_policy = default_packing_policy()

    result = pack_and_reconcile(serving_unit, sizing_breakdown, resilience_policy, packing_policy)

    assert result.status == PackingResultStatus.SUCCESS
    # 3 units * 4 acc/unit = 12 acc needed. 2 servers * 8 acc/server = 16 acc installed.
    assert result.installed_accelerators == 16
    assert result.installed_servers == 2
    assert result.installed_racks == 2
    assert result.installed_zones == 2
    assert result.installed_sites == 2
    assert result.installed_serving_unit_equivalents == 4
    assert result.stranded_accelerators == 0
    assert result.capacity_classification == CapacityClassification(productive=1, headroom=1, growth=1, reserved=0, resilience=0, stranded=0, idle=1)
    assert result.sellable_units == 4


def test_pack_and_reconcile_n_plus_k_server_resilience():
    """Tests N+k server resilience."""
    serving_unit = ServingUnit(accelerators_per_serving_unit=4)
    sizing_breakdown = SizingBreakdown(productive_units=1)
    resilience_policy = ResiliencePolicy(n_plus_k={FailureDomain.SERVER: 1})
    packing_policy = default_packing_policy()

    result = pack_and_reconcile(serving_unit, sizing_breakdown, resilience_policy, packing_policy)

    assert result.status == PackingResultStatus.SUCCESS
    # Base demand: 1 unit = 4 acc.
    # N+1 server: 4 acc (base) + 8 acc (loss of 1 server) = 12 acc needed.
    # Total units to provision: ceil(12/4) = 3 units.
    # Total accelerators to pack: 3 units * 4 acc/unit = 12 acc.
    # Servers: ceil(12/8) = 2 servers.
    # Installed accelerators: 2 servers * 8 acc/server = 16 acc.
    assert result.installed_accelerators == 16
    assert result.installed_servers == 2
    assert result.installed_racks == 2
    assert result.installed_zones == 2
    assert result.installed_sites == 2
    assert result.installed_serving_unit_equivalents == 4
    assert result.stranded_accelerators == 0
    assert result.capacity_classification == CapacityClassification(productive=1, headroom=0, growth=0, reserved=0, resilience=2, stranded=0, idle=1)
    assert result.sellable_units == 2


def test_pack_and_reconcile_n_plus_k_rack_resilience():
    """Tests N+k rack resilience."""
    serving_unit = ServingUnit(accelerators_per_serving_unit=4)
    sizing_breakdown = SizingBreakdown(productive_units=1)
    resilience_policy = ResiliencePolicy(n_plus_k={FailureDomain.RACK: 1})
    packing_policy = replace(default_packing_policy(), servers_per_rack=2) # 2 servers/rack = 16 acc/rack

    result = pack_and_reconcile(serving_unit, sizing_breakdown, resilience_policy, packing_policy)

    assert result.status == PackingResultStatus.SUCCESS
    # Base demand: 1 unit = 4 acc.
    # N+1 rack: 4 acc (base) + 16 acc (loss of 1 rack) = 20 acc needed.
    # Total units to provision: ceil(20/4) = 5 units.
    # Total accelerators to pack: 5 units * 4 acc/unit = 20 acc.
    # Servers: ceil(20/8) = 3 servers (24 acc installed).
    assert result.installed_accelerators == 24
    assert result.installed_servers == 3
    assert result.installed_racks == 2 # ceil(3 servers / 2 servers_per_rack) = 2 racks
    assert result.installed_zones == 2 # ceil(2 racks / 1 rack_per_zone) = 2 zones
    assert result.installed_sites == 2 # ceil(2 zones / 1 zone_per_site) = 2 sites
    assert result.installed_serving_unit_equivalents == 6 # floor(24/4) = 6
    assert result.stranded_accelerators == 0
    assert result.capacity_classification == CapacityClassification(productive=1, headroom=0, growth=0, reserved=0, resilience=4, stranded=0, idle=1)
    assert result.sellable_units == 2


def test_pack_and_reconcile_zone_outage_active_passive():
    """Tests active-passive zone outage resilience."""
    serving_unit = ServingUnit(accelerators_per_serving_unit=4)
    sizing_breakdown = SizingBreakdown(productive_units=1)
    resilience_policy = ResiliencePolicy(
        failure_domains=[FailureDomain.ZONE],
        multi_site_policy=MultiSitePolicy.ACTIVE_PASSIVE,
    )
    packing_policy = replace(default_packing_policy(), racks_per_zone=2) # 2 zones available

    result = pack_and_reconcile(serving_unit, sizing_breakdown, resilience_policy, packing_policy)

    assert result.status == PackingResultStatus.SUCCESS
    # Base demand: 1 unit = 4 acc.
    # Active-passive zone (2 zones): 4 acc (base) * 2 zones = 8 acc needed.
    # Total units to provision: ceil(8/4) = 2 units.
    # Total accelerators to pack: 2 units * 4 acc/unit = 8 acc.
    # Servers: ceil(8/8) = 1 server.
    # Installed accelerators: 1 server * 8 acc/server = 8 acc.
    assert result.installed_accelerators == 8
    assert result.installed_servers == 1
    assert result.installed_racks == 1 # ceil(1 server / 1 server_per_rack) = 1 rack
    assert result.installed_zones == 1 # ceil(1 rack / 2 racks_per_zone) = 1 zone
    assert result.installed_sites == 1 # ceil(1 zone / 1 zone_per_site) = 1 site
    assert result.installed_serving_unit_equivalents == 2
    assert result.stranded_accelerators == 0
    assert result.capacity_classification == CapacityClassification(productive=1, headroom=0, growth=0, reserved=0, resilience=1, stranded=0, idle=0)
    assert result.sellable_units == 1


def test_pack_and_reconcile_site_outage_active_passive():
    """Tests active-passive site outage resilience."""
    serving_unit = ServingUnit(accelerators_per_serving_unit=4)
    sizing_breakdown = SizingBreakdown(productive_units=1)
    resilience_policy = ResiliencePolicy(
        failure_domains=[FailureDomain.SITE],
        multi_site_policy=MultiSitePolicy.ACTIVE_PASSIVE,
    )
    packing_policy = replace(default_packing_policy(), zones_per_site=2) # 2 sites available

    result = pack_and_reconcile(serving_unit, sizing_breakdown, resilience_policy, packing_policy)

    assert result.status == PackingResultStatus.SUCCESS
    # Base demand: 1 unit = 4 acc.
    # Active-passive site (2 sites): 4 acc (base) * 2 sites = 8 acc needed.
    # Total units to provision: ceil(8/4) = 2 units.
    # Total accelerators to pack: 2 units * 4 acc/unit = 8 acc.
    # Servers: ceil(8/8) = 1 server.
    # Installed accelerators: 1 server * 8 acc/server = 8 acc.
    assert result.installed_accelerators == 8
    assert result.installed_servers == 1
    assert result.installed_racks == 1
    assert result.installed_zones == 1
    assert result.installed_sites == 1
    assert result.installed_serving_unit_equivalents == 2
    assert result.stranded_accelerators == 0
    assert result.capacity_classification == CapacityClassification(productive=1, headroom=0, growth=0, reserved=0, resilience=1, stranded=0, idle=0)
    assert result.sellable_units == 1


def test_pack_and_reconcile_n_plus_k_and_site_outage_combined():
    """Tests combined N+k and site outage resilience."""
    serving_unit = ServingUnit(accelerators_per_serving_unit=4)
    sizing_breakdown = SizingBreakdown(productive_units=1, headroom_units=0, growth_units=0) # Base 1 unit = 4 acc
    resilience_policy = ResiliencePolicy(
        n_plus_k={FailureDomain.SERVER: 1}, # N+1 server: 4 acc + 8 acc = 12 acc needed
        failure_domains=[FailureDomain.SITE], # Active-passive site: 4 acc * 2 sites = 8 acc needed
        multi_site_policy=MultiSitePolicy.ACTIVE_PASSIVE,
        anti_affinity_rules=[],
    )
    packing_policy = replace(default_packing_policy(), zones_per_site=2) # 8 acc/server

    result = pack_and_reconcile(serving_unit, sizing_breakdown, resilience_policy, packing_policy)

    assert result.status == PackingResultStatus.SUCCESS
    # Base demand: 1 unit * 4 acc/unit = 4 acc.
    # N+1 server: 4 acc (base) + 8 acc (loss) = 12 acc.
    # Active-passive site (2 sites): 4 acc (base) * 2 = 8 acc.
    # Max required accelerators = max(4, 12, 8) = 12 acc.
    # Total units to provision: ceil(12 / 4) = 3 units.
    # Total accelerators to pack: 3 units * 4 acc/unit = 12 acc.
    # Servers: ceil(12 / 8) = 2 servers.
    # Installed accelerators: 2 servers * 8 acc/server = 16 acc.
    assert result.installed_accelerators == 16
    assert result.installed_servers == 2
    assert result.installed_racks == 2 # Corrected from 1
    assert result.installed_zones == 2 # Corrected from 1
    assert result.installed_sites == 1
    assert result.installed_serving_unit_equivalents == 4 # floor(16/4) = 4
    assert result.stranded_accelerators == 0
    assert result.capacity_classification == CapacityClassification(productive=1, headroom=0, growth=0, reserved=0, resilience=2, stranded=0, idle=1)
    assert result.sellable_units == 2 # Corrected from 3


def test_pack_and_reconcile_n_plus_k_and_zone_outage_combined():
    """Tests combined N+k and zone outage resilience."""
    serving_unit = ServingUnit(accelerators_per_serving_unit=4)
    sizing_breakdown = SizingBreakdown(productive_units=1, headroom_units=0, growth_units=0) # Base 1 unit = 4 acc
    resilience_policy = ResiliencePolicy(
        n_plus_k={FailureDomain.SERVER: 1}, # N+1 server: 4 acc + 8 acc = 12 acc needed
        failure_domains=[FailureDomain.ZONE], # Active-passive zone: 4 acc * 2 zones = 8 acc needed
        multi_site_policy=MultiSitePolicy.ACTIVE_PASSIVE,
        anti_affinity_rules=[],
    )
    packing_policy = replace(default_packing_policy(), racks_per_zone=2) # 8 acc/server

    result = pack_and_reconcile(serving_unit, sizing_breakdown, resilience_policy, packing_policy)

    assert result.status == PackingResultStatus.SUCCESS
    # Base demand: 1 unit * 4 acc/unit = 4 acc.
    # N+1 server: 4 acc (base) + 8 acc (loss) = 12 acc.
    # Active-passive zone (2 zones): 4 acc (base) * 2 = 8 acc.
    # Max required accelerators = max(4, 12, 8) = 12 acc.
    # Total units to provision: ceil(12 / 4) = 3 units.
    # Total accelerators to pack: 3 units * 4 acc/unit = 12 acc.
    # Servers: ceil(12 / 8) = 2 servers.
    # Installed accelerators: 2 servers * 8 acc/server = 16 acc.
    assert result.installed_accelerators == 16
    assert result.installed_servers == 2
    assert result.installed_racks == 2 # Corrected from 1
    assert result.installed_zones == 1
    assert result.installed_sites == 1
    assert result.installed_serving_unit_equivalents == 4 # floor(16/4) = 4
    assert result.stranded_accelerators == 0
    assert result.capacity_classification == CapacityClassification(productive=1, headroom=0, growth=0, reserved=0, resilience=2, stranded=0, idle=1)
    assert result.sellable_units == 2 # Corrected from 3


def test_pack_and_reconcile_server_capacity_exceeded():
    """Tests rejection when ServingUnit exceeds server capacity."""
    serving_unit = ServingUnit(accelerators_per_serving_unit=10)
    sizing_breakdown = SizingBreakdown(productive_units=1)
    resilience_policy = ResiliencePolicy()
    packing_policy = default_packing_policy() # 8 acc/server

    result = pack_and_reconcile(serving_unit, sizing_breakdown, resilience_policy, packing_policy)

    assert result.status == PackingResultStatus.REJECTED
    assert result.message == "Serving Unit accelerator count exceeds server capacity."


def test_pack_and_reconcile_zero_demand():
    """Tests packing with zero demand."""
    serving_unit = ServingUnit(accelerators_per_serving_unit=4)
    sizing_breakdown = SizingBreakdown(productive_units=0, headroom_units=0, growth_units=0)
    resilience_policy = ResiliencePolicy()
    packing_policy = default_packing_policy()

    result = pack_and_reconcile(serving_unit, sizing_breakdown, resilience_policy, packing_policy)

    assert result.status == PackingResultStatus.SUCCESS
    assert result.installed_accelerators == 0
    assert result.installed_servers == 0
    assert result.installed_racks == 0
    assert result.installed_zones == 0
    assert result.installed_sites == 0
    assert result.installed_serving_unit_equivalents == 0
    assert result.stranded_accelerators == 0
    assert result.capacity_classification == CapacityClassification(productive=0, headroom=0, growth=0, reserved=0, resilience=0, stranded=0, idle=0)
    assert result.sellable_units == 0


def test_pack_and_reconcile_with_reserved_units():
    """Tests packing with reserved units."""
    serving_unit = ServingUnit(accelerators_per_serving_unit=4)
    sizing_breakdown = SizingBreakdown(productive_units=1, reserved_units=1)
    resilience_policy = ResiliencePolicy()
    packing_policy = default_packing_policy()

    result = pack_and_reconcile(serving_unit, sizing_breakdown, resilience_policy, packing_policy)

    assert result.status == PackingResultStatus.SUCCESS
    # 2 units * 4 acc/unit = 8 acc needed. 1 server * 8 acc/server = 8 acc installed.
    assert result.installed_accelerators == 8
    assert result.installed_servers == 1
    assert result.installed_racks == 1
    assert result.installed_zones == 1
    assert result.installed_sites == 1
    assert result.installed_serving_unit_equivalents == 2
    assert result.stranded_accelerators == 0
    assert result.capacity_classification == CapacityClassification(productive=1, headroom=0, growth=0, reserved=1, resilience=0, stranded=0, idle=0)
    assert result.sellable_units == 1


def test_pack_and_reconcile_active_active_site_resilience():
    """Tests active-active site outage resilience."""
    serving_unit = ServingUnit(accelerators_per_serving_unit=4)
    sizing_breakdown = SizingBreakdown(productive_units=4) # 16 acc productive
    resilience_policy = ResiliencePolicy(
        failure_domains=[FailureDomain.SITE],
        multi_site_policy=MultiSitePolicy.ACTIVE_ACTIVE,
    )
    packing_policy = replace(default_packing_policy(), zones_per_site=2) # 2 sites available

    result = pack_and_reconcile(serving_unit, sizing_breakdown, resilience_policy, packing_policy)

    assert result.status == PackingResultStatus.SUCCESS
    # Productive: 4 units = 16 acc.
    # Active-active site (2 sites): To maintain 16 acc if 1 site fails, need 16 * (2/1) = 32 acc total.
    # Total units to provision: ceil(32/4) = 8 units.
    # Total accelerators to pack: 8 units * 4 acc/unit = 32 acc.
    # Servers: ceil(32/8) = 4 servers.
    # Installed accelerators: 4 servers * 8 acc/server = 32 acc.
    assert result.installed_accelerators == 32
    assert result.installed_servers == 4
    assert result.installed_racks == 4
    assert result.installed_zones == 4
    assert result.installed_sites == 2 # ceil(4 zones / 2 zones_per_site) = 2 sites
    assert result.installed_serving_unit_equivalents == 8
    assert result.stranded_accelerators == 0
    assert result.capacity_classification == CapacityClassification(productive=4, headroom=0, growth=0, reserved=0, resilience=4, stranded=0, idle=0)
    assert result.sellable_units == 4


def test_pack_and_reconcile_active_active_zone_resilience():
    """Tests active-active zone outage resilience."""
    serving_unit = ServingUnit(accelerators_per_serving_unit=4)
    sizing_breakdown = SizingBreakdown(productive_units=4) # 16 acc productive
    resilience_policy = ResiliencePolicy(
        failure_domains=[FailureDomain.ZONE],
        multi_site_policy=MultiSitePolicy.ACTIVE_ACTIVE,
    )
    packing_policy = replace(default_packing_policy(), racks_per_zone=2) # 2 zones available

    result = pack_and_reconcile(serving_unit, sizing_breakdown, resilience_policy, packing_policy)

    assert result.status == PackingResultStatus.SUCCESS
    # Productive: 4 units = 16 acc.
    # Active-active zone (2 zones): To maintain 16 acc if 1 zone fails, need 16 * (2/1) = 32 acc total.
    # Total units to provision: ceil(32/4) = 8 units.
    # Total accelerators to pack: 8 units * 4 acc/unit = 32 acc.
    # Servers: ceil(32/8) = 4 servers.
    # Installed accelerators: 4 servers * 8 acc/server = 32 acc.
    assert result.installed_accelerators == 32
    assert result.installed_servers == 4
    assert result.installed_racks == 4
    assert result.installed_zones == 2 # ceil(4 racks / 2 racks_per_zone) = 2 zones
    assert result.installed_sites == 2 # ceil(2 zones / 1 zone_per_site) = 2 sites
    assert result.installed_serving_unit_equivalents == 8
    assert result.stranded_accelerators == 0
    assert result.capacity_classification == CapacityClassification(productive=4, headroom=0, growth=0, reserved=0, resilience=4, stranded=0, idle=0)
    assert result.sellable_units == 4


def test_pack_and_reconcile_n_plus_k_zone_resilience():
    """Tests N+k zone resilience."""
    serving_unit = ServingUnit(accelerators_per_serving_unit=4)
    sizing_breakdown = SizingBreakdown(productive_units=1)
    resilience_policy = ResiliencePolicy(n_plus_k={FailureDomain.ZONE: 1})
    packing_policy = replace(default_packing_policy(), racks_per_zone=2, servers_per_rack=2) # 2 servers/rack, 2 racks/zone = 32 acc/zone

    result = pack_and_reconcile(serving_unit, sizing_breakdown, resilience_policy, packing_policy)

    assert result.status == PackingResultStatus.SUCCESS
    # Base demand: 1 unit = 4 acc.
    # N+1 zone: 4 acc (base) + 32 acc (loss of 1 zone) = 36 acc needed.
    # Total units to provision: ceil(36/4) = 9 units.
    # Total accelerators to pack: 9 units * 4 acc/unit = 36 acc.
    # Servers: ceil(36/8) = 5 servers (40 acc installed).
    assert result.installed_accelerators == 40
    assert result.installed_servers == 5
    assert result.installed_racks == 3 # ceil(5 servers / 2 servers_per_rack) = 3 racks
    assert result.installed_zones == 2 # ceil(3 racks / 2 racks_per_zone) = 2 zones
    assert result.installed_sites == 2 # ceil(2 zones / 1 zone_per_site) = 2 sites
    assert result.installed_serving_unit_equivalents == 10 # floor(40/4) = 10
    assert result.stranded_accelerators == 0
    assert result.capacity_classification == CapacityClassification(productive=1, headroom=0, growth=0, reserved=0, resilience=8, stranded=0, idle=1)
    assert result.sellable_units == 2


def test_pack_and_reconcile_n_plus_k_site_resilience():
    """Tests N+k site resilience."""
    serving_unit = ServingUnit(accelerators_per_serving_unit=4)
    sizing_breakdown = SizingBreakdown(productive_units=1)
    resilience_policy = ResiliencePolicy(n_plus_k={FailureDomain.SITE: 1})
    packing_policy = replace(default_packing_policy(), zones_per_site=2, racks_per_zone=2, servers_per_rack=2) # 2 servers/rack, 2 racks/zone, 2 zones/site = 64 acc/site

    result = pack_and_reconcile(serving_unit, sizing_breakdown, resilience_policy, packing_policy)

    assert result.status == PackingResultStatus.SUCCESS
    # Base demand: 1 unit = 4 acc.
    # N+1 site: 4 acc (base) + 64 acc (loss of 1 site) = 68 acc needed.
    # Total units to provision: ceil(68/4) = 17 units.
    # Total accelerators to pack: 17 units * 4 acc/unit = 68 acc.
    # Servers: ceil(68/8) = 9 servers (72 acc installed).
    assert result.installed_accelerators == 72
    assert result.installed_servers == 9
    assert result.installed_racks == 5 # ceil(9 servers / 2 servers_per_rack) = 5 racks
    assert result.installed_zones == 3 # ceil(5 racks / 2 racks_per_zone) = 3 zones
    assert result.installed_sites == 2 # ceil(3 zones / 2 zones_per_site) = 2 sites
    assert result.installed_serving_unit_equivalents == 18 # floor(72/4) = 18
    assert result.stranded_accelerators == 0
    assert result.capacity_classification == CapacityClassification(productive=1, headroom=0, growth=0, reserved=0, resilience=16, stranded=0, idle=1)
    assert result.sellable_units == 2
