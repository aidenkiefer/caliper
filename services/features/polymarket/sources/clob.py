"""
CLOB data source for the Polymarket feature pipeline.

Maintains a live orderbook buffer via WebSocket and provides REST-based
snapshots for recovery, reward config, and fee rate lookups.

WebSocket endpoint: wss://ws-subscriptions-clob.polymarket.com/ws/market
REST base:          https://clob.polymarket.com

Usage::

    source = CLOBSource()
    await source.connect(token_id="12345...")
    state = await source.get_orderbook_state()
    fee_rate = await source.fetch_fee_rate("12345...")
    reward_cfg = await source.fetch_reward_config("12345...")
    await source.reconnect()

Notes
-----
- This is a **data source only** — it does not place orders or manage order
  heartbeats.  The heartbeat loop here keeps the CLOB WebSocket connection
  alive for market-data subscriptions only.
- No authentication is required for public book/fee-rate endpoints.
- ``bids_depth_5tick`` / ``asks_depth_5tick`` are computed by summing level
  sizes within 5 × tick_size of the best bid/ask respectively.
- HTTP 425 (weekly CLOB restart) is handled with exponential backoff.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

import httpx
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
_REST_BASE = "https://clob.polymarket.com"
_HEARTBEAT_INTERVAL_SECONDS = 5
_DEFAULT_TICK_SIZE = Decimal("0.01")

# Reconnect backoff parameters
_BACKOFF_BASE = 1.0   # seconds
_BACKOFF_MAX = 30.0   # seconds

# RewardConfig cache TTL
_REWARD_CACHE_TTL_SECONDS = 86_400  # 24 h


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class DataUnavailable(Exception):
    """Raised when ``CLOBSource.get_orderbook_state()`` is called before any
    data has been received from the CLOB WebSocket or REST snapshot."""


# ---------------------------------------------------------------------------
# Public dataclasses
# ---------------------------------------------------------------------------


@dataclass
class OrderbookState:
    """Point-in-time snapshot of the CLOB orderbook for a single token.

    Attributes
    ----------
    best_bid:
        Best (highest) bid price.
    best_ask:
        Best (lowest) ask price.
    bids_depth_5tick:
        Total size of all bid levels within 5 ticks of ``best_bid``.
    asks_depth_5tick:
        Total size of all ask levels within 5 ticks of ``best_ask``.
    last_trade_price:
        Most-recent trade price received from the WebSocket, or ``None``.
    last_trade_ts:
        Timestamp of the most-recent trade message, or ``None``.
    last_price_change_ts:
        Timestamp of the most-recent ``price_change`` message, or ``None``.
    received_at:
        Wall-clock UTC time when this snapshot was captured.
    """

    best_bid: Decimal
    best_ask: Decimal
    bids_depth_5tick: Decimal
    asks_depth_5tick: Decimal
    last_trade_price: Optional[Decimal]
    last_trade_ts: Optional[datetime]
    last_price_change_ts: Optional[datetime]
    received_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))


@dataclass
class RewardConfig:
    """Reward eligibility configuration for a CLOB market.

    Attributes
    ----------
    eligible:
        Whether the market currently offers maker rewards.
    max_spread:
        Maximum allowable spread (inclusive) to qualify for rewards.
    min_size:
        Minimum resting order size to qualify for rewards.
    """

    eligible: bool
    max_spread: Optional[Decimal]
    min_size: Optional[Decimal]


# ---------------------------------------------------------------------------
# Internal buffer
# ---------------------------------------------------------------------------


@dataclass
class _BookBuffer:
    """Mutable internal state updated by WebSocket messages."""

    bids: List[Tuple[Decimal, Decimal]] = field(default_factory=list)  # desc
    asks: List[Tuple[Decimal, Decimal]] = field(default_factory=list)  # asc
    last_trade_price: Optional[Decimal] = None
    last_trade_ts: Optional[datetime] = None
    last_price_change_ts: Optional[datetime] = None
    tick_size: Decimal = _DEFAULT_TICK_SIZE
    has_data: bool = False
    stale: bool = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_levels(raw: list) -> List[Tuple[Decimal, Decimal]]:
    """Parse ``[{"price": "0.48", "size": "50"}, ...]`` into ``(Decimal, Decimal)`` tuples."""
    result: List[Tuple[Decimal, Decimal]] = []
    for lvl in raw:
        try:
            result.append((Decimal(str(lvl["price"])), Decimal(str(lvl["size"]))))
        except (KeyError, Exception) as exc:  # noqa: BLE001
            logger.warning("Skipping unparseable level %r: %s", lvl, exc)
    return result


def _apply_delta(
    existing: List[Tuple[Decimal, Decimal]],
    updates: List[Tuple[Decimal, Decimal]],
    descending: bool,
) -> List[Tuple[Decimal, Decimal]]:
    """Apply a price-change delta to an existing sorted level list.

    Levels with size ``== 0`` in *updates* are treated as removals.
    """
    book: Dict[Decimal, Decimal] = {p: s for p, s in existing}
    for price, size in updates:
        if size == Decimal("0"):
            book.pop(price, None)
        else:
            book[price] = size
    return sorted(book.items(), key=lambda x: x[0], reverse=descending)


def _depth_within_ticks(
    levels: List[Tuple[Decimal, Decimal]],
    best: Decimal,
    tick_size: Decimal,
    n_ticks: int = 5,
    side: str = "bid",
) -> Decimal:
    """Sum sizes within ``n_ticks * tick_size`` of *best* price.

    Parameters
    ----------
    levels:
        Sorted list of ``(price, size)`` tuples (desc for bids, asc for asks).
    best:
        Best bid or ask price.
    tick_size:
        Market tick size.
    n_ticks:
        Number of ticks from best price to include (default 5).
    side:
        ``"bid"`` (levels ≥ best − threshold) or ``"ask"`` (levels ≤ best + threshold).
    """
    threshold = tick_size * n_ticks
    total = Decimal("0")
    for price, size in levels:
        if side == "bid":
            if price >= best - threshold:
                total += size
        else:
            if price <= best + threshold:
                total += size
    return total


# ---------------------------------------------------------------------------
# CLOBSource
# ---------------------------------------------------------------------------


class CLOBSource:
    """Async CLOB data source.

    Maintains a live orderbook buffer via WebSocket and provides REST-based
    snapshots for recovery, reward config, and fee-rate lookups.

    All network I/O is deferred until ``connect()`` is called; the constructor
    is synchronous and creates no connections.
    """

    def __init__(self) -> None:
        self._buffer = _BookBuffer()
        self._lock = asyncio.Lock()
        self._running = False
        self._token_id: Optional[str] = None

        # Timestamps
        self.source_timestamp: datetime = datetime.now(tz=timezone.utc)

        # Reconnect state
        self._backoff: float = _BACKOFF_BASE

        # Background tasks
        self._ws_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None

        # RewardConfig cache: token_id -> (RewardConfig, cached_at_utc)
        self._reward_cache: Dict[str, Tuple[RewardConfig, datetime]] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self, token_id: str) -> None:
        """Open WebSocket, subscribe to book channels, and start background tasks.

        Parameters
        ----------
        token_id:
            CLOB token ID (YES or NO outcome token) to subscribe to.
        """
        self._token_id = token_id
        self._running = True

        # Populate buffer from REST before streaming begins
        await self.restore_from_rest(token_id)

        # Start WebSocket listener
        self._ws_task = asyncio.create_task(
            self._run_websocket(token_id),
            name=f"clob-ws-{token_id}",
        )

        # Start heartbeat loop
        self._heartbeat_task = asyncio.create_task(
            self._heartbeat_loop(),
            name="clob-heartbeat",
        )

        logger.info("CLOBSource connected: token_id=%s", token_id)

    async def disconnect(self) -> None:
        """Cancel background tasks and mark as stopped."""
        self._running = False
        for task in [self._ws_task, self._heartbeat_task]:
            if task and not task.done():
                task.cancel()
        tasks = [t for t in [self._ws_task, self._heartbeat_task] if t]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._ws_task = None
        self._heartbeat_task = None
        logger.info("CLOBSource disconnected")

    async def reconnect(self) -> None:
        """Reconnect after a disconnect.

        Cancels existing tasks, re-fetches the REST snapshot to populate the
        buffer, and restarts the WebSocket listener and heartbeat loop.
        Uses exponential backoff (1s, 2s, 4s … capped at 30s).
        """
        if not self._token_id:
            raise RuntimeError("Cannot reconnect: token_id not set (call connect() first)")

        # Cancel existing tasks
        for task in [self._ws_task, self._heartbeat_task]:
            if task and not task.done():
                task.cancel()
        tasks = [t for t in [self._ws_task, self._heartbeat_task] if t]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        logger.info(
            "CLOBSource reconnecting (backoff=%.1fs): token_id=%s",
            self._backoff,
            self._token_id,
        )
        await asyncio.sleep(self._backoff)
        self._backoff = min(self._backoff * 2, _BACKOFF_MAX)

        # Mark buffer stale until REST snapshot restores it
        async with self._lock:
            self._buffer.stale = True
            self._buffer.has_data = False

        await self.restore_from_rest(self._token_id)

        self._running = True
        self._ws_task = asyncio.create_task(
            self._run_websocket(self._token_id),
            name=f"clob-ws-{self._token_id}",
        )
        self._heartbeat_task = asyncio.create_task(
            self._heartbeat_loop(),
            name="clob-heartbeat",
        )

        logger.info("CLOBSource reconnected: token_id=%s", self._token_id)

    def _reset_backoff(self) -> None:
        """Reset reconnect backoff to initial value on successful connection."""
        self._backoff = _BACKOFF_BASE

    # ------------------------------------------------------------------
    # State access
    # ------------------------------------------------------------------

    async def get_orderbook_state(self) -> OrderbookState:
        """Return the current buffered orderbook state.

        Raises
        ------
        DataUnavailable
            If no data has been received yet or the buffer is marked stale.
        """
        async with self._lock:
            buf = self._buffer
            if not buf.has_data or buf.stale:
                raise DataUnavailable(
                    "No orderbook data available — buffer is empty or stale. "
                    "Call connect() and wait for the first WebSocket message."
                )
            # Copy all fields before releasing the lock to avoid further races
            bids = list(buf.bids)
            asks = list(buf.asks)
            tick_size = buf.tick_size
            last_trade_price = buf.last_trade_price
            last_trade_ts = buf.last_trade_ts
            last_price_change_ts = buf.last_price_change_ts

        # Compute depth outside the lock using the copied lists
        # bids are sorted descending; best bid is bids[0] (highest price)
        # asks are sorted ascending; best ask is asks[0] (lowest price)
        best_bid = bids[0][0] if bids else Decimal("0")
        best_ask = asks[0][0] if asks else Decimal("0")

        bids_depth = _depth_within_ticks(bids, best_bid, tick_size, side="bid")
        asks_depth = _depth_within_ticks(asks, best_ask, tick_size, side="ask")

        return OrderbookState(
            best_bid=best_bid,
            best_ask=best_ask,
            bids_depth_5tick=bids_depth,
            asks_depth_5tick=asks_depth,
            last_trade_price=last_trade_price,
            last_trade_ts=last_trade_ts,
            last_price_change_ts=last_price_change_ts,
            received_at=datetime.now(tz=timezone.utc),
        )

    # ------------------------------------------------------------------
    # REST lookups
    # ------------------------------------------------------------------

    async def fetch_fee_rate(self, token_id: str) -> Decimal:
        """Fetch the maker fee rate for *token_id*.

        Returns ``Decimal("0")`` if the market is not fee-enabled or the
        endpoint returns a non-200 response.

        Parameters
        ----------
        token_id:
            CLOB token ID to look up.
        """
        url = f"{_REST_BASE}/fee-rate"
        params = {"token_id": token_id}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params=params)
                if resp.status_code != 200:
                    logger.warning(
                        "fetch_fee_rate: non-200 response %d for token_id=%s",
                        resp.status_code,
                        token_id,
                    )
                    return Decimal("0")
                data = resp.json()
                fee_str = data.get("fee_rate") or data.get("rate") or data.get("feeRate")
                if fee_str is None:
                    return Decimal("0")
                return Decimal(str(fee_str))
        except Exception as exc:  # noqa: BLE001
            logger.warning("fetch_fee_rate failed for token_id=%s: %s", token_id, exc)
            return Decimal("0")

    async def fetch_reward_config(self, token_id: str) -> RewardConfig:
        """Fetch reward eligibility config for *token_id*, with 24-hour cache.

        Returns a ``RewardConfig`` with ``eligible=False`` if the endpoint
        returns a non-200 response or the token is not reward-eligible.

        Parameters
        ----------
        token_id:
            CLOB token ID to look up.
        """
        # Check in-memory cache
        if token_id in self._reward_cache:
            cached, cached_at = self._reward_cache[token_id]
            age = (datetime.now(tz=timezone.utc) - cached_at).total_seconds()
            if age < _REWARD_CACHE_TTL_SECONDS:
                return cached

        url = f"{_REST_BASE}/rewards/config"
        params = {"token_id": token_id}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params=params)
                if resp.status_code != 200:
                    logger.warning(
                        "fetch_reward_config: non-200 response %d for token_id=%s",
                        resp.status_code,
                        token_id,
                    )
                    config = RewardConfig(eligible=False, max_spread=None, min_size=None)
                    self._reward_cache[token_id] = (config, datetime.now(tz=timezone.utc))
                    return config
                data = resp.json()
                eligible = bool(data.get("rewards_eligible") or data.get("eligible") or False)
                max_spread_raw = data.get("max_spread") or data.get("maxSpread")
                min_size_raw = data.get("min_size") or data.get("minSize")
                config = RewardConfig(
                    eligible=eligible,
                    max_spread=Decimal(str(max_spread_raw)) if max_spread_raw is not None else None,
                    min_size=Decimal(str(min_size_raw)) if min_size_raw is not None else None,
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "fetch_reward_config failed for token_id=%s: %s", token_id, exc
            )
            config = RewardConfig(eligible=False, max_spread=None, min_size=None)

        self._reward_cache[token_id] = (config, datetime.now(tz=timezone.utc))
        return config

    async def restore_from_rest(self, token_id: str) -> None:
        """Fetch a full orderbook snapshot from REST and populate the buffer.

        Uses GET ``https://clob.polymarket.com/book?token_id=...``.
        Called on startup and after reconnect to ensure the buffer is
        populated before streaming begins.

        Implements exponential backoff (1s, 2s, 4s, max 30s) for HTTP 425
        (weekly CLOB restart), up to 5 retries.

        Parameters
        ----------
        token_id:
            CLOB token ID to snapshot.
        """
        url = f"{_REST_BASE}/book"
        params = {"token_id": token_id}
        backoff = 1.0
        max_retries = 5

        try:
            for attempt in range(max_retries):
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.get(url, params=params)
                    if resp.status_code == 425:
                        if attempt < max_retries - 1:
                            await asyncio.sleep(min(backoff, 30.0))
                            backoff = min(backoff * 2, 30.0)
                            continue
                        else:
                            logger.error(
                                "restore_from_rest: HTTP 425 after %d retries, giving up for token_id=%s",
                                max_retries,
                                token_id,
                            )
                            return
                    elif resp.status_code != 200:
                        logger.warning(
                            "restore_from_rest: non-200 response %d for token_id=%s",
                            resp.status_code,
                            token_id,
                        )
                        return
                    data = resp.json()
                    await self._apply_book_snapshot(data)
                    logger.info("restore_from_rest: buffer populated for token_id=%s", token_id)
                    break
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "restore_from_rest failed for token_id=%s: %s", token_id, exc
            )

    # ------------------------------------------------------------------
    # WebSocket loop
    # ------------------------------------------------------------------

    async def _run_websocket(self, token_id: str) -> None:
        """Connect to the CLOB WebSocket and dispatch messages until stopped.

        Automatically reconnects (with exponential backoff) on disconnect.
        Stops when ``self._running`` is False.
        """
        while self._running:
            try:
                async with websockets.connect(_WS_URL) as ws:
                    # Subscribe to all required channels
                    subscribe_msg = json.dumps({
                        "auth": {},
                        "type": "Market",
                        "markets": [],
                        "assets_ids": [token_id],
                    })
                    await ws.send(subscribe_msg)
                    logger.debug(
                        "_run_websocket: subscribed to market channel for token_id=%s",
                        token_id,
                    )

                    _backoff_reset_done = False
                    async for raw in ws:
                        if not self._running:
                            break
                        try:
                            messages = json.loads(raw)
                            # CLOB may send a list or a single dict
                            if isinstance(messages, dict):
                                messages = [messages]
                            for msg in messages:
                                await self._handle_ws_message(msg)
                            # Reset backoff only after the first successfully
                            # parsed and handled message to avoid resetting on
                            # a connection that closes right after the handshake
                            if not _backoff_reset_done:
                                self._reset_backoff()
                                _backoff_reset_done = True
                        except json.JSONDecodeError as exc:
                            logger.warning(
                                "_run_websocket: JSON parse error: %s (raw=%r)", exc, raw
                            )
                        except Exception as exc:  # noqa: BLE001
                            logger.warning(
                                "_run_websocket: error handling message: %s", exc
                            )

            except asyncio.CancelledError:
                logger.info("_run_websocket: task cancelled")
                return
            except (ConnectionClosed, WebSocketException, OSError) as exc:
                if not self._running:
                    return
                logger.warning(
                    "_run_websocket: connection lost (%s); reconnecting in %.1fs",
                    exc,
                    self._backoff,
                )
            except Exception as exc:  # noqa: BLE001
                if not self._running:
                    return
                logger.error("_run_websocket: unexpected error: %s", exc)

            if not self._running:
                return

            # Mark buffer stale during reconnect gap
            async with self._lock:
                self._buffer.stale = True

            await asyncio.sleep(self._backoff)
            self._backoff = min(self._backoff * 2, _BACKOFF_MAX)

            # Re-fetch REST snapshot before re-subscribing
            if self._running:
                await self.restore_from_rest(token_id)

    # ------------------------------------------------------------------
    # Message handlers
    # ------------------------------------------------------------------

    async def _handle_ws_message(self, msg: dict) -> None:
        """Dispatch a parsed WebSocket message to the appropriate handler."""
        msg_type = msg.get("event_type") or msg.get("type") or ""

        async with self._lock:
            self.source_timestamp = datetime.now(tz=timezone.utc)
            if msg_type == "book":
                self._apply_book_snapshot_unlocked(msg)
            elif msg_type == "price_change":
                self._apply_price_change(msg)
                self._buffer.last_price_change_ts = datetime.now(tz=timezone.utc)
            elif msg_type == "last_trade_price":
                price_str = msg.get("price")
                if price_str:
                    self._buffer.last_trade_price = Decimal(str(price_str))
                    self._buffer.last_trade_ts = datetime.now(tz=timezone.utc)
            elif msg_type == "tick_size_change":
                tick_str = msg.get("tick_size")
                if tick_str:
                    self._buffer.tick_size = Decimal(str(tick_str))
            else:
                logger.debug("_handle_ws_message: unknown type %r", msg_type)

    def _apply_book_snapshot_unlocked(self, data: dict) -> None:
        """Rebuild buffer from a full ``book`` message or REST snapshot.

        Caller is responsible for holding ``self._lock`` before invoking this
        method (or being in a single-threaded context where concurrent access
        is not possible, such as ``restore_from_rest`` before the WS task is
        started).
        """
        raw_bids = data.get("bids", [])
        raw_asks = data.get("asks", [])

        bids = sorted(_parse_levels(raw_bids), key=lambda x: x[0], reverse=True)
        asks = sorted(_parse_levels(raw_asks), key=lambda x: x[0])

        self._buffer.bids = bids
        self._buffer.asks = asks
        self._buffer.has_data = bool(bids or asks)
        self._buffer.stale = False

    async def _apply_book_snapshot(self, data: dict) -> None:
        """Acquire the lock then rebuild buffer from a full ``book`` snapshot.

        Used by ``restore_from_rest`` which runs outside the WS message loop.
        ``_handle_ws_message`` holds the lock and calls
        ``_apply_book_snapshot_unlocked`` directly to avoid re-entry.
        """
        async with self._lock:
            self._apply_book_snapshot_unlocked(data)

    def _apply_price_change(self, data: dict) -> None:
        """Apply a ``price_change`` delta to the buffer.

        Assumes the lock is already held.
        """
        delta_bids = _parse_levels(data.get("bids", []))
        delta_asks = _parse_levels(data.get("asks", []))

        if delta_bids:
            self._buffer.bids = _apply_delta(self._buffer.bids, delta_bids, descending=True)
        if delta_asks:
            self._buffer.asks = _apply_delta(self._buffer.asks, delta_asks, descending=False)

        self._buffer.has_data = True
        self._buffer.stale = False

    # ------------------------------------------------------------------
    # Heartbeat loop
    # ------------------------------------------------------------------

    async def _heartbeat_loop(self) -> None:
        """POST to ``/heartbeat`` every 5 seconds to keep the data connection alive.

        If the POST fails (network error or non-200 status), marks the buffer
        stale so that ``get_orderbook_state()`` raises ``DataUnavailable``
        until the connection is re-established.
        """
        url = f"{_REST_BASE}/heartbeat"
        while self._running:
            try:
                await asyncio.sleep(_HEARTBEAT_INTERVAL_SECONDS)
            except asyncio.CancelledError:
                return

            if not self._running:
                return

            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.post(url)
                if resp.status_code == 200:
                    logger.debug("_heartbeat_loop: OK")
                    async with self._lock:
                        # Clear stale flag only if we have data
                        if self._buffer.has_data:
                            self._buffer.stale = False
                elif resp.status_code == 425:
                    logger.warning(
                        "_heartbeat_loop: HTTP 425 (weekly restart); marking buffer stale"
                    )
                    async with self._lock:
                        self._buffer.stale = True
                else:
                    logger.warning(
                        "_heartbeat_loop: unexpected status %d; marking buffer stale",
                        resp.status_code,
                    )
                    async with self._lock:
                        self._buffer.stale = True
            except asyncio.CancelledError:
                return
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "_heartbeat_loop: POST failed (%s); marking buffer stale", exc
                )
                async with self._lock:
                    self._buffer.stale = True
