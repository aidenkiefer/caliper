from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PolymarketSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: UUID
    market_condition_id: str
    token_id_yes: str
    window_start: datetime
    window_end: datetime
    started_at: datetime
    ended_at: Optional[datetime]
    status: str  # active | completed | failed
    realized_pnl_usdc: Decimal
    total_fees_paid: Decimal
    total_volume: Decimal
    fill_count: int
    volatility_regime: Optional[str]
    spread_regime: Optional[str]
    volume_regime: Optional[str]
    btc_trend_regime: Optional[str]


class PolymarketOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    order_id: UUID
    session_id: UUID
    clob_order_id: str
    token_id: str
    side: str  # BUY | SELL
    price: Decimal
    size: Decimal
    status: str  # open | filled | cancelled
    placed_at: datetime
    cancelled_at: Optional[datetime]
    post_only: bool


class PolymarketFillResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    fill_id: UUID
    order_id: UUID
    session_id: UUID
    price: Decimal
    size: Decimal
    side: str
    filled_at: datetime
    fee_paid: Decimal
    midpoint_at_fill: Optional[Decimal]
    midpoint_5s_after: Optional[Decimal]
    midpoint_10s_after: Optional[Decimal]
    adverse_selection_flag: Optional[bool]


class PolymarketSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    snapshot_id: int
    session_id: UUID
    token_id: str
    best_bid: Optional[Decimal]
    best_ask: Optional[Decimal]
    midpoint: Optional[Decimal]
    spread: Optional[Decimal]
    bid_depth: Optional[Decimal]
    ask_depth: Optional[Decimal]
    imbalance: Optional[Decimal]
    recorded_at: datetime


class PolymarketPnLResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: UUID
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    total_fees: Decimal
    fill_count: int
    recorded_at: datetime  # most recent snapshot


class PolymarketToxicFlowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    minute_bucket: datetime
    session_id: UUID
    fill_count: int
    adverse_fill_count: int
    toxic_flow_ratio: Decimal
    avg_edge_5s: Optional[Decimal]


class PolymarketSessionListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sessions: List[PolymarketSessionResponse]
    total: int
    page: int
    page_size: int


class PolymarketSnapshotListResponse(BaseModel):
    snapshots: List[PolymarketSnapshotResponse]
    total: int
    page: int
    page_size: int
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Sprint 12 — Unified feature pipeline schemas
# ---------------------------------------------------------------------------


class FeatureSnapshot(BaseModel):
    """Flat, serialisable snapshot of all computed features for a single
    Polymarket token at a point in time.  Consumed by the ML layer and
    stored for back-fill / replay.
    """

    model_config = ConfigDict(from_attributes=True)

    # --- Identity / timing ---
    market_id: str
    token_id: str
    captured_at: datetime  # UTC

    time_to_close_seconds: float
    time_since_open_seconds: float

    # --- Family 1: microstructure ---
    mid_price: Decimal
    implied_probability: Decimal
    spread: Decimal
    spread_bps: Decimal
    book_depth_bid_5tick: Decimal
    book_depth_ask_5tick: Decimal
    time_since_last_trade: float
    time_since_last_price_change: float

    # --- Family 2: flow / reward ---
    order_book_imbalance: Decimal
    trade_flow_imbalance_1m: Decimal
    trade_flow_imbalance_5m: Decimal
    last_5min_volume_share: Decimal
    aggressor_buy_fraction_1m: Decimal
    vpin_proxy: Decimal
    fee_rate_current: Decimal
    reward_eligible: bool
    reward_max_spread: Optional[Decimal] = None
    reward_min_size: Optional[Decimal] = None

    # --- Family 3: BTC macro ---
    btc_distance_to_open: Decimal
    btc_rv_1m: Decimal
    btc_rv_5m: Decimal
    btc_rv_15m: Decimal
    btc_momentum_5m: Decimal
    btc_sign_persistence_5m: Decimal
    btc_funding_rate: Decimal
    btc_basis_proxy: Decimal

    # --- Family 4: regime / meta ---
    vol_regime: Literal["low", "medium", "high"]
    trend_regime: Literal["trending", "mean_reverting", "neutral"]
    time_bucket: Literal["early", "mid", "late"]
    near_close_flag: bool
    toxicity_regime: Literal["low", "medium", "high"]
    spread_regime: Literal["tight", "normal", "wide"]
    liquidity_score: Decimal
    competitive_pressure: Decimal

    # --- Quality flag ---
    data_staleness_flag: bool = False


class FeatureRecord(BaseModel):
    """DB round-trip wrapper for :class:`FeatureSnapshot`.

    Adds a surrogate ``id`` and ``created_at`` timestamp so that records
    stored in TimescaleDB can be fetched by primary key and ordered by
    insertion time independently of ``captured_at``.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    snapshot: FeatureSnapshot
