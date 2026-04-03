"""
Safety layer for the Polymarket BTC hourly market-making service.

The SafetyLayer is a stateless (mostly) guard invoked by the session orchestrator
before placing quotes each cycle. It consolidates all pre-trade safety checks into
a single class so the orchestrator never needs to inline guard logic.

Usage::

    safety = SafetyLayer(config=config)

    # Per-cycle session-level check
    result = safety.check_quote_safety(
        inventory_yes, inventory_no, realized_pnl,
        last_binance_update, session_end_time, config,
    )
    if not result["safe"]:
        logger.warning("Skipping quote: %s", result["reason"])
        continue

    # Emergency shutdown on critical failure
    safety.emergency_shutdown(executor)
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, TypedDict

from services.polymarket.config import PolymarketConfig

logger = logging.getLogger(__name__)


class QuoteSafetyResult(TypedDict):
    safe: bool
    reason: Optional[str]
    wind_down: bool


class SafetyLayer:
    """Pre-trade safety checks and emergency shutdown for one market-making session.

    Parameters
    ----------
    config:
        ``PolymarketConfig`` supplying all threshold values (inventory_cap,
        max_session_loss_usdc, wind_down_minutes, binance_stale_seconds).
    """

    def __init__(self, config: PolymarketConfig) -> None:
        self._config = config
        self._killed = False

    # ------------------------------------------------------------------
    # Public properties
    # ------------------------------------------------------------------

    @property
    def is_killed(self) -> bool:
        """True after emergency_shutdown has been called at least once."""
        return self._killed

    # ------------------------------------------------------------------
    # Individual safety checks
    # ------------------------------------------------------------------

    def check_inventory_cap(
        self,
        inventory_yes: Decimal,
        inventory_no: Decimal,
        config: PolymarketConfig,
    ) -> bool:
        """Return True if EITHER side's inventory has hit or exceeded the cap.

        Parameters
        ----------
        inventory_yes:
            Current YES share inventory for the session.
        inventory_no:
            Current NO share inventory for the session.
        config:
            Config supplying the inventory_cap threshold.

        Returns
        -------
        bool
            ``True`` if the cap is breached (stop quoting),
            ``False`` if both sides are below the cap (safe to quote).
        """
        return inventory_yes >= config.inventory_cap or inventory_no >= config.inventory_cap

    def check_session_loss_limit(
        self,
        realized_pnl: Decimal,
        config: PolymarketConfig,
    ) -> bool:
        """Return True if the session P&L has breached the maximum loss limit.

        Parameters
        ----------
        realized_pnl:
            Realised session P&L in USDC (negative = loss).
        config:
            Config supplying the max_session_loss_usdc threshold.

        Returns
        -------
        bool
            ``True`` if the loss limit is breached (should trigger shutdown),
            ``False`` if within limits (safe to continue).
        """
        return realized_pnl < -config.max_session_loss_usdc

    def check_binance_staleness(
        self,
        last_binance_update: Optional[datetime],
        config: Optional[PolymarketConfig] = None,
    ) -> bool:
        """Return True if the Binance feed is stale (data is too old).

        A ``None`` last_update indicates the feed has never polled successfully
        (cold start). This is treated as NOT stale to allow the quoting loop to
        start up gracefully before the first Binance response arrives.

        Parameters
        ----------
        last_update:
            UTC datetime of the most recent successful Binance price poll, or
            ``None`` if no poll has completed yet.
        config:
            Optional config override; defaults to the instance config.

        Returns
        -------
        bool
            ``True`` if the data is stale and quoting should be suppressed,
            ``False`` if the data is fresh or no poll has occurred yet.
        """
        if last_binance_update is None:
            return False  # cold-start grace period

        cfg = config if config is not None else self._config
        now = datetime.now(tz=timezone.utc)
        # Ensure last_binance_update is timezone-aware for comparison
        if last_binance_update.tzinfo is None:
            last_binance_update = last_binance_update.replace(tzinfo=timezone.utc)

        age_seconds = (now - last_binance_update).total_seconds()
        return age_seconds > cfg.binance_stale_seconds

    def should_wind_down(
        self,
        session_end_time: datetime,
        config: PolymarketConfig,
    ) -> bool:
        """Return True when the market is close enough to closing that we should
        stop posting new quotes (wind-down period).

        Parameters
        ----------
        session_end_time:
            Absolute UTC datetime when the session/market window closes.
        config:
            Config supplying the wind_down_minutes threshold.

        Returns
        -------
        bool
            ``True`` if we are within the wind-down window (stop quoting),
            ``False`` otherwise (continue quoting).
        """
        now = datetime.now(tz=timezone.utc)
        # Ensure session_end_time is timezone-aware for comparison
        if session_end_time.tzinfo is None:
            session_end_time = session_end_time.replace(tzinfo=timezone.utc)
        remaining = (session_end_time - now).total_seconds() / 60
        return remaining <= config.wind_down_minutes

    # ------------------------------------------------------------------
    # Composite session-level check
    # ------------------------------------------------------------------

    def check_quote_safety(
        self,
        inventory_yes: Decimal,
        inventory_no: Decimal,
        realized_pnl: Decimal,
        last_binance_update: Optional[datetime],
        session_end_time: datetime,
        config: PolymarketConfig,
    ) -> QuoteSafetyResult:
        """Run all session-level safety checks before placing a quote cycle.

        Checks are evaluated in this order:
        1. Emergency shutdown / killed flag
        2. Inventory cap (either side)
        3. Session loss limit
        4. Binance feed staleness
        5. Wind-down period

        Parameters
        ----------
        inventory_yes:
            Current YES share inventory.
        inventory_no:
            Current NO share inventory.
        realized_pnl:
            Realised session P&L in USDC.
        last_binance_update:
            UTC datetime of the most recent successful Binance price poll, or None.
        session_end_time:
            Absolute UTC datetime when the session/market window closes.
        config:
            Config supplying all thresholds.

        Returns
        -------
        dict
            Keys: ``safe`` (bool), ``reason`` (Optional[str]), ``wind_down`` (bool).
            ``safe=True, reason=None`` when all checks pass (wind_down may still be True).
            ``safe=False, reason=<str>`` at the first failing check.
        """
        if self._killed:
            return {"safe": False, "reason": "Emergency shutdown active", "wind_down": False}

        if self.check_inventory_cap(inventory_yes, inventory_no, config):
            return {"safe": False, "reason": "Inventory cap breached", "wind_down": False}

        if self.check_session_loss_limit(realized_pnl, config):
            return {"safe": False, "reason": "Session loss limit exceeded", "wind_down": False}

        if self.check_binance_staleness(last_binance_update, config):
            return {"safe": False, "reason": "Binance price data stale", "wind_down": False}

        wind_down = self.should_wind_down(session_end_time, config)
        return {"safe": True, "reason": None, "wind_down": wind_down}

    # ------------------------------------------------------------------
    # Emergency shutdown
    # ------------------------------------------------------------------

    def emergency_shutdown(self, executor, reason: Optional[str] = None) -> None:
        """Cancel all open orders and set the killed flag.

        This method is idempotent: subsequent calls after the first are no-ops.
        The ``_killed`` flag is set synchronously. Cancellation of open orders is
        fire-and-forget via ``asyncio.ensure_future``; errors from
        ``executor.cancel_all_orders()`` are caught and logged rather than
        re-raised.

        Parameters
        ----------
        executor:
            ``Executor`` instance whose ``cancel_all_orders()`` will be called.
        reason:
            Optional human-readable description of the failure that triggered
            shutdown. Logged at CRITICAL level if provided.
        """
        if self._killed:
            return  # already shut down — idempotent

        self._killed = True
        if reason:
            logger.critical("EMERGENCY SHUTDOWN: %s", reason)
        else:
            logger.critical("EMERGENCY SHUTDOWN triggered")

        async def _cancel() -> None:
            try:
                count = await executor.cancel_all_orders()
                logger.info("Cancelled %d orders", count)
            except Exception as e:  # noqa: BLE001
                logger.error("cancel_all failed during shutdown: %s", e)

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_cancel())
        except RuntimeError:
            pass  # No running event loop; cancel is best-effort
