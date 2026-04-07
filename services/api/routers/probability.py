from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel

from services.ml.probability_model.schemas import (
    PredictionRecord,
    LagTestResult,
    CalibrationReport,
)

router = APIRouter()


# ── Request/Response models ────────────────────────────────────────────────────

class TrainRequest(BaseModel):
    market_id: str
    model_type: str
    start: datetime
    end: datetime


class TrainResponse(BaseModel):
    run_id: str
    status: str = "queued"


# ── Background task ────────────────────────────────────────────────────────────

def _run_training(run_id: str, request: TrainRequest) -> None:
    """Placeholder background task for future probability training."""
    return


# ── Probability endpoints ──────────────────────────────────────────────────────
# NOTE: /calibration and /lag-tests MUST be defined BEFORE /{market_id}/latest
# to prevent FastAPI from matching "calibration" as a market_id path parameter.

@router.get("/probability/calibration", response_model=CalibrationReport)
def get_calibration(model_version: Optional[str] = Query(None)) -> CalibrationReport:
    """Returns the latest CalibrationReport, optionally filtered by model_version."""
    raise HTTPException(
        status_code=501,
        detail="Probability calibration is not wired yet (mock responses removed)",
    )


@router.get("/probability/lag-tests", response_model=LagTestResult)
def get_lag_tests(type: str = Query("cross_correlation")) -> LagTestResult:
    """Returns the latest LagTestResult for the given test type."""
    raise HTTPException(
        status_code=501,
        detail="Probability lag tests are not wired yet (mock responses removed)",
    )


@router.get("/probability/{market_id}/latest", response_model=PredictionRecord)
def get_latest_prediction(market_id: str) -> PredictionRecord:
    """Returns the latest PredictionRecord for the given market."""
    raise HTTPException(
        status_code=501,
        detail="Probability latest prediction is not wired yet (mock responses removed)",
    )


@router.get("/probability/{market_id}/history", response_model=List[PredictionRecord])
def get_prediction_history(
    market_id: str,
    start: Optional[datetime] = Query(None),
    end: Optional[datetime] = Query(None),
) -> List[PredictionRecord]:
    """Returns historical PredictionRecords for the given market."""
    raise HTTPException(
        status_code=501,
        detail="Probability history is not wired yet (mock responses removed)",
    )


@router.post("/probability/train", status_code=202, response_model=TrainResponse)
def train_model(request: TrainRequest, background_tasks: BackgroundTasks) -> TrainResponse:
    """Kick off a probability model training run."""
    raise HTTPException(
        status_code=501,
        detail="Probability training is not wired yet (stub queue removed)",
    )
