"""
Unit tests for services/polymarket/market_discovery.py.

Tests cover:
- Successful market discovery with DB caching
- MarketNotFoundError propagation
- DST-aware UTC conversion (summer EDT and winter EST)
- Correct SQL parameters passed to asyncpg in cache_market_metadata
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.polymarket.adapters.gamma_client import MarketNotFoundError
from services.polymarket.market_discovery import MarketDiscovery, _local_hour_to_utc
from services.polymarket.schemas import MarketInfo


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_market_info() -> MarketInfo:
    """Return a minimal valid MarketInfo for use in tests."""
    return MarketInfo(
        condition_id="0xABC123",
        token_id_yes="yes_token",
        token_id_no="no_token",
        slug="btc-hourly-test",
        question="Will BTC be above $X at 9 AM?",
        window_start=datetime.datetime(2026, 3, 25, 13, 0, 0, tzinfo=datetime.timezone.utc),
        window_end=datetime.datetime(2026, 3, 25, 14, 0, 0, tzinfo=datetime.timezone.utc),
        tick_size=Decimal("0.01"),
        fees_enabled=True,
        fee_rate_bps=Decimal("200"),
        rewards_max_spread=Decimal("0.05"),
        rewards_min_size=Decimal("10"),
        total_volume=Decimal("50000"),
    )


def _make_config():
    """Return a minimal PolymarketConfig-like object without env validation."""
    cfg = MagicMock()
    cfg.target_hour_local = 9
    cfg.target_timezone = "America/New_York"
    return cfg


# ---------------------------------------------------------------------------
# test_discover_market_success
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_discover_market_success():
    """GammaClient returns a MarketInfo; verify it is returned and cached."""
    market = _make_market_info()
    mock_gamma = AsyncMock()
    mock_gamma.find_hourly_btc_market = AsyncMock(return_value=market)

    mock_conn = AsyncMock()

    discovery = MarketDiscovery(gamma_client=mock_gamma)
    config = _make_config()

    result = await discovery.discover_target_market(
        config=config,
        db_conn=mock_conn,
        target_date=datetime.date(2026, 3, 25),
    )

    assert result is market
    mock_gamma.find_hourly_btc_market.assert_called_once()
    # DB write should have been called
    mock_conn.execute.assert_called_once()


# ---------------------------------------------------------------------------
# test_discover_market_not_found
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_discover_market_not_found():
    """MarketNotFoundError from GammaClient propagates unchanged."""
    mock_gamma = AsyncMock()
    mock_gamma.find_hourly_btc_market = AsyncMock(
        side_effect=MarketNotFoundError("No BTC market for 2026-03-25 hour=13:00 UTC")
    )

    mock_conn = AsyncMock()

    discovery = MarketDiscovery(gamma_client=mock_gamma)
    config = _make_config()

    with pytest.raises(MarketNotFoundError):
        await discovery.discover_target_market(
            config=config,
            db_conn=mock_conn,
            target_date=datetime.date(2026, 3, 25),
        )

    # DB write must NOT have been called on failure
    mock_conn.execute.assert_not_called()


# ---------------------------------------------------------------------------
# DST conversion tests
# ---------------------------------------------------------------------------


def test_dst_summer_conversion():
    """9 AM ET in summer (EDT = UTC-4) should map to UTC hour 13."""
    summer_date = datetime.date(2026, 7, 1)
    utc_hour = _local_hour_to_utc(9, "America/New_York", summer_date)
    assert utc_hour == 13, f"Expected 13 (EDT UTC-4), got {utc_hour}"


def test_dst_winter_conversion():
    """9 AM ET in winter (EST = UTC-5) should map to UTC hour 14."""
    winter_date = datetime.date(2026, 1, 15)
    utc_hour = _local_hour_to_utc(9, "America/New_York", winter_date)
    assert utc_hour == 14, f"Expected 14 (EST UTC-5), got {utc_hour}"


# ---------------------------------------------------------------------------
# test_cache_market_metadata_writes_correct_params
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cache_market_metadata_writes_correct_params():
    """cache_market_metadata passes all MarketInfo fields to asyncpg execute."""
    market = _make_market_info()

    mock_conn = AsyncMock()

    discovery = MarketDiscovery(gamma_client=MagicMock())
    await discovery.cache_market_metadata(market, mock_conn)

    mock_conn.execute.assert_called_once()
    call_args = mock_conn.execute.call_args

    # First positional arg is the SQL string
    sql: str = call_args[0][0]
    assert "pm.market_metadata" in sql
    assert "ON CONFLICT" in sql
    assert "DO UPDATE" in sql

    # Remaining positional args are the parameter values in order
    params = call_args[0][1:]
    assert params[0] == market.condition_id       # $1
    assert params[1] == market.slug               # $2
    assert params[2] == market.question           # $3
    assert params[3] == market.token_id_yes       # $4
    assert params[4] == market.token_id_no        # $5
    assert params[5] == market.window_start       # $6
    assert params[6] == market.window_end         # $7
    assert params[7] == market.tick_size          # $8
    assert params[8] == market.fees_enabled       # $9
    assert params[9] == market.fee_rate_bps       # $10
    assert params[10] == market.rewards_max_spread  # $11
    assert params[11] == market.rewards_min_size    # $12
    assert params[12] == market.total_volume        # $13


# ---------------------------------------------------------------------------
# Additional: discover_target_market skips DB write when db_conn is None
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_discover_market_no_db_conn():
    """When db_conn is None, the DB write is skipped and MarketInfo is still returned."""
    market = _make_market_info()
    mock_gamma = AsyncMock()
    mock_gamma.find_hourly_btc_market = AsyncMock(return_value=market)

    discovery = MarketDiscovery(gamma_client=mock_gamma)
    config = _make_config()

    result = await discovery.discover_target_market(
        config=config,
        db_conn=None,
        target_date=datetime.date(2026, 3, 25),
    )

    assert result is market
