from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel

from services.simulation.schemas import SimResult
from services.evaluation.schemas import EvaluationReport, RegimeMetrics

router = APIRouter(tags=["simulation"])


# ── Request/Response models ────────────────────────────────────────────────────

class SimulationRunRequest(BaseModel):
    strategy_id: str
    market_id: str
    token_id: str
    start: datetime
    end: datetime
    config: Optional[Dict[str, Any]] = None


class SimulationRunResponse(BaseModel):
    run_id: str
    status: str = "queued"


# ── Background task ────────────────────────────────────────────────────────────

def _run_simulation(run_id: str, request: SimulationRunRequest) -> None:
    """Placeholder background task for future simulation wiring."""
    return


# ── Simulation endpoints ───────────────────────────────────────────────────────

@router.post("/simulation/run", status_code=202, response_model=SimulationRunResponse)
def start_simulation(request: SimulationRunRequest, background_tasks: BackgroundTasks) -> SimulationRunResponse:
    """Kick off a backtest simulation run. Returns run_id synchronously."""
    raise HTTPException(status_code=501, detail="Simulation runs are not wired yet (stub responses removed)")


@router.get("/simulation/{run_id}/result")
def get_simulation_result(run_id: str) -> Any:
    """Poll simulation result. Returns 404 if unknown, 202 if still running."""
    raise HTTPException(status_code=501, detail="Simulation runs are not wired yet (stub responses removed)")


# ── Evaluation endpoints ───────────────────────────────────────────────────────

@router.get("/evaluation/compare", response_model=EvaluationReport)
def compare_evaluations(strategy_ids: str = Query(...)) -> EvaluationReport:
    """Returns side-by-side EvaluationReport for comma-separated strategy_ids."""
    raise HTTPException(status_code=501, detail="Evaluation compare is not wired yet (stub responses removed)")


@router.get("/evaluation/{strategy_id}/latest", response_model=EvaluationReport)
def get_latest_evaluation(strategy_id: str) -> EvaluationReport:
    """Returns latest EvaluationReport for the strategy (stub mode)."""
    raise HTTPException(status_code=501, detail="Evaluation reports are not wired yet (stub responses removed)")


@router.get("/evaluation/{strategy_id}/regimes", response_model=List[RegimeMetrics])
def get_regime_breakdown(strategy_id: str) -> List[RegimeMetrics]:
    """Returns regime metrics breakdown for a strategy (stub returns empty list)."""
    raise HTTPException(status_code=501, detail="Evaluation regimes are not wired yet (stub responses removed)")
