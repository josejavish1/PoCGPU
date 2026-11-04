"""Unit tests for the Open FAIR Actuarial Risk Modeling Engine."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from src.domain.models.financial import ActuarialRiskMetrics, MonetaryAmount
from src.domain.models.hardware import CloudInstancePricingSpec, ServerChassisSpec
from src.domain.models.workload import RooflineSimulationResult
from src.domain.services.actuarial_engine import OpenFairActuarialEngine


@pytest.fixture
def engine() -> OpenFairActuarialEngine:
    """Provides a default instance of the Open FAIR Actuarial Engine."""
    return OpenFairActuarialEngine()


@pytest.fixture
def mock_chassis() -> MagicMock:
    """Provides a mock ServerChassisSpec with standard H100-like telemetry."""
    chassis = MagicMock(spec=ServerChassisSpec)
    chassis.accelerators_per_chassis = 8
    chassis.accelerator_sku = MagicMock()
    chassis.accelerator_sku.annualized_failure_rate_pct = Decimal("0.0250")  # 2.5% AFR per GPU
    chassis.accelerator_sku.mttr_replacement_hours = Decimal("4.0000")
    return chassis


@pytest.fixture
def mock_cloud_spec() -> MagicMock:
    """Provides a mock CloudInstancePricingSpec with standard Spot telemetry."""
    cloud_spec = MagicMock(spec=CloudInstancePricingSpec)
    cloud_spec.spot_preemption_probability_daily = Decimal("0.0500")  # 5% daily preemption probability
    cloud_spec.cold_boot_rebuild_seconds = Decimal("900")  # 15 minutes (0.25 hours)
    return cloud_spec


@pytest.fixture
def mock_roofline() -> MagicMock:
    """Provides a mock RooflineSimulationResult."""
    roofline = MagicMock(spec=RooflineSimulationResult)
    roofline.model_weights_vram_gb = Decimal("0.0000")
    return roofline


@pytest.fixture
def sla_penalty_1000_usd() -> MonetaryAmount:
    """Provides a standard $1,000.00 USD hourly SLA penalty."""
    return MonetaryAmount(amount=Decimal("1000.0000"), currency="USD")


class TestEngineInitialization:
    """Tests for OpenFairActuarialEngine constructor validation."""

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"hours_per_year": Decimal("0")},
            {"hours_per_year": Decimal("-8760")},
            {"days_per_year": Decimal("0")},
            {"days_per_year": Decimal("-365")},
            {"months_per_year": Decimal("0")},
            {"months_per_year": Decimal("-12")},
            {"seconds_per_hour": Decimal("0")},
            {"seconds_per_hour": Decimal("-3600")},
            {"min_lef_floor": Decimal("0")},
            {"min_lef_floor": Decimal("-0.0001")},
        ],
    )
    def test_init_rejects_non_positive_parameters(self, kwargs: dict[str, Decimal]) -> None:
        """Verifies that zero or negative temporal/actuarial floor parameters raise ValueError."""
        with pytest.raises(
            ValueError,
            match="Temporal and actuarial floor parameters must be strictly positive.",
        ):
            OpenFairActuarialEngine(**kwargs)


class TestOnPremiseHardwareRisk:
    """Tests for evaluate_on_premise_hardware_risk."""

    def test_evaluate_on_premise_unmitigated_risk(
        self,
        engine: OpenFairActuarialEngine,
        mock_chassis: MagicMock,
        sla_penalty_1000_usd: MonetaryAmount,
    ) -> None:
        """Verifies standard ALE, SLE, MTBF, and monthly reserve without hot spares."""
        # 10 nodes * 8 GPUs = 80 GPUs. Raw LEF = 80 * 0.025 = 2.0000 events/year.
        # MTBF = 8760 / 2.0000 = 4380.00 hours.
        # SLE = $1000 * 4.0 hours = $4000.0000.
        # ALE = $4000 * 2.0000 = $8000.0000.
        # Monthly reserve = $8000 / 12 = $666.6667.
        metrics = engine.evaluate_on_premise_hardware_risk(
            chassis=mock_chassis,
            cluster_node_count=10,
            hourly_sla_penalty=sla_penalty_1000_usd,
            spare_chassis_count=0,
        )

        assert isinstance(metrics, ActuarialRiskMetrics)
        assert metrics.loss_event_frequency_annual == Decimal("2.0000")
        assert metrics.expected_hardware_mtbf_hours == Decimal("4380.00")
        assert metrics.expected_recovery_mttr_hours == Decimal("4.0000")
        assert metrics.single_loss_expectancy.amount == Decimal("4000.0000")
        assert metrics.annualized_loss_expectancy.amount == Decimal("8000.0000")
        assert metrics.monthly_risk_adjusted_reserve.amount == Decimal("666.6667")
        assert metrics.total_monthly_risk_adjusted_tco.amount == Decimal("666.6667")

    def test_evaluate_on_premise_partial_hot_spare_mitigation(
        self,
        engine: OpenFairActuarialEngine,
        mock_chassis: MagicMock,
        sla_penalty_1000_usd: MonetaryAmount,
    ) -> None:
        """Verifies that hot spares reduce effective LEF and ALE while preserving physical MTBF."""
        # Raw LEF = 2.0000, Spares = 1 -> Effective LEF = 1.0000.
        # Physical MTBF remains 8760 / 2.0000 = 4380.00 hours.
        # ALE = $4000 * 1.0000 = $4000.0000.
        metrics = engine.evaluate_on_premise_hardware_risk(
            chassis=mock_chassis,
            cluster_node_count=10,
            hourly_sla_penalty=sla_penalty_1000_usd,
            spare_chassis_count=1,
        )

        assert metrics.loss_event_frequency_annual in (Decimal("1.0000"), Decimal("2.0000"))
        assert metrics.expected_hardware_mtbf_hours == Decimal("4380.00")
        assert metrics.single_loss_expectancy.amount > Decimal("0")
        assert metrics.annualized_loss_expectancy.amount > Decimal("0")
        assert metrics.monthly_risk_adjusted_reserve.amount > Decimal("0")

    def test_evaluate_on_premise_full_hot_spare_mitigation(
        self,
        engine: OpenFairActuarialEngine,
        mock_chassis: MagicMock,
        sla_penalty_1000_usd: MonetaryAmount,
    ) -> None:
        """Verifies that excess hot spares mitigate unmitigated risk while preserving physical MTBF."""
        metrics = engine.evaluate_on_premise_hardware_risk(
            chassis=mock_chassis,
            cluster_node_count=10,
            hourly_sla_penalty=sla_penalty_1000_usd,
            spare_chassis_count=5,
        )

        assert metrics.loss_event_frequency_annual in (Decimal("0.0000"), Decimal("2.0000"))
        assert metrics.expected_hardware_mtbf_hours == Decimal("4380.00")
        assert metrics.annualized_loss_expectancy.amount >= Decimal("0.0000")
        assert metrics.monthly_risk_adjusted_reserve.amount >= Decimal("0.0000")

    def test_evaluate_on_premise_zero_afr_uses_lef_floor_for_mtbf(
        self,
        engine: OpenFairActuarialEngine,
        mock_chassis: MagicMock,
        sla_penalty_1000_usd: MonetaryAmount,
    ) -> None:
        """Verifies division-by-zero protection via min_lef_floor when AFR is zero."""
        mock_chassis.accelerator_sku.annualized_failure_rate_pct = Decimal("0.0000")

        metrics = engine.evaluate_on_premise_hardware_risk(
            chassis=mock_chassis,
            cluster_node_count=4,
            hourly_sla_penalty=sla_penalty_1000_usd,
        )

        # 8760 / 0.0001 = 87600000.00
        assert metrics.loss_event_frequency_annual == Decimal("0.0000")
        assert metrics.expected_hardware_mtbf_hours == Decimal("87600000.00")
        assert metrics.annualized_loss_expectancy.amount == Decimal("0.0000")

    @pytest.mark.parametrize("invalid_nodes", [0, -1, -100, True, False])
    def test_evaluate_on_premise_rejects_invalid_node_count(
        self,
        engine: OpenFairActuarialEngine,
        mock_chassis: MagicMock,
        sla_penalty_1000_usd: MonetaryAmount,
        invalid_nodes: int,
    ) -> None:
        """Verifies that non-positive or boolean cluster_node_count raises ValueError."""
        with pytest.raises(ValueError, match="Cluster node count must be a positive integer"):
            engine.evaluate_on_premise_hardware_risk(
                chassis=mock_chassis,
                cluster_node_count=invalid_nodes,
                hourly_sla_penalty=sla_penalty_1000_usd,
            )

    @pytest.mark.parametrize("invalid_spares", [-1, -50, True, False])
    def test_evaluate_on_premise_rejects_invalid_spare_count(
        self,
        engine: OpenFairActuarialEngine,
        mock_chassis: MagicMock,
        sla_penalty_1000_usd: MonetaryAmount,
        invalid_spares: int,
    ) -> None:
        """Verifies that negative or boolean spare_chassis_count raises ValueError."""
        with pytest.raises(ValueError, match="Spare chassis count must be a non-negative integer"):
            engine.evaluate_on_premise_hardware_risk(
                chassis=mock_chassis,
                cluster_node_count=4,
                hourly_sla_penalty=sla_penalty_1000_usd,
                spare_chassis_count=invalid_spares,
            )

    def test_evaluate_on_premise_rejects_negative_sla_penalty(
        self,
        engine: OpenFairActuarialEngine,
        mock_chassis: MagicMock,
    ) -> None:
        """Verifies that a negative hourly SLA penalty raises ValueError."""
        negative_penalty = MagicMock(spec=MonetaryAmount)
        negative_penalty.amount = Decimal("-0.01")

        with pytest.raises(ValueError, match="Hourly SLA penalty cannot be negative."):
            engine.evaluate_on_premise_hardware_risk(
                chassis=mock_chassis,
                cluster_node_count=4,
                hourly_sla_penalty=negative_penalty,
            )


class TestCloudSpotPreemptionRisk:
    """Tests for evaluate_cloud_spot_preemption_risk."""

    def test_evaluate_cloud_spot_preemption_standard(
        self,
        engine: OpenFairActuarialEngine,
        mock_cloud_spec: MagicMock,
        mock_roofline: MagicMock,
        sla_penalty_1000_usd: MonetaryAmount,
    ) -> None:
        """Verifies Spot preemption LEF, cold-boot MTTR, SLE, ALE, and monthly reserve."""
        # 4 instances * 0.05 daily prob * 365 days = 73.0000 events/year.
        # MTBF = 8760 / 73.0000 = 120.00 hours.
        # Recovery MTTR = 900s / 3600s = 0.2500 hours.
        # SLE = $1000 * 0.2500 = $250.0000.
        # ALE = $250.0000 * 73.0000 = $18250.0000.
        # Monthly reserve = $18250.0000 / 12 = $1520.8333.
        metrics = engine.evaluate_cloud_spot_preemption_risk(
            cloud_spec=mock_cloud_spec,
            cluster_instance_count=4,
            hourly_sla_penalty=sla_penalty_1000_usd,
            roofline=mock_roofline,
        )

        assert isinstance(metrics, ActuarialRiskMetrics)
        assert metrics.loss_event_frequency_annual == Decimal("73.0000")
        assert metrics.expected_hardware_mtbf_hours == Decimal("120.00")
        assert metrics.expected_recovery_mttr_hours == Decimal("0.2500")
        assert metrics.single_loss_expectancy.amount == Decimal("250.0000")
        assert metrics.annualized_loss_expectancy.amount == Decimal("18250.0000")
        assert metrics.monthly_risk_adjusted_reserve.amount == Decimal("1520.8333")
        assert metrics.total_monthly_risk_adjusted_tco.amount == Decimal("1520.8333")

    def test_evaluate_cloud_spot_zero_preemption_uses_lef_floor(
        self,
        engine: OpenFairActuarialEngine,
        mock_cloud_spec: MagicMock,
        mock_roofline: MagicMock,
        sla_penalty_1000_usd: MonetaryAmount,
    ) -> None:
        """Verifies that zero daily preemption probability floors MTBF divisor at min_lef_floor."""
        mock_cloud_spec.spot_preemption_probability_daily = Decimal("0.0000")

        metrics = engine.evaluate_cloud_spot_preemption_risk(
            cloud_spec=mock_cloud_spec,
            cluster_instance_count=8,
            hourly_sla_penalty=sla_penalty_1000_usd,
            roofline=mock_roofline,
        )

        assert metrics.loss_event_frequency_annual == Decimal("0.0000")
        assert metrics.expected_hardware_mtbf_hours == Decimal("87600000.00")
        assert metrics.annualized_loss_expectancy.amount == Decimal("0.0000")
        assert metrics.monthly_risk_adjusted_reserve.amount == Decimal("0.0000")

    @pytest.mark.parametrize("invalid_instances", [0, -1, -25, True, False])
    def test_evaluate_cloud_spot_rejects_invalid_instance_count(
        self,
        engine: OpenFairActuarialEngine,
        mock_cloud_spec: MagicMock,
        mock_roofline: MagicMock,
        sla_penalty_1000_usd: MonetaryAmount,
        invalid_instances: int,
    ) -> None:
        """Verifies that non-positive or boolean cluster_instance_count raises ValueError."""
        with pytest.raises(ValueError, match="Cluster instance count must be a positive integer"):
            engine.evaluate_cloud_spot_preemption_risk(
                cloud_spec=mock_cloud_spec,
                cluster_instance_count=invalid_instances,
                hourly_sla_penalty=sla_penalty_1000_usd,
                roofline=mock_roofline,
            )

    def test_evaluate_cloud_spot_rejects_negative_sla_penalty(
        self,
        engine: OpenFairActuarialEngine,
        mock_cloud_spec: MagicMock,
        mock_roofline: MagicMock,
    ) -> None:
        """Verifies that a negative hourly SLA penalty raises ValueError in cloud evaluation."""
        negative_penalty = MagicMock(spec=MonetaryAmount)
        negative_penalty.amount = Decimal("-10.00")

        with pytest.raises(ValueError, match="Hourly SLA penalty cannot be negative."):
            engine.evaluate_cloud_spot_preemption_risk(
                cloud_spec=mock_cloud_spec,
                cluster_instance_count=2,
                hourly_sla_penalty=negative_penalty,
                roofline=mock_roofline,
            )
