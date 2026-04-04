"""
Integration tests for FeatureBuilder using mock data sources.

Covers:
  - AC-7: Three consecutive snapshots are written to the output queue
  - AC-5: Deterministic output — two builders with identical inputs produce
          identical FeatureSnapshot values
  - Staleness flag is set when CLOB source_timestamp is > 30 s old
  - Staleness flag is clear when both sources are fresh
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional

import pytest

from packages.common.polymarket_schemas import FeatureSnapshot
from services.features.polymarket.builder import FeatureBuilder
from services.features.polymarket.sources.binance import KlineBar, PremiumIndex
from services.features.polymarket.sources.clob import OrderbookState, RewardConfig

# ---------------------------------------------------------------------------
# Helpers — fixed timestamps used throughout tests
# ---------------------------------------------------------------------------

_NOW = datetime(2026, 4, 4, 12, 0, 0, tzinfo=timezone.utc)
_MARKET_OPEN = _NOW - timedelta(hours=1)
_MARKET_CLOSE = _NOW + timedelta(hours=1)

# ---------------------------------------------------------------------------
# Mock sources
# ---------------------------------------------------------------------------


class MockCLOBSource:
    """Drop-in mock for CLOBSource — returns deterministic values, no I/O."""

    def __init__(self, stale_seconds: float = 0.0) -> None:
        self._stale_seconds = stale_seconds

    async def connect(self, token_id: str) -> None:
        pass

    async def disconnect(self) -> None:
        pass

    async def get_orderbook_state(self) -> OrderbookState:
        return OrderbookState(
            best_bid=Decimal("0.48"),
            best_ask=Decimal("0.52"),
            bids_depth_5tick=Decimal("500"),
            asks_depth_5tick=Decimal("450"),
            last_trade_price=Decimal("0.50"),
            last_trade_ts=datetime.now(timezone.utc) - timedelta(seconds=5),
            last_price_change_ts=datetime.now(timezone.utc) - timedelta(seconds=3),
        )

    async def fetch_fee_rate(self, token_id: str) -> Decimal:
        return Decimal("0.0025")

    async def fetch_reward_config(self, token_id: str) -> RewardConfig:
        return RewardConfig(
            eligible=True,
            max_spread=Decimal("0.03"),
            min_size=Decimal("5"),
        )

    @property
    def source_timestamp(self) -> datetime:
        return datetime.now(timezone.utc) - timedelta(seconds=self._stale_seconds)


class MockBinanceSource:
    """Drop-in mock for BinanceSource — returns deterministic values, no I/O."""

    def __init__(self, stale_seconds: float = 0.0) -> None:
        self._stale_seconds = stale_seconds

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    def get_btc_price(self) -> Decimal:
        return Decimal("50100")

    def get_hour_open(self) -> Decimal:
        return Decimal("50000")

    def get_kline_buffer(self) -> List[KlineBar]:
        """Return 15 KlineBar objects with prices cycling from 49900 to 50200."""
        bars: List[KlineBar] = []
        base_open_time = datetime(2026, 4, 4, 11, 0, 0, tzinfo=timezone.utc)
        for i in range(15):
            price = Decimal(str(49900 + i * (300 / 14)))
            bar = KlineBar(
                open_time=base_open_time + timedelta(minutes=i),
                open=price,
                high=price + Decimal("10"),
                low=price - Decimal("10"),
                close=price + Decimal("5"),
                volume=Decimal("1000"),
            )
            bars.append(bar)
        return bars

    def get_premium_index(self) -> PremiumIndex:
        return PremiumIndex(
            mark_price=Decimal("50105"),
            index_price=Decimal("50100"),
            last_funding_rate=Decimal("0.0001"),
            next_funding_time=datetime(2026, 4, 4, 16, 0, 0, tzinfo=timezone.utc),
            received_at=datetime.now(timezone.utc),
        )

    @property
    def source_timestamp(self) -> datetime:
        return datetime.now(timezone.utc) - timedelta(seconds=self._stale_seconds)


# ---------------------------------------------------------------------------
# Helper: build a FeatureBuilder with mocks, skipping real network calls
# ---------------------------------------------------------------------------


def _make_builder(
    clob: Optional[MockCLOBSource] = None,
    binance: Optional[MockBinanceSource] = None,
    tick_seconds: float = 0.05,
) -> FeatureBuilder:
    return FeatureBuilder(
        clob=clob or MockCLOBSource(),
        binance=binance or MockBinanceSource(),
        market_id="test-market",
        token_id="test-token",
        market_open_ts=_MARKET_OPEN,
        market_close_ts=_MARKET_CLOSE,
        tick_seconds=tick_seconds,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_three_consecutive_snapshots_written():
    """AC-7: at least 3 snapshots are written to the output queue within 0.5 s."""
    builder = _make_builder(tick_seconds=0.05)

    # Manually start the tick loop without calling clob.connect / binance.start
    builder._tick_task = asyncio.create_task(
        builder._tick_loop(), name="test-tick-loop"
    )

    # Drain the queue in a consumer coroutine
    snapshots: List[FeatureSnapshot] = []

    async def _consume():
        while True:
            snapshot = await asyncio.wait_for(builder.output_queue.get(), timeout=2.0)
            snapshots.append(snapshot)

    consumer_task = asyncio.create_task(_consume())

    # Let the loop run for 0.5 s (10 ticks at 0.05 s each)
    await asyncio.sleep(0.5)

    # Stop tick loop
    builder._tick_task.cancel()
    try:
        await builder._tick_task
    except asyncio.CancelledError:
        pass

    consumer_task.cancel()
    try:
        await consumer_task
    except (asyncio.CancelledError, asyncio.TimeoutError):
        pass

    assert len(snapshots) >= 3, f"Expected >= 3 snapshots, got {len(snapshots)}"

    for snap in snapshots:
        assert isinstance(snap, FeatureSnapshot)
        assert snap.market_id == "test-market"
        assert snap.token_id == "test-token"


@pytest.mark.asyncio
async def test_deterministic_output():
    """AC-5: two builders with identical mock sources produce identical snapshots."""
    builder_a = _make_builder()
    builder_b = _make_builder()

    fixed_ts = _NOW

    snap_a = await builder_a._compute_snapshot(captured_at=fixed_ts)
    snap_b = await builder_b._compute_snapshot(captured_at=fixed_ts)

    # All numeric / string / bool fields must match exactly
    assert snap_a.mid_price == snap_b.mid_price
    assert snap_a.spread == snap_b.spread
    assert snap_a.spread_bps == snap_b.spread_bps
    assert snap_a.implied_probability == snap_b.implied_probability
    assert snap_a.order_book_imbalance == snap_b.order_book_imbalance
    assert snap_a.btc_distance_to_open == snap_b.btc_distance_to_open
    assert snap_a.btc_rv_1m == snap_b.btc_rv_1m
    assert snap_a.btc_rv_5m == snap_b.btc_rv_5m
    assert snap_a.btc_rv_15m == snap_b.btc_rv_15m
    assert snap_a.btc_momentum_5m == snap_b.btc_momentum_5m
    assert snap_a.btc_sign_persistence_5m == snap_b.btc_sign_persistence_5m
    assert snap_a.btc_funding_rate == snap_b.btc_funding_rate
    assert snap_a.btc_basis_proxy == snap_b.btc_basis_proxy
    assert snap_a.vol_regime == snap_b.vol_regime
    assert snap_a.trend_regime == snap_b.trend_regime
    assert snap_a.toxicity_regime == snap_b.toxicity_regime
    assert snap_a.time_bucket == snap_b.time_bucket
    assert snap_a.near_close_flag == snap_b.near_close_flag
    assert snap_a.liquidity_score == snap_b.liquidity_score
    assert snap_a.competitive_pressure == snap_b.competitive_pressure
    assert snap_a.data_staleness_flag == snap_b.data_staleness_flag


@pytest.mark.asyncio
async def test_staleness_flag_set():
    """Staleness flag is True when CLOB source_timestamp is > 30 s old."""
    stale_clob = MockCLOBSource(stale_seconds=45.0)
    builder = _make_builder(clob=stale_clob)

    captured_at = datetime.now(timezone.utc)
    snapshot = await builder._compute_snapshot(captured_at=captured_at)

    assert snapshot.data_staleness_flag is True


@pytest.mark.asyncio
async def test_staleness_flag_clear_when_fresh():
    """Staleness flag is False when both sources have recent timestamps."""
    fresh_clob = MockCLOBSource(stale_seconds=0.0)
    fresh_binance = MockBinanceSource(stale_seconds=0.0)
    builder = _make_builder(clob=fresh_clob, binance=fresh_binance)

    captured_at = datetime.now(timezone.utc)
    snapshot = await builder._compute_snapshot(captured_at=captured_at)

    assert snapshot.data_staleness_flag is False
