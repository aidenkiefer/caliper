"""
Threshold-based alerts for drift detection.
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel
from .metrics import DriftMetrics


class AlertLevel(str, Enum):
    """Alert severity levels."""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class DriftAlert(BaseModel):
    """Drift alert."""
    
    level: AlertLevel
    model_id: str
    feature_name: Optional[str] = None
    metric_type: str  # "psi", "kl_divergence", "mean_shift", "confidence_drift", "error_drift"
    value: float
    threshold: float
    message: str
    timestamp: str


class DriftAlertManager:
    """
    Manages threshold-based alerts for drift metrics.
    """
    
    # Thresholds
    PSI_WARNING = 0.1
    PSI_CRITICAL = 0.25
    KL_WARNING = 0.1
    KL_CRITICAL = 0.2
    MEAN_SHIFT_WARNING = 2.0
    MEAN_SHIFT_CRITICAL = 3.0
    CONFIDENCE_DRIFT_WARNING = 0.10  # 10 percentage points
    CONFIDENCE_DRIFT_CRITICAL = 0.20  # 20 percentage points
    
    def check_thresholds(self, metrics: DriftMetrics) -> List[DriftAlert]:
        """
        Check metrics against thresholds and generate alerts.
        
        Args:
            metrics: DriftMetrics to check
            
        Returns:
            List of alerts (empty if no thresholds exceeded)
        """
        alerts = []
        timestamp = metrics.timestamp
        
        # PSI alerts
        if metrics.psi >= self.PSI_CRITICAL:
            alerts.append(DriftAlert(
                level=AlertLevel.CRITICAL,
                model_id=metrics.model_id,
                feature_name=metrics.feature_name,
                metric_type="psi",
                value=metrics.psi,
                threshold=self.PSI_CRITICAL,
                message=f"Critical PSI drift detected: {metrics.psi:.3f} (threshold: {self.PSI_CRITICAL})",
                timestamp=timestamp,
            ))
        elif metrics.psi >= self.PSI_WARNING:
            alerts.append(DriftAlert(
                level=AlertLevel.WARNING,
                model_id=metrics.model_id,
                feature_name=metrics.feature_name,
                metric_type="psi",
                value=metrics.psi,
                threshold=self.PSI_WARNING,
                message=f"Warning: PSI drift detected: {metrics.psi:.3f} (threshold: {self.PSI_WARNING})",
                timestamp=timestamp,
            ))
        
        # KL divergence alerts
        if metrics.kl_divergence >= self.KL_CRITICAL:
            alerts.append(DriftAlert(
                level=AlertLevel.CRITICAL,
                model_id=metrics.model_id,
                feature_name=metrics.feature_name,
                metric_type="kl_divergence",
                value=metrics.kl_divergence,
                threshold=self.KL_CRITICAL,
                message=f"Critical KL divergence detected: {metrics.kl_divergence:.3f} (threshold: {self.KL_CRITICAL})",
                timestamp=timestamp,
            ))
        elif metrics.kl_divergence >= self.KL_WARNING:
            alerts.append(DriftAlert(
                level=AlertLevel.WARNING,
                model_id=metrics.model_id,
                feature_name=metrics.feature_name,
                metric_type="kl_divergence",
                value=metrics.kl_divergence,
                threshold=self.KL_WARNING,
                message=f"Warning: KL divergence detected: {metrics.kl_divergence:.3f} (threshold: {self.KL_WARNING})",
                timestamp=timestamp,
            ))
        
        # Mean shift alerts
        abs_mean_shift = abs(metrics.mean_shift)
        if abs_mean_shift >= self.MEAN_SHIFT_CRITICAL:
            alerts.append(DriftAlert(
                level=AlertLevel.CRITICAL,
                model_id=metrics.model_id,
                feature_name=metrics.feature_name,
                metric_type="mean_shift",
                value=metrics.mean_shift,
                threshold=self.MEAN_SHIFT_CRITICAL,
                message=f"Critical mean shift detected: {metrics.mean_shift:.2f} std dev (threshold: {self.MEAN_SHIFT_CRITICAL})",
                timestamp=timestamp,
            ))
        elif abs_mean_shift >= self.MEAN_SHIFT_WARNING:
            alerts.append(DriftAlert(
                level=AlertLevel.WARNING,
                model_id=metrics.model_id,
                feature_name=metrics.feature_name,
                metric_type="mean_shift",
                value=metrics.mean_shift,
                threshold=self.MEAN_SHIFT_WARNING,
                message=f"Warning: Mean shift detected: {metrics.mean_shift:.2f} std dev (threshold: {self.MEAN_SHIFT_WARNING})",
                timestamp=timestamp,
            ))
        
        # Confidence drift alerts
        if metrics.confidence_drift is not None:
            abs_confidence_drift = abs(metrics.confidence_drift)
            if abs_confidence_drift >= self.CONFIDENCE_DRIFT_CRITICAL:
                alerts.append(DriftAlert(
                    level=AlertLevel.CRITICAL,
                    model_id=metrics.model_id,
                    feature_name=metrics.feature_name,
                    metric_type="confidence_drift",
                    value=metrics.confidence_drift,
                    threshold=self.CONFIDENCE_DRIFT_CRITICAL,
                    message=f"Critical confidence drift detected: {metrics.confidence_drift:.2%} (threshold: {self.CONFIDENCE_DRIFT_CRITICAL:.2%})",
                    timestamp=timestamp,
                ))
            elif abs_confidence_drift >= self.CONFIDENCE_DRIFT_WARNING:
                alerts.append(DriftAlert(
                    level=AlertLevel.WARNING,
                    model_id=metrics.model_id,
                    feature_name=metrics.feature_name,
                    metric_type="confidence_drift",
                    value=metrics.confidence_drift,
                    threshold=self.CONFIDENCE_DRIFT_WARNING,
                    message=f"Warning: Confidence drift detected: {metrics.confidence_drift:.2%} (threshold: {self.CONFIDENCE_DRIFT_WARNING:.2%})",
                    timestamp=timestamp,
                ))
        
        # Error drift alerts (use same thresholds as PSI)
        if metrics.error_drift is not None:
            # For error drift, we care about the PSI of error distribution
            if metrics.psi >= self.PSI_CRITICAL:
                alerts.append(DriftAlert(
                    level=AlertLevel.CRITICAL,
                    model_id=metrics.model_id,
                    feature_name=metrics.feature_name,
                    metric_type="error_drift",
                    value=metrics.error_drift,
                    threshold=self.PSI_CRITICAL,
                    message=f"Critical error drift detected: mean error change = {metrics.error_drift:.4f}",
                    timestamp=timestamp,
                ))
        
        return alerts
