"""
Runs endpoints.

Provides endpoints for backtest runs and trading sessions.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from packages.common.api_schemas import (
    RunListResponse,
    RunListMeta,
    RunDetailResponse,
    RunCreateRequest,
    RunCreateResponse,
)

router = APIRouter()




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
    return RunListResponse(
        data=[],
        meta=RunListMeta(
            total_count=0,
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
    raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")


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
    raise HTTPException(status_code=501, detail="Backtest runs are not wired yet (job system pending).")
