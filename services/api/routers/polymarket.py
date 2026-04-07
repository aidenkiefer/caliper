"""
Polymarket endpoints.

Provides read access to Polymarket BTC market-making sessions, orders,
fills, order-book snapshots, PnL, and toxic-flow analytics stored in
the pm.* PostgreSQL schema.

All queries are written against the pm.* TimescaleDB tables. The DB
dependency follows the same stub pattern as the rest of the API; swap
`get_db` for a real asyncpg pool when the connection is wired up.
"""

from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from packages.common.polymarket_schemas import (
    PolymarketFillResponse,
    PolymarketOrderResponse,
    PolymarketPnLResponse,
    PolymarketSessionListResponse,
    PolymarketSessionResponse,
    PolymarketSnapshotListResponse,
    PolymarketSnapshotResponse,
    PolymarketToxicFlowResponse,
)
from services.api.dependencies import get_db

router = APIRouter()


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


@router.get(
    "/polymarket/sessions",
    response_model=PolymarketSessionListResponse,
    summary="List Polymarket sessions",
    description="List market-making sessions with optional filters.",
)
async def list_sessions(
    status: Optional[str] = Query(None, description="Filter by status: active | completed | failed"),
    regime: Optional[str] = Query(None, description="Filter by volatility_regime"),
    start_date: Optional[date] = Query(None, description="Session started on or after this date"),
    end_date: Optional[date] = Query(None, description="Session started on or before this date"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=500, description="Results per page"),
    db: Session = Depends(get_db),
) -> PolymarketSessionListResponse:
    """
    Return a paginated list of Polymarket market-making sessions.

    SQL target:
        SELECT * FROM pm.sessions
        WHERE (status = $status OR $status IS NULL)
          AND (volatility_regime = $regime OR $regime IS NULL)
          AND (window_start >= $start_date OR $start_date IS NULL)
          AND (window_start <= $end_date OR $end_date IS NULL)
        ORDER BY window_start DESC
        LIMIT $page_size OFFSET ($page - 1) * $page_size;
    """
    # TODO: Replace stub with real asyncpg query once the DB pool is wired up.
    # Example (asyncpg):
    #
    #   conditions = []
    #   params: list = []
    #   idx = 1
    #   if status:
    #       conditions.append(f"status = ${idx}"); params.append(status); idx += 1
    #   if regime:
    #       conditions.append(f"volatility_regime = ${idx}"); params.append(regime); idx += 1
    #   if start_date:
    #       conditions.append(f"window_start >= ${idx}"); params.append(start_date); idx += 1
    #   if end_date:
    #       conditions.append(f"window_start <= ${idx}"); params.append(end_date); idx += 1
    #   where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    #   offset = (page - 1) * page_size
    #   rows = await db.pool.fetch(
    #       f"SELECT * FROM pm.sessions {where} ORDER BY window_start DESC "
    #       f"LIMIT ${idx} OFFSET ${idx+1}",
    #       *params, page_size, offset,
    #   )
    #   count_row = await db.pool.fetchrow(
    #       f"SELECT COUNT(*) FROM pm.sessions {where}", *params
    #   )
    #   total = count_row["count"]
    #   sessions = [PolymarketSessionResponse(**dict(r)) for r in rows]
    #   return PolymarketSessionListResponse(sessions=sessions, total=total, page=page, page_size=page_size)

    return PolymarketSessionListResponse(sessions=[], total=0, page=page, page_size=page_size)


@router.get(
    "/polymarket/sessions/{session_id}",
    response_model=PolymarketSessionResponse,
    summary="Get Polymarket session",
    description="Get details for a single market-making session.",
)
async def get_session(
    session_id: UUID,
    db: Session = Depends(get_db),
) -> PolymarketSessionResponse:
    """
    Fetch a single session from pm.sessions by primary key.

    SQL target:
        SELECT * FROM pm.sessions WHERE session_id = $1;

    Raises:
        HTTPException: 404 if session not found.
    """
    # TODO: Replace stub with real asyncpg query once the DB pool is wired up.
    # Example (asyncpg):
    #
    #   row = await db.pool.fetchrow(
    #       "SELECT * FROM pm.sessions WHERE session_id = $1", session_id
    #   )
    #   if row is None:
    #       raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    #   return PolymarketSessionResponse(**dict(row))

    raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------


@router.get(
    "/polymarket/sessions/{session_id}/orders",
    response_model=List[PolymarketOrderResponse],
    summary="List orders for a session",
    description="Return all orders placed during the given session.",
)
async def list_session_orders(
    session_id: UUID,
    status: Optional[str] = Query(None, description="Filter by order status: open | filled | cancelled"),
    db: Session = Depends(get_db),
) -> List[PolymarketOrderResponse]:
    """
    Fetch orders from pm.orders for the given session.

    SQL target:
        SELECT * FROM pm.orders
        WHERE session_id = $1
          AND (status = $2 OR $2 IS NULL)
        ORDER BY placed_at DESC;
    """
    # TODO: Replace stub with real asyncpg query once the DB pool is wired up.
    # Example (asyncpg):
    #
    #   if status:
    #       rows = await db.pool.fetch(
    #           "SELECT * FROM pm.orders WHERE session_id = $1 AND status = $2 ORDER BY placed_at DESC",
    #           session_id, status,
    #       )
    #   else:
    #       rows = await db.pool.fetch(
    #           "SELECT * FROM pm.orders WHERE session_id = $1 ORDER BY placed_at DESC",
    #           session_id,
    #       )
    #   return [PolymarketOrderResponse(**dict(r)) for r in rows]

    return []


# ---------------------------------------------------------------------------
# Fills
# ---------------------------------------------------------------------------


@router.get(
    "/polymarket/sessions/{session_id}/fills",
    response_model=List[PolymarketFillResponse],
    summary="List fills for a session",
    description="Return all fills for the given session, optionally filtered to adverse fills only.",
)
async def list_session_fills(
    session_id: UUID,
    adverse_only: Optional[bool] = Query(None, description="If true, return only adverse-selection fills"),
    db: Session = Depends(get_db),
) -> List[PolymarketFillResponse]:
    """
    Fetch fills from pm.fills for the given session.

    SQL target:
        SELECT * FROM pm.fills
        WHERE session_id = $1
          AND (adverse_selection_flag = true OR $2 IS NOT TRUE)
        ORDER BY filled_at DESC;
    """
    # TODO: Replace stub with real asyncpg query once the DB pool is wired up.
    # Example (asyncpg):
    #
    #   if adverse_only:
    #       rows = await db.pool.fetch(
    #           "SELECT * FROM pm.fills WHERE session_id = $1 AND adverse_selection_flag = TRUE ORDER BY filled_at DESC",
    #           session_id,
    #       )
    #   else:
    #       rows = await db.pool.fetch(
    #           "SELECT * FROM pm.fills WHERE session_id = $1 ORDER BY filled_at DESC",
    #           session_id,
    #       )
    #   return [PolymarketFillResponse(**dict(r)) for r in rows]

    return []


# ---------------------------------------------------------------------------
# Order-book snapshots
# ---------------------------------------------------------------------------


@router.get(
    "/polymarket/sessions/{session_id}/snapshots",
    response_model=PolymarketSnapshotListResponse,
    summary="List order-book snapshots for a session",
    description="Return paginated order-book snapshots recorded during the session.",
)
async def list_session_snapshots(
    session_id: UUID,
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(100, ge=1, le=1000, description="Results per page"),
    db: Session = Depends(get_db),
) -> PolymarketSnapshotListResponse:
    """
    Fetch snapshots from pm.orderbook_snapshots for the given session.

    SQL target:
        SELECT * FROM pm.orderbook_snapshots
        WHERE session_id = $1
        ORDER BY recorded_at ASC
        LIMIT $2 OFFSET $3;
    """
    # TODO: Replace stub with real asyncpg query once the DB pool is wired up.
    # Example (asyncpg):
    #
    #   offset = (page - 1) * page_size
    #   rows = await db.pool.fetch(
    #       "SELECT * FROM pm.orderbook_snapshots WHERE session_id = $1 "
    #       "ORDER BY recorded_at ASC LIMIT $2 OFFSET $3",
    #       session_id, page_size, offset,
    #   )
    #   return [PolymarketSnapshotResponse(**dict(r)) for r in rows]

    return PolymarketSnapshotListResponse(snapshots=[], total=0, page=page, page_size=page_size)


# ---------------------------------------------------------------------------
# PnL
# ---------------------------------------------------------------------------


@router.get(
    "/polymarket/sessions/{session_id}/pnl",
    response_model=PolymarketPnLResponse,
    summary="Get PnL snapshot for a session",
    description="Return the latest PnL snapshot for the given session.",
)
async def get_session_pnl(
    session_id: UUID,
    db: Session = Depends(get_db),
) -> PolymarketPnLResponse:
    """
    Fetch the most recent row from pm.pnl_snapshots for the given session.

    SQL target:
        SELECT * FROM pm.pnl_snapshots
        WHERE session_id = $1
        ORDER BY recorded_at DESC
        LIMIT 1;

    Raises:
        HTTPException: 404 if no PnL snapshot exists for the session.
    """
    # TODO: Replace stub with real asyncpg query once the DB pool is wired up.
    # Example (asyncpg):
    #
    #   row = await db.pool.fetchrow(
    #       "SELECT * FROM pm.pnl_snapshots WHERE session_id = $1 ORDER BY recorded_at DESC LIMIT 1",
    #       session_id,
    #   )
    #   if row is None:
    #       raise HTTPException(status_code=404, detail=f"No PnL data found for session '{session_id}'")
    #   return PolymarketPnLResponse(**dict(row))

    raise HTTPException(status_code=404, detail=f"No PnL data found for session '{session_id}'")


# ---------------------------------------------------------------------------
# Toxic-flow analytics
# ---------------------------------------------------------------------------


@router.get(
    "/polymarket/sessions/{session_id}/toxic-flow",
    response_model=List[PolymarketToxicFlowResponse],
    summary="Get toxic-flow analytics for a session",
    description="Return per-minute toxic-flow metrics for the given session.",
)
async def get_session_toxic_flow(
    session_id: UUID,
    db: Session = Depends(get_db),
) -> List[PolymarketToxicFlowResponse]:
    """
    Fetch rows from pm.toxic_flow_metrics for the given session.

    SQL target:
        SELECT * FROM pm.toxic_flow_metrics
        WHERE session_id = $1
        ORDER BY minute_bucket ASC;
    """
    # TODO: Replace stub with real asyncpg query once the DB pool is wired up.
    # Example (asyncpg):
    #
    #   rows = await db.pool.fetch(
    #       "SELECT * FROM pm.toxic_flow_metrics WHERE session_id = $1 ORDER BY minute_bucket ASC",
    #       session_id,
    #   )
    #   return [PolymarketToxicFlowResponse(**dict(r)) for r in rows]

    return []
