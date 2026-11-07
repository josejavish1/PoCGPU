from dataclasses import dataclass
from datetime import datetime
from enum import Enum

type UtcInstant = datetime


class EquivalenceStatus(Enum):
    INPUT_REQUIRED = "INPUT_REQUIRED"
    POLICY_REQUIRED = "POLICY_REQUIRED"
    REJECTED = "REJECTED"
    STALE = "STALE"
    EQUIVALENT = "EQUIVALENT"


class EquivalenceDimension(Enum):
    WORKLOAD_COMPATIBILITY = "WORKLOAD_COMPATIBILITY"
    MODEL_SERVICE_CAPABILITY = "MODEL_SERVICE_CAPABILITY"
    SLO_LATENCY_THROUGHPUT = "SLO_LATENCY_THROUGHPUT"
    GEOGRAPHY_REGION = "GEOGRAPHY_REGION"
    AVAILABILITY = "AVAILABILITY"
    SUPPORT_TIER = "SUPPORT_TIER"
    SECURITY_COMPLIANCE = "SECURITY_COMPLIANCE"
    CURRENCY = "CURRENCY"
    EFFECTIVE_PERIOD = "EFFECTIVE_PERIOD"
    PRICE_TYPE = "PRICE_TYPE"


class PriceType(Enum):
    LIST_PRICE = "LIST_PRICE"
    NEGOTIATED_PRICE = "NEGOTIATED_PRICE"


@dataclass(frozen=True)
class ExternalServiceOffer:
    """Represents an external service offer with all mandatory dimensions."""
    offer_id: str
    workload_compatibility: str
    model_service_capability: str
    slo_latency_throughput: str
    geography_region: str
    availability: str
    support_tier: str
    security_compliance: str
    currency: str
    effective_start: UtcInstant
    effective_end: UtcInstant
    price_type: PriceType
    price_value: float


@dataclass(frozen=True)
class PriceCard:
    """Represents a specific price card, distinguishing between list and negotiated prices."""
    card_id: str
    currency: str
    price_type: PriceType
    value: float
    effective_start: UtcInstant
    effective_end: UtcInstant


@dataclass(frozen=True)
class MeteredUsage:
    """Represents a record of metered resource usage."""
    usage_id: str
    resource_type: str
    quantity: float
    unit: str
    timestamp: UtcInstant


@dataclass(frozen=True)
class EquivalenceAssessment:
    """The result of an equivalence evaluation between a private scenario and an external offer."""
    status: EquivalenceStatus
    blockers: list[EquivalenceDimension]
    evaluated_offer: ExternalServiceOffer | None
    message: str


def evaluate_equivalence(
    private_scenario: ExternalServiceOffer,
    external_offer: ExternalServiceOffer,
    current_time: UtcInstant,
    policy_engine_approved_mappings: dict[EquivalenceDimension, dict[str, str]] | None = None,
) -> EquivalenceAssessment:
    """
    Evaluates the equivalence between a private scenario and an external service offer
    based on mandatory dimensions and governed rules.

    Args:
        private_scenario: The internal desired service configuration.
        external_offer: The external service offer to be evaluated.
        current_time: The current UTC time for effective period checks.
        policy_engine_approved_mappings: A dictionary of approved mappings for dimensions
                                         to resolve non-exact matches (e.g., region aliases).

    Returns:
        An EquivalenceAssessment detailing the status and any blocking dimensions.
    """
    blockers: list[EquivalenceDimension] = []

    # Rule 1: Missing commercial or technical facts must return status INPUT_REQUIRED.
    required_fields_check = [
        (private_scenario.workload_compatibility, EquivalenceDimension.WORKLOAD_COMPATIBILITY),
        (private_scenario.model_service_capability, EquivalenceDimension.MODEL_SERVICE_CAPABILITY),
        (private_scenario.slo_latency_throughput, EquivalenceDimension.SLO_LATENCY_THROUGHPUT),
        (private_scenario.geography_region, EquivalenceDimension.GEOGRAPHY_REGION),
        (private_scenario.availability, EquivalenceDimension.AVAILABILITY),
        (private_scenario.support_tier, EquivalenceDimension.SUPPORT_TIER),
        (private_scenario.security_compliance, EquivalenceDimension.SECURITY_COMPLIANCE),
        (private_scenario.currency, EquivalenceDimension.CURRENCY),
        (private_scenario.effective_start, EquivalenceDimension.EFFECTIVE_PERIOD),
        (private_scenario.effective_end, EquivalenceDimension.EFFECTIVE_PERIOD),
        (private_scenario.price_type, EquivalenceDimension.PRICE_TYPE),
        (external_offer.workload_compatibility, EquivalenceDimension.WORKLOAD_COMPATIBILITY),
        (external_offer.model_service_capability, EquivalenceDimension.MODEL_SERVICE_CAPABILITY),
        (external_offer.slo_latency_throughput, EquivalenceDimension.SLO_LATENCY_THROUGHPUT),
        (external_offer.geography_region, EquivalenceDimension.GEOGRAPHY_REGION),
        (external_offer.availability, EquivalenceDimension.AVAILABILITY),
        (external_offer.support_tier, EquivalenceDimension.SUPPORT_TIER),
        (external_offer.security_compliance, EquivalenceDimension.SECURITY_COMPLIANCE),
        (external_offer.currency, EquivalenceDimension.CURRENCY),
        (external_offer.effective_start, EquivalenceDimension.EFFECTIVE_PERIOD),
        (external_offer.effective_end, EquivalenceDimension.EFFECTIVE_PERIOD),
        (external_offer.price_type, EquivalenceDimension.PRICE_TYPE),
    ]

    for value, dim in required_fields_check:
        if value is None or (isinstance(value, str) and not value.strip()):
            return EquivalenceAssessment(
                status=EquivalenceStatus.INPUT_REQUIRED,
                blockers=[dim],
                evaluated_offer=None,
                message=f"Missing or empty input for dimension: {dim.name}",
            )

    # Rule 4: Expired or out-of-period price cards or evidence must return STALE.
    if not (external_offer.effective_start <= current_time < external_offer.effective_end):
        return EquivalenceAssessment(
            status=EquivalenceStatus.STALE,
            blockers=[EquivalenceDimension.EFFECTIVE_PERIOD],
            evaluated_offer=external_offer,
            message="External offer is outside its effective period.",
        )
    if not (private_scenario.effective_start <= current_time < private_scenario.effective_end):
        return EquivalenceAssessment(
            status=EquivalenceStatus.STALE,
            blockers=[EquivalenceDimension.EFFECTIVE_PERIOD],
            evaluated_offer=external_offer,
            message="Private scenario is outside its effective period.",
        )

    # Rule 2 & 6: Unresolved equivalence policies or unapproved mappings must return POLICY_REQUIRED.
    # Public list prices and negotiated contract prices must be explicitly distinguished and cannot be
    # treated as interchangeable without governed policy.
    if (
        private_scenario.price_type == PriceType.NEGOTIATED_PRICE
        and external_offer.price_type == PriceType.LIST_PRICE
    ):
        if not (
            policy_engine_approved_mappings
            and EquivalenceDimension.PRICE_TYPE in policy_engine_approved_mappings
            and policy_engine_approved_mappings[EquivalenceDimension.PRICE_TYPE].get(
                private_scenario.price_type.value
            )
            == external_offer.price_type.value
        ):
            return EquivalenceAssessment(
                status=EquivalenceStatus.POLICY_REQUIRED,
                blockers=[EquivalenceDimension.PRICE_TYPE],
                evaluated_offer=external_offer,
                message="Policy required to compare negotiated private price with public list price.",
            )

    # Rule 3: Any single-dimension mismatch between the private scenario and external offer
    # must return REJECTED with explicit dimension blockers.
    dimensions_to_compare = [
        (private_scenario.workload_compatibility, external_offer.workload_compatibility, EquivalenceDimension.WORKLOAD_COMPATIBILITY),
        (private_scenario.model_service_capability, external_offer.model_service_capability, EquivalenceDimension.MODEL_SERVICE_CAPABILITY),
        (private_scenario.slo_latency_throughput, external_offer.slo_latency_throughput, EquivalenceDimension.SLO_LATENCY_THROUGHPUT),
        (private_scenario.geography_region, external_offer.geography_region, EquivalenceDimension.GEOGRAPHY_REGION),
        (private_scenario.availability, external_offer.availability, EquivalenceDimension.AVAILABILITY),
        (private_scenario.support_tier, external_offer.support_tier, EquivalenceDimension.SUPPORT_TIER),
        (private_scenario.security_compliance, external_offer.security_compliance, EquivalenceDimension.SECURITY_COMPLIANCE),
        (private_scenario.currency, external_offer.currency, EquivalenceDimension.CURRENCY),
        (private_scenario.price_type, external_offer.price_type, EquivalenceDimension.PRICE_TYPE),
    ]

    for private_val, external_val, dim in dimensions_to_compare:
        is_match = False
        if private_val == external_val:
            is_match = True
        elif policy_engine_approved_mappings and dim in policy_engine_approved_mappings:
            private_val_str = str(private_val.value) if isinstance(private_val, Enum) else str(private_val)
            external_val_str = str(external_val.value) if isinstance(external_val, Enum) else str(external_val)
            if policy_engine_approved_mappings[dim].get(private_val_str) == external_val_str:
                is_match = True

        if not is_match:
            blockers.append(dim)

    if blockers:
        return EquivalenceAssessment(
            status=EquivalenceStatus.REJECTED,
            blockers=blockers,
            evaluated_offer=external_offer,
            message=f"Dimension mismatches: {[b.name for b in blockers]}",
        )

    return EquivalenceAssessment(
        status=EquivalenceStatus.EQUIVALENT,
        blockers=[],
        evaluated_offer=external_offer,
        message="All mandatory dimensions are equivalent.",
    )
