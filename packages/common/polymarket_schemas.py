from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
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
