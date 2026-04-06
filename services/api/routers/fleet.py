from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

router = APIRouter()


class FleetStrategyStatus(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    strategy_id: str
    name: str
    status: Literal["active", "paused", "cooldown", "abstain"]
    mode: Literal["paper", "live"]
    current_regime: Literal["R1", "R2", "R3", "R4", "R5"]
    pnl_24h_usd: float
    sharpe_7d: float
    fill_rate: float = Field(..., ge=0, le=1)
    allocation_weight: float = Field(..., ge=0, le=1)
    regime_alignment: float = Field(..., ge=0, le=1)
    signal_count_24h: int


class RegimeTimelinePoint(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    timestamp: datetime
    regime: Literal["R1", "R2", "R3", "R4", "R5"]
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
    current_regime: Literal["R1", "R2", "R3", "R4", "R5"]
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
    regime: Literal["R1", "R2", "R3", "R4", "R5"]


class PaperTrade(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    trade_id: str
    timestamp: datetime
    strategy_id: str
    market_id: str
    side: Literal["BUY", "SELL"]
    price: float
    size: float
    pnl_usd: float
    status: Literal["filled", "simulated", "cancelled"]


def _require_db_url() -> str:
    db_url = os.environ.get("DB_URL")
    if not db_url:
        raise HTTPException(status_code=503, detail="Fleet service not available")
    return db_url


def _mock_fleet_status() -> FleetStatus:
    generated_at = datetime.now(tz=timezone.utc)
    return FleetStatus(
        generated_at=generated_at,
        current_regime="R1",
        current_mode="paper",
        strategies=[
            FleetStrategyStatus(
                strategy_id="poly_mm_v2",
                name="Microstructure Maker v2",
                status="active",
                mode="paper",
                current_regime="R1",
                pnl_24h_usd=184.25,
                sharpe_7d=1.72,
                fill_rate=0.61,
                allocation_weight=0.34,
                regime_alignment=0.88,
                signal_count_24h=148,
            ),
            FleetStrategyStatus(
                strategy_id="poly_directional_v1",
                name="Directional Probability Model",
                status="active",
                mode="paper",
                current_regime="R1",
                pnl_24h_usd=92.4,
                sharpe_7d=1.35,
                fill_rate=0.54,
                allocation_weight=0.24,
                regime_alignment=0.79,
                signal_count_24h=74,
            ),
            FleetStrategyStatus(
                strategy_id="poly_hybrid_v1",
                name="Hybrid Maker/Directional",
                status="cooldown",
                mode="paper",
                current_regime="R2",
                pnl_24h_usd=141.75,
                sharpe_7d=1.51,
                fill_rate=0.58,
                allocation_weight=0.24,
                regime_alignment=0.83,
                signal_count_24h=112,
            ),
            FleetStrategyStatus(
                strategy_id="poly_regime_v1",
                name="Regime-Aware Model",
                status="abstain",
                mode="paper",
                current_regime="R3",
                pnl_24h_usd=-12.8,
                sharpe_7d=0.84,
                fill_rate=0.29,
                allocation_weight=0.18,
                regime_alignment=0.63,
                signal_count_24h=34,
            ),
        ],
        regime_timeline=[
            RegimeTimelinePoint(
                timestamp=generated_at - timedelta(hours=3),
                regime="R1",
                allocation_weights={
                    "poly_mm_v2": 0.34,
                    "poly_directional_v1": 0.24,
                    "poly_hybrid_v1": 0.24,
                    "poly_regime_v1": 0.18,
                },
            ),
            RegimeTimelinePoint(
                timestamp=generated_at - timedelta(hours=2),
                regime="R1",
                allocation_weights={
                    "poly_mm_v2": 0.33,
                    "poly_directional_v1": 0.24,
                    "poly_hybrid_v1": 0.25,
                    "poly_regime_v1": 0.18,
                },
            ),
            RegimeTimelinePoint(
                timestamp=generated_at - timedelta(hours=1),
                regime="R2",
                allocation_weights={
                    "poly_mm_v2": 0.31,
                    "poly_directional_v1": 0.21,
                    "poly_hybrid_v1": 0.28,
                    "poly_regime_v1": 0.20,
                },
            ),
            RegimeTimelinePoint(
                timestamp=generated_at,
                regime="R1",
                allocation_weights={
                    "poly_mm_v2": 0.34,
                    "poly_directional_v1": 0.24,
                    "poly_hybrid_v1": 0.24,
                    "poly_regime_v1": 0.18,
                },
            ),
        ],
        comparison=[
            StrategyComparisonRow(
                strategy_id="poly_mm_v2",
                baseline="baseline_mm",
                sharpe_7d=1.72,
                sortino_7d=2.08,
                win_rate=0.59,
                max_drawdown=-0.062,
                profit_factor=1.41,
            ),
            StrategyComparisonRow(
                strategy_id="poly_directional_v1",
                baseline="baseline_directional",
                sharpe_7d=1.35,
                sortino_7d=1.87,
                win_rate=0.56,
                max_drawdown=-0.071,
                profit_factor=1.29,
            ),
            StrategyComparisonRow(
                strategy_id="poly_hybrid_v1",
                baseline="baseline_hybrid",
                sharpe_7d=1.51,
                sortino_7d=2.01,
                win_rate=0.57,
                max_drawdown=-0.055,
                profit_factor=1.36,
            ),
            StrategyComparisonRow(
                strategy_id="poly_regime_v1",
                baseline="baseline_regime",
                sharpe_7d=0.84,
                sortino_7d=1.12,
                win_rate=0.49,
                max_drawdown=-0.098,
                profit_factor=0.97,
            ),
        ],
    )


def _mock_signals(limit: int) -> List[FleetSignal]:
    generated_at = datetime.now(tz=timezone.utc)
    signals: List[FleetSignal] = [
        FleetSignal(
            signal_id="sig-001",
            timestamp=generated_at - timedelta(minutes=4),
            strategy_id="poly_mm_v2",
            market_id="btc-hourly-2026-04-06-09",
            signal_type="MARKET_MAKING",
            direction="none",
            confidence=0.91,
            action_taken="executed",
            fill_price=None,
            regime="R1",
        ),
        FleetSignal(
            signal_id="sig-002",
            timestamp=generated_at - timedelta(minutes=3),
            strategy_id="poly_directional_v1",
            market_id="btc-hourly-2026-04-06-10",
            signal_type="DIRECTIONAL",
            direction="long",
            confidence=0.78,
            action_taken="executed",
            fill_price=0.54,
            regime="R1",
        ),
        FleetSignal(
            signal_id="sig-003",
            timestamp=generated_at - timedelta(minutes=2),
            strategy_id="poly_hybrid_v1",
            market_id="btc-hourly-2026-04-06-08",
            signal_type="HYBRID",
            direction="long",
            confidence=0.83,
            action_taken="cancelled",
            fill_price=None,
            regime="R2",
        ),
        FleetSignal(
            signal_id="sig-004",
            timestamp=generated_at - timedelta(minutes=1),
            strategy_id="poly_regime_v1",
            market_id="btc-hourly-2026-04-06-11",
            signal_type="DIRECTIONAL",
            direction="abstain",
            confidence=0.32,
            action_taken="abstained",
            fill_price=None,
            regime="R3",
        ),
    ]
    return signals[: max(limit, 0)]


def _mock_paper_trades(
    limit: int,
    strategy_id: Optional[str] = None,
    market_id: Optional[str] = None,
) -> List[PaperTrade]:
    generated_at = datetime.now(tz=timezone.utc)
    trades = [
        PaperTrade(
            trade_id="trade-001",
            timestamp=generated_at - timedelta(minutes=6),
            strategy_id="poly_mm_v2",
            market_id="btc-hourly-2026-04-06-09",
            side="BUY",
            price=0.53,
            size=120.0,
            pnl_usd=12.5,
            status="filled",
        ),
        PaperTrade(
            trade_id="trade-002",
            timestamp=generated_at - timedelta(minutes=5),
            strategy_id="poly_directional_v1",
            market_id="btc-hourly-2026-04-06-10",
            side="BUY",
            price=0.54,
            size=80.0,
            pnl_usd=7.2,
            status="filled",
        ),
        PaperTrade(
            trade_id="trade-003",
            timestamp=generated_at - timedelta(minutes=4),
            strategy_id="poly_hybrid_v1",
            market_id="btc-hourly-2026-04-06-08",
            side="SELL",
            price=0.49,
            size=60.0,
            pnl_usd=-1.4,
            status="simulated",
        ),
    ]
    filtered = [
        trade
        for trade in trades
        if (strategy_id is None or trade.strategy_id == strategy_id)
        and (market_id is None or trade.market_id == market_id)
    ]
    return filtered[: max(limit, 0)]


@router.get("/fleet/status", response_model=FleetStatus, summary="Get fleet status")
async def get_fleet_status(_db_url: str = Depends(_require_db_url)) -> FleetStatus:
    return _mock_fleet_status()


@router.get("/fleet/signals", response_model=List[FleetSignal], summary="Get fleet signal log")
async def get_fleet_signals(
    limit: int = Query(50, ge=1, le=200),
    _db_url: str = Depends(_require_db_url),
) -> List[FleetSignal]:
    return _mock_signals(limit)


@router.get("/fleet/paper-trades", response_model=List[PaperTrade], summary="Get paper trades")
async def get_paper_trades(
    start: Optional[datetime] = Query(None),
    end: Optional[datetime] = Query(None),
    strategy_id: Optional[str] = Query(None),
    market_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    _db_url: str = Depends(_require_db_url),
) -> List[PaperTrade]:
    if start is not None and end is not None and start >= end:
        raise HTTPException(status_code=422, detail="Query parameter 'start' must be before 'end'")
    trades = _mock_paper_trades(limit=limit, strategy_id=strategy_id, market_id=market_id)
    if start is not None:
        trades = [trade for trade in trades if trade.timestamp >= start]
    if end is not None:
        trades = [trade for trade in trades if trade.timestamp <= end]
    return trades
