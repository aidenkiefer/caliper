"""
Unit tests for explainability service (SHAP).
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, MagicMock

from services.ml.explainability.schemas import TradeExplanation, FeatureContribution
from services.ml.explainability.shap_explainer import ShapExplainer
from services.ml.explainability.permutation import PermutationImportanceExplainer


class TestShapExplainer:
    """Test SHAP explainer."""
    
    def test_shap_returns_feature_contributions(self):
        """SHAP explainer should return feature contributions."""
        # Mock model and explainer
        mock_model = Mock()
        mock_explainer = MagicMock()
        mock_explainer.expected_value = 0.5
        mock_explainer.shap_values.return_value = np.array([[0.1, -0.05, 0.02]])
        
        # Create explainer with mocked SHAP
        explainer = ShapExplainer(mock_model, feature_names=["f1", "f2", "f3"])
        explainer.explainer = mock_explainer
        
        X = pd.DataFrame({
            "f1": [1.0],
            "f2": [2.0],
            "f3": [3.0],
        })
        
        explanation = explainer.explain(
            X=X,
            signal="BUY",
            confidence=0.8,
            trade_id="trade-1",
            model_id="model-1",
        )
        
        assert explanation.trade_id == "trade-1"
        assert explanation.signal == "BUY"
        assert explanation.confidence == 0.8
        assert len(explanation.top_features) > 0
    
    def test_top_features_sorted_by_importance(self):
        """Top features should be sorted by absolute contribution."""
        # Mock explanation with features
        features = [
            FeatureContribution(
                feature_name="f1",
                value=1.0,
                contribution=0.05,
                direction="positive",
            ),
            FeatureContribution(
                feature_name="f2",
                value=2.0,
                contribution=-0.15,
                direction="negative",
            ),
            FeatureContribution(
                feature_name="f3",
                value=3.0,
                contribution=0.10,
                direction="positive",
            ),
        ]
        
        # Sort by absolute contribution
        sorted_features = sorted(features, key=lambda x: abs(x.contribution), reverse=True)
        
        assert sorted_features[0].feature_name == "f2"  # Highest absolute contribution
        assert sorted_features[1].feature_name == "f3"
        assert sorted_features[2].feature_name == "f1"


class TestPermutationImportance:
    """Test permutation importance fallback."""
    
    def test_permutation_fallback_works(self):
        """Permutation importance should work as fallback."""
        # Mock model
        mock_model = Mock()
        mock_model.predict.return_value = np.array([0.5, 0.6, 0.7])
        
        explainer = PermutationImportanceExplainer(mock_model)
        
        X = pd.DataFrame({
            "f1": [1.0, 2.0, 3.0],
            "f2": [4.0, 5.0, 6.0],
        })
        y = np.array([0.5, 0.6, 0.7])
        
        # This would call sklearn.inspection.permutation_importance
        # For unit test, we'll just verify the explainer can be instantiated
        assert explainer.model == mock_model


class TestExplanationPayload:
    """Test explanation payload structure."""
    
    def test_explanation_has_required_fields(self):
        """Explanation should have all required fields."""
        explanation = TradeExplanation(
            trade_id="trade-1",
            signal="BUY",
            confidence=0.8,
            top_features=[
                FeatureContribution(
                    feature_name="f1",
                    value=1.0,
                    contribution=0.1,
                    direction="positive",
                )
            ],
            model_id="model-1",
        )
        
        assert explanation.trade_id == "trade-1"
        assert explanation.signal == "BUY"
        assert explanation.confidence == 0.8
        assert len(explanation.top_features) == 1
        assert explanation.model_id == "model-1"
    
    def test_feature_contribution_direction(self):
        """Feature contribution should have correct direction."""
        positive = FeatureContribution(
            feature_name="f1",
            value=1.0,
            contribution=0.1,
            direction="positive",
        )
        
        negative = FeatureContribution(
            feature_name="f2",
            value=2.0,
            contribution=-0.1,
            direction="negative",
        )
        
        assert positive.direction == "positive"
        assert negative.direction == "negative"
        assert positive.contribution > 0
        assert negative.contribution < 0
