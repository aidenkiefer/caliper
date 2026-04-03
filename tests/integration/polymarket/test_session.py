"""
Integration tests for SessionOrchestrator.

All external dependencies (data feed, executor, safety layer, recorder,
wallet, market discovery, quoting engine) are mocked so these tests run
without a live Polymarket connection or database.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from services.polymarket.session import SessionOrchestrator


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_config():
    """Return a minimal PolymarketConfig-like MagicMock."""
    config = MagicMock()
    config.quote_size = Decimal("50")
    config.requote_interval_seconds = 0  # run loop immediately without sleeping
    config.wind_down_minutes = 5
    config.binance_stale_seconds = 30
    config.max_session_loss_usdc = Decimal("20")
    config.inventory_cap = Decimal("200")
    return config


def _make_market(window_end: datetime | None = None):
    """Return a minimal MarketInfo-like MagicMock."""
    market = MagicMock()
    market.condition_id = "cond-001"
    market.token_id_yes = "token-yes-001"
    market.tick_size = Decimal("0.01")
    market.window_end = window_end or datetime.now(tz=timezone.utc) + timedelta(hours=1)
    return market


def _make_data_feed_state(binance_last_updated: datetime | None = None):
    """Return a minimal DataFeedState-like MagicMock."""
    state = MagicMock()
    state.best_bid = Decimal("0.50")
    state.best_ask = Decimal("0.52")
    state.midpoint = Decimal("0.51")
    state.spread = Decimal("0.02")
    state.binance_last_updated = binance_last_updated
    state.last_updated = datetime.now(tz=timezone.utc)
    state.bid_depth_1pct = Decimal("100")
    state.ask_depth_1pct = Decimal("100")
    state.imbalance = Decimal("0")
    return state


def _make_quote_decision():
    """Return a minimal QuoteDecision-like MagicMock."""
    quote = MagicMock()
    quote.should_quote_bid = True
    quote.should_quote_ask = True
    quote.bid_price = Decimal("0.49")
    quote.ask_price = Decimal("0.53")
    quote.bid_size = Decimal("50")
    quote.ask_size = Decimal("50")
    return quote


def _build_orchestrator(
    *,
    balance: Decimal = Decimal("200"),
    session_id: UUID | None = None,
    safety_safe: bool = True,
    safety_wind_down: bool = False,
    wind_down_after_n_calls: int | None = None,
    market_window_end: datetime | None = None,
):
    """Build a SessionOrchestrator with fully mocked components.

    Parameters
    ----------
    balance:
        USDC balance returned by the wallet manager.
    session_id:
        UUID returned by recorder.create_session.
    safety_safe:
        Whether safety checks return safe=True.
    safety_wind_down:
        Whether safety checks return wind_down=True (triggers loop exit).
    wind_down_after_n_calls:
        If set, safety returns wind_down=True after this many calls.
    market_window_end:
        Override for market.window_end.
    """
    sid = session_id or uuid4()
    config = _make_config()
    market = _make_market(window_end=market_window_end)
    state = _make_data_feed_state()
    quote = _make_quote_decision()

    market_discovery = MagicMock()
    market_discovery.discover_target_market = AsyncMock(return_value=market)

    wallet_manager = MagicMock()
    wallet_manager.get_usdc_balance = AsyncMock(return_value=balance)

    recorder = MagicMock()
    recorder.create_session = AsyncMock(return_value=sid)
    recorder.start = AsyncMock()
    recorder.stop = AsyncMock()
    recorder.record_snapshot = AsyncMock()
    recorder.record_order = AsyncMock()
    recorder.record_fill = AsyncMock()
    recorder.record_pnl_snapshot = AsyncMock()
    recorder.finalize_session = AsyncMock()
    recorder.compute_toxic_flow_by_minute = AsyncMock()

    data_feed = MagicMock()
    data_feed.start = AsyncMock()
    data_feed.stop = AsyncMock()
    data_feed.get_current_state = MagicMock(return_value=state)

    quoting_engine = MagicMock()
    quoting_engine.compute_quotes = MagicMock(return_value=quote)

    executor = MagicMock()
    executor.start_heartbeat = AsyncMock()
    executor.stop_heartbeat = AsyncMock()
    executor.cancel_all_orders = AsyncMock(return_value=0)
    executor.place_quotes = AsyncMock(return_value=("bid-001", "ask-001"))
    executor.inventory_delta = Decimal("0")

    # Build safety result factory
    call_count = 0

    def _safety_check(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if wind_down_after_n_calls is not None and call_count >= wind_down_after_n_calls:
            return {"safe": True, "reason": None, "wind_down": True}
        return {
            "safe": safety_safe,
            "reason": None if safety_safe else "test-unsafe-reason",
            "wind_down": safety_wind_down,
        }

    safety_layer = MagicMock()
    safety_layer.check_quote_safety = MagicMock(side_effect=_safety_check)
    safety_layer.emergency_shutdown = MagicMock()

    orchestrator = SessionOrchestrator(
        market_discovery=market_discovery,
        data_feed=data_feed,
        quoting_engine=quoting_engine,
        executor=executor,
        safety_layer=safety_layer,
        recorder=recorder,
        wallet_manager=wallet_manager,
    )

    return orchestrator, config, {
        "session_id": sid,
        "market": market,
        "market_discovery": market_discovery,
        "wallet_manager": wallet_manager,
        "recorder": recorder,
        "data_feed": data_feed,
        "quoting_engine": quoting_engine,
        "executor": executor,
        "safety_layer": safety_layer,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_session_flow():
    """Complete session runs without error; all major methods are called."""
    orchestrator, config, mocks = _build_orchestrator(wind_down_after_n_calls=2)

    await orchestrator.run_session(config)

    # Market discovery
    mocks["market_discovery"].discover_target_market.assert_called_once_with(config)

    # Wallet check
    mocks["wallet_manager"].get_usdc_balance.assert_called_once()

    # Session created
    mocks["recorder"].create_session.assert_called_once()

    # Data feed started with correct token id
    mocks["data_feed"].start.assert_called_once_with(mocks["market"].token_id_yes)

    # Recorder started
    mocks["recorder"].start.assert_called_once()

    # Heartbeat started
    mocks["executor"].start_heartbeat.assert_called_once()

    # At least one quote was placed
    mocks["executor"].place_quotes.assert_called()

    # Wind-down: cancel orders and stop heartbeat
    mocks["executor"].cancel_all_orders.assert_called_once()
    mocks["executor"].stop_heartbeat.assert_called_once()

    # Data feed and recorder stopped
    mocks["data_feed"].stop.assert_called_once()
    mocks["recorder"].stop.assert_called_once()

    # Post-session finalization
    mocks["recorder"].compute_toxic_flow_by_minute.assert_called_once_with(
        mocks["session_id"]
    )
    mocks["recorder"].finalize_session.assert_called_once()

    # on_fill_callback wired to orchestrator's _on_fill method
    assert mocks["executor"]._on_fill == orchestrator._on_fill

    # No emergency shutdown was triggered
    mocks["safety_layer"].emergency_shutdown.assert_not_called()


@pytest.mark.asyncio
async def test_wind_down_exits_loop():
    """When safety returns wind_down=True, the session ends cleanly."""
    # Wind down immediately on the first safety check
    orchestrator, config, mocks = _build_orchestrator(
        safety_safe=True,
        safety_wind_down=True,
    )

    await orchestrator.run_session(config)

    # Loop should have exited without placing any quotes
    mocks["executor"].place_quotes.assert_not_called()

    # Wind-down cleanup should still happen
    mocks["executor"].cancel_all_orders.assert_called_once()
    mocks["executor"].stop_heartbeat.assert_called_once()
    mocks["data_feed"].stop.assert_called_once()
    mocks["recorder"].stop.assert_called_once()
    mocks["recorder"].finalize_session.assert_called_once()

    # No emergency shutdown
    mocks["safety_layer"].emergency_shutdown.assert_not_called()


@pytest.mark.asyncio
async def test_emergency_shutdown_on_error():
    """An unhandled exception triggers safety_layer.emergency_shutdown and re-raises."""
    orchestrator, config, mocks = _build_orchestrator()

    # Make the data feed raise an error on the first get_current_state call
    mocks["data_feed"].get_current_state = MagicMock(
        side_effect=RuntimeError("WebSocket connection lost")
    )

    with pytest.raises(RuntimeError, match="WebSocket connection lost"):
        await orchestrator.run_session(config)

    # Emergency shutdown must have been called
    mocks["safety_layer"].emergency_shutdown.assert_called_once_with(mocks["executor"])

    # Wind-down cleanup still runs (in finally block)
    mocks["executor"].cancel_all_orders.assert_called_once()
    mocks["recorder"].stop.assert_called_once()


@pytest.mark.asyncio
async def test_insufficient_balance_raises():
    """Wallet balance below quote_size * 2 raises ValueError before the session starts."""
    # config.quote_size = 50, so required = 100; set balance to 50 (insufficient)
    orchestrator, config, mocks = _build_orchestrator(balance=Decimal("50"))
    config.quote_size = Decimal("50")  # required = 100

    with pytest.raises(ValueError, match="Insufficient USDC balance"):
        await orchestrator.run_session(config)

    # No session should have been created
    mocks["recorder"].create_session.assert_not_called()

    # Data feed should not have been started
    mocks["data_feed"].start.assert_not_called()

    # Emergency shutdown must NOT be called — insufficient balance is a pre-flight
    # validation failure, not a runtime emergency
    mocks["safety_layer"].emergency_shutdown.assert_not_called()


@pytest.mark.asyncio
async def test_cleanup_continues_if_cancel_raises():
    """cancel_all_orders raising during wind-down does not prevent further cleanup."""
    orchestrator, config, mocks = _build_orchestrator(safety_wind_down=True)

    # Make cancel_all_orders raise
    mocks["executor"].cancel_all_orders.side_effect = RuntimeError("cancel failed")

    # Should complete without re-raising the cancel error
    await orchestrator.run_session(config)

    # Cleanup must have continued past the failure
    mocks["data_feed"].stop.assert_called_once()
    mocks["recorder"].stop.assert_called_once()
