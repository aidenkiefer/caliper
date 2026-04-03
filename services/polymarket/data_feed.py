"""
Real-time data feed for the Polymarket BTC hourly market-making service.

Aggregates two concurrent data sources:
1. Polymarket CLOB WebSocket (`market` channel) — orderbook snapshots and deltas
2. Binance REST price polling — BTC/USDT current price every 5 seconds

The `DataFeed` class maintains an internal `DataFeedState` dataclass with
thread-safe updates via `asyncio.Lock`. Callers retrieve a point-in-time
snapshot as an `OrderbookState` via `get_current_state()`.

Staleness: if the Binance price has not been updated within
`config.binance_stale_seconds`, `get_current_state()` sets
`binance_stale=True` on the returned snapshot. Callers may raise or log
accordingly.

Usage::

    feed = DataFeed(clob_client, binance_client, config)
    await feed.start(token_id="12345")
    state = feed.get_current_state()
    await feed.stop()
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field, replace as dataclass_replace
from datetime import datetime, timezone
from decimal import Decimal
from typing import Callable, List, Optional

from services.polymarket.adapters.binance_client import BinanceClient
from services.polymarket.adapters.clob_client import CLOBClient
from services.polymarket.config import PolymarketConfig

logger = logging.getLogger(__name__)

# How frequently to poll Binance (seconds)
BINANCE_POLL_INTERVAL_SECONDS = 5


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class StaleDataError(Exception):
    """Raised when the Binance price has not been refreshed within the
    configured staleness threshold."""


# ---------------------------------------------------------------------------
# Internal state dataclass
# ---------------------------------------------------------------------------


@dataclass
class DataFeedState:
    """Internal mutable state for the DataFeed.

    Updated by the WebSocket callback and the Binance polling loop.
    All mutations must be performed while holding the associated asyncio.Lock.
    """

    # Core book state
    best_bid: Optional[Decimal] = None
    best_ask: Optional[Decimal] = None
    midpoint: Optional[Decimal] = None
    spread: Optional[Decimal] = None
    bids: List[tuple] = field(default_factory=list)  # [(price, size), ...] desc
    asks: List[tuple] = field(default_factory=list)  # [(price, size), ...] asc

    # Depth metrics
    bid_depth_1pct: Optional[Decimal] = None
    ask_depth_1pct: Optional[Decimal] = None
    imbalance: Optional[Decimal] = None
    num_orders_at_best_bid: int = 0
    num_orders_at_best_ask: int = 0
    total_depth_top_3_levels: Optional[Decimal] = None

    # Queue position estimates (size of orders ahead of ours at best bid/ask)
    our_bid_queue_ahead_size: Optional[Decimal] = None
    our_ask_queue_ahead_size: Optional[Decimal] = None

    # Reward eligibility
    is_within_reward_spread: bool = False
    is_above_min_size: bool = False

    # Binance
    binance_price: Optional[Decimal] = None
    binance_last_updated: Optional[datetime] = None

    # Timing
    last_updated: Optional[datetime] = None

    # Last trade price (from WebSocket)
    last_trade_price: Optional[Decimal] = None

    # Current tick size
    tick_size: Optional[Decimal] = None

    # Staleness flag (set by get_current_state when converting to snapshot)
    binance_stale: bool = False


# ---------------------------------------------------------------------------
# Book metrics computation
# ---------------------------------------------------------------------------


def _compute_book_metrics(
    bids: List[tuple],
    asks: List[tuple],
) -> dict:
    """Compute derived metrics from sorted bid/ask level lists.

    Parameters
    ----------
    bids:
        List of ``(price, size)`` tuples sorted descending by price.
    asks:
        List of ``(price, size)`` tuples sorted ascending by price.

    Returns
    -------
    dict
        Containing ``best_bid``, ``best_ask``, ``midpoint``, ``spread``,
        ``bid_depth_1pct``, ``ask_depth_1pct``, ``imbalance``,
        ``num_orders_at_best_bid``, ``num_orders_at_best_ask``,
        ``total_depth_top_3_levels``.
    """
    best_bid = bids[0][0] if bids else None
    best_ask = asks[0][0] if asks else None

    midpoint: Optional[Decimal] = None
    spread: Optional[Decimal] = None
    if best_bid is not None and best_ask is not None:
        midpoint = (best_bid + best_ask) / Decimal("2")
        spread = best_ask - best_bid

    bid_depth_1pct: Optional[Decimal] = None
    ask_depth_1pct: Optional[Decimal] = None
    imbalance: Optional[Decimal] = None

    if midpoint is not None:
        bid_threshold = midpoint * Decimal("0.99")
        ask_threshold = midpoint * Decimal("1.01")
        bid_depth_1pct = sum(
            (size for price, size in bids if price >= bid_threshold),
            Decimal("0"),
        )
        ask_depth_1pct = sum(
            (size for price, size in asks if price <= ask_threshold),
            Decimal("0"),
        )
        total_depth = bid_depth_1pct + ask_depth_1pct
        if total_depth > Decimal("0"):
            imbalance = (bid_depth_1pct - ask_depth_1pct) / total_depth

    # Top-3 levels depth
    top_3_bid = sum((size for _, size in bids[:3]), Decimal("0"))
    top_3_ask = sum((size for _, size in asks[:3]), Decimal("0"))
    total_depth_top_3_levels = top_3_bid + top_3_ask

    # Order counts at best bid/ask
    num_orders_at_best_bid = sum(1 for p, _ in bids if p == best_bid) if best_bid else 0
    num_orders_at_best_ask = sum(1 for p, _ in asks if p == best_ask) if best_ask else 0

    return {
        "best_bid": best_bid,
        "best_ask": best_ask,
        "midpoint": midpoint,
        "spread": spread,
        "bid_depth_1pct": bid_depth_1pct,
        "ask_depth_1pct": ask_depth_1pct,
        "imbalance": imbalance,
        "num_orders_at_best_bid": num_orders_at_best_bid,
        "num_orders_at_best_ask": num_orders_at_best_ask,
        "total_depth_top_3_levels": total_depth_top_3_levels,
    }


def _parse_levels(raw_levels: list) -> List[tuple]:
    """Parse a list of CLOB level dicts ``[{"price": "0.48", "size": "50"}, ...]``
    into a list of ``(Decimal, Decimal)`` tuples."""
    result = []
    for level in raw_levels:
        try:
            price = Decimal(str(level["price"]))
            size = Decimal(str(level["size"]))
            result.append((price, size))
        except (KeyError, Exception) as exc:
            logger.warning("Skipping unparseable level %r: %s", level, exc)
    return result


def _apply_price_change(
    existing: List[tuple],
    update: List[tuple],
    descending: bool,
) -> List[tuple]:
    """Apply a price-change delta to an existing level list.

    Levels with size == 0 in ``update`` are treated as removals.  New or
    updated prices replace existing entries at the same price.

    Parameters
    ----------
    existing:
        Current level list.
    update:
        Delta levels from the ``price_change`` message.
    descending:
        If True the result is sorted descending (bids); else ascending (asks).
    """
    book: dict = {price: size for price, size in existing}
    for price, size in update:
        if size == Decimal("0"):
            book.pop(price, None)
        else:
            book[price] = size
    return sorted(book.items(), key=lambda x: x[0], reverse=descending)


# ---------------------------------------------------------------------------
# DataFeed
# ---------------------------------------------------------------------------


class DataFeed:
    """Aggregates the Polymarket CLOB WebSocket orderbook and Binance price
    polling into a unified real-time state.

    Parameters
    ----------
    clob_client:
        Authenticated CLOB client used to subscribe to the WebSocket.
    binance_client:
        Binance client used to poll the current BTC/USDT price.
    config:
        Service configuration (poll intervals, staleness thresholds, reward
        eligibility parameters).
    hour_open_price:
        BTC price at the start of the current hourly window. Used for reward
        eligibility computations that need the window reference price.
    """

    def __init__(
        self,
        clob_client: CLOBClient,
        binance_client: BinanceClient,
        config: PolymarketConfig,
        hour_open_price: Optional[Decimal] = None,
    ) -> None:
        self._clob = clob_client
        self._binance = binance_client
        self._config = config
        self._hour_open = hour_open_price
        self._state = DataFeedState()
        self._lock = asyncio.Lock()
        self._running = False
        self._tasks: List[asyncio.Task] = []
        self._token_id: Optional[str] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self, token_id: str) -> None:
        """Subscribe to the WebSocket and start the Binance polling loop.

        Both tasks run concurrently. Errors are logged but do not propagate
        to the caller — the DataFeed keeps running (WebSocket reconnect is
        handled inside ``CLOBClient.subscribe_market_channel``).

        Parameters
        ----------
        token_id:
            The CLOB token ID (YES or NO outcome token) to subscribe to.
        """
        self._token_id = token_id
        self._running = True

        ws_task = asyncio.create_task(
            self._run_websocket(token_id),
            name=f"datafeed-ws-{token_id}",
        )
        binance_task = asyncio.create_task(
            self._poll_binance(),
            name="datafeed-binance-poll",
        )
        self._tasks = [ws_task, binance_task]
        logger.info("DataFeed started: token_id=%s", token_id)

    async def stop(self) -> None:
        """Cancel all background tasks and mark the feed as stopped."""
        self._running = False
        for task in self._tasks:
            if not task.done():
                task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = []
        logger.info("DataFeed stopped")

    # ------------------------------------------------------------------
    # State access
    # ------------------------------------------------------------------

    def get_current_state(self) -> DataFeedState:
        """Return a snapshot of the current market state as a DataFeedState.

        This is a synchronous method (no lock acquisition) that reads the
        current state.  Concurrent writes by the WebSocket or polling tasks
        will complete atomically before this read because Python's GIL and
        asyncio's single-threaded event loop ensure that attribute reads are
        not interleaved with async-context-manager-guarded writes.

        The returned DataFeedState contains all basic and extended fields
        (binance_price, num_orders_at_best_bid, num_orders_at_best_ask,
        total_depth_top_3_levels, our_bid_queue_ahead_size,
        our_ask_queue_ahead_size, is_within_reward_spread, is_above_min_size)
        that the quoting engine requires.

        Raises
        ------
        StaleDataError
            If the Binance price was last updated more than
            ``config.binance_stale_seconds`` ago.
        """
        state = self._state

        # Staleness check
        if state.binance_last_updated is not None:
            age = (datetime.now(tz=timezone.utc) - state.binance_last_updated).total_seconds()
            if age > self._config.binance_stale_seconds:
                raise StaleDataError(
                    f"Binance price is stale: last updated {age:.1f}s ago "
                    f"(threshold={self._config.binance_stale_seconds}s)"
                )

        # Return a shallow copy so callers get a stable snapshot
        snapshot = dataclass_replace(state)
        if snapshot.last_updated is None:
            snapshot.last_updated = datetime.now(tz=timezone.utc)
        return snapshot

    # ------------------------------------------------------------------
    # WebSocket handler
    # ------------------------------------------------------------------

    async def _run_websocket(self, token_id: str) -> None:
        """Wrapper task that calls ``subscribe_market_channel`` and logs errors."""
        try:
            await self._clob.subscribe_market_channel(token_id, self._on_book_update)
        except Exception as exc:
            logger.error("DataFeed WebSocket task ended with error: %s", exc)

    async def _on_book_update(self, book_data: dict) -> None:
        """Handle a single parsed WebSocket message.

        Dispatches on ``event_type`` / ``type``:
        - ``book``: full snapshot → rebuild local book
        - ``price_change``: delta → apply to local book
        - ``last_trade_price``: update last trade price field
        - ``tick_size_change``: update tick size field

        Parameters
        ----------
        book_data:
            Parsed message dict from the CLOB WebSocket.
        """
        msg_type = book_data.get("event_type") or book_data.get("type") or ""

        async with self._lock:
            if msg_type == "book":
                await self._handle_book_snapshot(book_data)
            elif msg_type == "price_change":
                await self._handle_price_change(book_data)
            elif msg_type == "last_trade_price":
                price_str = book_data.get("price")
                if price_str:
                    self._state.last_trade_price = Decimal(str(price_str))
            elif msg_type == "tick_size_change":
                tick_str = book_data.get("tick_size")
                if tick_str:
                    self._state.tick_size = Decimal(str(tick_str))
            else:
                logger.debug("Unknown WebSocket message type: %r", msg_type)

    async def _handle_book_snapshot(self, book_data: dict) -> None:
        """Rebuild the local orderbook from a full ``book`` snapshot message.

        Assumes the lock is already held.
        """
        raw_bids = book_data.get("bids", [])
        raw_asks = book_data.get("asks", [])

        bids = sorted(_parse_levels(raw_bids), key=lambda x: x[0], reverse=True)
        asks = sorted(_parse_levels(raw_asks), key=lambda x: x[0])

        self._state.bids = bids
        self._state.asks = asks
        self._update_computed_fields()

    async def _handle_price_change(self, book_data: dict) -> None:
        """Apply a ``price_change`` delta to the local orderbook.

        Assumes the lock is already held.
        """
        # price_change messages use the same bids/asks structure
        raw_bids = book_data.get("bids", [])
        raw_asks = book_data.get("asks", [])

        delta_bids = _parse_levels(raw_bids)
        delta_asks = _parse_levels(raw_asks)

        if delta_bids:
            self._state.bids = _apply_price_change(
                self._state.bids, delta_bids, descending=True
            )
        if delta_asks:
            self._state.asks = _apply_price_change(
                self._state.asks, delta_asks, descending=False
            )

        self._update_computed_fields()

    def _update_computed_fields(self) -> None:
        """Recompute all derived metrics from `self._state.bids` / `.asks`.

        Assumes the lock is already held.
        """
        metrics = _compute_book_metrics(self._state.bids, self._state.asks)

        self._state.best_bid = metrics["best_bid"]
        self._state.best_ask = metrics["best_ask"]
        self._state.midpoint = metrics["midpoint"]
        self._state.spread = metrics["spread"]
        self._state.bid_depth_1pct = metrics["bid_depth_1pct"]
        self._state.ask_depth_1pct = metrics["ask_depth_1pct"]
        self._state.imbalance = metrics["imbalance"]
        self._state.num_orders_at_best_bid = metrics["num_orders_at_best_bid"]
        self._state.num_orders_at_best_ask = metrics["num_orders_at_best_ask"]
        self._state.total_depth_top_3_levels = metrics["total_depth_top_3_levels"]

        # Queue position: treat the full size at best bid/ask as ahead of ours
        # (conservative estimate — our orders have not been placed yet)
        self._state.our_bid_queue_ahead_size = (
            self._state.bids[0][1] if self._state.bids else None
        )
        self._state.our_ask_queue_ahead_size = (
            self._state.asks[0][1] if self._state.asks else None
        )

        # Reward eligibility
        self._update_reward_eligibility()

        self._state.last_updated = datetime.now(tz=timezone.utc)

    def _update_reward_eligibility(self) -> None:
        """Update reward eligibility flags.

        Assumes the lock is already held.

        - ``is_within_reward_spread``: True if spread ≤ ``rewards_max_spread`` (if set).
          When ``rewards_max_spread`` is not configured, defaults to False.
        - ``is_above_min_size``: True if both sides of the book at best have
          size ≥ ``rewards_min_size`` (if set). When not configured, defaults to False.
        """
        # Spread eligibility — compare against config quote_spread as a proxy
        # (a proper MarketInfo with rewards_max_spread would be passed in for
        # production; for now we use the configured quote_spread as the ceiling)
        spread = self._state.spread
        if spread is not None and self._config.quote_spread is not None:
            self._state.is_within_reward_spread = spread <= self._config.quote_spread
        else:
            self._state.is_within_reward_spread = False

        # Size eligibility — check best-level sizes against quote_size
        bid_size = self._state.bids[0][1] if self._state.bids else Decimal("0")
        ask_size = self._state.asks[0][1] if self._state.asks else Decimal("0")
        min_size = self._config.quote_size
        self._state.is_above_min_size = (
            bid_size >= min_size and ask_size >= min_size
        )

    # ------------------------------------------------------------------
    # Binance polling
    # ------------------------------------------------------------------

    async def _poll_binance(self) -> None:
        """Poll Binance for the current BTC/USDT price every
        ``BINANCE_POLL_INTERVAL_SECONDS`` seconds.

        Errors are logged and the loop continues. Stops when
        ``self._running`` is False.
        """
        while self._running:
            try:
                price = await self._binance.get_current_price("BTCUSDT")
                async with self._lock:
                    self._state.binance_price = price
                    self._state.binance_last_updated = datetime.now(tz=timezone.utc)
                logger.debug("Binance price updated: %s", price)
            except Exception as exc:
                logger.warning("Binance poll failed: %s", exc)

            # Wait before next poll; check _running frequently
            try:
                await asyncio.sleep(BINANCE_POLL_INTERVAL_SECONDS)
            except asyncio.CancelledError:
                break
