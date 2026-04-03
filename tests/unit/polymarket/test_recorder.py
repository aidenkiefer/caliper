"""
Unit tests for services/polymarket/recorder.py

Coverage:
- test_create_session              — DB insert called with correct data; returns a UUID
- test_record_order                — immediate insert into pm.orders
- test_record_fill                 — immediate insert into pm.fills
- test_record_snapshot_buffers     — snapshot buffer accumulates without flush at < 10
- test_record_snapshot_flushes_at_10 — flush triggered when buffer reaches 10
- test_flush_periodic              — manual _flush_all drains both buffers
- test_finalize_session_inserts_regime_tags — regime tags computed and UPDATE issued
- test_compute_toxic_flow          — aggregation SQL executed for the session
- test_update_adverse_selection    — correct UPDATE executed with fill_id
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, call, patch
from uuid import UUID, uuid4

import asyncpg
import pytest

from services.polymarket.recorder import Recorder, _SNAPSHOT_BATCH_SIZE
from services.polymarket.schemas import MarketInfo, OrderbookState


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_pool():
    """
    Returns (pool, conn).

    pool.acquire() is an async context manager that yields ``conn``.
    ``conn`` is an AsyncMock with .execute, .executemany, .fetchrow wired up.
    """
    pool = MagicMock(spec=asyncpg.Pool)
    conn = AsyncMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    return pool, conn


def make_market_info() -> MarketInfo:
    return MarketInfo(
        condition_id="cond-abc",
        token_id_yes="tok-yes",
        token_id_no="tok-no",
        slug="btc-hourly-test",
        window_start=datetime(2026, 3, 25, 9, 0, 0, tzinfo=timezone.utc),
        window_end=datetime(2026, 3, 25, 10, 0, 0, tzinfo=timezone.utc),
        tick_size=Decimal("0.01"),
        fees_enabled=False,
    )


def make_config():
    cfg = MagicMock()
    cfg.quote_spread = Decimal("0.02")
    cfg.quote_size = Decimal("50")
    cfg.inventory_cap = Decimal("200")
    cfg.max_session_loss_usdc = Decimal("20")
    cfg.requote_interval_seconds = 10
    cfg.wind_down_minutes = 5
    return cfg


def make_snapshot(spread: Decimal = Decimal("0.02")) -> OrderbookState:
    return OrderbookState(
        token_id="tok-yes",
        best_bid=Decimal("0.49"),
        best_ask=Decimal("0.51"),
        midpoint=Decimal("0.50"),
        spread=spread,
        last_updated=datetime.now(tz=timezone.utc),
    )


# ---------------------------------------------------------------------------
# test_create_session
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_session(mock_pool):
    pool, conn = mock_pool
    expected_session_id = uuid4()
    conn.fetchrow = AsyncMock(return_value={"session_id": expected_session_id})

    recorder = Recorder(pool)
    result = await recorder.create_session(make_market_info(), make_config())

    assert isinstance(result, UUID)
    assert result == expected_session_id
    conn.fetchrow.assert_awaited_once()
    # Verify the SQL statement includes pm.sessions
    sql_arg = conn.fetchrow.call_args[0][0]
    assert "pm.sessions" in sql_arg
    # Verify condition_id and token ids are passed
    positional_args = conn.fetchrow.call_args[0]
    assert "cond-abc" in positional_args
    assert "tok-yes" in positional_args
    assert "tok-no" in positional_args


# ---------------------------------------------------------------------------
# test_record_order
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_record_order(mock_pool):
    pool, conn = mock_pool
    conn.execute = AsyncMock(return_value="INSERT 0 1")

    recorder = Recorder(pool)
    session_id = uuid4()
    order_data = {
        "token_id": "tok-yes",
        "side": "BUY",
        "price": Decimal("0.48"),
        "original_size": Decimal("50"),
        "polymarket_order_id": "pm-order-123",
        "midpoint_at_place": Decimal("0.50"),
    }
    await recorder.record_order(order_data, session_id)

    conn.execute.assert_awaited_once()
    sql_arg = conn.execute.call_args[0][0]
    assert "pm.orders" in sql_arg
    # session_id should appear in the positional args
    positional_args = conn.execute.call_args[0]
    assert session_id in positional_args


# ---------------------------------------------------------------------------
# test_record_fill
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_record_fill(mock_pool):
    pool, conn = mock_pool
    conn.execute = AsyncMock(return_value="INSERT 0 1")

    recorder = Recorder(pool)
    session_id = uuid4()
    fill_data = {
        "token_id": "tok-yes",
        "side": "BUY",
        "price": Decimal("0.48"),
        "size": Decimal("50"),
        "filled_at": datetime.now(tz=timezone.utc),
    }
    await recorder.record_fill(fill_data, session_id)

    conn.execute.assert_awaited_once()
    sql_arg = conn.execute.call_args[0][0]
    assert "pm.fills" in sql_arg
    positional_args = conn.execute.call_args[0]
    assert session_id in positional_args


# ---------------------------------------------------------------------------
# test_record_binance_candle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_record_binance_candle(mock_pool):
    """record_binance_candle should execute one INSERT using ON CONFLICT (source, open_time)."""
    pool, conn = mock_pool
    conn.execute = AsyncMock(return_value="INSERT 0 1")

    recorder = Recorder(pool)
    session_id = uuid4()
    candle_data = {
        "open_time": datetime(2026, 3, 25, 9, 0, 0, tzinfo=timezone.utc),
        "close_time": datetime(2026, 3, 25, 9, 59, 59, tzinfo=timezone.utc),
        "open": Decimal("70000"),
        "high": Decimal("70500"),
        "low": Decimal("69800"),
        "close": Decimal("70250"),
        "volume": Decimal("120.5"),
        "source": "binance",
    }
    await recorder.record_binance_candle(candle_data, session_id)

    conn.execute.assert_awaited_once()
    sql_arg = conn.execute.call_args[0][0]
    # Conflict target must use (source, open_time), NOT candle_id
    assert "ON CONFLICT (source, open_time)" in sql_arg
    positional_args = conn.execute.call_args[0]
    # 'source' value should appear in the positional args
    assert "binance" in positional_args


# ---------------------------------------------------------------------------
# test_record_snapshot_buffers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_record_snapshot_buffers(mock_pool):
    """Buffer should accumulate without flushing when below the batch size."""
    pool, conn = mock_pool
    conn.executemany = AsyncMock()

    recorder = Recorder(pool)
    session_id = uuid4()

    for _ in range(_SNAPSHOT_BATCH_SIZE - 1):
        await recorder.record_snapshot(make_snapshot(), session_id)

    assert len(recorder._snapshot_buffer) == _SNAPSHOT_BATCH_SIZE - 1
    conn.executemany.assert_not_awaited()


# ---------------------------------------------------------------------------
# test_record_snapshot_flushes_at_10
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_record_snapshot_flushes_at_10(mock_pool):
    """Adding the 10th snapshot should trigger a flush and empty the buffer."""
    pool, conn = mock_pool
    conn.executemany = AsyncMock()

    recorder = Recorder(pool)
    session_id = uuid4()

    for _ in range(_SNAPSHOT_BATCH_SIZE):
        await recorder.record_snapshot(make_snapshot(), session_id)

    # Buffer should be cleared after flush
    assert len(recorder._snapshot_buffer) == 0
    conn.executemany.assert_awaited_once()
    # The flush should have passed all 10 rows
    rows_arg = conn.executemany.call_args[0][1]
    assert len(rows_arg) == _SNAPSHOT_BATCH_SIZE


# ---------------------------------------------------------------------------
# test_flush_periodic
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_flush_periodic(mock_pool):
    """
    Manual call to _flush_all drains both snapshot and PnL buffers.
    Simulates what the periodic task does on each cycle.
    """
    pool, conn = mock_pool
    conn.executemany = AsyncMock()

    recorder = Recorder(pool)
    session_id = uuid4()

    # Populate both buffers with less than _SNAPSHOT_BATCH_SIZE items
    for _ in range(3):
        await recorder.record_snapshot(make_snapshot(), session_id)
    for _ in range(2):
        await recorder.record_pnl_snapshot(
            {"timestamp": datetime.now(tz=timezone.utc), "realized_pnl": Decimal("1.5")},
            session_id,
        )

    assert len(recorder._snapshot_buffer) == 3
    assert len(recorder._pnl_buffer) == 2

    # Manual flush
    await recorder._flush_all()

    assert len(recorder._snapshot_buffer) == 0
    assert len(recorder._pnl_buffer) == 0
    assert conn.executemany.await_count == 2


# ---------------------------------------------------------------------------
# test_finalize_session_inserts_regime_tags
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_finalize_session_inserts_regime_tags(mock_pool):
    """
    finalize_session should query the DB for regime inputs and then UPDATE
    pm.sessions with regime tag columns populated.
    """
    pool, conn = mock_pool

    # fetchrow returns different data depending on call order:
    #   1st call → orderbook_snapshots AVG(spread)
    #   2nd call → fills COUNT(*)
    #   3rd call → binance_candles first/last close
    conn.fetchrow = AsyncMock(
        side_effect=[
            {"avg_spread": Decimal("0.015")},           # tight spread → volatility LOW, spread TIGHT
            {"cnt": 25},                                  # 25 fills → HIGH volume
            {"first_close": Decimal("50000"), "last_close": Decimal("51500")},  # +3 % → UP
        ]
    )
    conn.execute = AsyncMock(return_value="UPDATE 1")

    recorder = Recorder(pool)
    session_id = uuid4()
    final_state = {
        "final_usdc": Decimal("100"),
        "realized_pnl": Decimal("5"),
        "total_orders_placed": 30,
        "total_fills": 25,
        "status": "COMPLETED",
    }
    await recorder.finalize_session(session_id, final_state)

    # The UPDATE should have been called
    conn.execute.assert_awaited_once()
    sql_arg = conn.execute.call_args[0][0]
    assert "UPDATE pm.sessions" in sql_arg

    # Regime values should appear in the positional args
    positional_args = conn.execute.call_args[0]
    assert "LOW" in positional_args       # volatility_regime
    assert "TIGHT" in positional_args     # spread_regime
    assert "HIGH" in positional_args      # volume_regime
    assert "UP" in positional_args        # btc_trend_regime


# ---------------------------------------------------------------------------
# test_compute_toxic_flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compute_toxic_flow(mock_pool):
    """compute_toxic_flow_by_minute should execute an aggregation INSERT on pm.fills."""
    pool, conn = mock_pool
    conn.execute = AsyncMock(return_value="INSERT 0 5")

    recorder = Recorder(pool)
    session_id = uuid4()

    await recorder.compute_toxic_flow_by_minute(session_id)

    conn.execute.assert_awaited_once()
    sql_arg = conn.execute.call_args[0][0]
    # Should reference both the target table and source fills table
    assert "pm.toxic_flow_by_minute" in sql_arg
    assert "pm.fills" in sql_arg
    # session_id passed as parameter
    positional_args = conn.execute.call_args[0]
    assert session_id in positional_args


# ---------------------------------------------------------------------------
# test_update_adverse_selection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_adverse_selection(mock_pool):
    """update_adverse_selection_async should issue a targeted UPDATE on pm.fills."""
    pool, conn = mock_pool
    conn.execute = AsyncMock(return_value="UPDATE 1")

    recorder = Recorder(pool)
    fill_id = uuid4()
    midpoint_5s = Decimal("0.505")
    midpoint_10s = Decimal("0.510")

    await recorder.update_adverse_selection_async(fill_id, midpoint_5s, midpoint_10s)

    conn.execute.assert_awaited_once()
    sql_arg = conn.execute.call_args[0][0]
    assert "UPDATE pm.fills" in sql_arg
    assert "midpoint_5s_after" in sql_arg
    assert "midpoint_10s_after" in sql_arg
    assert "adverse_selection_flag" in sql_arg

    positional_args = conn.execute.call_args[0]
    assert fill_id in positional_args
    assert midpoint_5s in positional_args
    assert midpoint_10s in positional_args


# ---------------------------------------------------------------------------
# start / stop lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("services.polymarket.recorder.asyncio.sleep", new_callable=AsyncMock)
async def test_start_creates_flush_task(mock_sleep):
    """start() should create a background asyncio task."""
    pool = MagicMock(spec=asyncpg.Pool)
    recorder = Recorder(pool)
    assert recorder._flush_task is None

    await recorder.start()
    assert recorder._flush_task is not None
    assert not recorder._flush_task.done()

    # Clean up
    await recorder.stop()


@pytest.mark.asyncio
@patch("services.polymarket.recorder.asyncio.sleep", new_callable=AsyncMock)
async def test_stop_cancels_task_and_flushes(mock_sleep):
    """stop() cancels the background task and flushes remaining buffers."""
    pool = MagicMock(spec=asyncpg.Pool)
    conn = AsyncMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    conn.executemany = AsyncMock()

    recorder = Recorder(pool)
    session_id = uuid4()

    await recorder.start()

    # Add items to buffers
    for _ in range(3):
        recorder._snapshot_buffer.append(
            {
                "session_id": session_id,
                "timestamp": datetime.now(tz=timezone.utc),
                "best_bid": None,
                "best_ask": None,
                "midpoint": None,
                "spread": None,
                "bid_depth_1pct": None,
                "ask_depth_1pct": None,
                "imbalance": None,
            }
        )

    await recorder.stop()

    assert recorder._flush_task is None
    # Buffers flushed → executemany called
    conn.executemany.assert_awaited()
