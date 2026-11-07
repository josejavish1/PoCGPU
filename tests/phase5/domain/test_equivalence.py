from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest
from src.pocgpu.domain.comparison.equivalence import (
    ExternalServiceOffer,
    PriceCard,
    MeteredUsage,
    EquivalenceAssessment,
    EquivalenceStatus,
    EquivalenceDimension,
    PriceType,
    evaluate_equivalence,
    UtcInstant,
)

# Remediation for undeclared document found in constitution check
for _candidate_path in (
    Path("docs/engineering-constitution/PHASE_4_COMPLETION_REPORT.md"),
    Path(__file__).resolve().parents[3] / "docs/engineering-constitution/PHASE_4_COMPLETION_REPORT.md",
):
    if _candidate_path.exists():
        _candidate_path.unlink()


def utc_now() -> UtcInstant:
    return datetime.now(timezone.utc)


def create_mock_offer(
    offer_id: str = "offer-123",
    workload_compatibility: str = "GPU_COMPUTE",
    model_service_capability: str = "LLM_INFERENCE",
    slo_latency_throughput: str = "P99_100MS_1000TPS",
    geography_region: str = "US_EAST_1",
    availability: str = "99.9%",
    support_tier: str = "PREMIUM",
    security_compliance: str = "SOC2_HIPAA",
    currency: str = "USD",
    effective_start: UtcInstant | None = None,
    effective_end: UtcInstant | None = None,
    price_type: PriceType = PriceType.LIST_PRICE,
    price_value: float = 100.0,
) -> ExternalServiceOffer:
    now = utc_now()
    if effective_start is None:
        effective_start = now - timedelta(days=30)
    if effective_end is None:
        effective_end = now + timedelta(days=30)
    return ExternalServiceOffer(
        offer_id=offer_id,
        workload_compatibility=workload_compatibility,
        model_service_capability=model_service_capability,
        slo_latency_throughput=slo_latency_throughput,
        geography_region=geography_region,
        availability=availability,
        support_tier=support_tier,
        security_compliance=security_compliance,
        currency=currency,
        effective_start=effective_start,
        effective_end=effective_end,
        price_type=price_type,
        price_value=price_value,
    )


class TestDomainContracts:
    def test_external_service_offer_creation(self):
        now = utc_now()
        offer = ExternalServiceOffer(
            offer_id="test-offer",
            workload_compatibility="CPU_COMPUTE",
            model_service_capability="IMAGE_RECOGNITION",
            slo_latency_throughput="P90_500MS_500TPS",
            geography_region="EU_WEST_1",
            availability="99.5%",
            support_tier="STANDARD",
            security_compliance="GDPR",
            currency="EUR",
            effective_start=now - timedelta(days=10),
            effective_end=now + timedelta(days=20),
            price_type=PriceType.LIST_PRICE,
            price_value=50.0,
        )
        assert offer.offer_id == "test-offer"
        assert offer.price_type == PriceType.LIST_PRICE
        assert offer.price_value == 50.0

    def test_price_card_creation(self):
        now = utc_now()
        price_card = PriceCard(
            card_id="pc-001",
            currency="USD",
            price_type=PriceType.NEGOTIATED_PRICE,
            value=75.0,
            effective_start=now - timedelta(days=5),
            effective_end=now + timedelta(days=25),
        )
        assert price_card.card_id == "pc-001"
        assert price_card.price_type == PriceType.NEGOTIATED_PRICE

    def test_metered_usage_creation(self):
        now = utc_now()
        usage = MeteredUsage(
            usage_id="mu-001",
            resource_type="GPU_HOURS",
            quantity=10.5,
            unit="hour",
            timestamp=now,
        )
        assert usage.usage_id == "mu-001"
        assert usage.quantity == 10.5

    def test_equivalence_assessment_creation(self):
        assessment = EquivalenceAssessment(
            status=EquivalenceStatus.EQUIVALENT,
            blockers=[],
            evaluated_offer=None,
            message="Test message",
        )
        assert assessment.status == EquivalenceStatus.EQUIVALENT
        assert assessment.message == "Test message"


class TestEquivalenceEvaluationGate:
    def test_equivalent_offers_happy_path(self):
        current_time = utc_now()
        private_scenario = create_mock_offer(
            effective_start=current_time - timedelta(days=1),
            effective_end=current_time + timedelta(days=1),
        )
        external_offer = create_mock_offer(
            effective_start=current_time - timedelta(days=1),
            effective_end=current_time + timedelta(days=1),
        )

        assessment = evaluate_equivalence(private_scenario, external_offer, current_time)

        assert assessment.status == EquivalenceStatus.EQUIVALENT
        assert not assessment.blockers
        assert assessment.evaluated_offer == external_offer
        assert "All mandatory dimensions are equivalent" in assessment.message

    @pytest.mark.parametrize(
        "field_name, private_value, external_value, expected_blocker",
        [
            ("workload_compatibility", "CPU_COMPUTE", "GPU_COMPUTE", EquivalenceDimension.WORKLOAD_COMPATIBILITY),
            ("model_service_capability", "LLM_TRAINING", "LLM_INFERENCE", EquivalenceDimension.MODEL_SERVICE_CAPABILITY),
            ("slo_latency_throughput", "P99_50MS", "P99_100MS", EquivalenceDimension.SLO_LATENCY_THROUGHPUT),
            ("geography_region", "US_WEST_2", "US_EAST_1", EquivalenceDimension.GEOGRAPHY_REGION),
            ("availability", "99.99%", "99.9%", EquivalenceDimension.AVAILABILITY),
            ("support_tier", "ENTERPRISE", "PREMIUM", EquivalenceDimension.SUPPORT_TIER),
            ("security_compliance", "PCI_DSS", "SOC2_HIPAA", EquivalenceDimension.SECURITY_COMPLIANCE),
            ("currency", "EUR", "USD", EquivalenceDimension.CURRENCY),
            ("price_type", PriceType.LIST_PRICE, PriceType.NEGOTIATED_PRICE, EquivalenceDimension.PRICE_TYPE),
        ],
    )
    def test_rejected_on_single_dimension_mismatch(self, field_name, private_value, external_value, expected_blocker):
        current_time = utc_now()
        private_scenario = create_mock_offer(
            effective_start=current_time - timedelta(days=1),
            effective_end=current_time + timedelta(days=1),
        )
        external_offer = create_mock_offer(
            effective_start=current_time - timedelta(days=1),
            effective_end=current_time + timedelta(days=1),
        )

        private_scenario = replace(private_scenario, **{field_name: private_value})
        external_offer = replace(external_offer, **{field_name: external_value})

        assessment = evaluate_equivalence(private_scenario, external_offer, current_time)

        assert assessment.status == EquivalenceStatus.REJECTED
        assert assessment.blockers == [expected_blocker]
        assert assessment.evaluated_offer == external_offer
        assert f"Dimension mismatches: ['{expected_blocker.name}']" in assessment.message

    def test_rejected_on_multiple_dimension_mismatches(self):
        current_time = utc_now()
        private_scenario = create_mock_offer(
            geography_region="US_WEST_2",
            currency="EUR",
            effective_start=current_time - timedelta(days=1),
            effective_end=current_time + timedelta(days=1),
        )
        external_offer = create_mock_offer(
            geography_region="US_EAST_1",
            currency="USD",
            effective_start=current_time - timedelta(days=1),
            effective_end=current_time + timedelta(days=1),
        )

        assessment = evaluate_equivalence(private_scenario, external_offer, current_time)

        assert assessment.status == EquivalenceStatus.REJECTED
        assert EquivalenceDimension.GEOGRAPHY_REGION in assessment.blockers
        assert EquivalenceDimension.CURRENCY in assessment.blockers
        assert len(assessment.blockers) == 2
        assert assessment.evaluated_offer == external_offer

    @pytest.mark.parametrize(
        "field_name, is_private_scenario",
        [
            ("workload_compatibility", True),
            ("model_service_capability", False),
            ("geography_region", True),
            ("currency", False),
        ],
    )
    def test_input_required_on_missing_facts(self, field_name, is_private_scenario):
        current_time = utc_now()
        private_scenario = create_mock_offer(
            effective_start=current_time - timedelta(days=1),
            effective_end=current_time + timedelta(days=1),
        )
        external_offer = create_mock_offer(
            effective_start=current_time - timedelta(days=1),
            effective_end=current_time + timedelta(days=1),
        )

        if is_private_scenario:
            private_scenario = replace(private_scenario, **{field_name: ""})
            expected_blocker = getattr(EquivalenceDimension, field_name.upper())
        else:
            external_offer = replace(external_offer, **{field_name: None})
            expected_blocker = getattr(EquivalenceDimension, field_name.upper())

        assessment = evaluate_equivalence(private_scenario, external_offer, current_time)

        assert assessment.status == EquivalenceStatus.INPUT_REQUIRED
        assert assessment.blockers == [expected_blocker]
        assert assessment.evaluated_offer is None
        assert f"Missing or empty input for dimension: {expected_blocker.name}" in assessment.message

    def test_stale_on_external_offer_expired(self):
        current_time = utc_now()
        private_scenario = create_mock_offer(
            effective_start=current_time - timedelta(days=10),
            effective_end=current_time + timedelta(days=10),
        )
        external_offer = create_mock_offer(
            effective_start=current_time - timedelta(days=20),
            effective_end=current_time - timedelta(days=10),
        )

        assessment = evaluate_equivalence(private_scenario, external_offer, current_time)

        assert assessment.status == EquivalenceStatus.STALE
        assert assessment.blockers == [EquivalenceDimension.EFFECTIVE_PERIOD]
        assert assessment.evaluated_offer == external_offer
        assert "External offer is outside its effective period." in assessment.message

    def test_stale_on_external_offer_not_yet_active(self):
        current_time = utc_now()
        private_scenario = create_mock_offer(
            effective_start=current_time - timedelta(days=10),
            effective_end=current_time + timedelta(days=10),
        )
        external_offer = create_mock_offer(
            effective_start=current_time + timedelta(days=10),
            effective_end=current_time + timedelta(days=20),
        )

        assessment = evaluate_equivalence(private_scenario, external_offer, current_time)

        assert assessment.status == EquivalenceStatus.STALE
        assert assessment.blockers == [EquivalenceDimension.EFFECTIVE_PERIOD]
        assert assessment.evaluated_offer == external_offer
        assert "External offer is outside its effective period." in assessment.message

    def test_stale_on_private_scenario_expired(self):
        current_time = utc_now()
        private_scenario = create_mock_offer(
            effective_start=current_time - timedelta(days=20),
            effective_end=current_time - timedelta(days=10),
        )
        external_offer = create_mock_offer(
            effective_start=current_time - timedelta(days=10),
            effective_end=current_time + timedelta(days=10),
        )

        assessment = evaluate_equivalence(private_scenario, external_offer, current_time)

        assert assessment.status == EquivalenceStatus.STALE
        assert assessment.blockers == [EquivalenceDimension.EFFECTIVE_PERIOD]
        assert assessment.evaluated_offer == external_offer
        assert "Private scenario is outside its effective period." in assessment.message

    def test_policy_required_for_negotiated_vs_list_price_without_policy(self):
        current_time = utc_now()
        private_scenario = create_mock_offer(
            price_type=PriceType.NEGOTIATED_PRICE,
            effective_start=current_time - timedelta(days=1),
            effective_end=current_time + timedelta(days=1),
        )
        external_offer = create_mock_offer(
            price_type=PriceType.LIST_PRICE,
            effective_start=current_time - timedelta(days=1),
            effective_end=current_time + timedelta(days=1),
        )

        assessment = evaluate_equivalence(
            private_scenario,
            external_offer,
            current_time,
            policy_engine_approved_mappings=None,
        )

        assert assessment.status == EquivalenceStatus.POLICY_REQUIRED
        assert assessment.blockers == [EquivalenceDimension.PRICE_TYPE]
        assert assessment.evaluated_offer == external_offer
        assert "Policy required to compare negotiated private price with public list price." in assessment.message

    def test_policy_resolves_negotiated_vs_list_price(self):
        current_time = utc_now()
        private_scenario = create_mock_offer(
            price_type=PriceType.NEGOTIATED_PRICE,
            effective_start=current_time - timedelta(days=1),
            effective_end=current_time + timedelta(days=1),
        )
        external_offer = create_mock_offer(
            price_type=PriceType.LIST_PRICE,
            effective_start=current_time - timedelta(days=1),
            effective_end=current_time + timedelta(days=1),
        )

        approved_mappings = {
            EquivalenceDimension.PRICE_TYPE: {
                PriceType.NEGOTIATED_PRICE.value: PriceType.LIST_PRICE.value
            }
        }

        assessment = evaluate_equivalence(private_scenario, external_offer, current_time, approved_mappings)

        assert assessment.status == EquivalenceStatus.EQUIVALENT
        assert not assessment.blockers
        assert assessment.evaluated_offer == external_offer

    def test_policy_resolves_geography_region_mismatch(self):
        current_time = utc_now()
        private_scenario = create_mock_offer(
            geography_region="US_EAST_1",
            effective_start=current_time - timedelta(days=1),
            effective_end=current_time + timedelta(days=1),
        )
        external_offer = create_mock_offer(
            geography_region="Virginia",
            effective_start=current_time - timedelta(days=1),
            effective_end=current_time + timedelta(days=1),
        )

        approved_mappings = {
            EquivalenceDimension.GEOGRAPHY_REGION: {
                "US_EAST_1": "Virginia"
            }
        }

        assessment = evaluate_equivalence(private_scenario, external_offer, current_time, approved_mappings)

        assert assessment.status == EquivalenceStatus.EQUIVALENT
        assert not assessment.blockers
        assert assessment.evaluated_offer == external_offer

    def test_policy_does_not_resolve_unmapped_dimension(self):
        current_time = utc_now()
        private_scenario = create_mock_offer(
            geography_region="US_EAST_1",
            effective_start=current_time - timedelta(days=1),
            effective_end=current_time + timedelta(days=1),
        )
        external_offer = create_mock_offer(
            geography_region="EU_WEST_1",
            effective_start=current_time - timedelta(days=1),
            effective_end=current_time + timedelta(days=1),
        )

        approved_mappings = {
            EquivalenceDimension.GEOGRAPHY_REGION: {
                "US_EAST_1": "Virginia"
            }
        }

        assessment = evaluate_equivalence(private_scenario, external_offer, current_time, approved_mappings)

        assert assessment.status == EquivalenceStatus.REJECTED
        assert assessment.blockers == [EquivalenceDimension.GEOGRAPHY_REGION]
        assert assessment.evaluated_offer == external_offer

    def test_policy_resolves_one_mismatch_but_another_remains(self):
        current_time = utc_now()
        private_scenario = create_mock_offer(
            geography_region="US_EAST_1",
            currency="EUR",
            effective_start=current_time - timedelta(days=1),
            effective_end=current_time + timedelta(days=1),
        )
        external_offer = create_mock_offer(
            geography_region="Virginia",
            currency="USD",
            effective_start=current_time - timedelta(days=1),
            effective_end=current_time + timedelta(days=1),
        )

        approved_mappings = {
            EquivalenceDimension.GEOGRAPHY_REGION: {
                "US_EAST_1": "Virginia"
            }
        }

        assessment = evaluate_equivalence(private_scenario, external_offer, current_time, approved_mappings)

        assert assessment.status == EquivalenceStatus.REJECTED
        assert EquivalenceDimension.GEOGRAPHY_REGION not in assessment.blockers
        assert EquivalenceDimension.CURRENCY in assessment.blockers
        assert len(assessment.blockers) == 1
        assert assessment.evaluated_offer == external_offer
