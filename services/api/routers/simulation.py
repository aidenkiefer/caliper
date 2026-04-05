from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel

from services.simulation.schemas import SimResult
from services.evaluation.schemas import EvaluationReport, RegimeMetrics, StrategyMetrics, StrategyRanking

router = APIRouter(tags=["simulation"])

# In-memory store for stub mode (run_id → {"status": str, "result": SimResult | None})
_runs: Dict[str, Dict[str, Any]] = {}


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
    """Stub background task: marks the run as completed with a stub SimResult."""
    _runs[run_id]["status"] = "running"
    stub_result = SimResult(
        run_id=run_id,
        strategy_id=request.strategy_id,
        market_id=request.market_id,
        start_time=request.start,
        end_time=request.end,
        fills=[],
        pnl_components={
            "spread_capture": Decimal("0"),
            "inventory_drift": Decimal("0"),
            "maker_rebate": Decimal("0"),
            "liquidity_reward": Decimal("0"),
            "taker_fee": Decimal("0"),
            "ops_cost": Decimal("0"),
        },
        total_pnl=Decimal("0"),
        fill_count=0,
        fill_rate=Decimal("0"),
        maker_fill_rate=Decimal("0"),
        config=request.config or {},
    )
    _runs[run_id]["status"] = "completed"
    _runs[run_id]["result"] = stub_result


# ── Simulation endpoints ───────────────────────────────────────────────────────

@router.post("/simulation/run", status_code=202, response_model=SimulationRunResponse)
def start_simulation(request: SimulationRunRequest, background_tasks: BackgroundTasks) -> SimulationRunResponse:
    """Kick off a backtest simulation run. Returns run_id synchronously."""
    run_id = str(uuid.uuid4())
    _runs[run_id] = {"status": "queued", "result": None}
    background_tasks.add_task(_run_simulation, run_id, request)
    return SimulationRunResponse(run_id=run_id, status="queued")


@router.get("/simulation/{run_id}/result")
def get_simulation_result(run_id: str) -> Any:
    """Poll simulation result. Returns 404 if unknown, 202 if still running."""
    if run_id not in _runs:
        raise HTTPException(status_code=404, detail=f"Run {run_id!r} not found")
    entry = _runs[run_id]
    if entry["status"] != "completed":
        return {"status": entry["status"]}
    return entry["result"]


# ── Evaluation endpoints ───────────────────────────────────────────────────────

def _stub_strategy_metrics(strategy_id: str) -> StrategyMetrics:
    now = datetime.now(tz=timezone.utc)
    return StrategyMetrics(
        strategy_id=strategy_id,
        period_start=now,
        period_end=now,
        total_pnl=Decimal("0"),
        pnl_components={},
        sharpe_ratio=Decimal("0"),
        sortino_ratio=Decimal("0"),
        calmar_ratio=Decimal("0"),
        win_rate=Decimal("0"),
        profit_factor=Decimal("0"),
        max_drawdown=Decimal("0"),
        max_drawdown_duration_hours=0,
        consistency_score=Decimal("0"),
        stability_score=Decimal("0"),
        total_volume_usd=Decimal("0"),
        fill_rate=Decimal("0"),
        maker_fill_rate=Decimal("0"),
        regret_vs_hold_cash=Decimal("0"),
        regret_vs_buy_and_hold=Decimal("0"),
        regret_vs_random=Decimal("0"),
        sharpe_confidence="low",
        data_points=0,
    )


def _stub_report(strategy_ids: List[str]) -> EvaluationReport:
    return EvaluationReport(
        report_id=uuid.uuid4(),
        generated_at=datetime.now(tz=timezone.utc),
        strategy_ids=strategy_ids,
        period_start=datetime.now(tz=timezone.utc),
        period_end=datetime.now(tz=timezone.utc),
        per_strategy={s: _stub_strategy_metrics(s) for s in strategy_ids},
        regime_breakdown={s: [] for s in strategy_ids},
        rankings=[StrategyRanking(strategy_id=s, rank=i + 1, composite_score=Decimal("0")) for i, s in enumerate(strategy_ids)],
        baseline_comparison={},
    )


@router.get("/evaluation/compare", response_model=EvaluationReport)
def compare_evaluations(strategy_ids: str = Query(...)) -> EvaluationReport:
    """Returns side-by-side EvaluationReport for comma-separated strategy_ids."""
    if not strategy_ids:
        raise HTTPException(status_code=422, detail="strategy_ids query param is required")
    ids = [s.strip() for s in strategy_ids.split(",") if s.strip()]
    if not ids:
        raise HTTPException(status_code=422, detail="strategy_ids must not be empty")
    return _stub_report(ids)


@router.get("/evaluation/{strategy_id}/latest", response_model=EvaluationReport)
def get_latest_evaluation(strategy_id: str) -> EvaluationReport:
    """Returns latest EvaluationReport for the strategy (stub mode)."""
    if not strategy_id:
        raise HTTPException(status_code=404, detail="strategy_id is required")
    return _stub_report([strategy_id])


@router.get("/evaluation/{strategy_id}/regimes", response_model=List[RegimeMetrics])
def get_regime_breakdown(strategy_id: str) -> List[RegimeMetrics]:
    """Returns regime metrics breakdown for a strategy (stub returns empty list)."""
    return []
