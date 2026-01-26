"""
Schemas for trade explanations.
"""

from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class FeatureContribution(BaseModel):
    """Feature contribution to prediction."""
    
    feature_name: str
    value: float = Field(description="Actual feature value")
    contribution: float = Field(description="SHAP value (contribution to prediction)")
    direction: Literal["positive", "negative"] = Field(
        description="Whether feature pushes prediction up or down"
    )


class TradeExplanation(BaseModel):
    """Explanation for a trade recommendation."""
    
    trade_id: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    signal: str = Field(description="BUY, SELL, or ABSTAIN")
    confidence: float = Field(ge=0.0, le=1.0)
    top_features: List[FeatureContribution] = Field(
        default_factory=list,
        description="Top N features by absolute contribution"
    )
    model_id: str
    base_value: Optional[float] = Field(
        None,
        description="SHAP base value (expected prediction)"
    )
    
    class Config:
        from_attributes = True
