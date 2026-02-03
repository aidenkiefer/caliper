"""
Model health score calculation based on drift metrics.
"""

from typing import List, Optional
from datetime import datetime, timedelta
from .metrics import DriftMetrics


class HealthScore:
    """
    Calculates a composite health score (0-100) from drift metrics.

    Components:
    - Feature drift (30%): Average PSI across features
    - Confidence drift (30%): Drift in prediction confidence
    - Error drift (20%): Drift in prediction errors (if available)
    - Staleness (20%): Time since last retraining
    """

    # Thresholds for health score components
    PSI_WARNING = 0.1
    PSI_CRITICAL = 0.25
    KL_WARNING = 0.1
    KL_CRITICAL = 0.2
    MEAN_SHIFT_WARNING = 2.0
    MEAN_SHIFT_CRITICAL = 3.0

    def __init__(
        self,
        last_retraining_date: Optional[datetime] = None,
        max_staleness_days: int = 90,
    ):
        """
        Initialize health score calculator.

        Args:
            last_retraining_date: When model was last retrained
            max_staleness_days: Days after which staleness score = 0
        """
        self.last_retraining_date = last_retraining_date
        self.max_staleness_days = max_staleness_days

    def calculate(
        self,
        feature_metrics: List[DriftMetrics],
        confidence_metric: Optional[DriftMetrics] = None,
        error_metric: Optional[DriftMetrics] = None,
    ) -> float:
        """
        Calculate composite health score (0-100).

        Args:
            feature_metrics: List of drift metrics for features
            confidence_metric: Drift metric for confidence (optional)
            error_metric: Drift metric for errors (optional)

        Returns:
            Health score between 0 and 100
        """
        # Feature drift component (30%)
        feature_score = self._calculate_feature_score(feature_metrics)

        # Confidence drift component (30%)
        confidence_score = self._calculate_confidence_score(confidence_metric)

        # Error drift component (20%)
        error_score = self._calculate_error_score(error_metric)

        # Staleness component (20%)
        staleness_score = self._calculate_staleness_score()

        # Weighted average
        health_score = (
            feature_score * 0.30
            + confidence_score * 0.30
            + error_score * 0.20
            + staleness_score * 0.20
        )

        return max(0.0, min(100.0, health_score))

    def _calculate_feature_score(self, metrics: List[DriftMetrics]) -> float:
        """Calculate feature drift score (0-100)."""
        if not metrics:
            return 50.0  # Neutral if no features

        # Average PSI across features
        avg_psi = sum(m.psi for m in metrics) / len(metrics)
        avg_kl = sum(m.kl_divergence for m in metrics) / len(metrics)
        avg_mean_shift = sum(abs(m.mean_shift) for m in metrics) / len(metrics)

        # Score based on thresholds
        psi_score = self._score_from_threshold(avg_psi, self.PSI_WARNING, self.PSI_CRITICAL)
        kl_score = self._score_from_threshold(avg_kl, self.KL_WARNING, self.KL_CRITICAL)
        mean_shift_score = self._score_from_threshold(
            avg_mean_shift, self.MEAN_SHIFT_WARNING, self.MEAN_SHIFT_CRITICAL
        )

        # Average of three metrics
        return (psi_score + kl_score + mean_shift_score) / 3.0

    def _calculate_confidence_score(self, metric: Optional[DriftMetrics]) -> float:
        """Calculate confidence drift score (0-100)."""
        if metric is None:
            return 50.0  # Neutral if no confidence data

        # Use PSI and mean shift for confidence
        psi_score = self._score_from_threshold(metric.psi, self.PSI_WARNING, self.PSI_CRITICAL)
        mean_shift_score = self._score_from_threshold(
            abs(metric.mean_shift), self.MEAN_SHIFT_WARNING, self.MEAN_SHIFT_CRITICAL
        )

        return (psi_score + mean_shift_score) / 2.0

    def _calculate_error_score(self, metric: Optional[DriftMetrics]) -> float:
        """Calculate error drift score (0-100)."""
        if metric is None:
            return 50.0  # Neutral if no error data

        # Use PSI for error distribution
        return self._score_from_threshold(metric.psi, self.PSI_WARNING, self.PSI_CRITICAL)

    def _calculate_staleness_score(self) -> float:
        """Calculate staleness score (0-100) based on time since retraining."""
        if self.last_retraining_date is None:
            return 50.0  # Neutral if unknown

        days_since = (datetime.utcnow() - self.last_retraining_date).days

        if days_since < 7:
            return 100.0
        elif days_since < 30:
            return 80.0
        elif days_since < 60:
            return 60.0
        elif days_since < self.max_staleness_days:
            # Linear decay from 60 to 0
            progress = (days_since - 60) / (self.max_staleness_days - 60)
            return 60.0 * (1 - progress)
        else:
            return 0.0

    def _score_from_threshold(self, value: float, warning: float, critical: float) -> float:
        """
        Convert metric value to score (0-100) based on thresholds.

        - value < warning: 100 (healthy)
        - warning <= value < critical: Linear decay 100 -> 50
        - value >= critical: Linear decay 50 -> 0
        """
        if value < warning:
            return 100.0
        elif value < critical:
            # Linear interpolation between 100 and 50
            progress = (value - warning) / (critical - warning)
            return 100.0 - (50.0 * progress)
        else:
            # Linear decay from 50 to 0
            # Assume critical * 2 is the maximum we care about
            max_value = critical * 2
            if value >= max_value:
                return 0.0
            progress = (value - critical) / (max_value - critical)
            return 50.0 * (1 - progress)
