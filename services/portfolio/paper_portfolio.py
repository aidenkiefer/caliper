from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
from typing import Any, Dict, Iterable, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session


MARK_SPREAD_MAX = Decimal("0.05")  # Polymarket spread threshold


def _d(value: Any, default: str = "0") -> Decimal:
    if value is None:
        return Decimal(default)
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass
class DerivedPosition:
    surface: str  # "equity" | "polymarket"
    strategy_id: str
    instrument_id: str  # equity symbol or polymarket market_id
    quantity: Decimal
    avg_cost: Decimal
    mark_price: Optional[Decimal]
    mark_source: str
    market_value: Optional[Decimal]
    unrealized_pnl: Optional[Decimal]


@dataclass
class SleeveState:
    strategy_id: str
    starting_capital_usd: Decimal
    cash_usd: Decimal
    deployed_capital_usd: Decimal
    positions_value_usd: Decimal
    equity_usd: Decimal
    realized_pnl_usd: Decimal
    unrealized_pnl_usd: Decimal
    updated_at: datetime
    positions: List[DerivedPosition]
    metadata: Dict[str, Any]


@dataclass
class PortfolioState:
    starting_capital_usd: Decimal
    cash_usd: Decimal
    deployed_capital_usd: Decimal
    positions_value_usd: Decimal
    equity_usd: Decimal
    realized_pnl_usd: Decimal
    unrealized_pnl_usd: Decimal
    updated_at: datetime
    sleeves: List[SleeveState]
    metadata: Dict[str, Any]


def list_strategy_ids(db: Session) -> List[str]:
    rows = db.execute(
        text(
            """
            SELECT DISTINCT strategy_id FROM (
                SELECT strategy_id FROM paper.allocations
                UNION ALL
                SELECT strategy_id FROM paper.equity_fills
                UNION ALL
                SELECT strategy_id FROM pm.paper_trades
            ) s
            """
        )
    ).fetchall()
    return sorted({r[0] for r in rows if r and r[0]})


def _load_allocations_sum(db: Session, strategy_id: Optional[str] = None) -> Decimal:
    if strategy_id is None:
        val = db.execute(text("SELECT COALESCE(SUM(amount_usd), 0) FROM paper.allocations")).scalar()
        return _d(val)
    val = db.execute(
        text("SELECT COALESCE(SUM(amount_usd), 0) FROM paper.allocations WHERE strategy_id = :sid"),
        {"sid": strategy_id},
    ).scalar()
    return _d(val)


def _load_equity_fills(db: Session, strategy_id: str) -> List[dict]:
    rows = db.execute(
        text(
            """
            SELECT filled_at, symbol, side, quantity, price, fees_usd
            FROM paper.equity_fills
            WHERE strategy_id = :sid
            ORDER BY filled_at ASC
            """
        ),
        {"sid": strategy_id},
    ).mappings()
    return [dict(r) for r in rows]


def _load_pm_trades(db: Session, strategy_id: str) -> List[dict]:
    rows = db.execute(
        text(
            """
            SELECT executed_at, market_id, side, quantity, price, notional
            FROM pm.paper_trades
            WHERE strategy_id = :sid
            ORDER BY executed_at ASC
            """
        ),
        {"sid": strategy_id},
    ).mappings()
    return [dict(r) for r in rows]


def _pm_mark(db: Session) -> Tuple[Optional[Decimal], str]:
    """
    Return (mark_price, mark_source) for Polymarket positions.

    Uses the latest pm.orderbook_snapshots row (single-market feed assumption).
    Mark rules:
    - midpoint if spread <= 0.05 and midpoint exists
    - else last_trade_price if present
    - else midpoint/best_bid/best_ask midpoint fallback
    """
    row = db.execute(
        text(
            """
            SELECT midpoint, spread, best_bid, best_ask, last_trade_price
            FROM pm.orderbook_snapshots
            ORDER BY timestamp DESC
            LIMIT 1
            """
        )
    ).fetchone()
    if not row:
        return None, "pm_missing"

    midpoint, spread, best_bid, best_ask, last_trade = row
    midpoint_d = _d(midpoint) if midpoint is not None else None
    spread_d = _d(spread) if spread is not None else None
    best_bid_d = _d(best_bid) if best_bid is not None else None
    best_ask_d = _d(best_ask) if best_ask is not None else None
    last_trade_d = _d(last_trade) if last_trade is not None else None

    if midpoint_d is not None and spread_d is not None and spread_d <= MARK_SPREAD_MAX:
        return midpoint_d, "pm_mid"

    if last_trade_d is not None:
        return last_trade_d, "pm_last_trade"

    if midpoint_d is not None:
        return midpoint_d, "pm_mid_fallback"

    if best_bid_d is not None and best_ask_d is not None:
        return (best_bid_d + best_ask_d) / Decimal("2"), "pm_top_mid_fallback"

    return None, "pm_missing"


def _equity_mark_from_last_fill(fills: Iterable[dict], symbol: str) -> Optional[Decimal]:
    last_price: Optional[Decimal] = None
    for f in fills:
        if f.get("symbol") == symbol:
            last_price = _d(f.get("price"))
    return last_price


def _apply_avg_cost_fills(
    fills: Iterable[dict],
    *,
    instrument_key: str,
    side_key: str,
    qty_key: str,
    price_key: str,
) -> Tuple[Dict[str, Dict[str, Decimal]], Dict[str, Decimal]]:
    """
    Return (positions, realized_pnl_by_instrument).

    positions[instrument] = {"qty": ..., "avg_cost": ...}
    """
    positions: Dict[str, Dict[str, Decimal]] = {}
    realized: Dict[str, Decimal] = {}

    for f in fills:
        instrument = str(f[instrument_key])
        side = str(f[side_key]).upper()
        qty = _d(f[qty_key])
        price = _d(f[price_key])
        if qty <= 0:
            continue

        pos = positions.get(instrument, {"qty": Decimal("0"), "avg_cost": Decimal("0")})
        cur_qty = pos["qty"]
        avg_cost = pos["avg_cost"]

        if side == "BUY":
            new_qty = cur_qty + qty
            if new_qty > 0:
                new_avg = (cur_qty * avg_cost + qty * price) / new_qty
            else:
                new_avg = Decimal("0")
            positions[instrument] = {"qty": new_qty, "avg_cost": new_avg}
        elif side == "SELL":
            sell_qty = min(qty, cur_qty) if cur_qty > 0 else Decimal("0")
            if sell_qty > 0:
                realized[instrument] = realized.get(instrument, Decimal("0")) + (price - avg_cost) * sell_qty
                new_qty = cur_qty - sell_qty
                if new_qty == 0:
                    positions[instrument] = {"qty": Decimal("0"), "avg_cost": Decimal("0")}
                else:
                    positions[instrument] = {"qty": new_qty, "avg_cost": avg_cost}
        else:
            continue

    # Strip zero qty positions
    positions = {k: v for k, v in positions.items() if v["qty"] != 0}
    return positions, realized


def compute_strategy_sleeve(db: Session, strategy_id: str, *, as_of: Optional[datetime] = None) -> SleeveState:
    as_of = as_of or datetime.now(timezone.utc)

    starting_capital = _load_allocations_sum(db, strategy_id)

    equity_fills = _load_equity_fills(db, strategy_id)
    pm_trades = _load_pm_trades(db, strategy_id)

    equity_positions, equity_realized_by_symbol = _apply_avg_cost_fills(
        equity_fills,
        instrument_key="symbol",
        side_key="side",
        qty_key="quantity",
        price_key="price",
    )
    pm_positions, pm_realized_by_market = _apply_avg_cost_fills(
        pm_trades,
        instrument_key="market_id",
        side_key="side",
        qty_key="quantity",
        price_key="price",
    )

    # Cashflows
    buys_notional = sum(
        _d(f["quantity"]) * _d(f["price"])
        for f in equity_fills
        if str(f.get("side", "")).upper() == "BUY"
    )
    sells_notional = sum(
        _d(f["quantity"]) * _d(f["price"])
        for f in equity_fills
        if str(f.get("side", "")).upper() == "SELL"
    )
    fees = sum(_d(f.get("fees_usd")) for f in equity_fills)

    pm_buys = sum(_d(f.get("notional")) for f in pm_trades if str(f.get("side", "")).upper() == "BUY")
    pm_sells = sum(_d(f.get("notional")) for f in pm_trades if str(f.get("side", "")).upper() == "SELL")

    cash = starting_capital - buys_notional - fees + sells_notional - pm_buys + pm_sells

    # Marks
    pm_mark, pm_mark_source = _pm_mark(db)

    positions: List[DerivedPosition] = []
    deployed = Decimal("0")
    positions_value = Decimal("0")
    realized_total = sum(equity_realized_by_symbol.values(), Decimal("0")) + sum(pm_realized_by_market.values(), Decimal("0")) - fees
    unrealized_total = Decimal("0")

    for symbol, pos in equity_positions.items():
        qty = pos["qty"]
        avg_cost = pos["avg_cost"]
        mark = _equity_mark_from_last_fill(equity_fills, symbol) or avg_cost
        mv = qty * mark
        upnl = (mark - avg_cost) * qty
        deployed += abs(qty) * avg_cost
        positions_value += mv
        unrealized_total += upnl
        positions.append(
            DerivedPosition(
                surface="equity",
                strategy_id=strategy_id,
                instrument_id=symbol,
                quantity=qty,
                avg_cost=avg_cost,
                mark_price=mark,
                mark_source="equity_last_fill",
                market_value=mv,
                unrealized_pnl=upnl,
            )
        )

    for market_id, pos in pm_positions.items():
        qty = pos["qty"]
        avg_cost = pos["avg_cost"]
        mark = pm_mark or avg_cost
        mv = qty * mark if mark is not None else None
        upnl = (mark - avg_cost) * qty if mark is not None else None
        deployed += abs(qty) * avg_cost
        if mv is not None:
            positions_value += mv
        if upnl is not None:
            unrealized_total += upnl
        positions.append(
            DerivedPosition(
                surface="polymarket",
                strategy_id=strategy_id,
                instrument_id=market_id,
                quantity=qty,
                avg_cost=avg_cost,
                mark_price=mark,
                mark_source=pm_mark_source,
                market_value=mv,
                unrealized_pnl=upnl,
            )
        )

    equity = cash + positions_value
    return SleeveState(
        strategy_id=strategy_id,
        starting_capital_usd=starting_capital,
        cash_usd=cash,
        deployed_capital_usd=deployed,
        positions_value_usd=positions_value,
        equity_usd=equity,
        realized_pnl_usd=realized_total,
        unrealized_pnl_usd=unrealized_total,
        updated_at=as_of,
        positions=positions,
        metadata={"pm_mark_source": pm_mark_source},
    )


def compute_portfolio(db: Session, *, as_of: Optional[datetime] = None) -> PortfolioState:
    as_of = as_of or datetime.now(timezone.utc)
    strategy_ids = list_strategy_ids(db)
    sleeves = [compute_strategy_sleeve(db, sid, as_of=as_of) for sid in strategy_ids]

    starting = sum((s.starting_capital_usd for s in sleeves), Decimal("0"))
    cash = sum((s.cash_usd for s in sleeves), Decimal("0"))
    deployed = sum((s.deployed_capital_usd for s in sleeves), Decimal("0"))
    pv = sum((s.positions_value_usd for s in sleeves), Decimal("0"))
    eq = sum((s.equity_usd for s in sleeves), Decimal("0"))
    realized = sum((s.realized_pnl_usd for s in sleeves), Decimal("0"))
    unrealized = sum((s.unrealized_pnl_usd for s in sleeves), Decimal("0"))

    return PortfolioState(
        starting_capital_usd=starting,
        cash_usd=cash,
        deployed_capital_usd=deployed,
        positions_value_usd=pv,
        equity_usd=eq,
        realized_pnl_usd=realized,
        unrealized_pnl_usd=unrealized,
        updated_at=as_of,
        sleeves=sleeves,
        metadata={},
    )


def write_equity_snapshot(
    db: Session,
    *,
    timestamp: datetime,
    strategy_id: Optional[str],
    starting_capital_usd: Decimal,
    cash_usd: Decimal,
    deployed_capital_usd: Decimal,
    positions_value_usd: Decimal,
    equity_usd: Decimal,
    realized_pnl_usd: Decimal,
    unrealized_pnl_usd: Decimal,
    mark_source: Optional[str],
    metadata: Optional[dict] = None,
) -> None:
    db.execute(
        text(
            """
            INSERT INTO paper.equity_snapshots(
              timestamp, strategy_id,
              starting_capital_usd, cash_usd, deployed_capital_usd,
              positions_value_usd, equity_usd,
              realized_pnl_usd, unrealized_pnl_usd,
              mark_source, metadata
            )
            VALUES (
              :ts, :sid,
              :starting, :cash, :deployed,
              :pv, :eq,
              :realized, :unrealized,
              :mark_source, CAST(:meta AS jsonb)
            )
            """
        ),
        {
            "ts": timestamp,
            "sid": strategy_id,
            "starting": str(starting_capital_usd),
            "cash": str(cash_usd),
            "deployed": str(deployed_capital_usd),
            "pv": str(positions_value_usd),
            "eq": str(equity_usd),
            "realized": str(realized_pnl_usd),
            "unrealized": str(unrealized_pnl_usd),
            "mark_source": mark_source,
            "meta": json.dumps(metadata or {}, default=str),
        },
    )


def snapshot_strategy_and_portfolio(db: Session, strategy_id: str, *, as_of: Optional[datetime] = None) -> None:
    as_of = as_of or datetime.now(timezone.utc)
    sleeve = compute_strategy_sleeve(db, strategy_id, as_of=as_of)
    write_equity_snapshot(
        db,
        timestamp=as_of,
        strategy_id=strategy_id,
        starting_capital_usd=sleeve.starting_capital_usd,
        cash_usd=sleeve.cash_usd,
        deployed_capital_usd=sleeve.deployed_capital_usd,
        positions_value_usd=sleeve.positions_value_usd,
        equity_usd=sleeve.equity_usd,
        realized_pnl_usd=sleeve.realized_pnl_usd,
        unrealized_pnl_usd=sleeve.unrealized_pnl_usd,
        mark_source=sleeve.metadata.get("pm_mark_source"),
        metadata={"strategy_id": strategy_id},
    )

    portfolio = compute_portfolio(db, as_of=as_of)
    write_equity_snapshot(
        db,
        timestamp=as_of,
        strategy_id=None,
        starting_capital_usd=portfolio.starting_capital_usd,
        cash_usd=portfolio.cash_usd,
        deployed_capital_usd=portfolio.deployed_capital_usd,
        positions_value_usd=portfolio.positions_value_usd,
        equity_usd=portfolio.equity_usd,
        realized_pnl_usd=portfolio.realized_pnl_usd,
        unrealized_pnl_usd=portfolio.unrealized_pnl_usd,
        mark_source=None,
        metadata={"kind": "portfolio"},
    )


def snapshot_all_strategies_and_portfolio(db: Session, *, as_of: Optional[datetime] = None) -> None:
    """
    Compute all sleeves + portfolio once and persist snapshots.

    Useful for "refresh" endpoints and read-path opportunistic snapshotting.
    """
    as_of = as_of or datetime.now(timezone.utc)
    portfolio = compute_portfolio(db, as_of=as_of)
    for sleeve in portfolio.sleeves:
        write_equity_snapshot(
            db,
            timestamp=as_of,
            strategy_id=sleeve.strategy_id,
            starting_capital_usd=sleeve.starting_capital_usd,
            cash_usd=sleeve.cash_usd,
            deployed_capital_usd=sleeve.deployed_capital_usd,
            positions_value_usd=sleeve.positions_value_usd,
            equity_usd=sleeve.equity_usd,
            realized_pnl_usd=sleeve.realized_pnl_usd,
            unrealized_pnl_usd=sleeve.unrealized_pnl_usd,
            mark_source=sleeve.metadata.get("pm_mark_source"),
            metadata={"strategy_id": sleeve.strategy_id},
        )
    write_equity_snapshot(
        db,
        timestamp=as_of,
        strategy_id=None,
        starting_capital_usd=portfolio.starting_capital_usd,
        cash_usd=portfolio.cash_usd,
        deployed_capital_usd=portfolio.deployed_capital_usd,
        positions_value_usd=portfolio.positions_value_usd,
        equity_usd=portfolio.equity_usd,
        realized_pnl_usd=portfolio.realized_pnl_usd,
        unrealized_pnl_usd=portfolio.unrealized_pnl_usd,
        mark_source=None,
        metadata={"kind": "portfolio"},
    )


def maybe_refresh_snapshot_for_strategy(
    db: Session,
    strategy_id: str,
    *,
    as_of: Optional[datetime] = None,
    staleness_seconds: int = 30,
) -> None:
    """
    Best-effort: if latest snapshot is older than latest allocation/fill event,
    write a fresh snapshot.
    """
    as_of = as_of or datetime.now(timezone.utc)
    latest_event = db.execute(
        text(
            """
            SELECT GREATEST(
              COALESCE((SELECT MAX(allocated_at) FROM paper.allocations WHERE strategy_id = :sid), 'epoch'::timestamptz),
              COALESCE((SELECT MAX(filled_at) FROM paper.equity_fills WHERE strategy_id = :sid), 'epoch'::timestamptz),
              COALESCE((SELECT MAX(executed_at) FROM pm.paper_trades WHERE strategy_id = :sid), 'epoch'::timestamptz)
            ) AS latest_event
            """
        ),
        {"sid": strategy_id},
    ).scalar()
    latest_event_dt = latest_event if isinstance(latest_event, datetime) else None

    latest_snapshot = db.execute(
        text(
            """
            SELECT MAX(timestamp)
            FROM paper.equity_snapshots
            WHERE strategy_id = :sid
            """
        ),
        {"sid": strategy_id},
    ).scalar()
    latest_snapshot_dt = latest_snapshot if isinstance(latest_snapshot, datetime) else None

    if latest_event_dt is None:
        return

    if latest_snapshot_dt is None:
        snapshot_strategy_and_portfolio(db, strategy_id, as_of=as_of)
        return

    # Refresh when behind latest event or simply stale.
    if latest_snapshot_dt < latest_event_dt or (as_of - latest_snapshot_dt) > timedelta(seconds=staleness_seconds):
        snapshot_strategy_and_portfolio(db, strategy_id, as_of=as_of)
