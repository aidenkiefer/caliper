"""
Integration tests for SessionOrchestrator end-to-end flow.

All external dependencies are mocked (no live Polymarket connection or
database required). The tests exercise the full session lifecycle —
market discovery → quoting loop → wind-down → finalization.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from services.polymarket.session import SessionOrchestrator
from tests.integration.polymarket.fixtures import (
    make_config,
    make_data_feed_state,
    make_market_info,
    make_quote_decision,
)


# ---------------------------------------------------------------------------
# Helper: build a fully-mocked orchestrator
# ---------------------------------------------------------------------------


def _build_orchestrator(config=None):
    """Return (orchestrator, config, mocks_dict) with all seven components mocked."""
    cfg = config or make_config(requote_interval_seconds=1)

    session_id = uuid4()
    market = make_market_info(
        window_end=datetime.now(timezone.utc) + timedelta(seconds=10),
    )
    state = make_data_feed_state()
    quote = make_quote_decision(
        bid_price=Decimal("0.54"),
        ask_price=Decimal("0.56"),
        bid_size=Decimal("50"),
        ask_size=Decimal("50"),
    )

    market_discovery = MagicMock()
    market_discovery.discover_target_market = AsyncMock(return_value=market)

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
    executor.place_quotes = AsyncMock(
        return_value={"bid_order_id": "bid_123", "ask_order_id": "ask_456"}
    )
    executor.inventory_delta = Decimal("0")

    safety_layer = MagicMock()
    safety_layer.emergency_shutdown = MagicMock()

    recorder = MagicMock()
    recorder.create_session = AsyncMock(return_value=session_id)
    recorder.start = AsyncMock()
    recorder.stop = AsyncMock()
    recorder.record_snapshot = AsyncMock()
    recorder.finalize_session = AsyncMock()
    recorder.compute_toxic_flow_by_minute = AsyncMock()

    wallet_manager = MagicMock()
    wallet_manager.get_usdc_balance = AsyncMock(return_value=Decimal("500"))

    orchestrator = SessionOrchestrator(
        market_discovery=market_discovery,
        data_feed=data_feed,
        quoting_engine=quoting_engine,
        executor=executor,
        safety_layer=safety_layer,
        recorder=recorder,
        wallet_manager=wallet_manager,
    )

    mocks = {
        "session_id": session_id,
        "market": market,
        "market_discovery": market_discovery,
        "data_feed": data_feed,
        "quoting_engine": quoting_engine,
        "executor": executor,
        "safety_layer": safety_layer,
        "recorder": recorder,
        "wallet_manager": wallet_manager,
    }

    return orchestrator, cfg, mocks


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_session_flow():
    """Happy path: session runs, quotes are placed, cleanup happens correctly.

    The safety layer returns safe=True on the first call, then wind_down=True
    on the second call to trigger a clean exit without waiting for the clock.
    asyncio.sleep is patched to return immediately so the test is fast.
    """
    orchestrator, cfg, mocks = _build_orchestrator()

    # First safety check: proceed with quoting; second: trigger wind-down.
    safety_responses = [
        {"safe": True, "reason": None, "wind_down": False},
        {"safe": True, "reason": None, "wind_down": True},
    ]
    mocks["safety_layer"].check_quote_safety = MagicMock(
        side_effect=safety_responses
    )

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await orchestrator.run_session(cfg)

    # Session record created exactly once
    mocks["recorder"].create_session.assert_called_once()

    # At least one quote cycle executed
    mocks["executor"].place_quotes.assert_called()

    # Wind-down cleanup
    mocks["executor"].cancel_all_orders.assert_called_once()

    # Post-session finalization
    mocks["recorder"].finalize_session.assert_called_once()

    # asyncio.sleep was called (not waited on for real)
    mock_sleep.assert_called()


@pytest.mark.asyncio
async def test_wind_down_immediate():
    """Session ends immediately when the safety layer returns wind_down=True from the start.

    No quotes should be placed; cleanup must still run.
    """
    orchestrator, cfg, mocks = _build_orchestrator()

    mocks["safety_layer"].check_quote_safety = MagicMock(
        return_value={"safe": True, "reason": None, "wind_down": True}
    )

    with patch("asyncio.sleep", new_callable=AsyncMock):
        await orchestrator.run_session(cfg)

    # No quotes placed because wind-down triggered before the quote step
    mocks["executor"].place_quotes.assert_not_called()

    # Cleanup still ran
    mocks["executor"].cancel_all_orders.assert_called_once()
    mocks["recorder"].finalize_session.assert_called_once()

    # Snapshot is recorded before wind-down check fires
    mocks["recorder"].record_snapshot.assert_called()


@pytest.mark.asyncio
async def test_emergency_shutdown_scenario():
    """RuntimeError raised by data_feed triggers emergency_shutdown and re-raises."""
    orchestrator, cfg, mocks = _build_orchestrator()

    mocks["data_feed"].get_current_state = MagicMock(
        side_effect=RuntimeError("feed crashed")
    )

    with patch("asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(RuntimeError, match="feed crashed"):
            await orchestrator.run_session(cfg)

    # Emergency shutdown must have been called with the executor
    mocks["safety_layer"].emergency_shutdown.assert_called_once_with(mocks["executor"])

    # finalize_session still called in finally block since session_id was set
    mocks["recorder"].finalize_session.assert_called_once()
