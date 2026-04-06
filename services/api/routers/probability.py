from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel

from services.ml.probability_model.schemas import (
    PredictionRecord,
    LagTestResult,
    CalibrationReport,
    CalibrationBin,
    BrierDecomposition,
)

router = APIRouter()

# In-memory store for stub training runs (run_id → {"status": str})
_train_runs: Dict[str, Dict[str, Any]] = {}


# ── Request/Response models ────────────────────────────────────────────────────

class TrainRequest(BaseModel):
    market_id: str
    model_type: str
    start: datetime
    end: datetime


class TrainResponse(BaseModel):
    run_id: str
    status: str = "queued"


# ── Stub helpers ───────────────────────────────────────────────────────────────

def _mock_prediction(market_id: str) -> PredictionRecord:
    return PredictionRecord(
        market_id=market_id,
        token_id=f"{market_id}_yes",
        predicted_at=datetime.now(tz=timezone.utc),
        p_hat=Decimal("0.52"),
        implied_probability=Decimal("0.50"),
        mispricing=Decimal("0.02"),
        threshold=Decimal("0.015"),
        threshold_met=True,
        model_version="logistic_v1",
        confidence=Decimal("0.2496"),
        data_staleness_ok=True,
    )


def _mock_calibration_report(model_version: Optional[str] = None) -> CalibrationReport:
    now = datetime.now(tz=timezone.utc)
    return CalibrationReport(
        generated_at=now,
        model_version=model_version or "logistic_v1",
        brier_score=Decimal("0.2300"),
        ece=Decimal("0.0210"),
        auc=Decimal("0.6500"),
        reliability=[
            CalibrationBin(
                bin_midpoint=Decimal("0.1"),
                observed_freq=Decimal("0.09"),
                predicted_freq=Decimal("0.10"),
            ),
            CalibrationBin(
                bin_midpoint=Decimal("0.5"),
                observed_freq=Decimal("0.51"),
                predicted_freq=Decimal("0.50"),
            ),
            CalibrationBin(
                bin_midpoint=Decimal("0.9"),
                observed_freq=Decimal("0.88"),
                predicted_freq=Decimal("0.90"),
            ),
        ],
        needs_recal=False,
        brier_decomposition=BrierDecomposition(
            reliability=0.0021,
            resolution=0.0190,
            uncertainty=0.2300,
        ),
    )


def _mock_lag_test(test_type: str = "cross_correlation") -> LagTestResult:
    now = datetime.now(tz=timezone.utc)
    return LagTestResult(
        run_at=now,
        test_type="cross_correlation",  # type: ignore[arg-type]
        period_start=now,
        period_end=now,
        results={
            "test_type": test_type,
            "lags_tested": list(range(-5, 6)),
            "correlations": [round(0.05 * i, 3) for i in range(-5, 6)],
            "peak_lag": 0,
            "peak_correlation": 0.0,
        },
    )


# ── Background task ────────────────────────────────────────────────────────────

def _run_training(run_id: str, request: TrainRequest) -> None:
    """Stub background task: marks the training run as completed immediately."""
    _train_runs[run_id]["status"] = "completed"


# ── Probability endpoints ──────────────────────────────────────────────────────
# NOTE: /calibration and /lag-tests MUST be defined BEFORE /{market_id}/latest
# to prevent FastAPI from matching "calibration" as a market_id path parameter.

@router.get("/probability/calibration", response_model=CalibrationReport)
def get_calibration(model_version: Optional[str] = Query(None)) -> CalibrationReport:
    """Returns the latest CalibrationReport, optionally filtered by model_version."""
    return _mock_calibration_report(model_version=model_version)


@router.get("/probability/lag-tests", response_model=LagTestResult)
def get_lag_tests(type: str = Query("cross_correlation")) -> LagTestResult:
    """Returns the latest LagTestResult for the given test type."""
    return _mock_lag_test(test_type=type)


@router.get("/probability/{market_id}/latest", response_model=PredictionRecord)
def get_latest_prediction(market_id: str) -> PredictionRecord:
    """Returns the latest PredictionRecord for the given market (stub mode)."""
    return _mock_prediction(market_id)


@router.get("/probability/{market_id}/history", response_model=List[PredictionRecord])
def get_prediction_history(
    market_id: str,
    start: Optional[datetime] = Query(None),
    end: Optional[datetime] = Query(None),
) -> List[PredictionRecord]:
    """Returns historical PredictionRecords for the given market (stub returns empty list)."""
    return []


@router.post("/probability/train", status_code=202, response_model=TrainResponse)
def train_model(request: TrainRequest, background_tasks: BackgroundTasks) -> TrainResponse:
    """Kick off a probability model training run. Returns run_id synchronously."""
    run_id = str(uuid.uuid4())
    _train_runs[run_id] = {"status": "queued"}
    background_tasks.add_task(_run_training, run_id, request)
    return TrainResponse(run_id=run_id, status="queued")
