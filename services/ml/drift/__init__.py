"""
Model Drift & Decay Detection

Detects when model performance degrades due to:
- Feature distribution drift (PSI, KL divergence, mean shift)
- Prediction confidence drift
- Error drift (when ground truth available)
"""

from .detector import DriftDetector
from .metrics import DriftMetrics, calculate_psi, calculate_kl_divergence, calculate_mean_shift
from .health_score import HealthScore
from .alerts import DriftAlert, AlertLevel, DriftAlertManager

__all__ = [
    "DriftDetector",
    "DriftMetrics",
    "calculate_psi",
    "calculate_kl_divergence",
    "calculate_mean_shift",
    "HealthScore",
    "DriftAlert",
    "AlertLevel",
    "DriftAlertManager",
]
