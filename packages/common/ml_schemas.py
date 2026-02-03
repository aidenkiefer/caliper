"""
Pydantic schemas for ML Safety & Interpretability features.

These schemas are used across ML services and API endpoints.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Literal, Optional, Dict, Any
from pydantic import BaseModel, Field


# ============================================================================
# Model Interface Schemas (Sprint 7)
# ============================================================================


class ModelInput(BaseModel):
    """
    Standardized input to ML model for inference.

    This schema ensures consistent model invocation across strategies.
    """

    symbol: str = Field(..., description="Trading symbol")
    timestamp: datetime = Field(..., description="Timestamp of prediction (bar close time)")
    features: Dict[str, float] = Field(
        ..., description="Feature dictionary with feature names as keys"
    )

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class ModelPrediction(BaseModel):
    """
    Raw model prediction output before confidence gating.

    This is what the trained model returns directly. The prediction
    flows through ConfidenceGating to produce the final ModelOutput
    with potential ABSTAIN signal.

    For binary classifier:
        - prediction: 0 (DOWN) or 1 (UP)
        - confidence: max(probability, 1-probability)
        - raw_probability: model.predict_proba()[:, 1]
    """

    prediction: int = Field(..., description="Raw prediction: 0 (DOWN) or 1 (UP)")
    confidence: float = Field(ge=0.0, le=1.0, description="Prediction confidence (0.0 to 1.0)")
    raw_probability: float = Field(
        ge=0.0, le=1.0, description="Raw probability of UP class from model"
    )
    features_used: List[str] = Field(..., description="Feature names used for prediction")

    def to_signal_side(self) -> Literal["BUY", "SELL"]:
        """
        Convert prediction to signal side before gating.

        Returns:
            "BUY" if prediction is 1 (UP), "SELL" if 0 (DOWN)
        """
        return "BUY" if self.prediction == 1 else "SELL"


class ModelInferenceOutput(BaseModel):
    """
    Complete inference output after confidence gating.

    This extends ModelPrediction with the gated signal (may be ABSTAIN)
    and is ready to be consumed by the strategy layer.

    Flow: Model → ModelPrediction → ConfidenceGating → ModelInferenceOutput → Signal
    """

    signal: Literal["BUY", "SELL", "ABSTAIN"] = Field(
        ..., description="Final signal after confidence gating"
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Prediction confidence")
    uncertainty: float = Field(ge=0.0, description="Prediction uncertainty (entropy)")
    raw_probability: float = Field(ge=0.0, le=1.0, description="Raw model probability")
    features_used: List[str] = Field(..., description="Features used")
    abstain_reason: Optional[str] = Field(
        None, description="Reason for ABSTAIN if signal is ABSTAIN"
    )

    def should_trade(self) -> bool:
        """Check if signal is actionable (not ABSTAIN)."""
        return self.signal != "ABSTAIN"


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
    agreement_rate: float = Field(
        ge=0.0, le=1.0, description="Percentage of times human agreed with model"
    )
    pending: int
