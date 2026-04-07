"""
Internal Pydantic models for the Polymarket BTC hourly market-making service.

These schemas are used for in-process data exchange between the quoting loop
components (data feed, executor, recorder) and are NOT shared with the equity
OMS or the Strategy ABC layer.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, model_validator


class MarketInfo(BaseModel):
    """Static + semi-static metadata for a single Polymarket binary market."""

    condition_id: str
    token_id_yes: str
    token_id_no: str
    slug: Optional[str] = None
    question: Optional[str] = None
    window_start: datetime
    window_end: datetime
    tick_size: Decimal
    fees_enabled: bool
    fee_rate_bps: Optional[Decimal] = None
    rewards_max_spread: Optional[Decimal] = None
    rewards_min_size: Optional[Decimal] = None
    total_volume: Optional[Decimal] = None


class OrderbookState(BaseModel):
    """Real-time orderbook snapshot for a single token (YES or NO)."""

    token_id: str
    best_bid: Optional[Decimal] = None
    best_ask: Optional[Decimal] = None
    midpoint: Optional[Decimal] = None
    spread: Optional[Decimal] = None
    last_trade_price: Optional[Decimal] = None
    bid_depth_1pct: Optional[Decimal] = None  # USDC depth within 1% of best bid
    ask_depth_1pct: Optional[Decimal] = None  # USDC depth within 1% of best ask
    imbalance: Optional[Decimal] = None       # (bid_depth - ask_depth) / total_depth
    last_updated: datetime


class QuoteDecision(BaseModel):
    """Output of the quoting logic: prices, sizes, and gating flags."""

    bid_price: Optional[Decimal] = None
    ask_price: Optional[Decimal] = None
    bid_size: Decimal
    ask_size: Decimal
    should_quote_bid: bool = True
    should_quote_ask: bool = True
    midpoint: Optional[Decimal] = None
    reason: Optional[str] = None  # Populated when quoting is skipped (e.g. inventory cap)

    @model_validator(mode="after")
    def check_prices_set_when_quoting(self) -> "QuoteDecision":
        if self.should_quote_bid and self.bid_price is None:
            raise ValueError("bid_price must not be None when should_quote_bid is True")
        if self.should_quote_ask and self.ask_price is None:
            raise ValueError("ask_price must not be None when should_quote_ask is True")
        return self
