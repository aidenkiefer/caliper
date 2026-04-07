"""
Metrics endpoints.

Provides aggregated metrics for the dashboard overview.
"""

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, Tuple, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from packages.common.api_schemas import (
    MetricsSummaryResponse,
    MetricsSummaryData,
    MetricsMeta,
    EquityCurvePoint,
)
from services.ml.performance.tracker import PerformanceTracker
from services.api.dependencies import get_db
from services.portfolio.paper_portfolio import (
    compute_portfolio,
    snapshot_all_strategies_and_portfolio,
)
from services.api.routers.alerts import emit_alert_db_dedup
from packages.common.api_schemas import AlertSeverity

router = APIRouter()

# Performance tracker cache (in production, use proper state management)
_performance_trackers = {}

logger = logging.getLogger(__name__)

PM_FEED_WARN_SECONDS = 60
PM_FEED_CRITICAL_SECONDS = 300
EQUITY_FEED_WARN_SECONDS = 300
EQUITY_FEED_CRITICAL_SECONDS = 900

FLEET_HEARTBEAT_WARN_SECONDS = 120
FLEET_HEARTBEAT_CRITICAL_SECONDS = 600

TOTAL_DRAWDOWN_WARN_PCT = Decimal("8.0")
TOTAL_DRAWDOWN_HALT_PCT = Decimal("10.0")
DAILY_DRAWDOWN_WARN_PCT = Decimal("2.0")
DAILY_DRAWDOWN_HALT_PCT = Decimal("3.0")


def _age_seconds(now: datetime, ts: Optional[datetime]) -> Optional[int]:
    if ts is None:
        return None
    return max(0, int((now - ts).total_seconds()))


def _emit_feed_staleness_alerts(db: Session, *, now: datetime) -> None:
    # Polymarket feed (orderbook snapshots)
    pm_last = db.execute(text("SELECT MAX(timestamp) FROM pm.orderbook_snapshots")).scalar()
    pm_age = _age_seconds(now, pm_last if isinstance(pm_last, datetime) else None)
    if pm_age is not None:
        if pm_age >= PM_FEED_CRITICAL_SECONDS:
            emit_alert_db_dedup(
                db,
                AlertSeverity.CRITICAL,
                f"Data feed stale (Polymarket orderbook): last update {pm_age}s ago",
                source="data",
                category="feed_staleness",
                dedup_key="data:feed:pm_orderbook:critical",
                context={"surface": "polymarket", "age_seconds": pm_age},
                window_seconds=300,
            )
        elif pm_age >= PM_FEED_WARN_SECONDS:
            emit_alert_db_dedup(
                db,
                AlertSeverity.WARNING,
                f"Data feed stale (Polymarket orderbook): last update {pm_age}s ago",
                source="data",
                category="feed_staleness",
                dedup_key="data:feed:pm_orderbook:warning",
                context={"surface": "polymarket", "age_seconds": pm_age},
                window_seconds=300,
            )

    # Equities feed (price bars) — only if we have any equity fills recorded
    has_equity = db.execute(text("SELECT 1 FROM paper.equity_fills LIMIT 1")).fetchone() is not None
    if not has_equity:
        return

    eq_last = db.execute(text("SELECT MAX(timestamp) FROM market_data.price_bars")).scalar()
    eq_age = _age_seconds(now, eq_last if isinstance(eq_last, datetime) else None)
    if eq_age is None:
        return

    if eq_age >= EQUITY_FEED_CRITICAL_SECONDS:
        emit_alert_db_dedup(
            db,
            AlertSeverity.CRITICAL,
            f"Data feed stale (equities price bars): last update {eq_age}s ago",
            source="data",
            category="feed_staleness",
            dedup_key="data:feed:equities_bars:critical",
            context={"surface": "equities", "age_seconds": eq_age},
            window_seconds=900,
        )
    elif eq_age >= EQUITY_FEED_WARN_SECONDS:
        emit_alert_db_dedup(
            db,
            AlertSeverity.WARNING,
            f"Data feed stale (equities price bars): last update {eq_age}s ago",
            source="data",
            category="feed_staleness",
            dedup_key="data:feed:equities_bars:warning",
            context={"surface": "equities", "age_seconds": eq_age},
            window_seconds=900,
        )


def _emit_runtime_heartbeat_alerts(db: Session, *, now: datetime) -> None:
    fleet_last = db.execute(text("SELECT MAX(captured_at) FROM pm.fleet_status_snapshots")).scalar()
    fleet_age = _age_seconds(now, fleet_last if isinstance(fleet_last, datetime) else None)
    if fleet_age is not None:
        if fleet_age >= FLEET_HEARTBEAT_CRITICAL_SECONDS:
            emit_alert_db_dedup(
                db,
                AlertSeverity.CRITICAL,
                f"Runtime unhealthy: fleet heartbeat missed (last seen {fleet_age}s ago)",
                source="runtime",
                category="heartbeat",
                dedup_key="runtime:fleet_heartbeat:critical",
                context={"component": "fleet_orchestrator", "age_seconds": fleet_age},
                window_seconds=600,
            )
        elif fleet_age >= FLEET_HEARTBEAT_WARN_SECONDS:
            emit_alert_db_dedup(
                db,
                AlertSeverity.WARNING,
                f"Runtime unhealthy: fleet heartbeat delayed (last seen {fleet_age}s ago)",
                source="runtime",
                category="heartbeat",
                dedup_key="runtime:fleet_heartbeat:warning",
                context={"component": "fleet_orchestrator", "age_seconds": fleet_age},
                window_seconds=600,
            )


def _emit_drawdown_alerts(db: Session, *, now: datetime, current_equity: Decimal) -> None:
    peak_val = db.execute(
        text("SELECT MAX(equity_usd) FROM paper.equity_snapshots WHERE strategy_id IS NULL")
    ).scalar()
    peak = Decimal(str(peak_val)) if peak_val is not None else None
    if peak is None or peak <= 0:
        return

    total_dd_pct = (current_equity / peak - Decimal("1")) * Decimal("100")
    if total_dd_pct <= -TOTAL_DRAWDOWN_HALT_PCT:
        emit_alert_db_dedup(
            db,
            AlertSeverity.CRITICAL,
            f"Circuit breaker: total drawdown {total_dd_pct:.2f}% breached halt threshold (-{TOTAL_DRAWDOWN_HALT_PCT}%)",
            source="risk",
            category="drawdown",
            dedup_key="risk:drawdown:total:halt",
            context={"total_drawdown_pct": float(total_dd_pct), "peak_equity": str(peak), "equity": str(current_equity)},
            window_seconds=900,
        )
    elif total_dd_pct <= -TOTAL_DRAWDOWN_WARN_PCT:
        emit_alert_db_dedup(
            db,
            AlertSeverity.WARNING,
            f"Drawdown warning: total drawdown {total_dd_pct:.2f}% (warning at -{TOTAL_DRAWDOWN_WARN_PCT}%, halt at -{TOTAL_DRAWDOWN_HALT_PCT}%)",
            source="risk",
            category="drawdown",
            dedup_key="risk:drawdown:total:warning",
            context={"total_drawdown_pct": float(total_dd_pct), "peak_equity": str(peak), "equity": str(current_equity)},
            window_seconds=900,
        )

    daily_peak_val = db.execute(
        text(
            """
            SELECT MAX(equity_usd)
            FROM paper.equity_snapshots
            WHERE strategy_id IS NULL
              AND timestamp >= date_trunc('day', :now)
            """
        ),
        {"now": now},
    ).scalar()
    daily_peak = Decimal(str(daily_peak_val)) if daily_peak_val is not None else None
    if daily_peak is None or daily_peak <= 0:
        return

    daily_dd_pct = (current_equity / daily_peak - Decimal("1")) * Decimal("100")
    if daily_dd_pct <= -DAILY_DRAWDOWN_HALT_PCT:
        emit_alert_db_dedup(
            db,
            AlertSeverity.CRITICAL,
            f"Circuit breaker: daily drawdown {daily_dd_pct:.2f}% breached halt threshold (-{DAILY_DRAWDOWN_HALT_PCT}%)",
            source="risk",
            category="drawdown",
            dedup_key="risk:drawdown:daily:halt",
            context={"daily_drawdown_pct": float(daily_dd_pct), "daily_peak_equity": str(daily_peak), "equity": str(current_equity)},
            window_seconds=900,
        )
    elif daily_dd_pct <= -DAILY_DRAWDOWN_WARN_PCT:
        emit_alert_db_dedup(
            db,
            AlertSeverity.WARNING,
            f"Drawdown warning: daily drawdown {daily_dd_pct:.2f}% (warning at -{DAILY_DRAWDOWN_WARN_PCT}%, halt at -{DAILY_DRAWDOWN_HALT_PCT}%)",
            source="risk",
            category="drawdown",
            dedup_key="risk:drawdown:daily:warning",
            context={"daily_drawdown_pct": float(daily_dd_pct), "daily_peak_equity": str(daily_peak), "equity": str(current_equity)},
            window_seconds=900,
        )


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
    db: Session = Depends(get_db),
) -> MetricsSummaryResponse:
    """
    Get aggregated metrics summary.

    Args:
        period: Time period filter (1d, 1w, 1m, 3m, 1y, all)
        mode: Optional mode filter (PAPER or LIVE)

    Returns:
        Aggregated metrics including P&L, Sharpe ratio, drawdown, etc.
    """
    if mode and mode != "PAPER":
        raise HTTPException(status_code=501, detail="LIVE metrics not implemented yet")

    now = datetime.now(timezone.utc)

    def _start_for_period(p: str) -> datetime:
        if p == "1d":
            return now - timedelta(days=1)
        if p == "1w":
            return now - timedelta(days=7)
        if p == "1m":
            return now - timedelta(days=30)
        if p == "3m":
            return now - timedelta(days=90)
        if p == "1y":
            return now - timedelta(days=365)
        return datetime(1970, 1, 1, tzinfo=timezone.utc)

    start_dt = _start_for_period(period)

    # Opportunistically refresh snapshots so curves are stable and reflect latest fills.
    try:
        snapshot_all_strategies_and_portfolio(db, as_of=now)
        db.commit()
    except SQLAlchemyError as exc:
        logger.exception("Paper portfolio snapshot failed (SQLAlchemyError)")
        raise HTTPException(
            status_code=503,
            detail="Paper portfolio store not available (check API logs for DB error)",
        ) from exc
    except Exception:
        # If snapshotting fails due to missing mark sources, we still try to serve existing snapshots.
        db.rollback()
        try:
            emit_alert_db_dedup(
                db,
                AlertSeverity.WARNING,
                "Persistence warning: equity snapshot refresh failed (serving last known snapshots)",
                source="runtime",
                category="persistence",
                dedup_key="runtime:snapshots:refresh_failed",
                context={"component": "paper_portfolio_snapshot"},
                window_seconds=300,
            )
            db.commit()
        except Exception:
            db.rollback()

    # Load equity curve from snapshots (portfolio aggregate => strategy_id IS NULL).
    snap_rows = db.execute(
        text(
            """
            SELECT timestamp, equity_usd, starting_capital_usd, cash_usd
            FROM paper.equity_snapshots
            WHERE strategy_id IS NULL
              AND timestamp >= :start_dt
              AND timestamp <= :end_dt
            ORDER BY timestamp ASC
            """
        ),
        {"start_dt": start_dt, "end_dt": now},
    ).fetchall()

    equity_curve: List[EquityCurvePoint] = []
    equity_vals: List[Decimal] = []
    starting_capital_end = Decimal("0")
    cash_end = Decimal("0")

    for ts, equity_usd, starting_cap, cash_usd in snap_rows:
        equity_d = Decimal(str(equity_usd))
        equity_curve.append(EquityCurvePoint(date=ts.date().isoformat(), value=f"{equity_d:.2f}"))
        equity_vals.append(equity_d)
        starting_capital_end = Decimal(str(starting_cap))
        cash_end = Decimal(str(cash_usd))

    # If there are no snapshots in-window, compute a single point from current state.
    portfolio_state = compute_portfolio(db, as_of=now)

    # Operational + safety alerts (best-effort; never break metrics response).
    try:
        _emit_feed_staleness_alerts(db, now=now)
        _emit_runtime_heartbeat_alerts(db, now=now)
        _emit_drawdown_alerts(db, now=now, current_equity=portfolio_state.equity_usd)
        db.commit()
    except Exception:
        db.rollback()

    if not equity_curve:
        equity_curve = [
            EquityCurvePoint(date=now.date().isoformat(), value=f"{portfolio_state.equity_usd:.2f}")
        ]
        equity_vals = [portfolio_state.equity_usd]
        starting_capital_end = portfolio_state.starting_capital_usd
        cash_end = portfolio_state.cash_usd

    equity_start = equity_vals[0] if equity_vals else Decimal("0")
    equity_end = equity_vals[-1] if equity_vals else Decimal("0")
    window_pnl = equity_end - equity_start

    pnl_pct = Decimal("0")
    if starting_capital_end != 0:
        pnl_pct = (window_pnl / starting_capital_end) * Decimal("100")

    sharpe, max_dd = _compute_sharpe_and_drawdown(equity_vals)

    total_trades = _count_fills_in_window(db, start_dt, now)
    active_positions = sum(len(s.positions) for s in portfolio_state.sleeves)

    data = MetricsSummaryData(
        total_pnl=f"{window_pnl:.2f}",
        total_pnl_percent=f"{pnl_pct:.2f}",
        sharpe_ratio=f"{sharpe:.2f}",
        max_drawdown=f"{max_dd:.2f}",
        win_rate="0.00",
        total_trades=total_trades,
        active_positions=active_positions,
        capital_deployed=f"{starting_capital_end:.2f}",
        available_capital=f"{cash_end:.2f}",
        equity_curve=equity_curve,
    )

    meta = MetricsMeta(
        period=period,
        updated_at=datetime.now(timezone.utc),
    )

    return MetricsSummaryResponse(data=data, meta=meta)


def _count_fills_in_window(db: Session, start_dt: datetime, end_dt: datetime) -> int:
    try:
        equity_count = db.execute(
            text(
                """
                SELECT COUNT(*) FROM paper.equity_fills
                WHERE filled_at >= :start_dt AND filled_at <= :end_dt
                """
            ),
            {"start_dt": start_dt, "end_dt": end_dt},
        ).scalar() or 0
        pm_count = db.execute(
            text(
                """
                SELECT COUNT(*) FROM pm.paper_trades
                WHERE executed_at >= :start_dt AND executed_at <= :end_dt
                """
            ),
            {"start_dt": start_dt, "end_dt": end_dt},
        ).scalar() or 0
        return int(equity_count) + int(pm_count)
    except Exception:
        return 0


def _compute_sharpe_and_drawdown(equity_vals: List[Decimal]) -> Tuple[Decimal, Decimal]:
    sharpe = Decimal("0")
    max_dd = Decimal("0")

    if len(equity_vals) < 2 or not all(v > 0 for v in equity_vals):
        return sharpe, max_dd

    returns: List[Decimal] = []
    for i in range(1, len(equity_vals)):
        prev = equity_vals[i - 1]
        cur = equity_vals[i]
        if prev != 0:
            returns.append((cur / prev) - Decimal("1"))

    if returns:
        mean_r = sum(returns) / Decimal(len(returns))
        var = sum((r - mean_r) ** 2 for r in returns) / Decimal(len(returns))
        std = var.sqrt() if var > 0 else Decimal("0")
        if std != 0:
            sharpe = (mean_r / std) * Decimal(str(252 ** 0.5))

    peak = equity_vals[0]
    worst = Decimal("0")
    for v in equity_vals:
        if v > peak:
            peak = v
        if peak != 0:
            dd = (v / peak) - Decimal("1")
            if dd < worst:
                worst = dd
    max_dd = worst * Decimal("100")
    return sharpe, max_dd


@router.get(
    "/metrics/performance/{model_id}",
    summary="Get model performance metrics",
    description="Rolling accuracy, abstention rate, and confidence calibration for a specific model.",
)
async def get_model_performance(
    model_id: str,
    window_days: int = Query(30, description="Rolling window in days", ge=1, le=365),
) -> dict:
    """
    Get performance metrics for a specific model.

    Args:
        model_id: Model identifier
        window_days: Rolling window for metrics (days)

    Returns:
        Performance metrics including accuracy, abstention rate, confidence stats
    """
    # Get or create tracker for this model
    if model_id not in _performance_trackers:
        _performance_trackers[model_id] = PerformanceTracker(model_id)

    tracker = _performance_trackers[model_id]
    metrics = tracker.get_metrics(window_days=window_days)

    return metrics
