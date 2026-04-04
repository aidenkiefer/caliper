"""
Session orchestrator for the Polymarket BTC hourly market-making service.

The SessionOrchestrator ties together every component — market discovery,
data feed, quoting engine, executor, safety layer, recorder, and wallet —
into a single end-to-end trading session.

Typical usage::

    orchestrator = SessionOrchestrator(
        market_discovery=discovery,
        data_feed=feed,
        quoting_engine=engine,
        executor=executor,
        safety_layer=safety,
        recorder=recorder,
        wallet_manager=wallet,
    )
    await orchestrator.run_session(config)
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from packages.strategies.polymarket_mm_strategy import PolymarketMMStrategy
from uuid import UUID

from packages.strategies.base import PortfolioState
from services.polymarket.config import PolymarketConfig
from services.polymarket.data_feed import DataFeed
from services.polymarket.executor import Executor
from services.polymarket.market_discovery import MarketDiscovery
from services.polymarket.quoting_engine import QuotingEngine
from services.polymarket.recorder import Recorder
from services.polymarket.safety import SafetyLayer
from services.polymarket.schemas import QuoteDecision
from services.polymarket.wallet import WalletManager

logger = logging.getLogger(__name__)


class SessionOrchestrator:
    """Orchestrates a single hourly market-making session on Polymarket.

    Parameters
    ----------
    market_discovery:
        Used to locate the target hourly BTC market.
    data_feed:
        Real-time orderbook and Binance price feed.
    quoting_engine:
        Produces ``QuoteDecision`` objects each cycle.
    executor:
        Places and cancels orders on the CLOB.
    safety_layer:
        Pre-trade safety checks and emergency shutdown.
    recorder:
        Persists session data (orders, fills, snapshots, PnL).
    wallet_manager:
        Provides USDC balance queries.
    """

    def __init__(
        self,
        market_discovery: MarketDiscovery,
        data_feed: DataFeed,
        quoting_engine: QuotingEngine,
        executor: Executor,
        safety_layer: SafetyLayer,
        recorder: Recorder,
        wallet_manager: WalletManager,
        strategy: Optional[PolymarketMMStrategy] = None,
    ) -> None:
        self._market_discovery = market_discovery
        self._data_feed = data_feed
        self._quoting_engine = quoting_engine
        self._executor = executor
        self._safety_layer = safety_layer
        self._recorder = recorder
        self._wallet_manager = wallet_manager
        self._strategy = strategy

        # Running sum of realised P&L in USDC for the current session.
        # Updated via the fill callback registered on the executor.
        self._realized_pnl: Decimal = Decimal("0")

        # Tracks fire-and-forget snapshot tasks so they can be awaited on exit.
        self._pending_tasks: list[asyncio.Task] = []

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def run_session(self, config: PolymarketConfig) -> None:
        """Run one complete market-making session.

        Steps:
        1. Discover the target hourly market.
        2. Validate the USDC wallet balance.
        3. Create the session record in the database.
        4. Start the data feed and recorder.
        5. Start the executor heartbeat.
        6. Enter the main quoting loop until wind-down or session end.
        7. Cancel all open orders and stop background tasks.
        8. Finalize the session record.

        Parameters
        ----------
        config:
            Service configuration for this session.

        Raises
        ------
        ValueError
            If the wallet balance is insufficient to quote both sides.
        Exception
            Any unhandled exception triggers an emergency shutdown before
            being re-raised.
        """
        session_id: Optional[UUID] = None
        market = None
        quote_version: int = 0

        try:
            # ----------------------------------------------------------
            # Step 1: Market discovery
            # ----------------------------------------------------------
            logger.info("Discovering target market...")
            market = await self._market_discovery.discover_target_market(config)
            logger.info(
                "Target market: condition_id=%s token_id_yes=%s window_end=%s",
                market.condition_id,
                market.token_id_yes,
                market.window_end,
            )

            # ----------------------------------------------------------
            # Step 2: Wallet balance check
            # ----------------------------------------------------------
            balance = await self._wallet_manager.get_usdc_balance()
            required = config.quote_size * 2
            if balance < required:
                raise ValueError(
                    f"Insufficient USDC balance: have {balance}, need {required}"
                )
            logger.info("Wallet balance OK: %s USDC (required %s)", balance, required)

            # ----------------------------------------------------------
            # Step 3: Session creation
            # ----------------------------------------------------------
            session_id = await self._recorder.create_session(market, config)
            logger.info("Session created: session_id=%s", session_id)

            # Reset per-session state
            self._realized_pnl = Decimal("0")
            quote_version = 0

            # Register fill callback so realized_pnl is updated on fills.
            # Assigns directly to the executor's internal attribute since
            # the callback may not be known at executor construction time.
            self._executor._on_fill = self._on_fill

            # ----------------------------------------------------------
            # Step 4: Start data feed and recorder
            # ----------------------------------------------------------
            await self._data_feed.start(market.token_id_yes)
            await self._recorder.start()
            logger.info("Data feed and recorder started.")

            # ----------------------------------------------------------
            # Step 5: Start executor heartbeat
            # ----------------------------------------------------------
            await self._executor.start_heartbeat()
            logger.info("Executor heartbeat started.")

            # ----------------------------------------------------------
            # Step 6: Compute session end time
            # ----------------------------------------------------------
            session_end: datetime = market.window_end
            # Ensure it is timezone-aware (UTC)
            if session_end.tzinfo is None:
                session_end = session_end.replace(tzinfo=timezone.utc)

            # ----------------------------------------------------------
            # Step 7: Main quoting loop
            # ----------------------------------------------------------
            logger.info("Entering main quoting loop. session_end=%s", session_end)

            while True:
                # 7a. Get current market state
                state = self._data_feed.get_current_state()

                # 7b. Record snapshot (fire-and-forget task)
                _snapshot_task = asyncio.create_task(
                    self._recorder.record_snapshot(state, session_id),
                    name=f"record-snapshot-{quote_version}",
                )
                self._pending_tasks.append(_snapshot_task)

                # 7c. Safety check
                safety_result = self._safety_layer.check_quote_safety(
                    inventory_yes=self._executor.inventory_delta,
                    inventory_no=Decimal("0"),
                    realized_pnl=self._realized_pnl,
                    last_binance_update=state.binance_last_updated,
                    session_end_time=session_end,
                    config=config,
                )

                # 7d. Wind-down or past session end
                now_utc = datetime.now(tz=timezone.utc)
                if safety_result["wind_down"] or now_utc >= session_end:
                    logger.info(
                        "Exiting quoting loop: wind_down=%s, now=%s, session_end=%s",
                        safety_result["wind_down"],
                        now_utc,
                        session_end,
                    )
                    break

                # 7e. Unsafe but not wind-down — skip this cycle
                if not safety_result["safe"]:
                    logger.warning(
                        "Skipping quote cycle (version=%d): %s",
                        quote_version,
                        safety_result["reason"],
                    )
                    await asyncio.sleep(config.requote_interval_seconds)
                    continue

                # 7f. Compute quotes via strategy (if provided) or fall back to quoting engine
                if self._strategy is not None:
                    self._strategy.update_inventory(self._executor.inventory_delta)
                    self._strategy.on_market_data(state)
                    _portfolio = PortfolioState(
                        equity=Decimal(str(balance)),
                        cash=Decimal(str(balance)),
                        positions=[],
                    )
                    _signals = self._strategy.generate_signals(_portfolio)
                    if not _signals:
                        logger.debug("Strategy suppressed quotes this cycle.")
                        await asyncio.sleep(config.requote_interval_seconds)
                        continue
                    _sig = _signals[0]
                    _bid_size = Decimal(_sig.metadata["bid_size"])
                    _ask_size = Decimal(_sig.metadata["ask_size"])
                    quote = QuoteDecision(
                        bid_price=Decimal(_sig.metadata["bid_price"]) if _bid_size > Decimal("0") else None,
                        bid_size=_bid_size,
                        ask_price=Decimal(_sig.metadata["ask_price"]) if _ask_size > Decimal("0") else None,
                        ask_size=_ask_size,
                        should_quote_bid=_bid_size > Decimal("0"),
                        should_quote_ask=_ask_size > Decimal("0"),
                    )
                else:
                    quote = self._quoting_engine.compute_quotes(
                        orderbook_state=state,
                        inventory_yes=self._executor.inventory_delta,
                        config=config,
                        tick_size=market.tick_size,
                    )

                # 7g. Place quotes
                quote_version += 1
                await self._executor.place_quotes(quote, market.token_id_yes, quote_version)

                await asyncio.sleep(config.requote_interval_seconds)

        except ValueError:
            # Pre-flight validation failure (e.g. insufficient balance) — not a runtime emergency
            raise
        except Exception:
            logger.exception("Unhandled exception in session orchestrator — initiating emergency shutdown")
            self._safety_layer.emergency_shutdown(self._executor)
            raise

        finally:
            # ----------------------------------------------------------
            # Step 8: Wind-down
            # ----------------------------------------------------------
            if self._pending_tasks:
                await asyncio.gather(*self._pending_tasks, return_exceptions=True)
                self._pending_tasks.clear()

            logger.info("Wind-down: cancelling all open orders...")
            try:
                await self._executor.cancel_all_orders()
            except Exception:
                logger.exception("Error cancelling orders during wind-down")

            try:
                await self._executor.stop_heartbeat()
            except Exception:
                logger.exception("Error stopping heartbeat during wind-down")

            # ----------------------------------------------------------
            # Step 9: Stop data feed and recorder
            # ----------------------------------------------------------
            try:
                await self._data_feed.stop()
            except Exception:
                logger.exception("Error stopping data feed")

            try:
                await self._recorder.stop()
            except Exception:
                logger.exception("Error stopping recorder")

            # ----------------------------------------------------------
            # Step 10: Post-session finalization
            # ----------------------------------------------------------
            if session_id is not None:
                try:
                    await self._recorder.compute_toxic_flow_by_minute(session_id)
                except Exception:
                    logger.exception("Error computing toxic flow metrics")

                final_state: dict = {
                    "realized_pnl": str(self._realized_pnl),
                    "inventory_delta": str(self._executor.inventory_delta),
                    "quote_version": quote_version,
                }
                try:
                    await self._recorder.finalize_session(session_id, final_state)
                    logger.info("Session finalized: session_id=%s", session_id)
                except Exception:
                    logger.exception("Error finalizing session record")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _on_fill(self, fill_data: dict) -> None:
        """Update realized P&L from a fill notification.

        Called by the executor's fill callback. BUY fills reduce USDC
        (negative P&L impact on cost basis); SELL fills increase USDC
        (positive P&L impact).  This is a simplified V1 model that tracks
        cash flow rather than mark-to-market P&L.

        Parameters
        ----------
        fill_data:
            Dict with keys: ``price``, ``size``, ``side``.
        """
        try:
            price = Decimal(str(fill_data.get("price", "0")))
            size = Decimal(str(fill_data.get("size", "0")))
            side = str(fill_data.get("side", "")).upper()
            cash_flow = price * size
            if side == "BUY":
                self._realized_pnl -= cash_flow
            elif side == "SELL":
                self._realized_pnl += cash_flow
        except Exception:
            logger.exception("Error updating realized P&L from fill: %s", fill_data)
