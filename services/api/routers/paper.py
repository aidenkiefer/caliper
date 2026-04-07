"""
Paper-capital ledger endpoints (Phase 1).

This ledger is the source of truth for portfolio equity + P&L during the
paper-trading phase, where each bot/strategy is allocated a fixed amount of
paper USD on a recurring cadence (e.g., $100/week).

The API is intentionally minimal and append-only:
- allocations: add paper capital to a strategy
- pnl events: record realized/unrealized P&L deltas for a strategy

Downstream KPIs are computed from these tables by /v1/metrics/summary.
"""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from services.api.dependencies import get_db
from services.portfolio.paper_portfolio import (
    snapshot_all_strategies_and_portfolio,
    snapshot_strategy_and_portfolio,
)

router = APIRouter(prefix="/paper")


class PaperAllocationCreate(BaseModel):
    strategy_id: str = Field(..., description="Bot/strategy identifier")
    amount_usd: Decimal = Field(..., gt=0, description="Paper USD allocated")
    allocated_at: Optional[datetime] = Field(None, description="Override allocation time (UTC)")
    note: Optional[str] = Field(None, description="Optional note (e.g., weekly funding)")


class PaperPnlEventCreate(BaseModel):
    strategy_id: str = Field(..., description="Bot/strategy identifier")
    pnl_usd: Decimal = Field(..., description="PnL delta in USD (positive or negative)")
    occurred_at: Optional[datetime] = Field(None, description="Override event time (UTC)")
    source: Optional[str] = Field(None, description="Source tag (fills, mark, manual, etc.)")
    note: Optional[str] = Field(None, description="Optional note")


class PaperLedgerRow(BaseModel):
    id: int
    strategy_id: str
    amount_usd: Optional[Decimal] = None
    pnl_usd: Optional[Decimal] = None
    timestamp: datetime
    kind: Literal["allocation", "pnl"]
    source: Optional[str] = None
    note: Optional[str] = None


class EquityFillCreate(BaseModel):
    strategy_id: str = Field(..., description="Bot/strategy identifier")
    symbol: str = Field(..., description="Equity symbol")
    side: Literal["BUY", "SELL"] = Field(..., description="Fill side")
    quantity: Decimal = Field(..., gt=0, description="Filled quantity")
    price: Decimal = Field(..., gt=0, description="Fill price")
    fees_usd: Decimal = Field(Decimal("0"), ge=0, description="Fees in USD")
    venue: str = Field("alpaca_paper", description="Execution venue identifier")
    client_order_id: Optional[str] = Field(None, description="Client order id (idempotency)")
    broker_order_id: Optional[str] = Field(None, description="Broker order id")
    filled_at: Optional[datetime] = Field(None, description="Override fill time (UTC)")
    metadata: dict = Field(default_factory=dict, description="Extra metadata")


@router.post(
    "/allocations",
    summary="Allocate paper capital to a strategy",
)
def create_allocation(body: PaperAllocationCreate, db: Session = Depends(get_db)) -> dict:
    try:
        result = db.execute(
            text(
                """
                INSERT INTO paper.allocations(strategy_id, amount_usd, allocated_at, note)
                VALUES (:strategy_id, :amount_usd, COALESCE(:allocated_at, NOW()), :note)
                RETURNING allocation_id;
                """
            ),
            {
                "strategy_id": body.strategy_id,
                "amount_usd": str(body.amount_usd),
                "allocated_at": body.allocated_at,
                "note": body.note,
            },
        ).fetchone()
        # Snapshot on allocation event (best-effort).
        try:
            snapshot_strategy_and_portfolio(db, body.strategy_id)
        except Exception:
            # Snapshot tables may not exist yet or mark sources may be unavailable.
            pass
        db.commit()
        return {"allocation_id": int(result[0])}
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Paper ledger not available (DB not configured or migrations not applied)",
        ) from exc


@router.post(
    "/pnl-events",
    summary="Record a P&L event for a strategy",
)
def create_pnl_event(body: PaperPnlEventCreate, db: Session = Depends(get_db)) -> dict:
    try:
        result = db.execute(
            text(
                """
                INSERT INTO paper.pnl_events(strategy_id, pnl_usd, occurred_at, source, note)
                VALUES (:strategy_id, :pnl_usd, COALESCE(:occurred_at, NOW()), :source, :note)
                RETURNING event_id;
                """
            ),
            {
                "strategy_id": body.strategy_id,
                "pnl_usd": str(body.pnl_usd),
                "occurred_at": body.occurred_at,
                "source": body.source,
                "note": body.note,
            },
        ).fetchone()
        # Snapshot on adjustment event (best-effort).
        try:
            snapshot_strategy_and_portfolio(db, body.strategy_id)
        except Exception:
            pass
        db.commit()
        return {"event_id": int(result[0])}
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Paper ledger not available (DB not configured or migrations not applied)",
        ) from exc


@router.post(
    "/equity-fills",
    summary="Ingest an equities paper fill (strategy-attributed)",
)
def create_equity_fill(body: EquityFillCreate, db: Session = Depends(get_db)) -> dict:
    try:
        row = db.execute(
            text(
                """
                INSERT INTO paper.equity_fills(
                  filled_at, strategy_id, symbol, side, quantity, price, fees_usd,
                  venue, client_order_id, broker_order_id, metadata
                )
                VALUES (
                  COALESCE(:filled_at, NOW()), :strategy_id, :symbol, :side, :quantity, :price, :fees_usd,
                  :venue, :client_order_id, :broker_order_id, :metadata::jsonb
                )
                RETURNING fill_id;
                """
            ),
            {
                "filled_at": body.filled_at,
                "strategy_id": body.strategy_id,
                "symbol": body.symbol,
                "side": body.side,
                "quantity": str(body.quantity),
                "price": str(body.price),
                "fees_usd": str(body.fees_usd),
                "venue": body.venue,
                "client_order_id": body.client_order_id,
                "broker_order_id": body.broker_order_id,
                "metadata": json.dumps(body.metadata or {}, default=str),
            },
        ).fetchone()
        # Snapshot on fill event (best-effort).
        try:
            snapshot_strategy_and_portfolio(db, body.strategy_id)
        except Exception:
            pass
        db.commit()
        return {"fill_id": str(row[0])}
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Paper portfolio store not available (DB not configured or migrations not applied)",
        ) from exc


@router.post(
    "/snapshots/compute",
    summary="Compute and persist paper equity snapshots (debug/ops)",
)
def compute_snapshots(db: Session = Depends(get_db)) -> dict:
    try:
        snapshot_all_strategies_and_portfolio(db)
        db.commit()
        return {"status": "ok"}
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Paper portfolio store not available (DB not configured or migrations not applied)",
        ) from exc


@router.get(
    "/ledger",
    response_model=list[PaperLedgerRow],
    summary="Unified paper ledger feed",
)
def list_ledger(
    strategy_id: Optional[str] = Query(None, description="Filter by strategy_id"),
    limit: int = Query(200, ge=1, le=2000),
    db: Session = Depends(get_db),
) -> list[PaperLedgerRow]:
    try:
        rows = db.execute(
            text(
                """
                WITH alloc AS (
                  SELECT
                    allocation_id AS id,
                    strategy_id,
                    amount_usd,
                    NULL::NUMERIC AS pnl_usd,
                    allocated_at AS ts,
                    'allocation'::TEXT AS kind,
                    NULL::TEXT AS source,
                    note
                  FROM paper.allocations
                  WHERE (:strategy_id IS NULL OR strategy_id = :strategy_id)
                ),
                pnl AS (
                  SELECT
                    event_id AS id,
                    strategy_id,
                    NULL::NUMERIC AS amount_usd,
                    pnl_usd,
                    occurred_at AS ts,
                    'pnl'::TEXT AS kind,
                    source,
                    note
                  FROM paper.pnl_events
                  WHERE (:strategy_id IS NULL OR strategy_id = :strategy_id)
                )
                SELECT * FROM alloc
                UNION ALL
                SELECT * FROM pnl
                ORDER BY ts DESC
                LIMIT :limit;
                """
            ),
            {"strategy_id": strategy_id, "limit": limit},
        ).mappings()
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Paper ledger not available (DB not configured or migrations not applied)",
        ) from exc

    out: list[PaperLedgerRow] = []
    for r in rows:
        out.append(
            PaperLedgerRow(
                id=int(r["id"]),
                strategy_id=r["strategy_id"],
                amount_usd=r["amount_usd"],
                pnl_usd=r["pnl_usd"],
                timestamp=r["ts"],
                kind=r["kind"],
                source=r["source"],
                note=r["note"],
            )
        )
    return out
