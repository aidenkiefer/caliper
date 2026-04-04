"""Unit tests for FeatureStore — uses in-memory mocks, no real DB (Sprint 12)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from packages.common.polymarket_schemas import FeatureSnapshot
from services.features.polymarket.store import FeatureStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _valid_snapshot() -> FeatureSnapshot:
    return FeatureSnapshot(
        market_id="0xabc123",
        token_id="0xtoken456",
        captured_at=datetime(2026, 4, 4, 12, 0, 0, tzinfo=timezone.utc),
        time_to_close_seconds=1800.0,
        time_since_open_seconds=600.0,
        mid_price=Decimal("0.50"),
        implied_probability=Decimal("0.50"),
        spread=Decimal("0.02"),
        spread_bps=Decimal("400"),
        book_depth_bid_5tick=Decimal("1000"),
        book_depth_ask_5tick=Decimal("900"),
        time_since_last_trade=5.0,
        time_since_last_price_change=3.0,
        order_book_imbalance=Decimal("0.05"),
        trade_flow_imbalance_1m=Decimal("100"),
        trade_flow_imbalance_5m=Decimal("250"),
        last_5min_volume_share=Decimal("0.25"),
        aggressor_buy_fraction_1m=Decimal("0.6"),
        vpin_proxy=Decimal("0.3"),
        fee_rate_current=Decimal("0.005"),
        reward_eligible=True,
        reward_max_spread=Decimal("0.05"),
        reward_min_size=Decimal("10"),
        btc_distance_to_open=Decimal("0.019"),
        btc_rv_1m=Decimal("0.0002"),
        btc_rv_5m=Decimal("0.001"),
        btc_rv_15m=Decimal("0.003"),
        btc_momentum_5m=Decimal("0.009"),
        btc_sign_persistence_5m=Decimal("0.8"),
        btc_funding_rate=Decimal("0.0001"),
        btc_basis_proxy=Decimal("0.0002"),
        vol_regime="medium",
        trend_regime="neutral",
        time_bucket="early",
        near_close_flag=False,
        toxicity_regime="low",
        spread_regime="normal",
        liquidity_score=Decimal("0.5"),
        competitive_pressure=Decimal("0.0025"),
        data_staleness_flag=False,
    )


def _make_mock_conn(execute_return=None, fetchrow_return=None, fetch_return=None):
    """Build a mock asyncpg connection that can be used as an async context manager."""
    conn = AsyncMock()
    conn.execute = AsyncMock(return_value=execute_return)
    conn.fetchrow = AsyncMock(return_value=fetchrow_return)
    conn.fetch = AsyncMock(return_value=fetch_return or [])
    return conn


def _make_mock_pool(conn: Any):
    """Build a mock asyncpg Pool whose acquire() context manager yields conn."""
    pool = MagicMock()
    # pool.acquire() returns an async context manager that yields conn
    acquire_ctx = AsyncMock()
    acquire_ctx.__aenter__ = AsyncMock(return_value=conn)
    acquire_ctx.__aexit__ = AsyncMock(return_value=False)
    pool.acquire = MagicMock(return_value=acquire_ctx)
    return pool


# ===========================================================================
# write()
# ===========================================================================

class TestFeatureStoreWrite:

    @pytest.mark.asyncio
    async def test_write_calls_insert(self):
        """write(snapshot) calls conn.execute with the INSERT SQL."""
        snapshot = _valid_snapshot()
        conn = _make_mock_conn()
        pool = _make_mock_pool(conn)

        store = FeatureStore("postgresql://fake/db")
        store._pool = pool

        await store.write(snapshot)

        conn.execute.assert_called_once()
        call_args = conn.execute.call_args
        sql_arg = call_args[0][0]  # first positional arg is the SQL string
        assert "INSERT INTO pm.features" in sql_arg
        assert "ON CONFLICT DO NOTHING" in sql_arg

    @pytest.mark.asyncio
    async def test_write_passes_correct_params(self):
        """write(snapshot) passes market_id, token_id, captured_at, and JSON."""
        snapshot = _valid_snapshot()
        conn = _make_mock_conn()
        pool = _make_mock_pool(conn)

        store = FeatureStore("postgresql://fake/db")
        store._pool = pool

        await store.write(snapshot)

        call_args = conn.execute.call_args[0]
        # Positional args: sql, market_id, token_id, captured_at, features_json
        assert call_args[1] == "0xabc123"
        assert call_args[2] == "0xtoken456"
        assert call_args[3] == datetime(2026, 4, 4, 12, 0, 0, tzinfo=timezone.utc)
        # The 4th positional arg is the JSON string
        features_json = call_args[4]
        parsed = json.loads(features_json)
        assert parsed["market_id"] == "0xabc123"


# ===========================================================================
# read_latest()
# ===========================================================================

class TestFeatureStoreReadLatest:

    @pytest.mark.asyncio
    async def test_read_latest_returns_none_empty(self):
        """When no rows exist, read_latest returns None."""
        conn = _make_mock_conn(fetchrow_return=None)
        pool = _make_mock_pool(conn)

        store = FeatureStore("postgresql://fake/db")
        store._pool = pool

        result = await store.read_latest("0xabc123")
        assert result is None

    @pytest.mark.asyncio
    async def test_read_latest_deserializes(self):
        """When a JSONB row is returned, read_latest returns a valid FeatureSnapshot."""
        snapshot = _valid_snapshot()
        json_payload = snapshot.model_dump(mode="json")

        # asyncpg rows are dict-like; simulate with a plain dict
        mock_row = {"features": json_payload}
        conn = _make_mock_conn(fetchrow_return=mock_row)
        pool = _make_mock_pool(conn)

        store = FeatureStore("postgresql://fake/db")
        store._pool = pool

        result = await store.read_latest("0xabc123")
        assert result is not None
        assert isinstance(result, FeatureSnapshot)
        assert result.market_id == "0xabc123"
        assert result.vol_regime == "medium"
        assert result.mid_price == Decimal("0.50")

    @pytest.mark.asyncio
    async def test_read_latest_passes_market_id(self):
        """read_latest queries by market_id."""
        conn = _make_mock_conn(fetchrow_return=None)
        pool = _make_mock_pool(conn)

        store = FeatureStore("postgresql://fake/db")
        store._pool = pool

        await store.read_latest("0xmarket999")
        conn.fetchrow.assert_called_once()
        call_args = conn.fetchrow.call_args[0]
        assert "0xmarket999" in call_args


# ===========================================================================
# read_window()
# ===========================================================================

class TestFeatureStoreReadWindow:

    @pytest.mark.asyncio
    async def test_read_window_empty(self):
        """When no rows match, read_window returns empty list."""
        conn = _make_mock_conn(fetch_return=[])
        pool = _make_mock_pool(conn)

        store = FeatureStore("postgresql://fake/db")
        store._pool = pool

        start = datetime(2026, 4, 4, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 4, 4, 11, 0, 0, tzinfo=timezone.utc)

        results = await store.read_window("0xabc123", start, end)
        assert results == []

    @pytest.mark.asyncio
    async def test_read_window_deserializes_multiple(self):
        """Multiple rows are each deserialized into FeatureSnapshot."""
        snapshot = _valid_snapshot()
        json_payload = snapshot.model_dump(mode="json")
        mock_rows = [
            {"features": json_payload},
            {"features": json_payload},
        ]
        conn = _make_mock_conn(fetch_return=mock_rows)
        pool = _make_mock_pool(conn)

        store = FeatureStore("postgresql://fake/db")
        store._pool = pool

        start = datetime(2026, 4, 4, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 4, 4, 13, 0, 0, tzinfo=timezone.utc)

        results = await store.read_window("0xabc123", start, end)
        assert len(results) == 2
        assert all(isinstance(r, FeatureSnapshot) for r in results)
        assert results[0].market_id == "0xabc123"


# ===========================================================================
# Not-connected guard
# ===========================================================================

class TestFeatureStoreNotConnected:

    @pytest.mark.asyncio
    async def test_not_connected_write_raises(self):
        """Calling write() before connect() raises RuntimeError."""
        store = FeatureStore("postgresql://fake/db")
        snapshot = _valid_snapshot()

        with pytest.raises(RuntimeError, match="not connected"):
            await store.write(snapshot)

    @pytest.mark.asyncio
    async def test_not_connected_read_latest_raises(self):
        """Calling read_latest() before connect() raises RuntimeError."""
        store = FeatureStore("postgresql://fake/db")

        with pytest.raises(RuntimeError, match="not connected"):
            await store.read_latest("0xabc123")

    @pytest.mark.asyncio
    async def test_not_connected_read_window_raises(self):
        """Calling read_window() before connect() raises RuntimeError."""
        store = FeatureStore("postgresql://fake/db")
        start = datetime(2026, 4, 4, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 4, 4, 11, 0, 0, tzinfo=timezone.utc)

        with pytest.raises(RuntimeError, match="not connected"):
            await store.read_window("0xabc123", start, end)


# ===========================================================================
# Standalone spec-required test function
# ===========================================================================

@pytest.mark.asyncio
async def test_not_connected_raises():
    """Creating FeatureStore without connect() and calling write() raises RuntimeError."""
    store = FeatureStore("postgresql://localhost/test")
    snapshot = _valid_snapshot()

    with pytest.raises(RuntimeError):
        await store.write(snapshot)
