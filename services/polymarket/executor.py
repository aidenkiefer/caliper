"""
Executor for the Polymarket BTC hourly market-making service.

The Executor is responsible for:
- Placing bid/ask quotes on the Polymarket CLOB (always post-only)
- Cancelling existing orders before re-quoting
- Running a background heartbeat task to prevent platform auto-cancellation
- Handling fill notifications and updating inventory tracking

The Executor does NOT own its own quoting event loop. It is called by the
session orchestrator every ``requote_interval_seconds``. The heartbeat is
the only background asyncio task managed internally.

Usage::

    executor = Executor(clob_client=clob, config=config)
    await executor.start_heartbeat()

    bid_id, ask_id = await executor.place_quotes(quote, token_id="12345", quote_version=1)

    await executor.handle_fill(fill_data)
    await executor.stop_heartbeat()
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Callable, Optional, Tuple

from services.polymarket.adapters.clob_client import CLOBClient
from services.polymarket.config import PolymarketConfig
from services.polymarket.schemas import QuoteDecision

logger = logging.getLogger(__name__)


class Executor:
    """Bridge between the quoting engine's decisions and the Polymarket CLOB API.

    Parameters
    ----------
    clob_client:
        Pre-configured ``CLOBClient`` instance used for order placement,
        cancellation, and heartbeat requests.
    config:
        ``PolymarketConfig`` driving heartbeat interval and related settings.
    on_fill_callback:
        Optional async or sync callable invoked whenever a fill is processed.
        Signature: ``callback(fill_data: dict) -> None``.  Used by the recorder
        to persist fill events without tight coupling.
    """

    def __init__(
        self,
        clob_client: CLOBClient,
        config: PolymarketConfig,
        on_fill_callback: Optional[Callable] = None,
    ) -> None:
        self._clob = clob_client
        self._config = config
        self._on_fill = on_fill_callback

        # order_id -> {"placed_at": datetime, "quote_version": int, "side": str,
        #               "price": Decimal, "size": Decimal, "token_id": str}
        self._live_orders: dict = {}

        # Net YES token inventory change from fills in this session.
        # BUY fills add to this; SELL fills subtract.
        self._inventory_delta: Decimal = Decimal("0")

        self._heartbeat_task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def place_quotes(
        self,
        quote: QuoteDecision,
        token_id: str,
        quote_version: int,
    ) -> Tuple[Optional[str], Optional[str]]:
        """Place bid and ask quotes for the given token.

        Cancels any existing tracked orders for this token before placing new
        ones. Post-only is always enforced.

        Parameters
        ----------
        quote:
            ``QuoteDecision`` from the quoting engine.
        token_id:
            The CLOB token ID (YES outcome token).
        quote_version:
            Monotonically increasing version counter supplied by the session
            orchestrator, used to attribute fills to a specific quote cycle.

        Returns
        -------
        Tuple[Optional[str], Optional[str]]
            ``(bid_order_id, ask_order_id)``.  Either element may be ``None``
            when that side is not quoted (``should_quote_*=False``).
        """
        # Cancel any live orders for this token first.
        token_order_ids = [
            oid
            for oid, meta in self._live_orders.items()
            if meta.get("token_id") == token_id
        ]
        for order_id in token_order_ids:
            try:
                await self._clob.cancel_order(order_id)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Failed to cancel existing order %s before re-quote: %s",
                    order_id, exc,
                )
            # Always remove from tracking regardless of cancellation success
            # to avoid stale references blocking the next quote cycle.
            self._live_orders.pop(order_id, None)

        bid_order_id: Optional[str] = None
        ask_order_id: Optional[str] = None
        now = datetime.now(tz=timezone.utc)

        # Place bid
        if quote.should_quote_bid and quote.bid_price is not None:
            try:
                bid_order_id = await self._clob.place_order(
                    token_id=token_id,
                    side="BUY",
                    price=quote.bid_price,
                    size=quote.bid_size,
                    post_only=True,  # Always enforced — never set to False
                )
                self._live_orders[bid_order_id] = {
                    "placed_at": now,
                    "quote_version": quote_version,
                    "side": "BUY",
                    "price": quote.bid_price,
                    "size": quote.bid_size,
                    "token_id": token_id,
                }
                logger.info(
                    "Bid placed: id=%s token=%s price=%s size=%s version=%d",
                    bid_order_id, token_id, quote.bid_price, quote.bid_size, quote_version,
                )
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "Failed to place bid for token %s (version=%d): %s",
                    token_id, quote_version, exc,
                )

        # Place ask
        if quote.should_quote_ask and quote.ask_price is not None:
            try:
                ask_order_id = await self._clob.place_order(
                    token_id=token_id,
                    side="SELL",
                    price=quote.ask_price,
                    size=quote.ask_size,
                    post_only=True,  # Always enforced — never set to False
                )
                self._live_orders[ask_order_id] = {
                    "placed_at": now,
                    "quote_version": quote_version,
                    "side": "SELL",
                    "price": quote.ask_price,
                    "size": quote.ask_size,
                    "token_id": token_id,
                }
                logger.info(
                    "Ask placed: id=%s token=%s price=%s size=%s version=%d",
                    ask_order_id, token_id, quote.ask_price, quote.ask_size, quote_version,
                )
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "Failed to place ask for token %s (version=%d): %s",
                    token_id, quote_version, exc,
                )

        return bid_order_id, ask_order_id

    async def cancel_all_orders(self) -> int:
        """Cancel all open orders via the CLOB and clear internal tracking.

        Returns
        -------
        int
            The number of orders cancelled as reported by the CLOB.
        """
        count = await self._clob.cancel_all()
        self._live_orders.clear()
        logger.info("cancel_all_orders: cleared tracking, CLOB reported %d cancelled", count)
        return count

    async def start_heartbeat(self) -> None:
        """Start the background heartbeat task.

        The task calls ``clob_client.send_heartbeat()`` every
        ``config.heartbeat_interval_seconds`` seconds.  Heartbeat failures are
        logged as errors but do NOT stop the task — Polymarket's platform will
        auto-cancel resting orders if heartbeats are missed for a sustained
        period, so silent failure is intentional.

        Calling ``start_heartbeat()`` when a heartbeat is already running is a
        no-op.
        """
        if self._heartbeat_task is not None and not self._heartbeat_task.done():
            logger.debug("Heartbeat task already running; ignoring start_heartbeat() call.")
            return

        self._heartbeat_task = asyncio.create_task(
            self._heartbeat_loop(), name="executor-heartbeat"
        )
        logger.info(
            "Heartbeat started (interval=%ds)",
            self._config.heartbeat_interval_seconds,
        )

    async def stop_heartbeat(self) -> None:
        """Cancel the background heartbeat task and wait for it to finish."""
        if self._heartbeat_task is None or self._heartbeat_task.done():
            return

        self._heartbeat_task.cancel()
        try:
            await self._heartbeat_task
        except asyncio.CancelledError:
            pass
        finally:
            self._heartbeat_task = None
        logger.info("Heartbeat stopped.")

    async def handle_fill(self, fill_data: dict) -> None:
        """Process a fill notification received from the CLOB WebSocket.

        Parameters
        ----------
        fill_data:
            Dict with keys: ``order_id``, ``price``, ``size``, ``side``,
            ``timestamp``.

        Side effects:
        - Computes ``time_on_book_seconds`` (logged for analytics).
        - Updates ``_inventory_delta`` (BUY fills add, SELL fills subtract).
        - Invokes ``on_fill_callback`` if set.
        - Removes the order from ``_live_orders`` (V1 treats every fill as
          a full fill; partial-fill tracking is a future enhancement).
        """
        order_id = fill_data.get("order_id", "")
        fill_size = Decimal(str(fill_data.get("size", "0")))
        fill_side = str(fill_data.get("side", "")).upper()

        # Compute time on book if we have tracking data.
        order_meta = self._live_orders.get(order_id)
        time_on_book_seconds: Optional[float] = None
        if order_meta is not None:
            placed_at: datetime = order_meta["placed_at"]
            now = datetime.now(tz=timezone.utc)
            time_on_book_seconds = (now - placed_at).total_seconds()
            logger.info(
                "Fill received: order_id=%s side=%s size=%s price=%s time_on_book=%.2fs",
                order_id,
                fill_side,
                fill_size,
                fill_data.get("price"),
                time_on_book_seconds,
            )
        else:
            logger.warning(
                "Fill received for untracked order %s (may have been placed in a prior session)",
                order_id,
            )

        # Update inventory delta.
        if fill_side == "BUY":
            self._inventory_delta += fill_size
        elif fill_side == "SELL":
            self._inventory_delta -= fill_size
        else:
            logger.warning("Fill has unrecognised side %r for order %s", fill_side, order_id)

        # Notify the recorder callback (if any).
        if self._on_fill is not None:
            try:
                result = self._on_fill(fill_data)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as exc:  # noqa: BLE001
                logger.error("on_fill_callback raised an exception: %s", exc)

        # Remove from live-order tracking (V1: treat every fill as full).
        if order_id in self._live_orders:
            self._live_orders.pop(order_id)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def inventory_delta(self) -> Decimal:
        """Net YES token inventory change from fills in this session.

        Positive → net bought (long YES); negative → net sold.
        """
        return self._inventory_delta

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _heartbeat_loop(self) -> None:
        """Background coroutine that sends heartbeats at a fixed interval.

        Heartbeat failures are caught and logged; the loop continues
        unconditionally to avoid crashing the main trading session.
        """
        while True:
            await asyncio.sleep(self._config.heartbeat_interval_seconds)
            try:
                await self._clob.send_heartbeat()
                logger.debug("Heartbeat sent successfully.")
            except Exception as exc:  # noqa: BLE001
                # Log the failure but do NOT re-raise.  The platform will
                # auto-cancel our orders if we miss too many heartbeats, which
                # is the intended safety mechanism.
                logger.error("Heartbeat failed (platform will auto-cancel if persistent): %s", exc)
