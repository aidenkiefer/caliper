"""
Confidence gating: configurable thresholds for BUY/SELL/ABSTAIN decisions.
"""

from enum import Enum
from typing import Literal, Optional
from pydantic import BaseModel, Field


class Signal(str, Enum):
    """Trading signal."""
    BUY = "BUY"
    SELL = "SELL"
    ABSTAIN = "ABSTAIN"


class ConfidenceLevel(str, Enum):
    """Confidence level bands."""
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"


class ModelOutput(BaseModel):
    """Extended model output with confidence and uncertainty."""
    
    signal: Literal["BUY", "SELL", "ABSTAIN"]
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence 0.0 to 1.0")
    uncertainty: float = Field(ge=0.0, description="Entropy/uncertainty measure")
    features_used: list[str] = Field(default_factory=list)
    raw_probability: Optional[float] = Field(None, description="Raw model probability before thresholding")


class ConfidenceConfig(BaseModel):
    """Configurable confidence thresholds per strategy."""
    
    strategy_id: str
    abstain_threshold: float = Field(
        default=0.55,
        ge=0.0,
        le=1.0,
        description="Confidence below this triggers ABSTAIN"
    )
    low_confidence_threshold: float = Field(
        default=0.65,
        ge=0.0,
        le=1.0,
        description="Confidence below this is LOW_CONFIDENCE"
    )
    high_confidence_threshold: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Confidence above this is HIGH_CONFIDENCE"
    )
    
    def get_confidence_level(self, confidence: float) -> ConfidenceLevel:
        """Get confidence level band for given confidence value."""
        if confidence >= self.high_confidence_threshold:
            return ConfidenceLevel.HIGH
        elif confidence >= self.low_confidence_threshold:
            return ConfidenceLevel.NORMAL
        else:
            return ConfidenceLevel.LOW


class ConfidenceGating:
    """
    Applies confidence thresholds to model predictions.
    """
    
    def __init__(self, config: ConfidenceConfig):
        """
        Initialize confidence gating with configuration.
        
        Args:
            config: Confidence threshold configuration
        """
        self.config = config
    
    def apply_gating(
        self,
        raw_signal: Literal["BUY", "SELL"],
        confidence: float,
        uncertainty: float,
        features_used: list[str],
        raw_probability: Optional[float] = None,
    ) -> ModelOutput:
        """
        Apply confidence gating to model prediction.
        
        Args:
            raw_signal: BUY or SELL from model
            confidence: Model confidence (0.0 to 1.0)
            uncertainty: Entropy/uncertainty measure
            features_used: List of feature names used
            raw_probability: Raw model probability (optional)
            
        Returns:
            ModelOutput with signal (may be ABSTAIN if confidence too low)
        """
        # Check if confidence is below abstain threshold
        if confidence < self.config.abstain_threshold:
            signal = Signal.ABSTAIN
        else:
            signal = Signal(raw_signal)
        
        return ModelOutput(
            signal=signal.value,
            confidence=confidence,
            uncertainty=uncertainty,
            features_used=features_used,
            raw_probability=raw_probability,
        )
    
    def should_abstain(self, confidence: float) -> bool:
        """Check if model should abstain based on confidence."""
        return confidence < self.config.abstain_threshold
    
    def get_confidence_level(self, confidence: float) -> ConfidenceLevel:
        """Get confidence level band."""
        return self.config.get_confidence_level(confidence)


class AbstentionDecision(BaseModel):
    """Decision to abstain from trading."""
    
    strategy_id: str
    reason: str  # "low_confidence", "ensemble_disagreement", "uncertainty_threshold"
    confidence: float
    threshold: float
    timestamp: str
