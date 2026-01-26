"""
Local Explainability for Trade Recommendations

Provides human-readable explanations for model predictions using SHAP.
"""

from .shap_explainer import ShapExplainer
from .permutation import PermutationImportanceExplainer
from .schemas import TradeExplanation, FeatureContribution

__all__ = [
    "ShapExplainer",
    "PermutationImportanceExplainer",
    "TradeExplanation",
    "FeatureContribution",
]
