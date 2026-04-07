from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from services.api.dependencies import get_db

router = APIRouter()


class FleetStrategyStatus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    strategy_id: str
    name: str
    status: Literal["active", "paused", "cooldown", "abstain"]
    mode: Literal["paper", "live"]
    current_regime: Optional[str] = None
    pnl_24h_usd: Optional[float] = None
    sharpe_7d: Optional[float] = None
    fill_rate: Optional[float] = Field(None, ge=0, le=1)
    allocation_weight: Optional[float] = Field(None, ge=0, le=1)
    regime_alignment: Optional[float] = Field(None, ge=0, le=1)
    signal_count_24h: Optional[int] = None


class RegimeTimelinePoint(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    timestamp: datetime
    regime: str
    allocation_weights: Dict[str, float]


class StrategyComparisonRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    strategy_id: str
    baseline: str
    sharpe_7d: float
    sortino_7d: float
    win_rate: float
    max_drawdown: float
    profit_factor: float


class FleetStatus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    generated_at: datetime
    current_regime: Optional[str] = None
    current_mode: Literal["paper", "live"]
    strategies: List[FleetStrategyStatus]
    regime_timeline: List[RegimeTimelinePoint]
    comparison: List[StrategyComparisonRow]


class FleetSignal(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    signal_id: str
    timestamp: datetime
    strategy_id: str
    market_id: str
    signal_type: str
    direction: Literal["long", "short", "none", "abstain"]
    confidence: float = Field(..., ge=0, le=1)
    action_taken: Literal["executed", "rejected", "abstained", "cancelled"]
    fill_price: Optional[float] = None
    regime: Optional[str] = None


class PaperTradeRow(BaseModel):
    """
    Truthful shape backed by pm.paper_trades.

    NOTE: This intentionally does not attempt to fabricate per-trade P&L.
    """

    model_config = ConfigDict(from_attributes=True)

    trade_id: str
    executed_at: datetime
    strategy_id: str
    market_id: str
    side: Literal["BUY", "SELL", "NONE"]
    price: float
    quantity: float
    notional: float
    confidence: float = Field(..., ge=0, le=1)
    status: str
    regime: Optional[str] = None
    allocation_weight: float = Field(..., ge=0)


@router.get("/fleet/status", response_model=FleetStatus, summary="Get fleet status")
async def get_fleet_status(db: Session = Depends(get_db)) -> FleetStatus:
    try:
        row = db.execute(
            text(
                """
                SELECT captured_at, mode, payload
                FROM pm.fleet_status_snapshots
                ORDER BY captured_at DESC
                LIMIT 1
                """
            )
        ).mappings().fetchone()
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Fleet status not available (DB not configured or migrations not applied)",
        ) from exc

    if row is None:
        raise HTTPException(status_code=503, detail="Fleet status not available (no snapshots yet)")

    payload = row.get("payload") or {}
    mode_raw = str(payload.get("mode") or row.get("mode") or "paper").lower()
    current_mode: Literal["paper", "live"] = "live" if mode_raw == "live" else "paper"

    strategies_payload = payload.get("strategies") or []
    strategies: List[FleetStrategyStatus] = []
    for s in strategies_payload:
        if not isinstance(s, dict):
            continue
        lifecycle = str(s.get("status") or "active").lower()
        status: Literal["active", "paused", "cooldown", "abstain"] = "active"
        if lifecycle == "paused":
            status = "paused"
        elif lifecycle == "cooldown":
            status = "cooldown"
        elif lifecycle == "abstain":
            status = "abstain"

        weight = s.get("current_allocation_weight")
        try:
            weight_f = float(weight) if weight is not None else None
        except Exception:
            weight_f = None

        sid = str(s.get("strategy_id") or "")
        if not sid:
            continue
        strategies.append(
            FleetStrategyStatus(
                strategy_id=sid,
                name=sid,
                status=status,
                mode=current_mode,
                allocation_weight=weight_f,
            )
        )

    return FleetStatus(
        generated_at=row["captured_at"],
        current_regime=None,
        current_mode=current_mode,
        strategies=strategies,
        regime_timeline=[],
        comparison=[],
    )


@router.get("/fleet/signals", response_model=List[FleetSignal], summary="Get fleet signal log")
async def get_fleet_signals(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> List[FleetSignal]:
    try:
        rows = db.execute(
            text(
                """
                SELECT signal_id, recorded_at, strategy_id, market_id, signal_type, direction,
                       confidence, action_taken, fill_price, regime
                FROM pm.fleet_signals
                ORDER BY recorded_at DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        ).mappings().all()
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Fleet signals not available (DB not configured or migrations not applied)",
        ) from exc

    out: List[FleetSignal] = []
    for r in rows:
        direction = str(r.get("direction") or "none")
        if direction not in ("long", "short", "none", "abstain"):
            direction = "none"
        action_taken = str(r.get("action_taken") or "executed")
        if action_taken not in ("executed", "rejected", "abstained", "cancelled"):
            action_taken = "executed"
        out.append(
            FleetSignal(
                signal_id=str(r["signal_id"]),
                timestamp=r["recorded_at"],
                strategy_id=str(r["strategy_id"]),
                market_id=str(r["market_id"]),
                signal_type=str(r["signal_type"]),
                direction=direction,  # type: ignore[arg-type]
                confidence=float(r.get("confidence") or 0),
                action_taken=action_taken,  # type: ignore[arg-type]
                fill_price=float(r["fill_price"]) if r.get("fill_price") is not None else None,
                regime=str(r["regime"]) if r.get("regime") is not None else None,
            )
        )
    return out


@router.get("/fleet/paper-trades", response_model=List[PaperTradeRow], summary="Get paper trades")
async def get_paper_trades(
    start: Optional[datetime] = Query(None),
    end: Optional[datetime] = Query(None),
    strategy_id: Optional[str] = Query(None),
    market_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
) -> List[PaperTradeRow]:
    if start is not None and end is not None and start >= end:
        raise HTTPException(status_code=422, detail="Query parameter 'start' must be before 'end'")

    where: List[str] = []
    params: dict = {"limit": limit}
    if start is not None:
        where.append("executed_at >= :start")
        params["start"] = start
    if end is not None:
        where.append("executed_at <= :end")
        params["end"] = end
    if strategy_id is not None:
        where.append("strategy_id = :strategy_id")
        params["strategy_id"] = strategy_id
    if market_id is not None:
        where.append("market_id = :market_id")
        params["market_id"] = market_id

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    sql = text(
        f"""
        SELECT trade_id, executed_at, strategy_id, market_id, side, price, quantity, notional,
               confidence, status, regime, allocation_weight
        FROM pm.paper_trades
        {where_sql}
        ORDER BY executed_at DESC
        LIMIT :limit
        """
    )

    try:
        rows = db.execute(sql, params).mappings().all()
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Fleet paper trades not available (DB not configured or migrations not applied)",
        ) from exc

    out: List[PaperTradeRow] = []
    for r in rows:
        out.append(
            PaperTradeRow(
                trade_id=str(r["trade_id"]),
                executed_at=r["executed_at"],
                strategy_id=str(r["strategy_id"]),
                market_id=str(r["market_id"]),
                side=str(r["side"]),
                price=float(r["price"]),
                quantity=float(r["quantity"]),
                notional=float(r["notional"]),
                confidence=float(r["confidence"]),
                status=str(r["status"]),
                regime=str(r["regime"]) if r.get("regime") is not None else None,
                allocation_weight=float(r.get("allocation_weight") or Decimal("0")),
            )
        )
    return out
