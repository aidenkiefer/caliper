"""
Recommendation approval queue for Human-in-the-Loop controls.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict
from uuid import uuid4
from pydantic import BaseModel, Field


class RecommendationStatus(str, Enum):
    """Recommendation status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"


class Recommendation(BaseModel):
    """Model recommendation pending human approval."""
    
    recommendation_id: str = Field(default_factory=lambda: str(uuid4()))
    strategy_id: str
    signal: str = Field(description="BUY, SELL, or ABSTAIN")
    symbol: str
    confidence: float = Field(ge=0.0, le=1.0)
    uncertainty: float = Field(ge=0.0)
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    explanation_id: Optional[str] = None
    status: RecommendationStatus = RecommendationStatus.PENDING
    approved_by: Optional[str] = None
    rejected_by: Optional[str] = None
    rationale: Optional[str] = None
    rejection_reason: Optional[str] = None


class RecommendationQueue:
    """
    Manages queue of recommendations pending human approval.
    """
    
    def __init__(self):
        """Initialize recommendation queue."""
        self._queue: Dict[str, Recommendation] = {}
        self._stats: Dict[str, Dict[str, int]] = {}
    
    def add(self, recommendation: Recommendation) -> str:
        """
        Add recommendation to queue.
        
        Args:
            recommendation: Recommendation to add
            
        Returns:
            recommendation_id
        """
        self._queue[recommendation.recommendation_id] = recommendation
        
        # Update stats
        strategy_id = recommendation.strategy_id
        if strategy_id not in self._stats:
            self._stats[strategy_id] = {
                "total": 0,
                "approved": 0,
                "rejected": 0,
                "pending": 0,
            }
        
        self._stats[strategy_id]["total"] += 1
        self._stats[strategy_id]["pending"] += 1
        
        return recommendation.recommendation_id
    
    def approve(self, recommendation_id: str, user_id: str, rationale: Optional[str] = None) -> None:
        """
        Approve a recommendation.
        
        Args:
            recommendation_id: ID of recommendation to approve
            user_id: User who approved
            rationale: Optional rationale for approval
        """
        if recommendation_id not in self._queue:
            raise ValueError(f"Recommendation {recommendation_id} not found")
        
        recommendation = self._queue[recommendation_id]
        recommendation.status = RecommendationStatus.APPROVED
        recommendation.approved_by = user_id
        recommendation.rationale = rationale
        
        # Update stats
        strategy_id = recommendation.strategy_id
        self._stats[strategy_id]["approved"] += 1
        self._stats[strategy_id]["pending"] = max(0, self._stats[strategy_id]["pending"] - 1)
    
    def reject(self, recommendation_id: str, user_id: str, reason: str) -> None:
        """
        Reject a recommendation.
        
        Args:
            recommendation_id: ID of recommendation to reject
            user_id: User who rejected
            reason: Reason for rejection
        """
        if recommendation_id not in self._queue:
            raise ValueError(f"Recommendation {recommendation_id} not found")
        
        recommendation = self._queue[recommendation_id]
        recommendation.status = RecommendationStatus.REJECTED
        recommendation.rejected_by = user_id
        recommendation.rejection_reason = reason
        
        # Update stats
        strategy_id = recommendation.strategy_id
        self._stats[strategy_id]["rejected"] += 1
        self._stats[strategy_id]["pending"] = max(0, self._stats[strategy_id]["pending"] - 1)
    
    def get_pending(self, strategy_id: Optional[str] = None) -> List[Recommendation]:
        """
        Get all pending recommendations.
        
        Args:
            strategy_id: Optional filter by strategy
            
        Returns:
            List of pending recommendations
        """
        pending = [
            rec for rec in self._queue.values()
            if rec.status == RecommendationStatus.PENDING
            and (strategy_id is None or rec.strategy_id == strategy_id)
        ]
        
        return sorted(pending, key=lambda r: r.timestamp, reverse=True)
    
    def get_stats(self, strategy_id: str) -> Dict[str, int]:
        """
        Get statistics for a strategy.
        
        Args:
            strategy_id: Strategy identifier
            
        Returns:
            Dictionary with stats (total, approved, rejected, pending)
        """
        return self._stats.get(strategy_id, {
            "total": 0,
            "approved": 0,
            "rejected": 0,
            "pending": 0,
        })
