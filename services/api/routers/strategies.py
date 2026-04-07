"""
Strategy endpoints.

Provides CRUD operations for trading strategies.
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from packages.common.api_schemas import (
    StrategyListResponse,
    StrategyListItem,
    StrategyListMeta,
    StrategyDetailResponse,
    StrategyDetailData,
    StrategyUpdateRequest,
    StrategyUpdateResponse,
    StrategyStatus,
    StrategyMode,
)
from services.api.dependencies import get_db
from services.portfolio.paper_portfolio import (
    compute_strategy_sleeve,
    maybe_refresh_snapshot_for_strategy,
)

router = APIRouter()

def _discover_strategies(db: Session) -> List[Dict[str, Any]]:
    """
    Discover strategy_ids from real runtime paper data (allocations/fills),
    and attach coarse created/updated timestamps (first/last seen).

    This is a minimal Phase 1 replacement for the previous in-memory mock list.
    """
    rows = db.execute(
        text(
            """
            WITH ids AS (
              SELECT strategy_id, MIN(allocated_at) AS created_at, MAX(allocated_at) AS updated_at
              FROM paper.allocations
              GROUP BY strategy_id
              UNION ALL
              SELECT strategy_id, MIN(executed_at) AS created_at, MAX(executed_at) AS updated_at
              FROM pm.paper_trades
              GROUP BY strategy_id
              UNION ALL
              SELECT strategy_id, MIN(filled_at) AS created_at, MAX(filled_at) AS updated_at
              FROM paper.equity_fills
              GROUP BY strategy_id
            )
            SELECT strategy_id,
                   MIN(created_at) AS created_at,
                   MAX(updated_at) AS updated_at
            FROM ids
            GROUP BY strategy_id
            ORDER BY strategy_id ASC;
            """
        )
    ).mappings()
    return [dict(r) for r in rows]


class StrategySleeveResponse(BaseModel):
    strategy_id: str
    starting_capital_usd: str
    cash_usd: str
    deployed_capital_usd: str
    positions_value_usd: str
    equity_usd: str
    realized_pnl_usd: str
    unrealized_pnl_usd: str
    updated_at: str


class StrategyPositionRow(BaseModel):
    surface: str = Field(..., description="equity or polymarket")
    instrument_id: str
    quantity: str
    avg_cost: str
    mark_price: Optional[str] = None
    mark_source: str
    market_value: Optional[str] = None
    unrealized_pnl: Optional[str] = None


@router.get(
    "/strategies",
    response_model=StrategyListResponse,
    summary="List strategies",
    description="List all configured trading strategies.",
)
async def list_strategies(
    status: Optional[str] = Query(
        None,
        description="Filter by status: active, inactive, or all",
        pattern="^(active|inactive|all)$",
    ),
    mode: Optional[str] = Query(
        None,
        description="Filter by mode: BACKTEST, PAPER, or LIVE",
        pattern="^(BACKTEST|PAPER|LIVE)$",
    ),
    db: Session = Depends(get_db),
) -> StrategyListResponse:
    """
    List all trading strategies.

    Args:
        status: Optional status filter (active, inactive, all)
        mode: Optional mode filter (BACKTEST, PAPER, LIVE)

    Returns:
        List of strategies with metadata
    """
    # This minimal Phase 1 implementation derives the strategy list from runtime paper activity.
    # If callers filter for inactive/BACKTEST/LIVE, return empty rather than fabricate state.
    if status == "inactive":
        return StrategyListResponse(
            data=[],
            meta=StrategyListMeta(total_count=0, active_count=0),
        )
    if mode in ("BACKTEST", "LIVE"):
        return StrategyListResponse(
            data=[],
            meta=StrategyListMeta(total_count=0, active_count=0),
        )

    try:
        discovered = _discover_strategies(db)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Strategy store not available (DB not configured or migrations not applied)",
        ) from exc
    now = datetime.now(timezone.utc)
    strategies: List[StrategyListItem] = []
    for r in discovered:
        sid = str(r["strategy_id"])
        created_at = r.get("created_at") or now
        updated_at = r.get("updated_at") or created_at
        strategies.append(
            StrategyListItem(
                strategy_id=sid,
                name=sid,
                description=None,
                status=StrategyStatus.ACTIVE,
                mode=StrategyMode.PAPER,
                universe_size=None,
                max_positions=None,
                risk_per_trade_pct=None,
                created_at=created_at,
                updated_at=updated_at,
                performance=None,
            )
        )

    active_count = len(strategies)

    return StrategyListResponse(
        data=strategies,
        meta=StrategyListMeta(
            total_count=len(strategies),
            active_count=active_count,
        ),
    )


@router.get(
    "/strategies/{strategy_id}",
    response_model=StrategyDetailResponse,
    summary="Get strategy details",
    description="Get detailed information for a specific strategy.",
)
async def get_strategy(strategy_id: str, db: Session = Depends(get_db)) -> StrategyDetailResponse:
    """
    Get details for a specific strategy.

    Args:
        strategy_id: Strategy identifier

    Returns:
        Strategy details including config and performance

    Raises:
        HTTPException: 404 if strategy not found
    """
    try:
        discovered = {r["strategy_id"]: r for r in _discover_strategies(db)}
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Strategy store not available (DB not configured or migrations not applied)",
        ) from exc
    if strategy_id not in discovered:
        raise HTTPException(status_code=404, detail=f"Strategy '{strategy_id}' not found")

    r = discovered[strategy_id]
    now = datetime.now(timezone.utc)
    created_at = r.get("created_at") or now
    updated_at = r.get("updated_at") or created_at

    return StrategyDetailResponse(
        data=StrategyDetailData(
            strategy_id=strategy_id,
            name=strategy_id,
            description=None,
            status=StrategyStatus.ACTIVE,
            mode=StrategyMode.PAPER,
            universe_size=None,
            max_positions=None,
            risk_per_trade_pct=None,
            created_at=created_at,
            updated_at=updated_at,
            config=None,
            performance=None,
        )
    )


@router.patch(
    "/strategies/{strategy_id}",
    response_model=StrategyUpdateResponse,
    summary="Update strategy",
    description="Update strategy configuration (enable/disable, adjust risk parameters).",
)
async def update_strategy(
    strategy_id: str,
    request: StrategyUpdateRequest,
) -> StrategyUpdateResponse:
    """
    Update a strategy's configuration.

    Args:
        strategy_id: Strategy identifier
        request: Update request with new status/config

    Returns:
        Updated strategy details

    Raises:
        HTTPException: 404 if strategy not found
    """
    raise HTTPException(
        status_code=501,
        detail="Strategy updates are not yet supported (strategy metadata is currently derived from runtime paper data).",
    )


@router.get(
    "/strategies/{strategy_id}/sleeve",
    response_model=StrategySleeveResponse,
    summary="Get runtime paper sleeve state for a strategy",
)
def get_strategy_sleeve(strategy_id: str, db: Session = Depends(get_db)) -> StrategySleeveResponse:
    try:
        maybe_refresh_snapshot_for_strategy(db, strategy_id)
        db.commit()
    except Exception:
        db.rollback()

    sleeve = compute_strategy_sleeve(db, strategy_id)
    return StrategySleeveResponse(
        strategy_id=strategy_id,
        starting_capital_usd=f"{sleeve.starting_capital_usd:.2f}",
        cash_usd=f"{sleeve.cash_usd:.2f}",
        deployed_capital_usd=f"{sleeve.deployed_capital_usd:.2f}",
        positions_value_usd=f"{sleeve.positions_value_usd:.2f}",
        equity_usd=f"{sleeve.equity_usd:.2f}",
        realized_pnl_usd=f"{sleeve.realized_pnl_usd:.2f}",
        unrealized_pnl_usd=f"{sleeve.unrealized_pnl_usd:.2f}",
        updated_at=sleeve.updated_at.isoformat(),
    )


@router.get(
    "/strategies/{strategy_id}/positions",
    response_model=List[StrategyPositionRow],
    summary="Get derived open positions for a strategy",
)
def get_strategy_positions(strategy_id: str, db: Session = Depends(get_db)) -> List[StrategyPositionRow]:
    sleeve = compute_strategy_sleeve(db, strategy_id)
    rows: List[StrategyPositionRow] = []
    for p in sleeve.positions:
        rows.append(
            StrategyPositionRow(
                surface=p.surface,
                instrument_id=p.instrument_id,
                quantity=str(p.quantity),
                avg_cost=str(p.avg_cost),
                mark_price=str(p.mark_price) if p.mark_price is not None else None,
                mark_source=p.mark_source,
                market_value=str(p.market_value) if p.market_value is not None else None,
                unrealized_pnl=str(p.unrealized_pnl) if p.unrealized_pnl is not None else None,
            )
        )
    return rows


@router.get(
    "/strategies/{strategy_id}/fills",
    summary="Get unified fills for a strategy (polymarket + equities)",
)
def get_strategy_fills(
    strategy_id: str,
    limit: int = Query(500, ge=1, le=5000),
    db: Session = Depends(get_db),
) -> dict:
    equity_rows = db.execute(
        text(
            """
            SELECT filled_at AS ts, 'equity' AS surface, symbol AS instrument_id,
                   side, quantity, price, fees_usd
            FROM paper.equity_fills
            WHERE strategy_id = :sid
            ORDER BY filled_at DESC
            LIMIT :limit
            """
        ),
        {"sid": strategy_id, "limit": limit},
    ).mappings()
    pm_rows = db.execute(
        text(
            """
            SELECT executed_at AS ts, 'polymarket' AS surface, market_id AS instrument_id,
                   side, quantity, price, 0::numeric AS fees_usd
            FROM pm.paper_trades
            WHERE strategy_id = :sid
            ORDER BY executed_at DESC
            LIMIT :limit
            """
        ),
        {"sid": strategy_id, "limit": limit},
    ).mappings()
    fills = [dict(r) for r in equity_rows] + [dict(r) for r in pm_rows]
    fills.sort(key=lambda r: r["ts"], reverse=True)
    fills = fills[:limit]
    # Convert decimals/datetimes for JSON.
    for r in fills:
        if hasattr(r["ts"], "isoformat"):
            r["ts"] = r["ts"].isoformat()
        for k in ("quantity", "price", "fees_usd"):
            if r.get(k) is not None:
                r[k] = str(r[k])
    return {"data": fills}
