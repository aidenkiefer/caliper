"""
Positions endpoints.

Provides endpoints for viewing open positions.

NOTE
----
This endpoint is meant to be "no dummy data": it derives open positions from
the runtime paper portfolio layer (fills + marks). If marks are unavailable
(e.g. Polymarket orderbook snapshots not being recorded), the endpoint returns
503 instead of fabricating prices/PnL.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from packages.common.api_schemas import (
    EntryOrder,
    PositionDetailData,
    PositionDetailResponse,
    PositionItem,
    PositionListMeta,
    PositionListResponse,
)
from services.api.dependencies import get_db
from services.portfolio.paper_portfolio import compute_portfolio, DerivedPosition

router = APIRouter()


def _pos_id(p: DerivedPosition) -> str:
    return f"{p.surface}:{p.strategy_id}:{p.instrument_id}"


def _fmt_dec(v: Decimal, places: int = 2) -> str:
    q = Decimal(10) ** (-places)
    return f"{v.quantize(q):f}"


def _load_opened_at_maps(db: Session) -> Tuple[Dict[Tuple[str, str], datetime], Dict[Tuple[str, str], datetime]]:
    equity_rows = db.execute(
        text(
            """
            SELECT strategy_id, symbol, MIN(filled_at) AS opened_at
            FROM paper.equity_fills
            GROUP BY strategy_id, symbol
            """
        )
    ).fetchall()
    pm_rows = db.execute(
        text(
            """
            SELECT strategy_id, market_id, MIN(executed_at) AS opened_at
            FROM pm.paper_trades
            GROUP BY strategy_id, market_id
            """
        )
    ).fetchall()

    equity_opened = {(r[0], r[1]): r[2] for r in equity_rows if r and r[2]}
    pm_opened = {(r[0], r[1]): r[2] for r in pm_rows if r and r[2]}
    return equity_opened, pm_opened


@router.get(
    "/positions",
    response_model=PositionListResponse,
    summary="List positions",
    description="List current open positions across all strategies (paper-first).",
)
async def list_positions(
    strategy_id: Optional[str] = Query(None, description="Filter by strategy ID"),
    symbol: Optional[str] = Query(None, description="Filter by symbol / instrument ID"),
    mode: Optional[str] = Query(
        None,
        description="Filter by mode: PAPER or LIVE",
        pattern="^(PAPER|LIVE)$",
    ),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
) -> PositionListResponse:
    if mode and mode != "PAPER":
        raise HTTPException(status_code=501, detail="LIVE positions not implemented yet")

    now = datetime.now(timezone.utc)

    try:
        portfolio = compute_portfolio(db, as_of=now)
        equity_opened, pm_opened = _load_opened_at_maps(db)
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Database not available") from exc

    positions: list[PositionItem] = []
    total_unrealized = Decimal("0")

    for sleeve in portfolio.sleeves:
        if strategy_id and sleeve.strategy_id != strategy_id:
            continue
        for p in sleeve.positions:
            if symbol and p.instrument_id != symbol:
                continue

            if p.mark_price is None or p.market_value is None or p.unrealized_pnl is None:
                raise HTTPException(
                    status_code=503,
                    detail="Position marks unavailable (ensure mark sources are running and DB has snapshots)",
                )

            opened_at = None
            if p.surface == "equity":
                opened_at = equity_opened.get((p.strategy_id, p.instrument_id))
                contract_type = "STOCK"
            else:
                opened_at = pm_opened.get((p.strategy_id, p.instrument_id))
                contract_type = "POLYMARKET"

            if opened_at is None:
                opened_at = now

            days_held = max(0, int((now - opened_at).total_seconds() // 86400))

            cost_basis = (p.avg_cost * p.quantity) if p.quantity != 0 else Decimal("0")
            pnl_pct = Decimal("0")
            if cost_basis != 0:
                pnl_pct = (p.unrealized_pnl / cost_basis) * Decimal("100")

            positions.append(
                PositionItem(
                    position_id=_pos_id(p),
                    strategy_id=p.strategy_id,
                    symbol=p.instrument_id,
                    contract_type=contract_type,
                    quantity=_fmt_dec(p.quantity, places=4),
                    average_entry_price=_fmt_dec(p.avg_cost, places=4),
                    current_price=_fmt_dec(p.mark_price, places=4),
                    unrealized_pnl=_fmt_dec(p.unrealized_pnl, places=2),
                    unrealized_pnl_pct=_fmt_dec(pnl_pct, places=2),
                    market_value=_fmt_dec(p.market_value, places=2),
                    opened_at=opened_at,
                    days_held=days_held,
                )
            )
            total_unrealized += p.unrealized_pnl

    # Sort by largest market value (descending) for stability
    positions.sort(key=lambda x: Decimal(x.market_value), reverse=True)

    total = len(positions)
    start = (page - 1) * per_page
    end = start + per_page
    paginated = positions[start:end]

    return PositionListResponse(
        data=paginated,
        meta=PositionListMeta(
            total_count=total,
            page=page,
            per_page=per_page,
            total_unrealized_pnl=_fmt_dec(total_unrealized, places=2),
        ),
    )


@router.get(
    "/positions/{position_id}",
    response_model=PositionDetailResponse,
    summary="Get position details",
    description="Get detailed information for a specific position (paper-first).",
)
async def get_position(position_id: str, db: Session = Depends(get_db)) -> PositionDetailResponse:
    """
    position_id format:
      - equity:{strategy_id}:{symbol}
      - polymarket:{strategy_id}:{market_id}
    """
    parts = position_id.split(":", 2)
    if len(parts) != 3:
        raise HTTPException(status_code=404, detail=f"Position '{position_id}' not found")

    surface, strategy_id, instrument_id = parts
    surface = surface.strip().lower()

    now = datetime.now(timezone.utc)

    portfolio = compute_portfolio(db, as_of=now)
    derived: Optional[DerivedPosition] = None
    for sleeve in portfolio.sleeves:
        if sleeve.strategy_id != strategy_id:
            continue
        for p in sleeve.positions:
            if p.surface == surface and p.instrument_id == instrument_id:
                derived = p
                break
        if derived:
            break

    if derived is None:
        raise HTTPException(status_code=404, detail=f"Position '{position_id}' not found")

    if derived.unrealized_pnl is None:
        raise HTTPException(
            status_code=503,
            detail="Position marks unavailable (ensure mark sources are running)",
        )

    entry_orders: list[EntryOrder] = []

    if surface == "equity":
        rows = db.execute(
            text(
                """
                SELECT filled_at, quantity, price, side
                FROM paper.equity_fills
                WHERE strategy_id = :sid AND symbol = :sym
                ORDER BY filled_at ASC
                """
            ),
            {"sid": strategy_id, "sym": instrument_id},
        ).fetchall()
        for filled_at, quantity, price, side in rows:
            if str(side).upper() != "BUY":
                continue
            entry_orders.append(
                EntryOrder(
                    order_id=f"fill:{strategy_id}:{instrument_id}:{filled_at.isoformat()}",
                    filled_at=filled_at,
                    quantity=str(quantity),
                    price=str(price),
                )
            )
    else:
        rows = db.execute(
            text(
                """
                SELECT executed_at, quantity, price, side
                FROM pm.paper_trades
                WHERE strategy_id = :sid AND market_id = :mid
                ORDER BY executed_at ASC
                """
            ),
            {"sid": strategy_id, "mid": instrument_id},
        ).fetchall()
        for executed_at, quantity, price, side in rows:
            if str(side).upper() != "BUY":
                continue
            entry_orders.append(
                EntryOrder(
                    order_id=f"pm:{strategy_id}:{instrument_id}:{executed_at.isoformat()}",
                    filled_at=executed_at,
                    quantity=str(quantity),
                    price=str(price),
                )
            )

    return PositionDetailResponse(
        data=PositionDetailData(
            position_id=position_id,
            strategy_id=strategy_id,
            symbol=instrument_id,
            quantity=_fmt_dec(derived.quantity, places=4),
            entry_orders=entry_orders,
            unrealized_pnl=_fmt_dec(derived.unrealized_pnl, places=2),
            risk_metrics=None,
        )
    )

