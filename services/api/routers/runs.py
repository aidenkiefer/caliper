"""
Runs endpoints.

Provides endpoints for backtest runs and trading sessions.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query

from packages.common.api_schemas import (
    RunListResponse,
    RunListItem,
    RunListMeta,
    RunDetailResponse,
    RunDetailData,
    RunMetrics,
    RunTrade,
    RunCreateRequest,
    RunCreateResponse,
    RunCreateData,
    RunType,
    RunStatus,
    EquityCurvePoint,
)

router = APIRouter()

# Mock run data - TODO: Replace with database queries
MOCK_RUNS = {
    "run-001": {
        "run_id": "run-001",
        "strategy_id": "momentum_v1",
        "run_type": RunType.BACKTEST,
        "start_date": "2024-01-01",
        "end_date": "2025-12-31",
        "total_return": "18.45",
        "sharpe_ratio": "2.15",
        "max_drawdown": "-9.23",
        "total_trades": 87,
        "status": RunStatus.COMPLETED,
        "report_url": "https://storage.example.com/reports/run-001.html",
        "created_at": datetime(2026, 1, 24, 12, 0, 0, tzinfo=timezone.utc),
        "completed_at": datetime(2026, 1, 24, 12, 15, 30, tzinfo=timezone.utc),
        "metrics": {
            "total_return": "18.45",
            "cagr": "17.82",
            "sharpe_ratio": "2.15",
            "sortino_ratio": "2.87",
            "max_drawdown": "-9.23",
            "win_rate": "0.61",
            "profit_factor": "2.34",
            "total_trades": 87,
            "avg_trade_duration_hours": "72.50",
        },
        "trades": [
            {
                "trade_id": "trade-001",
                "symbol": "AAPL",
                "entry_time": datetime(2024, 3, 15, 14, 30, 0, tzinfo=timezone.utc),
                "exit_time": datetime(2024, 3, 18, 15, 45, 0, tzinfo=timezone.utc),
                "entry_price": "172.50",
                "exit_price": "178.25",
                "quantity": "100",
                "pnl": "575.00",
                "return_pct": "3.33",
            },
            {
                "trade_id": "trade-002",
                "symbol": "MSFT",
                "entry_time": datetime(2024, 4, 10, 10, 0, 0, tzinfo=timezone.utc),
                "exit_time": datetime(2024, 4, 12, 11, 30, 0, tzinfo=timezone.utc),
                "entry_price": "405.00",
                "exit_price": "398.50",
                "quantity": "50",
                "pnl": "-325.00",
                "return_pct": "-1.60",
            },
        ],
        "equity_curve": [
            {"date": "2024-01-01", "value": "100000.00"},
            {"date": "2024-06-01", "value": "108500.00"},
            {"date": "2025-01-01", "value": "112000.00"},
            {"date": "2025-12-31", "value": "118450.00"},
        ],
    },
    "run-002": {
        "run_id": "run-002",
        "strategy_id": "momentum_v1",
        "run_type": RunType.PAPER,
        "start_date": "2026-01-01",
        "end_date": "2026-01-25",
        "total_return": "3.25",
        "sharpe_ratio": "1.95",
        "max_drawdown": "-2.10",
        "total_trades": 15,
        "status": RunStatus.RUNNING,
        "report_url": None,
        "created_at": datetime(2026, 1, 1, 9, 0, 0, tzinfo=timezone.utc),
        "completed_at": None,
        "metrics": {
            "total_return": "3.25",
            "cagr": None,
            "sharpe_ratio": "1.95",
            "sortino_ratio": "2.10",
            "max_drawdown": "-2.10",
            "win_rate": "0.67",
            "profit_factor": "2.85",
            "total_trades": 15,
            "avg_trade_duration_hours": "48.00",
        },
        "trades": [],
        "equity_curve": [
            {"date": "2026-01-01", "value": "100000.00"},
            {"date": "2026-01-15", "value": "102150.00"},
            {"date": "2026-01-25", "value": "103250.00"},
        ],
    },
}


@router.get(
    "/runs",
    response_model=RunListResponse,
    summary="List runs",
    description="List strategy runs (backtests, paper trading sessions, live sessions).",
)
async def list_runs(
    strategy_id: Optional[str] = Query(None, description="Filter by strategy ID"),
    run_type: Optional[str] = Query(
        None,
        description="Filter by type: BACKTEST, PAPER, or LIVE",
        pattern="^(BACKTEST|PAPER|LIVE)$",
    ),
    status: Optional[str] = Query(
        None,
        description="Filter by status: RUNNING, COMPLETED, or FAILED",
        pattern="^(RUNNING|COMPLETED|FAILED)$",
    ),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
) -> RunListResponse:
    """
    List all strategy runs.

    Args:
        strategy_id: Optional filter by strategy
        run_type: Optional filter by run type
        status: Optional filter by status
        page: Page number (1-based)
        per_page: Items per page (max 100)

    Returns:
        Paginated list of runs
    """
    runs = []

    for r in MOCK_RUNS.values():
        # Apply filters
        if strategy_id and r["strategy_id"] != strategy_id:
            continue
        if run_type and r["run_type"].value != run_type:
            continue
        if status and r["status"].value != status:
            continue

        runs.append(
            RunListItem(
                run_id=r["run_id"],
                strategy_id=r["strategy_id"],
                run_type=r["run_type"],
                start_date=r["start_date"],
                end_date=r["end_date"],
                total_return=r["total_return"],
                sharpe_ratio=r["sharpe_ratio"],
                max_drawdown=r["max_drawdown"],
                total_trades=r["total_trades"],
                status=r["status"],
                report_url=r["report_url"],
                created_at=r["created_at"],
                completed_at=r["completed_at"],
            )
        )

    # Simple pagination
    total = len(runs)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_runs = runs[start:end]

    return RunListResponse(
        data=paginated_runs,
        meta=RunListMeta(
            total_count=total,
            page=page,
            per_page=per_page,
        ),
    )


@router.get(
    "/runs/{run_id}",
    response_model=RunDetailResponse,
    summary="Get run details",
    description="Get detailed results for a specific run.",
)
async def get_run(run_id: str) -> RunDetailResponse:
    """
    Get details for a specific run.

    Args:
        run_id: Run identifier

    Returns:
        Run details including metrics, equity curve, and trades

    Raises:
        HTTPException: 404 if run not found
    """
    if run_id not in MOCK_RUNS:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    r = MOCK_RUNS[run_id]

    trades = [
        RunTrade(
            trade_id=t["trade_id"],
            symbol=t["symbol"],
            entry_time=t["entry_time"],
            exit_time=t["exit_time"],
            entry_price=t["entry_price"],
            exit_price=t["exit_price"],
            quantity=t["quantity"],
            pnl=t["pnl"],
            return_pct=t["return_pct"],
        )
        for t in r["trades"]
    ]

    equity_curve = [EquityCurvePoint(date=p["date"], value=p["value"]) for p in r["equity_curve"]]

    return RunDetailResponse(
        data=RunDetailData(
            run_id=r["run_id"],
            strategy_id=r["strategy_id"],
            metrics=RunMetrics(
                total_return=r["metrics"]["total_return"],
                cagr=r["metrics"]["cagr"],
                sharpe_ratio=r["metrics"]["sharpe_ratio"],
                sortino_ratio=r["metrics"]["sortino_ratio"],
                max_drawdown=r["metrics"]["max_drawdown"],
                win_rate=r["metrics"]["win_rate"],
                profit_factor=r["metrics"]["profit_factor"],
                total_trades=r["metrics"]["total_trades"],
                avg_trade_duration_hours=r["metrics"]["avg_trade_duration_hours"],
            ),
            equity_curve=equity_curve,
            trades=trades,
        )
    )


@router.post(
    "/runs",
    response_model=RunCreateResponse,
    status_code=202,
    summary="Create backtest run",
    description="Trigger a new backtest run.",
)
async def create_run(request: RunCreateRequest) -> RunCreateResponse:
    """
    Create a new backtest run.

    Args:
        request: Run configuration including strategy, dates, and capital

    Returns:
        New run ID and status (202 Accepted - async operation)
    """
    # TODO: Wire to actual backtest engine
    # For now, create a mock run

    run_id = f"run-{uuid4().hex[:8]}"
    estimated_completion = datetime.now(timezone.utc) + timedelta(minutes=15)

    return RunCreateResponse(
        message="Backtest started",
        data=RunCreateData(
            run_id=run_id,
            status=RunStatus.RUNNING,
            estimated_completion=estimated_completion,
        ),
    )
