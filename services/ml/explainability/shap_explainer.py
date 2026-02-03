"""
SHAP explainer for tree-based models.
"""

import numpy as np
import pandas as pd
from typing import Optional, List
import shap

from .schemas import TradeExplanation, FeatureContribution


class ShapExplainer:
    """
    SHAP explainer for tree-based models (XGBoost, LightGBM, scikit-learn trees).
    """

    def __init__(self, model, feature_names: Optional[List[str]] = None, explainer=None):
        """
        Initialize SHAP explainer.

        Args:
            model: Trained tree-based model (XGBoost, LightGBM, or sklearn)
            feature_names: Optional list of feature names
            explainer: Optional pre-built SHAP explainer (e.g. for tests with mocks)
        """
        self.model = model
        self.feature_names = feature_names
        if explainer is not None:
            self.explainer = explainer
            self.base_value = float(getattr(explainer, "expected_value", 0.0))
        else:
            self.explainer = shap.TreeExplainer(model)
            self.base_value = float(self.explainer.expected_value)

    def explain(
        self,
        X: pd.DataFrame,
        top_n: int = 10,
        signal: str = "BUY",
        confidence: float = 0.0,
        trade_id: str = "",
        model_id: str = "",
    ) -> TradeExplanation:
        """
        Generate SHAP explanation for prediction.

        Args:
            X: Feature dataframe (single row or multiple rows)
            top_n: Number of top features to return
            signal: Trading signal (BUY/SELL/ABSTAIN)
            confidence: Model confidence
            trade_id: Trade identifier
            model_id: Model identifier

        Returns:
            TradeExplanation with top features
        """
        # Ensure X is a DataFrame
        if isinstance(X, np.ndarray):
            if self.feature_names:
                X = pd.DataFrame(X, columns=self.feature_names)
            else:
                X = pd.DataFrame(X)

        # Calculate SHAP values
        shap_values = self.explainer.shap_values(X)

        # Handle multi-class case (shap_values is list) vs binary (shap_values is array)
        if isinstance(shap_values, list):
            # Multi-class: use the class corresponding to the signal
            # For simplicity, use first class (can be enhanced)
            shap_values = shap_values[0]

        # For single prediction, get first row
        if len(X) == 1:
            shap_values_single = shap_values[0] if len(shap_values.shape) > 1 else shap_values
            feature_values = X.iloc[0].values
        else:
            # Average across rows
            shap_values_single = (
                np.mean(shap_values, axis=0) if len(shap_values.shape) > 1 else shap_values
            )
            feature_values = X.mean().values

        # Get feature names
        if self.feature_names:
            feature_names_list = self.feature_names
        else:
            feature_names_list = X.columns.tolist()

        # Create feature contributions
        contributions = []
        for i, (name, value, shap_val) in enumerate(
            zip(feature_names_list, feature_values, shap_values_single)
        ):
            contributions.append(
                FeatureContribution(
                    feature_name=name,
                    value=float(value),
                    contribution=float(shap_val),
                    direction="positive" if shap_val > 0 else "negative",
                )
            )

        # Sort by absolute contribution and take top N
        contributions.sort(key=lambda x: abs(x.contribution), reverse=True)
        top_features = contributions[:top_n]

        return TradeExplanation(
            trade_id=trade_id,
            signal=signal,
            confidence=confidence,
            top_features=top_features,
            model_id=model_id,
            base_value=self.base_value,
        )
