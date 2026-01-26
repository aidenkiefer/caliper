"""
Permutation importance as fallback explainer for non-tree models.
"""

import numpy as np
import pandas as pd
from typing import List, Optional
from sklearn.inspection import permutation_importance

from .schemas import TradeExplanation, FeatureContribution


class PermutationImportanceExplainer:
    """
    Permutation importance explainer (fallback for non-tree models).
    """
    
    def __init__(self, model, scoring: str = "neg_mean_squared_error"):
        """
        Initialize permutation importance explainer.
        
        Args:
            model: Trained model (any sklearn-compatible model)
            scoring: Scoring function for permutation importance
        """
        self.model = model
        self.scoring = scoring
    
    def explain(
        self,
        X: pd.DataFrame,
        y: Optional[np.ndarray] = None,
        top_n: int = 10,
        signal: str = "BUY",
        confidence: float = 0.0,
        trade_id: str = "",
        model_id: str = "",
        n_repeats: int = 10,
    ) -> TradeExplanation:
        """
        Generate explanation using permutation importance.
        
        Args:
            X: Feature dataframe
            y: Target values (optional, for supervised importance)
            top_n: Number of top features to return
            signal: Trading signal
            confidence: Model confidence
            trade_id: Trade identifier
            model_id: Model identifier
            n_repeats: Number of permutation repeats
            
        Returns:
            TradeExplanation with top features
        """
        # If no target, use model predictions as proxy
        if y is None:
            y = self.model.predict(X)
        
        # Calculate permutation importance
        perm_importance = permutation_importance(
            self.model,
            X.values,
            y,
            scoring=self.scoring,
            n_repeats=n_repeats,
            random_state=42,
            n_jobs=-1,
        )
        
        # Get feature names
        feature_names = X.columns.tolist()
        
        # Create feature contributions
        contributions = []
        for i, (name, importance_mean, importance_std) in enumerate(zip(
            feature_names,
            perm_importance.importances_mean,
            perm_importance.importances_std,
        )):
            # Use mean importance as contribution
            # Direction is always positive for permutation importance
            contributions.append(FeatureContribution(
                feature_name=name,
                value=float(X.iloc[0, i]) if len(X) == 1 else float(X.mean().iloc[i]),
                contribution=float(importance_mean),
                direction="positive",  # Permutation importance is always positive
            ))
        
        # Sort by absolute contribution and take top N
        contributions.sort(key=lambda x: abs(x.contribution), reverse=True)
        top_features = contributions[:top_n]
        
        return TradeExplanation(
            trade_id=trade_id,
            signal=signal,
            confidence=confidence,
            top_features=top_features,
            model_id=model_id,
        )
