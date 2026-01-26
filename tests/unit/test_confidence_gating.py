"""
Unit tests for confidence gating and abstention logic.
"""

import pytest
import numpy as np
from services.ml.confidence.gating import (
    ConfidenceGating,
    ConfidenceConfig,
    ModelOutput,
    Signal,
    ConfidenceLevel,
)
from services.ml.confidence.uncertainty import (
    calculate_entropy,
    calculate_ensemble_disagreement,
)
from services.ml.confidence.abstention import AbstentionTracker


class TestConfidenceThresholds:
    """Test confidence threshold logic."""
    
    def test_abstain_below_threshold(self):
        """Confidence < 0.55 should ABSTAIN."""
        config = ConfidenceConfig(
            strategy_id="strategy-1",
            abstain_threshold=0.55,
        )
        gating = ConfidenceGating(config)
        
        output = gating.apply_gating(
            raw_signal="BUY",
            confidence=0.50,
            uncertainty=0.3,
            features_used=["feature1"],
        )
        
        assert output.signal == "ABSTAIN"
    
    def test_low_confidence_band(self):
        """Confidence 0.55-0.65 is LOW_CONFIDENCE."""
        config = ConfidenceConfig(
            strategy_id="strategy-1",
            low_confidence_threshold=0.65,
        )
        gating = ConfidenceGating(config)
        
        level = gating.get_confidence_level(0.60)
        
        assert level == ConfidenceLevel.LOW
    
    def test_normal_confidence_band(self):
        """Confidence 0.65-0.85 is NORMAL."""
        config = ConfidenceConfig(
            strategy_id="strategy-1",
            low_confidence_threshold=0.65,
            high_confidence_threshold=0.85,
        )
        gating = ConfidenceGating(config)
        
        level = gating.get_confidence_level(0.75)
        
        assert level == ConfidenceLevel.NORMAL
    
    def test_high_confidence_band(self):
        """Confidence > 0.85 is HIGH_CONFIDENCE."""
        config = ConfidenceConfig(
            strategy_id="strategy-1",
            high_confidence_threshold=0.85,
        )
        gating = ConfidenceGating(config)
        
        level = gating.get_confidence_level(0.90)
        
        assert level == ConfidenceLevel.HIGH
    
    def test_should_abstain_returns_true_below_threshold(self):
        """should_abstain should return True when confidence is low."""
        config = ConfidenceConfig(
            strategy_id="strategy-1",
            abstain_threshold=0.55,
        )
        gating = ConfidenceGating(config)
        
        assert gating.should_abstain(0.50) is True
        assert gating.should_abstain(0.60) is False


class TestUncertaintyMeasures:
    """Test uncertainty calculation."""
    
    def test_entropy_calculation(self):
        """Test entropy calculation from probabilities."""
        # Uniform distribution (maximum entropy)
        uniform = np.array([0.5, 0.5])
        entropy_uniform = calculate_entropy(uniform)
        
        # Certain distribution (minimum entropy)
        certain = np.array([1.0, 0.0])
        entropy_certain = calculate_entropy(certain)
        
        assert entropy_uniform > entropy_certain
        assert entropy_certain == pytest.approx(0.0, abs=0.01)
    
    def test_ensemble_disagreement(self):
        """Test ensemble disagreement calculation."""
        # High agreement
        high_agreement = [0.75, 0.76, 0.74, 0.75]
        disagreement_high = calculate_ensemble_disagreement(high_agreement)
        
        # Low agreement
        low_agreement = [0.3, 0.7, 0.4, 0.6]
        disagreement_low = calculate_ensemble_disagreement(low_agreement)
        
        assert disagreement_low > disagreement_high


class TestAbstentionTracker:
    """Test abstention tracking."""
    
    def test_record_signal_tracks_abstentions(self):
        """Tracker should count abstentions correctly."""
        tracker = AbstentionTracker("strategy-1")
        
        tracker.record_signal("BUY")
        tracker.record_signal("ABSTAIN")
        tracker.record_signal("SELL")
        tracker.record_signal("ABSTAIN")
        
        metrics = tracker.get_metrics()
        
        assert metrics.total_signals == 4
        assert metrics.abstentions == 2
        assert metrics.abstention_rate == pytest.approx(0.5)
    
    def test_abstention_rate_calculation(self):
        """Abstention rate should be calculated correctly."""
        tracker = AbstentionTracker("strategy-1")
        
        # 3 abstentions out of 10 signals
        for _ in range(7):
            tracker.record_signal("BUY")
        for _ in range(3):
            tracker.record_signal("ABSTAIN")
        
        metrics = tracker.get_metrics()
        
        assert metrics.abstention_rate == pytest.approx(0.3)


class TestBacktestAbstention:
    """Test abstention handling in backtest context."""
    
    def test_abstention_tracked_in_backtest(self):
        """Abstentions should be tracked during backtest."""
        # This would be tested in integration tests with actual backtest engine
        # For unit tests, we verify the tracker works
        tracker = AbstentionTracker("strategy-1")
        
        # Simulate backtest signals
        signals = ["BUY", "ABSTAIN", "SELL", "ABSTAIN", "BUY"]
        for signal in signals:
            tracker.record_signal(signal)
        
        metrics = tracker.get_metrics()
        
        assert metrics.abstentions == 2
        assert metrics.total_signals == 5
