from __future__ import annotations

import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from services.simulation.schemas import SimEvent, SimOrder
from services.simulation.orderbook.book import SimulatedOrderBook
from services.simulation.orderbook.matching import OrderMatcher

FIXED_TS = datetime(2026, 4, 1, 9, 0, 0)


def make_snapshot_event(bids, asks):
    return SimEvent(
        event_id="snap-1",
        timestamp=FIXED_TS,
        event_type="snapshot",
        market_id="mkt-1",
        token_id="tok-1",
        payload={"bids": bids, "asks": asks},
    )


def make_buy_order(price, size, order_type="taker"):
    return SimOrder(
        order_id=f"ord-buy-{price}",
        market_id="mkt-1",
        token_id="tok-1",
        side="BUY",
        order_type=order_type,
        price=Decimal(str(price)),
        size=Decimal(str(size)),
        submit_time=FIXED_TS,
        post_only=(order_type == "maker"),
    )


def make_sell_order(price, size, order_type="taker"):
    return SimOrder(
        order_id=f"ord-sell-{price}",
        market_id="mkt-1",
        token_id="tok-1",
        side="SELL",
        order_type=order_type,
        price=Decimal(str(price)),
        size=Decimal(str(size)),
        submit_time=FIXED_TS,
        post_only=(order_type == "maker"),
    )


def test_apply_snapshot_populates_book():
    book = SimulatedOrderBook()
    event = make_snapshot_event(
        bids=[["0.45", "100"], ["0.44", "80"]],
        asks=[["0.55", "100"], ["0.56", "80"]],
    )
    book.apply_snapshot(event)
    assert book.best_bid() == Decimal("0.45")
    assert book.best_ask() == Decimal("0.55")


def test_apply_trade_removes_volume():
    book = SimulatedOrderBook()
    event = make_snapshot_event(
        bids=[["0.45", "100"], ["0.44", "80"]],
        asks=[["0.55", "100"], ["0.56", "80"]],
    )
    book.apply_snapshot(event)
    trade_event = SimEvent(
        event_id="trade-1",
        timestamp=FIXED_TS,
        event_type="trade",
        market_id="mkt-1",
        token_id="tok-1",
        payload={"side": "BUY", "price": 0.55, "size": 50},
    )
    book.apply_trade(trade_event)
    # Level still exists with 50 remaining
    assert book.best_ask() == Decimal("0.55")


def test_apply_trade_prunes_zero_level():
    book = SimulatedOrderBook()
    event = make_snapshot_event(
        bids=[["0.45", "100"], ["0.44", "80"]],
        asks=[["0.55", "100"], ["0.56", "80"]],
    )
    book.apply_snapshot(event)
    trade_event = SimEvent(
        event_id="trade-1",
        timestamp=FIXED_TS,
        event_type="trade",
        market_id="mkt-1",
        token_id="tok-1",
        payload={"side": "BUY", "price": 0.55, "size": 100},
    )
    book.apply_trade(trade_event)
    # Level at 0.55 exhausted; next best ask is 0.56
    assert book.best_ask() == Decimal("0.56")


def test_apply_cancel_removes_order():
    book = SimulatedOrderBook()
    # Place a single maker SELL order
    order = SimOrder(
        order_id="my-maker-1",
        market_id="mkt-1",
        token_id="tok-1",
        side="SELL",
        order_type="maker",
        price=Decimal("0.55"),
        size=Decimal("20"),
        submit_time=FIXED_TS,
        post_only=True,
    )
    book.place_limit(order)
    assert book.best_ask() == Decimal("0.55")

    cancel_event = SimEvent(
        event_id="cancel-1",
        timestamp=FIXED_TS,
        event_type="cancel",
        market_id="mkt-1",
        token_id="tok-1",
        payload={"side": "SELL", "price": 0.55, "order_id": "my-maker-1", "size": 20},
    )
    book.apply_cancel(cancel_event)
    assert book.best_ask() is None


def test_taker_single_level_full_fill():
    book = SimulatedOrderBook()
    event = make_snapshot_event(bids=[], asks=[["0.55", "100"]])
    book.apply_snapshot(event)
    order = make_buy_order(0.60, 50, "taker")
    fills = book.match_market(order)
    assert len(fills) == 1
    assert fills[0].fill_size == Decimal("50")
    assert fills[0].fill_price == Decimal("0.55")


def test_taker_multi_level_partial_fills():
    book = SimulatedOrderBook()
    event = make_snapshot_event(
        bids=[],
        asks=[["0.55", "30"], ["0.56", "40"], ["0.57", "30"]],
    )
    book.apply_snapshot(event)
    order = make_buy_order(0.60, 80, "taker")
    fills = book.match_market(order)
    assert len(fills) == 3
    fill_prices = [f.fill_price for f in fills]
    assert fill_prices == [Decimal("0.55"), Decimal("0.56"), Decimal("0.57")]


def test_taker_fill_sizes_sum_to_order_size():
    book = SimulatedOrderBook()
    event = make_snapshot_event(
        bids=[],
        asks=[["0.55", "30"], ["0.56", "40"], ["0.57", "30"]],
    )
    book.apply_snapshot(event)
    order = make_buy_order(0.60, 80, "taker")
    fills = book.match_market(order)
    assert sum(f.fill_size for f in fills) == Decimal("80")


def test_taker_slippage_vs_mid():
    book = SimulatedOrderBook()
    event = make_snapshot_event(
        bids=[["0.45", "100"]],
        asks=[["0.55", "100"]],
    )
    book.apply_snapshot(event)
    # mid = (0.45 + 0.55) / 2 = 0.50
    matcher = OrderMatcher()
    order = make_buy_order(0.60, 50, "taker")
    fills = matcher.match_taker(order, book, FIXED_TS)
    assert len(fills) == 1
    assert fills[0].slippage_vs_mid == Decimal("0.05")


def test_maker_post_only_rejection_would_cross():
    book = SimulatedOrderBook()
    event = make_snapshot_event(
        bids=[["0.45", "100"]],
        asks=[["0.55", "100"]],
    )
    book.apply_snapshot(event)
    matcher = OrderMatcher()
    # BUY at 0.55 crosses the best ask
    order = make_buy_order(0.55, 10, "maker")
    result = matcher.match_maker(order, book)
    assert result is None
    # Best ask must remain unchanged — order was not placed
    assert book.best_ask() == Decimal("0.55")
    # Verify the book wasn't polluted: best_bid still 0.45 (no new bid added)
    assert book.best_bid() == Decimal("0.45")


def test_maker_post_only_accepted_no_cross():
    book = SimulatedOrderBook()
    event = make_snapshot_event(
        bids=[],
        asks=[["0.55", "100"]],
    )
    book.apply_snapshot(event)
    matcher = OrderMatcher()
    # BUY at 0.50 does not cross ask of 0.55
    order = make_buy_order(0.50, 20, "maker")
    result = matcher.match_maker(order, book)
    assert result is None
    # Order was placed; best_bid should now be 0.50
    assert book.best_bid() == Decimal("0.50")


def test_would_cross_bid_at_or_above_ask():
    book = SimulatedOrderBook()
    event = make_snapshot_event(
        bids=[["0.45", "100"]],
        asks=[["0.55", "100"]],
    )
    book.apply_snapshot(event)
    matcher = OrderMatcher()
    # BUY at 0.55 == best_ask → would cross
    assert matcher.would_cross(make_buy_order(0.55, 10, "maker"), book) is True


def test_would_cross_ask_at_or_below_bid():
    book = SimulatedOrderBook()
    event = make_snapshot_event(
        bids=[["0.45", "100"]],
        asks=[["0.55", "100"]],
    )
    book.apply_snapshot(event)
    matcher = OrderMatcher()
    # SELL at 0.45 == best_bid → would cross
    assert matcher.would_cross(make_sell_order(0.45, 10, "maker"), book) is True


def test_time_priority_at_same_price():
    book = SimulatedOrderBook()
    first_order = SimOrder(
        order_id="first",
        market_id="mkt-1",
        token_id="tok-1",
        side="SELL",
        order_type="maker",
        price=Decimal("0.55"),
        size=Decimal("10"),
        submit_time=FIXED_TS,
        post_only=True,
    )
    second_order = SimOrder(
        order_id="second",
        market_id="mkt-1",
        token_id="tok-1",
        side="SELL",
        order_type="maker",
        price=Decimal("0.55"),
        size=Decimal("10"),
        submit_time=FIXED_TS + timedelta(seconds=1),
        post_only=True,
    )
    book.place_limit(first_order)
    book.place_limit(second_order)

    # Both orders queued at the same price level
    assert book.best_ask() == Decimal("0.55")
    # Access the internal queue to verify time priority
    key = Decimal("0.55")
    queue = book._asks[key]
    queue_list = list(queue)
    assert len(queue_list) == 2
    assert queue_list[0][0] == "first"
    assert queue_list[1][0] == "second"
