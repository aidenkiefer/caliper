"""
Unit tests for drift detection service.
"""

import pytest
import numpy as np
from datetime import datetime

from services.ml.drift.metrics import (
    calculate_psi,
    calculate_kl_divergence,
    calculate_mean_shift,
    DriftMetrics,
)
from services.ml.drift.detector import DriftDetector
from services.ml.drift.health_score import HealthScore
from services.ml.drift.alerts import DriftAlertManager, AlertLevel


class TestPSICalculation:
    """Test PSI (Population Stability Index) calculation."""
    
    def test_psi_identical_distributions_returns_zero(self):
        """PSI of identical distributions should be 0."""
        reference = np.array([1, 2, 3, 4, 5])
        current = np.array([1, 2, 3, 4, 5])
        
        psi = calculate_psi(reference, current)
        
        assert psi == pytest.approx(0.0, abs=0.01)
    
    def test_psi_slightly_different_returns_small_value(self):
        """Slightly different distributions have PSI < 0.1."""
        reference = np.random.normal(0, 1, 1000)
        current = np.random.normal(0.1, 1, 1000)
        
        psi = calculate_psi(reference, current)
        
        assert psi < 0.1
    
    def test_psi_significantly_different_returns_high_value(self):
        """Very different distributions have PSI > 0.25."""
        reference = np.random.normal(0, 1, 1000)
        current = np.random.normal(3, 1, 1000)
        
        psi = calculate_psi(reference, current)
        
        assert psi > 0.25
    
    def test_psi_handles_empty_arrays(self):
        """PSI should return 0 for empty arrays."""
        reference = np.array([])
        current = np.array([])
        
        psi = calculate_psi(reference, current)
        
        assert psi == 0.0
    
    def test_psi_handles_nan_values(self):
        """PSI should handle NaN values gracefully."""
        reference = np.array([1, 2, np.nan, 4, 5])
        current = np.array([1, 2, 3, 4, 5])
        
        psi = calculate_psi(reference, current)
        
        assert psi >= 0
        assert not np.isnan(psi)


class TestKLDivergence:
    """Test KL divergence calculation."""
    
    def test_kl_identical_distributions(self):
        """KL divergence of identical distributions should be 0."""
        p = np.array([1, 2, 3, 4, 5])
        q = np.array([1, 2, 3, 4, 5])
        
        kl = calculate_kl_divergence(p, q)
        
        assert kl == pytest.approx(0.0, abs=0.01)
    
    def test_kl_divergence_asymmetry(self):
        """KL(P||Q) != KL(Q||P) in general."""
        p = np.array([1, 2, 3, 4, 5])
        q = np.array([5, 4, 3, 2, 1])
        
        kl_pq = calculate_kl_divergence(p, q)
        kl_qp = calculate_kl_divergence(q, p)
        
        # They should be different (unless distributions are identical)
        assert kl_pq != pytest.approx(kl_qp, abs=0.01)
    
    def test_kl_handles_empty_arrays(self):
        """KL divergence should return 0 for empty arrays."""
        p = np.array([])
        q = np.array([])
        
        kl = calculate_kl_divergence(p, q)
        
        assert kl == 0.0


class TestMeanShift:
    """Test mean shift calculation."""
    
    def test_mean_shift_identical_distributions(self):
        """Mean shift should be 0 for identical distributions."""
        reference = np.array([1, 2, 3, 4, 5])
        current = np.array([1, 2, 3, 4, 5])
        
        shift = calculate_mean_shift(reference, current)
        
        assert shift == pytest.approx(0.0, abs=0.01)
    
    def test_mean_shift_one_std_dev(self):
        """Mean shift of 1 std dev should return ~1.0."""
        reference = np.random.normal(0, 1, 1000)
        current = np.random.normal(1, 1, 1000)
        
        shift = calculate_mean_shift(reference, current)
        
        assert shift == pytest.approx(1.0, abs=0.2)
    
    def test_mean_shift_handles_zero_std(self):
        """Mean shift should return 0 when std is 0."""
        reference = np.array([5, 5, 5, 5, 5])
        current = np.array([5, 5, 5, 5, 5])
        
        shift = calculate_mean_shift(reference, current)
        
        assert shift == 0.0


class TestDriftDetector:
    """Test DriftDetector class."""
    
    def test_detect_feature_drift(self):
        """Test feature drift detection."""
        reference_features = {
            "feature1": np.random.normal(0, 1, 100),
            "feature2": np.random.normal(5, 2, 100),
        }
        
        detector = DriftDetector(reference_features=reference_features)
        
        current_features = {
            "feature1": np.random.normal(0.5, 1, 100),
            "feature2": np.random.normal(5, 2, 100),
        }
        
        metrics = detector.detect_feature_drift(current_features, "model-1")
        
        assert len(metrics) == 2
        assert all(m.model_id == "model-1" for m in metrics)
        assert all(m.feature_name in ["feature1", "feature2"] for m in metrics)
    
    def test_detect_confidence_drift(self):
        """Test confidence drift detection."""
        detector = DriftDetector(reference_confidence=0.75)
        
        current_confidences = np.array([0.70, 0.72, 0.68, 0.71])
        
        metric = detector.detect_confidence_drift(current_confidences, "model-1")
        
        assert metric.model_id == "model-1"
        assert metric.feature_name == "confidence"
        assert metric.confidence_drift is not None
        assert metric.confidence_drift < 0  # Confidence decreased


class TestHealthScore:
    """Test HealthScore calculation."""
    
    def test_healthy_model_scores_above_80(self):
        """Healthy model should score above 80."""
        health_calculator = HealthScore(
            last_retraining_date=datetime(2024, 1, 1)
        )
        
        # Create healthy metrics (low drift)
        feature_metrics = [
            DriftMetrics(
                feature_name="feature1",
                model_id="model-1",
                psi=0.05,
                kl_divergence=0.05,
                mean_shift=0.5,
                timestamp=datetime.utcnow().isoformat(),
            )
        ]
        
        score = health_calculator.calculate(
            feature_metrics=feature_metrics,
        )
        
        assert score > 80
    
    def test_drifted_model_scores_below_50(self):
        """Drifted model should score below 50."""
        health_calculator = HealthScore(
            last_retraining_date=datetime(2020, 1, 1)  # Very old
        )
        
        # Create drifted metrics (high drift)
        feature_metrics = [
            DriftMetrics(
                feature_name="feature1",
                model_id="model-1",
                psi=0.3,
                kl_divergence=0.25,
                mean_shift=4.0,
                timestamp=datetime.utcnow().isoformat(),
            )
        ]
        
        score = health_calculator.calculate(
            feature_metrics=feature_metrics,
        )
        
        assert score < 50
    
    def test_health_score_in_valid_range(self):
        """Score should always be between 0 and 100."""
        health_calculator = HealthScore()
        
        # Test with various metrics
        feature_metrics = [
            DriftMetrics(
                feature_name="feature1",
                model_id="model-1",
                psi=0.2,
                kl_divergence=0.15,
                mean_shift=2.5,
                timestamp=datetime.utcnow().isoformat(),
            )
        ]
        
        score = health_calculator.calculate(
            feature_metrics=feature_metrics,
        )
        
        assert 0 <= score <= 100


class TestDriftAlerts:
    """Test drift alert generation."""
    
    def test_warning_alert_at_psi_0_1(self):
        """Warning alert should trigger at PSI = 0.1."""
        alert_manager = DriftAlertManager()
        
        metrics = DriftMetrics(
            feature_name="feature1",
            model_id="model-1",
            psi=0.12,
            kl_divergence=0.05,
            mean_shift=1.0,
            timestamp=datetime.utcnow().isoformat(),
        )
        
        alerts = alert_manager.check_thresholds(metrics)
        
        warning_alerts = [a for a in alerts if a.level == AlertLevel.WARNING]
        assert len(warning_alerts) > 0
        assert any(a.metric_type == "psi" for a in warning_alerts)
    
    def test_critical_alert_at_psi_0_25(self):
        """Critical alert should trigger at PSI = 0.25."""
        alert_manager = DriftAlertManager()
        
        metrics = DriftMetrics(
            feature_name="feature1",
            model_id="model-1",
            psi=0.3,
            kl_divergence=0.2,
            mean_shift=3.5,
            timestamp=datetime.utcnow().isoformat(),
        )
        
        alerts = alert_manager.check_thresholds(metrics)
        
        critical_alerts = [a for a in alerts if a.level == AlertLevel.CRITICAL]
        assert len(critical_alerts) > 0
        assert any(a.metric_type == "psi" for a in critical_alerts)
    
    def test_no_alerts_below_thresholds(self):
        """No alerts should be generated below thresholds."""
        alert_manager = DriftAlertManager()
        
        metrics = DriftMetrics(
            feature_name="feature1",
            model_id="model-1",
            psi=0.05,
            kl_divergence=0.05,
            mean_shift=1.0,
            timestamp=datetime.utcnow().isoformat(),
        )
        
        alerts = alert_manager.check_thresholds(metrics)
        
        assert len(alerts) == 0
