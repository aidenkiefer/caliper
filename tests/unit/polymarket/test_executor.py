"""
Unit tests for services/polymarket/executor.py

Tests cover:
- place_quotes (both sides, bid only, cancels existing first)
- cancel_all_orders (clears internal tracking)
- heartbeat loop (runs periodically, failure does not crash)
- handle_fill (updates inventory, calls callback)
- post-only enforcement on every place_order call
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from services.polymarket.executor import Executor
from services.polymarket.schemas import QuoteDecision


# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------


def make_config(heartbeat_interval_seconds: int = 5) -> MagicMock:
    """Return a minimal mock PolymarketConfig."""
    cfg = MagicMock()
    cfg.heartbeat_interval_seconds = heartbeat_interval_seconds
    return cfg


def make_clob_client() -> MagicMock:
    """Return a mock CLOBClient with async methods."""
    clob = MagicMock()
    clob.place_order = AsyncMock(return_value="order-id-1")
    clob.cancel_order = AsyncMock(return_value=True)
    clob.cancel_all = AsyncMock(return_value=3)
    clob.send_heartbeat = AsyncMock(return_value={"heartbeatID": "hb-1"})
    return clob


def make_quote(
    bid_price: Optional[Decimal] = Decimal("0.48"),
    ask_price: Optional[Decimal] = Decimal("0.52"),
    bid_size: Decimal = Decimal("50"),
    ask_size: Decimal = Decimal("50"),
    should_quote_bid: bool = True,
    should_quote_ask: bool = True,
) -> QuoteDecision:
    """Build a QuoteDecision with sensible defaults."""
    return QuoteDecision(
        bid_price=bid_price,
        ask_price=ask_price,
        bid_size=bid_size,
        ask_size=ask_size,
        should_quote_bid=should_quote_bid,
        should_quote_ask=should_quote_ask,
    )


# ---------------------------------------------------------------------------
# place_quotes tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_place_quotes_both_sides():
    """place_quotes should place a bid and an ask when both sides are enabled."""
    clob = make_clob_client()
    clob.place_order = AsyncMock(side_effect=["bid-order-1", "ask-order-1"])
    executor = Executor(clob_client=clob, config=make_config())

    bid_id, ask_id = await executor.place_quotes(
        quote=make_quote(), token_id="12345", quote_version=1
    )

    assert bid_id == "bid-order-1"
    assert ask_id == "ask-order-1"
    assert clob.place_order.call_count == 2


@pytest.mark.asyncio
async def test_place_quotes_bid_only():
    """When should_quote_ask=False, only the bid is placed and ask_id is None."""
    clob = make_clob_client()
    clob.place_order = AsyncMock(return_value="bid-only")
    executor = Executor(clob_client=clob, config=make_config())

    quote = make_quote(should_quote_ask=False, ask_price=None)
    bid_id, ask_id = await executor.place_quotes(quote, token_id="tok1", quote_version=2)

    assert bid_id == "bid-only"
    assert ask_id is None
    assert clob.place_order.call_count == 1
    assert clob.place_order.call_args[1]["side"] == "BUY"


@pytest.mark.asyncio
async def test_place_quotes_ask_only():
    """When should_quote_bid=False, only the ask is placed and bid_id is None."""
    clob = make_clob_client()
    clob.place_order = AsyncMock(return_value="ask-only")
    executor = Executor(clob_client=clob, config=make_config())

    quote = make_quote(should_quote_bid=False, bid_price=None)
    bid_id, ask_id = await executor.place_quotes(quote, token_id="tok1", quote_version=3)

    assert bid_id is None
    assert ask_id == "ask-only"
    assert clob.place_order.call_count == 1
    assert clob.place_order.call_args[1]["side"] == "SELL"


@pytest.mark.asyncio
async def test_place_quotes_cancels_existing_first():
    """If tracked live orders exist for the token, they are cancelled before new quotes."""
    clob = make_clob_client()
    clob.place_order = AsyncMock(side_effect=["new-bid", "new-ask"])
    executor = Executor(clob_client=clob, config=make_config())

    # Pre-populate live orders for the same token
    executor._live_orders["old-bid"] = {
        "placed_at": datetime.now(tz=timezone.utc),
        "quote_version": 0,
        "side": "BUY",
        "price": Decimal("0.47"),
        "size": Decimal("50"),
        "token_id": "token-abc",
    }
    executor._live_orders["old-ask"] = {
        "placed_at": datetime.now(tz=timezone.utc),
        "quote_version": 0,
        "side": "SELL",
        "price": Decimal("0.53"),
        "size": Decimal("50"),
        "token_id": "token-abc",
    }

    await executor.place_quotes(make_quote(), token_id="token-abc", quote_version=1)

    # cancel_order should have been called for both pre-existing orders
    assert clob.cancel_order.call_count == 2
    cancelled_ids = {c.args[0] for c in clob.cancel_order.call_args_list}
    assert cancelled_ids == {"old-bid", "old-ask"}

    # Old orders should be removed from tracking
    assert "old-bid" not in executor._live_orders
    assert "old-ask" not in executor._live_orders


@pytest.mark.asyncio
async def test_place_quotes_only_cancels_same_token():
    """Orders for a different token are NOT cancelled when placing for a new token."""
    clob = make_clob_client()
    clob.place_order = AsyncMock(return_value="new-order")
    executor = Executor(clob_client=clob, config=make_config())

    # Order for a different token
    executor._live_orders["other-order"] = {
        "placed_at": datetime.now(tz=timezone.utc),
        "quote_version": 0,
        "side": "BUY",
        "price": Decimal("0.47"),
        "size": Decimal("50"),
        "token_id": "other-token",
    }

    await executor.place_quotes(make_quote(), token_id="my-token", quote_version=1)

    # cancel_order should NOT have been called
    clob.cancel_order.assert_not_called()
    # Other token's order should still be tracked
    assert "other-order" in executor._live_orders


@pytest.mark.asyncio
async def test_place_quotes_tracks_new_orders():
    """Newly placed orders are stored in _live_orders with correct metadata."""
    clob = make_clob_client()
    clob.place_order = AsyncMock(side_effect=["bid-111", "ask-222"])
    executor = Executor(clob_client=clob, config=make_config())

    quote = make_quote(bid_price=Decimal("0.48"), ask_price=Decimal("0.52"))
    await executor.place_quotes(quote, token_id="tok99", quote_version=7)

    bid_meta = executor._live_orders["bid-111"]
    ask_meta = executor._live_orders["ask-222"]

    assert bid_meta["side"] == "BUY"
    assert bid_meta["price"] == Decimal("0.48")
    assert bid_meta["quote_version"] == 7
    assert bid_meta["token_id"] == "tok99"
    assert isinstance(bid_meta["placed_at"], datetime)

    assert ask_meta["side"] == "SELL"
    assert ask_meta["price"] == Decimal("0.52")


# ---------------------------------------------------------------------------
# cancel_all_orders tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cancel_all_clears_tracking():
    """cancel_all_orders calls CLOB cancel_all and empties _live_orders."""
    clob = make_clob_client()
    clob.cancel_all = AsyncMock(return_value=5)
    executor = Executor(clob_client=clob, config=make_config())

    # Pre-populate some orders
    for i in range(3):
        executor._live_orders[f"order-{i}"] = {"side": "BUY", "token_id": "tok"}

    count = await executor.cancel_all_orders()

    assert count == 5
    assert executor._live_orders == {}
    clob.cancel_all.assert_awaited_once()


@pytest.mark.asyncio
async def test_cancel_all_returns_clob_count():
    """cancel_all_orders returns the count from the CLOB response."""
    clob = make_clob_client()
    clob.cancel_all = AsyncMock(return_value=12)
    executor = Executor(clob_client=clob, config=make_config())

    count = await executor.cancel_all_orders()
    assert count == 12


# ---------------------------------------------------------------------------
# Heartbeat tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_heartbeat_runs_periodically():
    """Heartbeat task calls send_heartbeat repeatedly at the configured interval."""
    clob = make_clob_client()
    heartbeat_call_count = 0

    async def mock_heartbeat():
        nonlocal heartbeat_call_count
        heartbeat_call_count += 1
        return {"heartbeatID": f"hb-{heartbeat_call_count}"}

    clob.send_heartbeat = mock_heartbeat

    # Patch asyncio.sleep so the loop runs fast and we can count iterations
    sleep_count = 0
    original_sleep = asyncio.sleep

    async def fast_sleep(seconds):
        nonlocal sleep_count
        sleep_count += 1
        if sleep_count >= 3:
            # After 3 iterations, cancel the task by raising CancelledError
            raise asyncio.CancelledError
        await original_sleep(0)  # yield control without real delay

    executor = Executor(clob_client=clob, config=make_config(heartbeat_interval_seconds=5))

    with patch("services.polymarket.executor.asyncio.sleep", side_effect=fast_sleep):
        await executor.start_heartbeat()
        # Wait for the task to be cancelled (fast_sleep raises after 3 iterations)
        try:
            await executor._heartbeat_task
        except asyncio.CancelledError:
            pass

    # send_heartbeat should have been called at least twice (iterations 1 and 2)
    assert heartbeat_call_count >= 2


@pytest.mark.asyncio
async def test_heartbeat_failure_does_not_crash():
    """When send_heartbeat raises, the heartbeat loop continues without crashing."""
    clob = make_clob_client()
    call_count = 0

    async def failing_then_succeeding_heartbeat():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("Heartbeat connection error")
        return {"heartbeatID": "hb-ok"}

    clob.send_heartbeat = failing_then_succeeding_heartbeat

    sleep_count = 0
    original_sleep = asyncio.sleep

    async def fast_sleep(seconds):
        nonlocal sleep_count
        sleep_count += 1
        if sleep_count >= 3:
            raise asyncio.CancelledError
        await original_sleep(0)

    executor = Executor(clob_client=clob, config=make_config(heartbeat_interval_seconds=5))

    with patch("services.polymarket.executor.asyncio.sleep", side_effect=fast_sleep):
        await executor.start_heartbeat()
        try:
            await executor._heartbeat_task
        except asyncio.CancelledError:
            pass

    # The loop should have continued after the first failure
    assert call_count >= 2


@pytest.mark.asyncio
@patch("services.polymarket.executor.asyncio.sleep", new_callable=AsyncMock)
async def test_stop_heartbeat_cancels_task(mock_sleep):
    """stop_heartbeat cancels the running task and sets _heartbeat_task to None."""
    executor = Executor(clob_client=make_clob_client(), config=make_config())
    await executor.start_heartbeat()
    task = executor._heartbeat_task
    assert task is not None
    assert not task.done()
    await executor.stop_heartbeat()
    assert task.done()
    assert executor._heartbeat_task is None


@pytest.mark.asyncio
@patch("services.polymarket.executor.asyncio.sleep", new_callable=AsyncMock)
async def test_start_heartbeat_idempotent(mock_sleep):
    """Calling start_heartbeat when already running is a no-op (same task object)."""
    executor = Executor(clob_client=make_clob_client(), config=make_config())
    await executor.start_heartbeat()
    task_first = executor._heartbeat_task
    await executor.start_heartbeat()  # second call should be no-op
    assert executor._heartbeat_task is task_first  # same task, not replaced
    await executor.stop_heartbeat()


# ---------------------------------------------------------------------------
# handle_fill tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_fill_updates_inventory_buy():
    """A BUY fill increases _inventory_delta by the fill size."""
    executor = Executor(clob_client=make_clob_client(), config=make_config())
    # Pre-track the order
    executor._live_orders["order-buy"] = {
        "placed_at": datetime.now(tz=timezone.utc),
        "quote_version": 1,
        "side": "BUY",
        "price": Decimal("0.48"),
        "size": Decimal("50"),
        "token_id": "tok",
    }

    fill_data = {
        "order_id": "order-buy",
        "price": "0.48",
        "size": "50",
        "side": "BUY",
        "timestamp": "2026-03-25T10:00:00Z",
    }
    await executor.handle_fill(fill_data)

    assert executor.inventory_delta == Decimal("50")


@pytest.mark.asyncio
async def test_handle_fill_updates_inventory_sell():
    """A SELL fill decreases _inventory_delta by the fill size."""
    executor = Executor(clob_client=make_clob_client(), config=make_config())
    executor._live_orders["order-sell"] = {
        "placed_at": datetime.now(tz=timezone.utc),
        "quote_version": 1,
        "side": "SELL",
        "price": Decimal("0.52"),
        "size": Decimal("30"),
        "token_id": "tok",
    }

    fill_data = {
        "order_id": "order-sell",
        "price": "0.52",
        "size": "30",
        "side": "SELL",
        "timestamp": "2026-03-25T10:00:05Z",
    }
    await executor.handle_fill(fill_data)

    assert executor.inventory_delta == Decimal("-30")


@pytest.mark.asyncio
async def test_handle_fill_accumulates_across_fills():
    """Multiple fills accumulate correctly in _inventory_delta."""
    executor = Executor(clob_client=make_clob_client(), config=make_config())
    now = datetime.now(tz=timezone.utc)
    executor._live_orders["b1"] = {"placed_at": now, "quote_version": 1, "side": "BUY", "price": Decimal("0.48"), "size": Decimal("50"), "token_id": "t"}
    executor._live_orders["s1"] = {"placed_at": now, "quote_version": 2, "side": "SELL", "price": Decimal("0.52"), "size": Decimal("20"), "token_id": "t"}

    await executor.handle_fill({"order_id": "b1", "price": "0.48", "size": "50", "side": "BUY", "timestamp": ""})
    await executor.handle_fill({"order_id": "s1", "price": "0.52", "size": "20", "side": "SELL", "timestamp": ""})

    # Net: +50 - 20 = +30
    assert executor.inventory_delta == Decimal("30")


@pytest.mark.asyncio
async def test_handle_fill_calls_callback():
    """handle_fill invokes on_fill_callback with the fill_data dict."""
    received_fills = []

    def sync_callback(fill_data: dict) -> None:
        received_fills.append(fill_data)

    executor = Executor(clob_client=make_clob_client(), config=make_config(), on_fill_callback=sync_callback)
    fill_data = {"order_id": "o1", "price": "0.50", "size": "10", "side": "BUY", "timestamp": ""}

    await executor.handle_fill(fill_data)

    assert len(received_fills) == 1
    assert received_fills[0] is fill_data


@pytest.mark.asyncio
async def test_handle_fill_calls_async_callback():
    """handle_fill supports async on_fill_callback coroutines."""
    received_fills = []

    async def async_callback(fill_data: dict) -> None:
        received_fills.append(fill_data)

    executor = Executor(clob_client=make_clob_client(), config=make_config(), on_fill_callback=async_callback)
    fill_data = {"order_id": "o2", "price": "0.50", "size": "10", "side": "SELL", "timestamp": ""}

    await executor.handle_fill(fill_data)

    assert len(received_fills) == 1
    assert received_fills[0] is fill_data
    # Inventory should also be updated
    assert executor.inventory_delta == Decimal("-10")


@pytest.mark.asyncio
async def test_handle_fill_removes_order_from_tracking():
    """After a fill, the order is removed from _live_orders (full-fill semantics)."""
    executor = Executor(clob_client=make_clob_client(), config=make_config())
    executor._live_orders["filled-order"] = {
        "placed_at": datetime.now(tz=timezone.utc),
        "quote_version": 1,
        "side": "BUY",
        "price": Decimal("0.48"),
        "size": Decimal("50"),
        "token_id": "tok",
    }

    await executor.handle_fill({
        "order_id": "filled-order",
        "price": "0.48",
        "size": "50",
        "side": "BUY",
        "timestamp": "",
    })

    assert "filled-order" not in executor._live_orders


@pytest.mark.asyncio
async def test_handle_fill_untracked_order_still_updates_inventory():
    """A fill for an untracked order (e.g., prior session) still updates inventory_delta."""
    executor = Executor(clob_client=make_clob_client(), config=make_config())

    fill_data = {"order_id": "unknown-order", "price": "0.50", "size": "25", "side": "BUY", "timestamp": ""}
    await executor.handle_fill(fill_data)

    assert executor.inventory_delta == Decimal("25")


# ---------------------------------------------------------------------------
# post-only enforcement tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_only_always_true_bid():
    """place_quotes always passes post_only=True when placing a BUY order."""
    clob = make_clob_client()
    clob.place_order = AsyncMock(return_value="bid-id")
    executor = Executor(clob_client=clob, config=make_config())

    quote = make_quote(should_quote_ask=False, ask_price=None)
    await executor.place_quotes(quote, token_id="t", quote_version=1)

    call_kwargs = clob.place_order.call_args[1]
    assert call_kwargs.get("post_only") is True


@pytest.mark.asyncio
async def test_post_only_always_true_ask():
    """place_quotes always passes post_only=True when placing a SELL order."""
    clob = make_clob_client()
    clob.place_order = AsyncMock(return_value="ask-id")
    executor = Executor(clob_client=clob, config=make_config())

    quote = make_quote(should_quote_bid=False, bid_price=None)
    await executor.place_quotes(quote, token_id="t", quote_version=1)

    call_kwargs = clob.place_order.call_args[1]
    assert call_kwargs.get("post_only") is True


@pytest.mark.asyncio
async def test_post_only_always_true_both_sides():
    """post_only=True is set on both bid and ask place_order calls."""
    clob = make_clob_client()
    clob.place_order = AsyncMock(side_effect=["bid-id", "ask-id"])
    executor = Executor(clob_client=clob, config=make_config())

    await executor.place_quotes(make_quote(), token_id="t", quote_version=1)

    assert clob.place_order.call_count == 2
    for single_call in clob.place_order.call_args_list:
        assert single_call[1].get("post_only") is True, (
            f"Expected post_only=True in call {single_call}"
        )


# ---------------------------------------------------------------------------
# inventory_delta property test
# ---------------------------------------------------------------------------


def test_inventory_delta_initial_value():
    """inventory_delta starts at Decimal('0')."""
    executor = Executor(clob_client=make_clob_client(), config=make_config())
    assert executor.inventory_delta == Decimal("0")
