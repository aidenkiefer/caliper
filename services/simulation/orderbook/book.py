from __future__ import annotations

import uuid
from collections import deque
from datetime import datetime
from decimal import Decimal
from typing import Dict, Deque, List, Optional, Tuple

from sortedcontainers import SortedDict

from services.simulation.schemas import SimEvent, SimFill, SimOrder


class SimulatedOrderBook:
    """Full limit order book for one Polymarket token with price-time priority."""

    def __init__(self) -> None:
        # Bids: key = -price (so SortedDict iterates ascending → highest bid first)
        self._bids: SortedDict = SortedDict()  # {-price: deque of (order_id, size, timestamp)}
        # Asks: key = +price (ascending → lowest ask first)
        self._asks: SortedDict = SortedDict()  # {+price: deque of (order_id, size, timestamp)}

    def apply_snapshot(self, event: SimEvent) -> None:
        """Replace full book state from a snapshot event."""
        # payload: {"bids": [[price, size], ...], "asks": [[price, size], ...]}
        self._bids.clear()
        self._asks.clear()
        payload = event.payload
        for price_str, size_str in payload.get("bids", []):
            price = Decimal(str(price_str))
            size = Decimal(str(size_str))
            if size > 0:
                # Use synthetic order_id for snapshot levels
                self._bids[-price] = deque([("snapshot", size, event.timestamp)])
        for price_str, size_str in payload.get("asks", []):
            price = Decimal(str(price_str))
            size = Decimal(str(size_str))
            if size > 0:
                self._asks[price] = deque([("snapshot", size, event.timestamp)])

    def apply_trade(self, event: SimEvent) -> None:
        """Remove matched volume from the appropriate side."""
        payload = event.payload
        side = payload.get("side", "BUY")
        price = Decimal(str(payload["price"]))
        size = Decimal(str(payload["size"]))
        # Trade removes from the resting (maker) side
        # BUY taker hits ASK side resting orders, SELL taker hits BID side
        if side == "BUY":
            key = price
            book = self._asks
        else:
            key = -price
            book = self._bids
        if key not in book:
            return
        queue: deque = book[key]
        remaining = size
        while remaining > 0 and queue:
            order_id, level_size, ts = queue[0]
            if level_size <= remaining:
                remaining -= level_size
                queue.popleft()
            else:
                queue[0] = (order_id, level_size - remaining, ts)
                remaining = Decimal(0)
        if not queue:
            del book[key]

    def apply_cancel(self, event: SimEvent) -> None:
        """Remove a specific order by id."""
        payload = event.payload
        side = payload.get("side", "BUY")
        price = Decimal(str(payload["price"]))
        order_id = payload.get("order_id", "")
        size = Decimal(str(payload.get("size", 0)))
        if side == "BUY":
            key = -price
            book = self._bids
        else:
            key = price
            book = self._asks
        if key not in book:
            return
        queue: deque = book[key]
        # Remove the first entry matching order_id
        for i, (oid, sz, ts) in enumerate(queue):
            if oid == order_id:
                # Rebuild deque without this element
                new_queue: deque = deque(item for j, item in enumerate(queue) if j != i)
                if new_queue:
                    book[key] = new_queue
                else:
                    del book[key]
                return

    def place_limit(self, order: SimOrder) -> None:
        """Insert a limit order at its price level (behind existing orders — price-time priority)."""
        if order.side == "BUY":
            key = -order.price
            book = self._bids
        else:
            key = order.price
            book = self._asks
        if key not in book:
            book[key] = deque()
        book[key].append((order.order_id, order.size, order.submit_time))

    def match_market(self, order: SimOrder) -> List[SimFill]:
        """Sweep opposite-side levels; return one SimFill per price level consumed."""
        if order.size <= 0:
            raise ValueError("Order size must be > 0")
        fills: List[SimFill] = []
        # BUY order sweeps asks, SELL order sweeps bids
        if order.side == "BUY":
            book = self._asks
            sign = 1
        else:
            book = self._bids
            sign = -1
        remaining = order.size
        fill_idx = 0
        keys_to_delete = []
        for key in list(book.keys()):
            if remaining <= 0:
                break
            # For asks book: key = price (positive)
            # For bids book: key = -price (negative), actual_price = -key
            if sign == -1:
                actual_price = -key
            else:
                actual_price = key
            queue: deque = book[key]
            level_fill_size = Decimal(0)
            while remaining > 0 and queue:
                order_id, level_size, ts = queue[0]
                fill_size = min(remaining, level_size)
                level_fill_size += fill_size
                remaining -= fill_size
                if fill_size >= level_size:
                    queue.popleft()
                else:
                    queue[0] = (order_id, level_size - fill_size, ts)
                    # remaining is now 0, loop will exit
            if level_fill_size > 0:
                fills.append(SimFill(
                    fill_id=f"{order.order_id}-fill-{fill_idx}",
                    order_id=order.order_id,
                    market_id=order.market_id,
                    token_id=order.token_id,
                    side=order.side,
                    fill_price=actual_price,
                    fill_size=level_fill_size,
                    fill_time=order.submit_time,
                    maker_fill=False,
                    slippage_vs_mid=Decimal(0),  # caller sets this
                    mid_at_fill=Decimal(0),       # caller sets this
                ))
                fill_idx += 1
            if not queue:
                keys_to_delete.append(key)
        for key in keys_to_delete:
            if key in book:
                del book[key]
        return fills

    def best_bid(self) -> Optional[Decimal]:
        if not self._bids:
            return None
        key = self._bids.keys()[0]
        return -key

    def best_ask(self) -> Optional[Decimal]:
        if not self._asks:
            return None
        key = self._asks.keys()[0]
        return key

    def mid_price(self) -> Optional[Decimal]:
        bid = self.best_bid()
        ask = self.best_ask()
        if bid is None or ask is None:
            return None
        return (bid + ask) / 2

    def spread(self) -> Optional[Decimal]:
        bid = self.best_bid()
        ask = self.best_ask()
        if bid is None or ask is None:
            return None
        return ask - bid
