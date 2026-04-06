from __future__ import annotations

from datetime import datetime
from typing import Dict, Literal, Optional

from pydantic import BaseModel, Field


RegimeLabel = Literal["R1", "R2", "R3", "R4", "R5"]
RegimeSource = Literal["threshold", "hmm", "blended"]


class ConnectivityMetrics(BaseModel):
    """Optional inputs used to compute the R4 connectivity override."""

    api_latency_ms: float = Field(..., ge=0)
    heartbeat_miss_count: int = Field(..., ge=0)


class RegimeQualityReport(BaseModel):
    computed_at: datetime
    posterior_entropy: float = Field(..., ge=0)
    switch_rate_per_hour: float = Field(..., ge=0)
    expected_duration_minutes: float = Field(..., ge=0)
    agreement_with_threshold: float = Field(..., ge=0, le=1)
    quality_score: float = Field(..., ge=0, le=1)


class RegimeState(BaseModel):
    detected_at: datetime
    market_id: Optional[str] = None  # None = global regime
    primary_regime: RegimeLabel
    regime_probabilities: Dict[RegimeLabel, float]
    quality: RegimeQualityReport
    source: RegimeSource

