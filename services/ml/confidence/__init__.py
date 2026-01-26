"""
Confidence Gating & Abstention Logic

Enables models to explicitly choose not to trade when confidence is low.
"""

from .gating import ConfidenceGating, ConfidenceConfig
from .abstention import AbstentionDecision
from .uncertainty import calculate_entropy, calculate_ensemble_disagreement

__all__ = [
    "ConfidenceGating",
    "ConfidenceConfig",
    "AbstentionDecision",
    "calculate_entropy",
    "calculate_ensemble_disagreement",
]
