"""
Unit tests for services/polymarket/safety.py — SafetyLayer.

Tests cover:
- check_inventory_cap (at limit, below limit, both sides)
- check_session_loss_limit (exceeded, within limit)
- check_binance_staleness (stale, fresh, never updated)
- should_wind_down (within window, outside window)
- check_quote_safety composite (all pass, killed, inventory cap, loss limit, stale Binance, wind-down)
- emergency_shutdown (cancels orders and sets killed flag, idempotent second call)
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.polymarket.safety import SafetyLayer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_config(
    inventory_cap: Decimal = Decimal("200"),
    max_session_loss_usdc: Decimal = Decimal("20"),
    wind_down_minutes: int = 5,
    binance_stale_seconds: int = 30,
):
    """Build a minimal PolymarketConfig-like object without requiring env vars."""
    cfg = MagicMock()
    cfg.inventory_cap = inventory_cap
    cfg.max_session_loss_usdc = max_session_loss_usdc
    cfg.wind_down_minutes = wind_down_minutes
    cfg.binance_stale_seconds = binance_stale_seconds
    return cfg


def make_safety(**config_kwargs) -> SafetyLayer:
    cfg = make_config(**config_kwargs)
    safety = SafetyLayer.__new__(SafetyLayer)
    safety._config = cfg
    safety._killed = False
    return safety


@pytest.fixture
def config():
    return make_config()


@pytest.fixture
def safety(config):
    instance = SafetyLayer.__new__(SafetyLayer)
    instance._config = config
    instance._killed = False
    return instance


# ---------------------------------------------------------------------------
# check_inventory_cap
# ---------------------------------------------------------------------------

def test_inventory_cap_yes_at_limit():
    """inventory_yes=200 with cap=200 → returns True (cap breached)."""
    safety = make_safety(inventory_cap=Decimal("200"))
    cfg = make_config(inventory_cap=Decimal("200"))
    assert safety.check_inventory_cap(Decimal("200"), Decimal("0"), cfg) is True


def test_inventory_cap_no_at_limit():
    """inventory_no=200 with cap=200 → returns True (cap breached)."""
    safety = make_safety(inventory_cap=Decimal("200"))
    cfg = make_config(inventory_cap=Decimal("200"))
    assert safety.check_inventory_cap(Decimal("0"), Decimal("200"), cfg) is True


def test_inventory_cap_both_below_limit():
    """inventory_yes=199, inventory_no=199 with cap=200 → returns False (safe)."""
    safety = make_safety(inventory_cap=Decimal("200"))
    cfg = make_config(inventory_cap=Decimal("200"))
    assert safety.check_inventory_cap(Decimal("199"), Decimal("199"), cfg) is False


def test_inventory_cap_yes_exceeds():
    """inventory_yes=250 (>200 cap) → returns True (cap breached)."""
    safety = make_safety(inventory_cap=Decimal("200"))
    cfg = make_config(inventory_cap=Decimal("200"))
    assert safety.check_inventory_cap(Decimal("250"), Decimal("0"), cfg) is True


# ---------------------------------------------------------------------------
# check_session_loss_limit
# ---------------------------------------------------------------------------

def test_session_loss_limit_exceeded():
    """pnl=-21, limit=20 → returns True (limit breached)."""
    safety = make_safety(max_session_loss_usdc=Decimal("20"))
    cfg = make_config(max_session_loss_usdc=Decimal("20"))
    assert safety.check_session_loss_limit(Decimal("-21"), cfg) is True


def test_session_loss_within_limit():
    """pnl=-5, limit=20 → returns False (within limit)."""
    safety = make_safety(max_session_loss_usdc=Decimal("20"))
    cfg = make_config(max_session_loss_usdc=Decimal("20"))
    assert safety.check_session_loss_limit(Decimal("-5"), cfg) is False


def test_session_loss_at_exact_limit():
    """pnl=-20, limit=20 → returns False (exactly at limit, not exceeded)."""
    safety = make_safety(max_session_loss_usdc=Decimal("20"))
    cfg = make_config(max_session_loss_usdc=Decimal("20"))
    assert safety.check_session_loss_limit(Decimal("-20"), cfg) is False


# ---------------------------------------------------------------------------
# check_binance_staleness
# ---------------------------------------------------------------------------

def test_binance_stale():
    """last_update=61s ago → returns True (is stale)."""
    safety = make_safety(binance_stale_seconds=30)
    last_update = datetime.now(tz=timezone.utc) - timedelta(seconds=61)
    assert safety.check_binance_staleness(last_update) is True


def test_binance_fresh():
    """last_update=5s ago → returns False (not stale)."""
    safety = make_safety(binance_stale_seconds=30)
    last_update = datetime.now(tz=timezone.utc) - timedelta(seconds=5)
    assert safety.check_binance_staleness(last_update) is False


def test_binance_never_updated():
    """last_update=None → returns False (cold-start grace period, not stale)."""
    safety = make_safety(binance_stale_seconds=30)
    assert safety.check_binance_staleness(None) is False


def test_check_binance_staleness_at_exact_threshold(safety, config):
    # Exactly at threshold is still fresh (strict >)
    ts = datetime.now(UTC) - timedelta(seconds=config.binance_stale_seconds)
    assert safety.check_binance_staleness(ts) is False


# ---------------------------------------------------------------------------
# should_wind_down
# ---------------------------------------------------------------------------

def test_should_wind_down_true():
    """session_end_time=4min from now, wind_down_minutes=5 → True (within wind-down window)."""
    safety = make_safety(wind_down_minutes=5)
    cfg = make_config(wind_down_minutes=5)
    session_end_time = datetime.now(tz=timezone.utc) + timedelta(minutes=4)
    assert safety.should_wind_down(session_end_time, cfg) is True


def test_should_wind_down_false():
    """session_end_time=10min from now, wind_down_minutes=5 → False (outside wind-down window)."""
    safety = make_safety(wind_down_minutes=5)
    cfg = make_config(wind_down_minutes=5)
    session_end_time = datetime.now(tz=timezone.utc) + timedelta(minutes=10)
    assert safety.should_wind_down(session_end_time, cfg) is False


def test_should_wind_down_past_end():
    """session_end_time=1min ago (past) → True (remaining is negative, <= wind_down_minutes)."""
    safety = make_safety(wind_down_minutes=5)
    cfg = make_config(wind_down_minutes=5)
    session_end_time = datetime.now(tz=timezone.utc) - timedelta(minutes=1)
    assert safety.should_wind_down(session_end_time, cfg) is True


# ---------------------------------------------------------------------------
# check_quote_safety composite
# ---------------------------------------------------------------------------

def test_check_quote_safety_all_pass():
    """All checks pass → safe=True, reason=None, wind_down=False."""
    safety = make_safety()
    cfg = make_config()
    binance_ts = datetime.now(tz=timezone.utc) - timedelta(seconds=5)
    session_end_time = datetime.now(tz=timezone.utc) + timedelta(minutes=30)
    result = safety.check_quote_safety(
        Decimal("0"), Decimal("0"), Decimal("0"),
        binance_ts, session_end_time, cfg,
    )
    assert result["safe"] is True
    assert result["reason"] is None
    assert result["wind_down"] is False


def test_check_quote_safety_all_pass_wind_down_flagged():
    """All safety checks pass but in wind-down window → safe=True, wind_down=True."""
    safety = make_safety()
    cfg = make_config(wind_down_minutes=5)
    binance_ts = datetime.now(tz=timezone.utc) - timedelta(seconds=5)
    session_end_time = datetime.now(tz=timezone.utc) + timedelta(minutes=3)
    result = safety.check_quote_safety(
        Decimal("0"), Decimal("0"), Decimal("0"),
        binance_ts, session_end_time, cfg,
    )
    assert result["safe"] is True
    assert result["reason"] is None
    assert result["wind_down"] is True


def test_check_quote_safety_killed():
    """_killed=True → safe=False, reason='Emergency shutdown active'."""
    safety = make_safety()
    safety._killed = True
    cfg = make_config()
    binance_ts = datetime.now(tz=timezone.utc) - timedelta(seconds=5)
    session_end_time = datetime.now(tz=timezone.utc) + timedelta(minutes=30)
    result = safety.check_quote_safety(
        Decimal("0"), Decimal("0"), Decimal("0"),
        binance_ts, session_end_time, cfg,
    )
    assert result["safe"] is False
    assert result["reason"] == "Emergency shutdown active"
    assert result["wind_down"] is False


def test_check_quote_safety_inventory_cap():
    """Inventory cap breached → safe=False, reason='Inventory cap breached'."""
    safety = make_safety()
    cfg = make_config(inventory_cap=Decimal("200"))
    binance_ts = datetime.now(tz=timezone.utc) - timedelta(seconds=5)
    session_end_time = datetime.now(tz=timezone.utc) + timedelta(minutes=30)
    result = safety.check_quote_safety(
        Decimal("200"), Decimal("0"), Decimal("0"),
        binance_ts, session_end_time, cfg,
    )
    assert result["safe"] is False
    assert result["reason"] == "Inventory cap breached"
    assert result["wind_down"] is False


def test_check_quote_safety_loss_limit():
    """Session loss limit exceeded → safe=False, reason='Session loss limit exceeded'."""
    safety = make_safety(max_session_loss_usdc=Decimal("20"))
    cfg = make_config(max_session_loss_usdc=Decimal("20"))
    binance_ts = datetime.now(tz=timezone.utc) - timedelta(seconds=5)
    session_end_time = datetime.now(tz=timezone.utc) + timedelta(minutes=30)
    result = safety.check_quote_safety(
        Decimal("0"), Decimal("0"), Decimal("-25"),
        binance_ts, session_end_time, cfg,
    )
    assert result["safe"] is False
    assert result["reason"] == "Session loss limit exceeded"
    assert result["wind_down"] is False


def test_check_quote_safety_stale_binance():
    """Binance feed stale → safe=False, reason='Binance price data stale'."""
    safety = make_safety(binance_stale_seconds=30)
    cfg = make_config(binance_stale_seconds=30)
    stale_ts = datetime.now(tz=timezone.utc) - timedelta(seconds=61)
    session_end_time = datetime.now(tz=timezone.utc) + timedelta(minutes=30)
    result = safety.check_quote_safety(
        Decimal("0"), Decimal("0"), Decimal("0"),
        stale_ts, session_end_time, cfg,
    )
    assert result["safe"] is False
    assert result["reason"] == "Binance price data stale"
    assert result["wind_down"] is False


# ---------------------------------------------------------------------------
# emergency_shutdown
# ---------------------------------------------------------------------------

def test_emergency_shutdown_sets_killed_flag():
    """emergency_shutdown sets is_killed=True synchronously."""
    safety = make_safety()
    executor = MagicMock()
    executor.cancel_all_orders = AsyncMock(return_value=3)

    assert safety.is_killed is False
    with patch("asyncio.get_running_loop", side_effect=RuntimeError("no loop")):
        safety.emergency_shutdown(executor, "test failure")
    assert safety.is_killed is True


def test_emergency_shutdown_idempotent():
    """Second call to emergency_shutdown is a no-op."""
    safety = make_safety()
    executor = MagicMock()
    executor.cancel_all_orders = AsyncMock(return_value=2)

    safety.emergency_shutdown(executor, "first shutdown")
    safety.emergency_shutdown(executor, "second shutdown")
    # _killed was set on the first call; second call returns early
    assert safety.is_killed is True


def test_emergency_shutdown_no_reason():
    """emergency_shutdown works without a reason argument."""
    safety = make_safety()
    executor = MagicMock()
    executor.cancel_all_orders = AsyncMock(return_value=0)

    with patch("asyncio.get_running_loop", side_effect=RuntimeError("no loop")):
        safety.emergency_shutdown(executor)
    assert safety.is_killed is True


def test_emergency_shutdown_no_event_loop():
    """When no event loop is running, emergency_shutdown swallows RuntimeError and sets killed."""
    safety = make_safety()
    executor = MagicMock()
    executor.cancel_all_orders = AsyncMock(return_value=1)

    # Simulate no running event loop
    with patch("asyncio.get_running_loop", side_effect=RuntimeError("no running event loop")):
        safety.emergency_shutdown(executor, "no loop test")
    assert safety.is_killed is True


@pytest.mark.asyncio
async def test_emergency_shutdown_async_cancel_called():
    """In an async context, the cancel coroutine fires and calls cancel_all_orders."""
    safety = make_safety()
    executor = MagicMock()
    executor.cancel_all_orders = AsyncMock(return_value=3)

    safety.emergency_shutdown(executor, "async test")
    assert safety.is_killed is True
    # Drain pending tasks so the fire-and-forget coroutine runs
    await asyncio.sleep(0)
    executor.cancel_all_orders.assert_awaited_once()


@pytest.mark.asyncio
async def test_emergency_shutdown_handles_cancel_failure():
    """If cancel_all_orders raises, emergency_shutdown does not re-raise."""
    safety = make_safety()
    executor = MagicMock()
    executor.cancel_all_orders = AsyncMock(side_effect=RuntimeError("CLOB unavailable"))

    safety.emergency_shutdown(executor, "clob down")
    assert safety.is_killed is True
    # Drain so the coroutine runs and swallows the error
    await asyncio.sleep(0)
