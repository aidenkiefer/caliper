"""
Simple text-based explainer for ML predictions.

Provides human-readable explanations without advanced techniques
(SHAP, permutation importance). Suitable for Sprint 7 initial explainability.

Sprint 8 will add SHAP and permutation importance.
"""

from typing import Dict, Any, List
from datetime import datetime

from packages.common.ml_schemas import ModelInferenceOutput


class SimpleExplainer:
    """
    Generate simple text-based explanations for model predictions.

    Explanation includes:
    - Features used
    - Confidence level
    - Rationale (template-based human-readable text)
    - Signal direction
    """

    def __init__(self, feature_names: List[str], model_type: str = "unknown"):
        """
        Initialize explainer.

        Args:
            feature_names: List of feature names used by model
            model_type: Type of model (e.g., "LogisticRegression")
        """
        self.feature_names = feature_names
        self.model_type = model_type

    def explain(
        self,
        features: Dict[str, float],
        inference_output: ModelInferenceOutput,
        symbol: str,
        timestamp: datetime,
    ) -> Dict[str, Any]:
        """
        Generate explanation for a prediction.

        Args:
            features: Feature dictionary used for prediction
            inference_output: Model inference output (signal, confidence, etc.)
            symbol: Trading symbol
            timestamp: Prediction timestamp

        Returns:
            Explanation dictionary with human-readable fields
        """
        # Extract key features for display (top 5 by absolute value)
        top_features = self._get_top_features(features, n=5)

        # Generate confidence description
        confidence_desc = self._confidence_description(inference_output.confidence)

        # Generate rationale
        rationale = self._generate_rationale(
            signal=inference_output.signal,
            confidence=inference_output.confidence,
            top_features=top_features,
            abstain_reason=inference_output.abstain_reason,
        )

        return {
            "features_used": self.feature_names,
            "top_features": top_features,
            "signal": inference_output.signal,
            "confidence": inference_output.confidence,
            "confidence_description": confidence_desc,
            "uncertainty": inference_output.uncertainty,
            "rationale": rationale,
            "model_type": self.model_type,
            "symbol": symbol,
            "timestamp": timestamp.isoformat(),
        }

    def _get_top_features(self, features: Dict[str, float], n: int = 5) -> List[Dict[str, Any]]:
        """
        Get top N features by absolute value for display.

        Args:
            features: Feature dictionary
            n: Number of top features to return

        Returns:
            List of feature dicts with name and value
        """
        # Sort by absolute value
        sorted_features = sorted(
            features.items(), key=lambda x: abs(x[1]) if x[1] is not None else 0, reverse=True
        )

        # Take top N
        top_n = sorted_features[:n]

        return [
            {
                "name": name,
                "value": float(value) if value is not None else None,
            }
            for name, value in top_n
        ]

    def _confidence_description(self, confidence: float) -> str:
        """
        Convert confidence score to human-readable description.

        Args:
            confidence: Confidence score (0.0 to 1.0)

        Returns:
            Human-readable confidence description
        """
        if confidence >= 0.85:
            return "high"
        elif confidence >= 0.65:
            return "normal"
        elif confidence >= 0.55:
            return "low"
        else:
            return "very low (abstain)"

    def _generate_rationale(
        self,
        signal: str,
        confidence: float,
        top_features: List[Dict[str, Any]],
        abstain_reason: str = None,
    ) -> str:
        """
        Generate human-readable rationale for prediction.

        Args:
            signal: Signal (BUY/SELL/ABSTAIN)
            confidence: Confidence score
            top_features: Top features by value
            abstain_reason: Reason for abstention if applicable

        Returns:
            Rationale text
        """
        if signal == "ABSTAIN":
            return f"Model chose to ABSTAIN: {abstain_reason}"

        # Build rationale
        direction = "upward" if signal == "BUY" else "downward"
        confidence_pct = confidence * 100

        rationale_parts = [
            f"Model predicts {direction} movement with {confidence_pct:.1f}% confidence.",
        ]

        # Add top feature context
        if top_features:
            feature_names = [f["name"] for f in top_features[:3]]
            rationale_parts.append(f"Key indicators: {', '.join(feature_names)}.")

        return " ".join(rationale_parts)
