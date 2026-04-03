"""
Reusable fixtures and factory helpers for Polymarket integration tests.

These helpers create instances of service schemas and config objects with
sensible defaults, making test setup concise without requiring live connections.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from services.polymarket.data_feed import DataFeedState
from services.polymarket.schemas import MarketInfo, QuoteDecision


def make_market_info(
    window_start: datetime | None = None,
    window_end: datetime | None = None,
) -> MarketInfo:
    """Return a MarketInfo with sensible defaults for testing.

    Parameters
    ----------
    window_start:
        Session window start (UTC). Defaults to now.
    window_end:
        Session window end (UTC). Defaults to now + 2 minutes (short window).
    """
    now = datetime.now(timezone.utc)
    return MarketInfo(
        condition_id="0xabc123",
        token_id_yes="yes_token_123",
        token_id_no="no_token_456",
        window_start=window_start or now,
        window_end=window_end or (now + timedelta(minutes=2)),
        tick_size=Decimal("0.01"),
        fees_enabled=True,
    )


def make_data_feed_state(midpoint: Decimal = Decimal("0.55")) -> DataFeedState:
    """Return a DataFeedState with sensible defaults.

    Parameters
    ----------
    midpoint:
        The midpoint price. Bid and ask are derived symmetrically around it.
    """
    half_spread = Decimal("0.01")
    best_bid = midpoint - half_spread
    best_ask = midpoint + half_spread
    return DataFeedState(
        best_bid=best_bid,
        best_ask=best_ask,
        midpoint=midpoint,
        spread=best_ask - best_bid,
        binance_price=Decimal("65000"),
        binance_last_updated=datetime.now(timezone.utc),
        last_updated=datetime.now(timezone.utc),
    )


def make_quote_decision(
    bid_price: Decimal = Decimal("0.54"),
    ask_price: Decimal = Decimal("0.56"),
    bid_size: Decimal = Decimal("50"),
    ask_size: Decimal = Decimal("50"),
    should_quote_bid: bool = True,
    should_quote_ask: bool = True,
) -> QuoteDecision:
    """Return a QuoteDecision with sensible defaults."""
    return QuoteDecision(
        should_quote_bid=should_quote_bid,
        should_quote_ask=should_quote_ask,
        bid_price=bid_price,
        ask_price=ask_price,
        bid_size=bid_size,
        ask_size=ask_size,
    )


def make_config(**overrides: Any):
    """Return a PolymarketConfig suitable for testing (no real secrets needed).

    Uses dummy values for required credentials. All other fields use their
    schema defaults unless overridden via keyword arguments.

    Parameters
    ----------
    **overrides:
        Any PolymarketConfig field to override.
    """
    from services.polymarket.config import PolymarketConfig

    defaults: dict[str, Any] = {
        "private_key": "0x" + "a" * 64,
        "wallet_address": "0x" + "0" * 40,
        "database_url": "postgresql://localhost/test",
        # Keep the loop fast during tests
        "requote_interval_seconds": 1,
    }
    defaults.update(overrides)
    return PolymarketConfig(**defaults)
