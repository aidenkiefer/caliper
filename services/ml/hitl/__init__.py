"""
Human-in-the-Loop (HITL) Controls

Manages approval queue for model recommendations and human decision logging.
"""

from .approval_queue import RecommendationQueue, Recommendation, RecommendationStatus

__all__ = [
    "RecommendationQueue",
    "Recommendation",
    "RecommendationStatus",
]
