from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# PredictionRecord — one real-time prediction output
class PredictionRecord(BaseModel):
    record_id: UUID = Field(default_factory=uuid4)
    market_id: str
    token_id: str
    predicted_at: datetime
    p_hat: Decimal
    implied_probability: Decimal
    mispricing: Decimal  # p_hat - implied_probability
    threshold: Decimal
    threshold_met: bool
    model_version: str
    confidence: Decimal  # p_hat * (1 - p_hat)
    data_staleness_ok: bool


# LagTestResult — stores results from one of the 4 lead-lag tests
class LagTestResult(BaseModel):
    test_id: UUID = Field(default_factory=uuid4)
    run_at: datetime
    test_type: Literal["cross_correlation", "granger", "event_study", "persistence"]
    period_start: datetime
    period_end: datetime
    results: Dict[str, Any]  # JSONB-compatible; structure varies by test_type


# CalibrationBin — one reliability-diagram bin
class CalibrationBin(BaseModel):
    bin_midpoint: Decimal
    observed_freq: Decimal
    predicted_freq: Decimal


# CalibrationReport — per-model calibration diagnostics
class CalibrationReport(BaseModel):
    report_id: UUID = Field(default_factory=uuid4)
    generated_at: datetime
    model_version: str
    brier_score: Decimal
    ece: Decimal  # Expected Calibration Error
    auc: Optional[Decimal] = None
    reliability: List[CalibrationBin]
    needs_recal: bool  # True if ECE > 0.05 on rolling 7-day window


# WalkForwardFold — describes one CV fold (used internally by trainer/dataset builder)
class WalkForwardFold(BaseModel):
    fold_index: int
    train_start: datetime
    train_end: datetime
    val_start: datetime
    val_end: datetime


# ModelType — discriminated literal for the two required models
ModelType = Literal["logistic", "gbt"]
