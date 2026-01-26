"""
Pydantic schemas for ML Safety & Interpretability features.

These schemas are used across ML services and API endpoints.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


# ============================================================================
# Drift Detection Schemas
# ============================================================================

class DriftMetricsResponse(BaseModel):
    """Drift metrics API response."""
    
    model_id: str
    feature_metrics: List[dict] = Field(description="Drift metrics per feature")
    confidence_metric: Optional[dict] = Field(None, description="Confidence drift metric")
    error_metric: Optional[dict] = Field(None, description="Error drift metric")
    timestamp: str


class HealthScoreResponse(BaseModel):
    """Model health score API response."""
    
    model_id: str
    health_score: float = Field(ge=0, le=100, description="Health score 0-100")
    components: dict = Field(description="Component scores (feature, confidence, error, staleness)")
    timestamp: str


# ============================================================================
# Confidence Gating Schemas
# ============================================================================

class ConfidenceConfigResponse(BaseModel):
    """Confidence configuration API response."""
    
    strategy_id: str
    abstain_threshold: float
    low_confidence_threshold: float
    high_confidence_threshold: float


class ConfidenceConfigUpdate(BaseModel):
    """Update confidence configuration."""
    
    abstain_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    low_confidence_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    high_confidence_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)


# ============================================================================
# Explainability Schemas
# ============================================================================

class FeatureContributionResponse(BaseModel):
    """Feature contribution in explanation."""
    
    feature_name: str
    value: float
    contribution: float
    direction: Literal["positive", "negative"]


class TradeExplanationResponse(BaseModel):
    """Trade explanation API response."""
    
    trade_id: str
    timestamp: str
    signal: str
    confidence: float
    top_features: List[FeatureContributionResponse]
    model_id: str
    base_value: Optional[float] = None


# ============================================================================
# Baselines & Regret Schemas
# ============================================================================

class BaselineComparisonResponse(BaseModel):
    """Baseline comparison API response."""
    
    strategy_id: str
    strategy_return: Decimal
    baseline_returns: dict = Field(description="Returns for each baseline")
    regret_metrics: dict = Field(description="Regret vs each baseline")
    outperforms: dict = Field(description="Whether strategy outperforms each baseline")


# ============================================================================
# Human-in-the-Loop Schemas
# ============================================================================

class RecommendationResponse(BaseModel):
    """Recommendation in approval queue."""
    
    recommendation_id: str
    strategy_id: str
    signal: Literal["BUY", "SELL", "ABSTAIN"]
    symbol: str
    confidence: float
    uncertainty: float
    timestamp: str
    explanation_id: Optional[str] = Field(None, description="Link to explanation if available")


class RecommendationApproveRequest(BaseModel):
    """Approve recommendation request."""
    
    user_id: str
    rationale: Optional[str] = None


class RecommendationRejectRequest(BaseModel):
    """Reject recommendation request."""
    
    user_id: str
    reason: str


class RecommendationStatsResponse(BaseModel):
    """Human-in-the-loop statistics."""
    
    strategy_id: str
    total_recommendations: int
    approved: int
    rejected: int
    agreement_rate: float = Field(ge=0.0, le=1.0, description="Percentage of times human agreed with model")
    pending: int
