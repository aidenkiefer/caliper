"""
Unit tests for services/polymarket/data_feed.py

Tests cover:
1. test_book_update_parses_bids_asks — full book snapshot populates state correctly
2. test_binance_poll_updates_price — Binance polling updates binance_price in state
3. test_state_aggregation — after book + Binance, get_current_state() returns correct DataFeedState
4. test_staleness_detection — stale Binance price raises StaleDataError
5. test_price_change_delta — price_change message applies delta to existing book
6. test_book_metrics_computation — _compute_book_metrics returns correct derived values
7. test_imbalance_computation — imbalance is (bid_depth - ask_depth) / total
8. test_stop_cancels_tasks — stop() cancels background tasks
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.polymarket.data_feed import (
    BINANCE_POLL_INTERVAL_SECONDS,
    DataFeed,
    DataFeedState,
    StaleDataError,
    _apply_price_change,
    _compute_book_metrics,
    _parse_levels,
)

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_config(binance_stale_seconds: int = 30):
    """Return a minimal PolymarketConfig-like mock with only the fields
    touched by DataFeed."""
    cfg = MagicMock()
    cfg.binance_stale_seconds = binance_stale_seconds
    cfg.quote_spread = Decimal("0.02")
    cfg.quote_size = Decimal("50")
    return cfg


def _make_feed(
    binance_price: Decimal = Decimal("85000"),
    binance_stale_seconds: int = 30,
):
    """Construct a DataFeed with mocked clients and a simple config."""
    clob = MagicMock()
    clob.subscribe_market_channel = AsyncMock()
    binance = MagicMock()
    binance.get_current_price = AsyncMock(return_value=binance_price)
    config = _make_config(binance_stale_seconds=binance_stale_seconds)
    return DataFeed(clob, binance, config), clob, binance, config


def _book_message(bids: list, asks: list) -> dict:
    """Build a minimal CLOB ``book`` WebSocket message."""
    return {
        "event_type": "book",
        "bids": [{"price": str(p), "size": str(s)} for p, s in bids],
        "asks": [{"price": str(p), "size": str(s)} for p, s in asks],
    }


def _price_change_message(bids: list, asks: list) -> dict:
    """Build a minimal CLOB ``price_change`` WebSocket message."""
    return {
        "event_type": "price_change",
        "bids": [{"price": str(p), "size": str(s)} for p, s in bids],
        "asks": [{"price": str(p), "size": str(s)} for p, s in asks],
    }


# ---------------------------------------------------------------------------
# Test 1 — book snapshot parses bids/asks and computes best bid/ask/midpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_book_update_parses_bids_asks():
    """A 'book' message should populate best_bid, best_ask, and midpoint."""
    feed, _, _, _ = _make_feed()
    feed._token_id = "tok1"

    msg = _book_message(
        bids=[(Decimal("0.48"), Decimal("100")), (Decimal("0.46"), Decimal("200"))],
        asks=[(Decimal("0.52"), Decimal("150")), (Decimal("0.54"), Decimal("300"))],
    )
    await feed._on_book_update(msg)

    state = feed._state
    assert state.best_bid == Decimal("0.48")
    assert state.best_ask == Decimal("0.52")
    assert state.midpoint == Decimal("0.50")
    assert state.spread == Decimal("0.04")
    assert state.last_updated is not None


# ---------------------------------------------------------------------------
# Test 2 — Binance polling updates binance_price in state
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_binance_poll_updates_price():
    """A single Binance poll iteration should update binance_price and
    binance_last_updated on the internal state."""
    feed, _, binance, _ = _make_feed(binance_price=Decimal("90000"))
    feed._running = True

    # Patch asyncio.sleep to avoid actually sleeping and to stop the loop
    # after one iteration by raising CancelledError on the sleep call.
    async def fake_sleep(_):
        feed._running = False
        raise asyncio.CancelledError

    with patch("services.polymarket.data_feed.asyncio.sleep", side_effect=fake_sleep):
        try:
            await feed._poll_binance()
        except asyncio.CancelledError:
            pass

    assert feed._state.binance_price == Decimal("90000")
    assert feed._state.binance_last_updated is not None
    binance.get_current_price.assert_awaited_once_with("BTCUSDT")


# ---------------------------------------------------------------------------
# Test 3 — state aggregation: book + Binance → correct DataFeedState
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_state_aggregation():
    """After a book update and a Binance poll, get_current_state() should
    return a DataFeedState with correct fields including binance_price."""
    from services.polymarket.data_feed import DataFeedState

    feed, _, binance, _ = _make_feed(binance_price=Decimal("87000"))
    feed._token_id = "tok2"

    # Apply book snapshot
    msg = _book_message(
        bids=[(Decimal("0.50"), Decimal("200"))],
        asks=[(Decimal("0.52"), Decimal("180"))],
    )
    await feed._on_book_update(msg)

    # Manually update Binance price (simulate one poll)
    async with feed._lock:
        feed._state.binance_price = Decimal("87000")
        feed._state.binance_last_updated = datetime.now(tz=timezone.utc)

    snap = feed.get_current_state()

    assert isinstance(snap, DataFeedState)
    assert snap.best_bid == Decimal("0.50")
    assert snap.best_ask == Decimal("0.52")
    assert snap.midpoint == Decimal("0.51")
    assert snap.spread == Decimal("0.02")
    assert snap.last_updated is not None
    assert snap.binance_price == Decimal("87000")


# ---------------------------------------------------------------------------
# Test 4 — staleness detection
# ---------------------------------------------------------------------------


def test_staleness_detection():
    """When binance_last_updated is older than binance_stale_seconds,
    get_current_state() should raise StaleDataError."""
    feed, _, _, _ = _make_feed(binance_stale_seconds=30)
    feed._token_id = "tok3"

    # Set a stale timestamp (60 seconds ago)
    stale_time = datetime.now(tz=timezone.utc) - timedelta(seconds=60)
    feed._state.binance_price = Decimal("85000")
    feed._state.binance_last_updated = stale_time
    # Provide a valid last_updated so the state appears otherwise healthy
    feed._state.last_updated = datetime.now(tz=timezone.utc)

    with pytest.raises(StaleDataError):
        feed.get_current_state()


def test_no_staleness_when_fresh():
    """When binance_last_updated is recent, get_current_state() should succeed."""
    feed, _, _, _ = _make_feed(binance_stale_seconds=30)
    feed._token_id = "tok4"

    feed._state.binance_price = Decimal("85000")
    feed._state.binance_last_updated = datetime.now(tz=timezone.utc)
    feed._state.last_updated = datetime.now(tz=timezone.utc)
    feed._state.best_bid = Decimal("0.48")
    feed._state.best_ask = Decimal("0.52")

    snap = feed.get_current_state()
    assert snap.best_bid == Decimal("0.48")


def test_no_staleness_when_binance_never_polled():
    """When binance_last_updated is None (never polled), no StaleDataError is raised."""
    from services.polymarket.data_feed import DataFeedState

    feed, _, _, _ = _make_feed()
    feed._token_id = "tok5"
    feed._state.binance_last_updated = None
    feed._state.last_updated = datetime.now(tz=timezone.utc)

    # Should not raise — we have no Binance data yet at all
    snap = feed.get_current_state()
    assert isinstance(snap, DataFeedState)


# ---------------------------------------------------------------------------
# Test 5 — price_change delta updates the book
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_price_change_delta():
    """A 'price_change' message should update existing levels, add new
    levels, and remove levels with size=0."""
    feed, _, _, _ = _make_feed()

    # Start with a full book snapshot
    await feed._on_book_update(
        _book_message(
            bids=[(Decimal("0.48"), Decimal("100")), (Decimal("0.46"), Decimal("200"))],
            asks=[(Decimal("0.52"), Decimal("150"))],
        )
    )

    # Apply a delta: update existing bid, remove 0.48, add new ask
    delta = _price_change_message(
        bids=[
            (Decimal("0.48"), Decimal("0")),   # remove
            (Decimal("0.47"), Decimal("250")),  # add new
        ],
        asks=[
            (Decimal("0.52"), Decimal("200")),  # update existing
            (Decimal("0.55"), Decimal("100")),  # add new
        ],
    )
    await feed._on_book_update(delta)

    state = feed._state
    bid_prices = [p for p, _ in state.bids]
    ask_prices = [p for p, _ in state.asks]

    assert Decimal("0.48") not in bid_prices  # removed
    assert Decimal("0.47") in bid_prices  # added
    assert Decimal("0.46") in bid_prices  # unchanged
    assert Decimal("0.52") in ask_prices
    assert Decimal("0.55") in ask_prices

    # Sizes should reflect updates
    bid_dict = dict(state.bids)
    ask_dict = dict(state.asks)
    assert bid_dict[Decimal("0.47")] == Decimal("250")
    assert ask_dict[Decimal("0.52")] == Decimal("200")


# ---------------------------------------------------------------------------
# Test 6 — _compute_book_metrics correctness
# ---------------------------------------------------------------------------


def test_book_metrics_computation():
    """_compute_book_metrics should return correct best_bid/ask, midpoint,
    spread, and top-3 depth."""
    bids = [
        (Decimal("0.50"), Decimal("100")),
        (Decimal("0.48"), Decimal("200")),
        (Decimal("0.46"), Decimal("150")),
        (Decimal("0.44"), Decimal("50")),
    ]
    asks = [
        (Decimal("0.54"), Decimal("120")),
        (Decimal("0.56"), Decimal("180")),
        (Decimal("0.58"), Decimal("90")),
    ]
    metrics = _compute_book_metrics(bids, asks)

    assert metrics["best_bid"] == Decimal("0.50")
    assert metrics["best_ask"] == Decimal("0.54")
    assert metrics["midpoint"] == Decimal("0.52")
    assert metrics["spread"] == Decimal("0.04")

    # Top 3: bids 100+200+150=450, asks 120+180+90=390 → total=840
    assert metrics["total_depth_top_3_levels"] == Decimal("840")

    assert metrics["num_orders_at_best_bid"] == 1
    assert metrics["num_orders_at_best_ask"] == 1


# ---------------------------------------------------------------------------
# Test 7 — imbalance computation
# ---------------------------------------------------------------------------


def test_imbalance_computation():
    """Imbalance should be (bid_depth_1pct - ask_depth_1pct) / total."""
    # Midpoint = 0.50. 1% thresholds: bid >= 0.495, ask <= 0.505.
    bids = [(Decimal("0.499"), Decimal("300")), (Decimal("0.48"), Decimal("100"))]
    asks = [(Decimal("0.501"), Decimal("100")), (Decimal("0.52"), Decimal("200"))]
    metrics = _compute_book_metrics(bids, asks)

    # Only 0.499 bid is within 1% of mid (0.50 * 0.99 = 0.495 → 0.499 >= 0.495 ✓)
    # Only 0.501 ask is within 1% of mid (0.50 * 1.01 = 0.505 → 0.501 <= 0.505 ✓)
    bid_d = Decimal("300")
    ask_d = Decimal("100")
    expected_imbalance = (bid_d - ask_d) / (bid_d + ask_d)
    assert metrics["imbalance"] == expected_imbalance


# ---------------------------------------------------------------------------
# Test 8 — stop() cancels background tasks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stop_cancels_tasks():
    """stop() should cancel all running background tasks."""
    feed, clob, binance, _ = _make_feed()
    binance.get_current_price = AsyncMock(return_value=Decimal("85000"))

    # Replace subscribe_market_channel with a long-running coroutine
    async def long_ws(*args, **kwargs):
        await asyncio.sleep(9999)

    clob.subscribe_market_channel = long_ws

    await feed.start("tok-stop-test")
    assert len(feed._tasks) == 2

    # Capture task references before stop() clears feed._tasks
    tasks_before_stop = list(feed._tasks)
    assert len(tasks_before_stop) == 2

    await feed.stop()

    assert feed._running is False
    assert feed._tasks == []  # stop() clears the list
    for task in tasks_before_stop:
        assert task.done()  # verify each task was actually cancelled


# ---------------------------------------------------------------------------
# Test 9 — _parse_levels handles malformed input gracefully
# ---------------------------------------------------------------------------


def test_parse_levels_skips_malformed():
    """_parse_levels should skip levels that are missing required keys."""
    raw = [
        {"price": "0.50", "size": "100"},
        {"price": "0.48"},        # missing size
        {"size": "50"},            # missing price
        {"price": "0.46", "size": "75"},
    ]
    levels = _parse_levels(raw)
    prices = [p for p, _ in levels]
    assert Decimal("0.50") in prices
    assert Decimal("0.46") in prices
    assert len(levels) == 2  # two malformed entries skipped


# ---------------------------------------------------------------------------
# Test 10 — _apply_price_change correctly merges deltas
# ---------------------------------------------------------------------------


def test_apply_price_change_merge():
    """_apply_price_change should add, update, and remove levels."""
    existing = [
        (Decimal("0.50"), Decimal("100")),
        (Decimal("0.48"), Decimal("200")),
    ]
    delta = [
        (Decimal("0.50"), Decimal("0")),    # remove
        (Decimal("0.48"), Decimal("250")),  # update
        (Decimal("0.46"), Decimal("150")),  # add
    ]
    result = _apply_price_change(existing, delta, descending=True)
    result_dict = dict(result)

    assert Decimal("0.50") not in result_dict
    assert result_dict[Decimal("0.48")] == Decimal("250")
    assert result_dict[Decimal("0.46")] == Decimal("150")

    # Verify descending sort
    prices = [p for p, _ in result]
    assert prices == sorted(prices, reverse=True)


# ---------------------------------------------------------------------------
# Test 11 — last_trade_price and tick_size update from WebSocket messages
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_last_trade_price_update():
    feed, _, _, _ = _make_feed()
    msg = {"event_type": "last_trade_price", "price": "0.51"}
    await feed._on_book_update(msg)
    assert feed._state.last_trade_price == Decimal("0.51")


@pytest.mark.asyncio
async def test_tick_size_change_update():
    feed, _, _, _ = _make_feed()
    msg = {"event_type": "tick_size_change", "tick_size": "0.01"}
    await feed._on_book_update(msg)
    assert feed._state.tick_size == Decimal("0.01")


# ---------------------------------------------------------------------------
# Test 12 — empty book returns None for metrics
# ---------------------------------------------------------------------------


def test_empty_book_metrics():
    """_compute_book_metrics with empty lists should return all-None metrics."""
    metrics = _compute_book_metrics([], [])
    assert metrics["best_bid"] is None
    assert metrics["best_ask"] is None
    assert metrics["midpoint"] is None
    assert metrics["spread"] is None
    assert metrics["imbalance"] is None
    assert metrics["total_depth_top_3_levels"] == Decimal("0")
