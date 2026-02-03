"""
Drift detector for monitoring feature and prediction drift.
"""

import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
from .metrics import DriftMetrics, calculate_psi, calculate_kl_divergence, calculate_mean_shift


class DriftDetector:
    """
    Detects drift in feature distributions and model predictions.
    """

    def __init__(
        self,
        reference_features: Optional[Dict[str, np.ndarray]] = None,
        reference_confidence: Optional[float] = None,
    ):
        """
        Initialize drift detector with reference data.

        Args:
            reference_features: Dict mapping feature names to reference distributions
            reference_confidence: Baseline confidence from training
        """
        self.reference_features = reference_features or {}
        self.reference_confidence = reference_confidence

    def detect_feature_drift(
        self,
        current_features: Dict[str, np.ndarray],
        model_id: str,
    ) -> List[DriftMetrics]:
        """
        Detect drift for each feature.

        Args:
            current_features: Dict mapping feature names to current distributions
            model_id: Model identifier

        Returns:
            List of DriftMetrics, one per feature
        """
        metrics_list = []

        for feature_name, current_values in current_features.items():
            if feature_name not in self.reference_features:
                continue

            reference_values = self.reference_features[feature_name]

            # Calculate drift metrics
            psi = calculate_psi(reference_values, current_values)
            kl_div = calculate_kl_divergence(reference_values, current_values)
            mean_shift = calculate_mean_shift(reference_values, current_values)

            metrics = DriftMetrics(
                feature_name=feature_name,
                model_id=model_id,
                psi=psi,
                kl_divergence=kl_div,
                mean_shift=mean_shift,
                timestamp=datetime.utcnow().isoformat(),
            )

            metrics_list.append(metrics)

        return metrics_list

    def detect_confidence_drift(
        self,
        current_confidences: np.ndarray,
        model_id: str,
    ) -> DriftMetrics:
        """
        Detect drift in prediction confidence.

        Args:
            current_confidences: Array of current prediction confidences
            model_id: Model identifier

        Returns:
            DriftMetrics with confidence_drift populated
        """
        if self.reference_confidence is None:
            # Use mean of current as baseline if no reference
            self.reference_confidence = float(np.mean(current_confidences))

        current_mean = float(np.mean(current_confidences))
        confidence_drift = current_mean - self.reference_confidence

        # Calculate distribution drift for confidence values
        reference_array = np.full(len(current_confidences), self.reference_confidence)
        psi = calculate_psi(reference_array, current_confidences)
        kl_div = calculate_kl_divergence(reference_array, current_confidences)
        mean_shift = calculate_mean_shift(reference_array, current_confidences)

        return DriftMetrics(
            feature_name="confidence",
            model_id=model_id,
            psi=psi,
            kl_divergence=kl_div,
            mean_shift=mean_shift,
            confidence_drift=confidence_drift,
            timestamp=datetime.utcnow().isoformat(),
        )

    def detect_error_drift(
        self,
        reference_errors: np.ndarray,
        current_errors: np.ndarray,
        model_id: str,
    ) -> DriftMetrics:
        """
        Detect drift in prediction errors (when ground truth available).

        Args:
            reference_errors: Reference error distribution (from validation)
            current_errors: Current error distribution
            model_id: Model identifier

        Returns:
            DriftMetrics with error_drift populated
        """
        psi = calculate_psi(reference_errors, current_errors)
        kl_div = calculate_kl_divergence(reference_errors, current_errors)
        mean_shift = calculate_mean_shift(reference_errors, current_errors)

        # Calculate mean error change
        ref_mean_error = float(np.mean(reference_errors))
        curr_mean_error = float(np.mean(current_errors))
        error_drift = curr_mean_error - ref_mean_error

        return DriftMetrics(
            feature_name="error",
            model_id=model_id,
            psi=psi,
            kl_divergence=kl_div,
            mean_shift=mean_shift,
            error_drift=error_drift,
            timestamp=datetime.utcnow().isoformat(),
        )
