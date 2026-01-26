"""
Metrics endpoints.

Provides aggregated metrics for the dashboard overview.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Query

from packages.common.api_schemas import (
    MetricsSummaryResponse,
    MetricsSummaryData,
    MetricsMeta,
    EquityCurvePoint,
)

router = APIRouter()


@router.get(
    "/metrics/summary",
    response_model=MetricsSummaryResponse,
    summary="Get metrics summary",
    description="Aggregate metrics across all strategies for dashboard overview.",
)
async def get_metrics_summary(
    period: str = Query(
        "1m",
        description="Time period: 1d, 1w, 1m, 3m, 1y, all",
        pattern="^(1d|1w|1m|3m|1y|all)$",
    ),
    mode: Optional[str] = Query(
        None,
        description="Filter by mode: PAPER or LIVE",
        pattern="^(PAPER|LIVE)$",
    ),
) -> MetricsSummaryResponse:
    """
    Get aggregated metrics summary.
    
    Args:
        period: Time period filter (1d, 1w, 1m, 3m, 1y, all)
        mode: Optional mode filter (PAPER or LIVE)
    
    Returns:
        Aggregated metrics including P&L, Sharpe ratio, drawdown, etc.
    """
    # TODO: Wire to database and compute actual metrics
    # For now, return mock data
    
    # Generate sample equity curve
    equity_curve = [
        EquityCurvePoint(date="2026-01-01", value="100000.00"),
        EquityCurvePoint(date="2026-01-02", value="101234.56"),
        EquityCurvePoint(date="2026-01-03", value="100890.12"),
        EquityCurvePoint(date="2026-01-04", value="102345.67"),
        EquityCurvePoint(date="2026-01-05", value="103456.78"),
    ]
    
    data = MetricsSummaryData(
        total_pnl="12345.67",
        total_pnl_percent="15.23",
        sharpe_ratio="1.85",
        max_drawdown="-8.45",
        win_rate="0.58",
        total_trades=142,
        active_positions=8,
        capital_deployed="45000.00",
        available_capital="55000.00",
        equity_curve=equity_curve,
    )
    
    meta = MetricsMeta(
        period=period,
        updated_at=datetime.now(timezone.utc),
    )
    
    return MetricsSummaryResponse(data=data, meta=meta)
