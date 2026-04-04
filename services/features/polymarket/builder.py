"""
FeatureBuilder — Sprint 12 central computation engine.

Runs on a 5-second tick cadence, pulls from CLOBSource and BinanceSource,
computes all 4 feature families, and publishes FeatureSnapshot to an asyncio.Queue.

Design notes
------------
- ``captured_at`` is set ONCE per tick in ``_tick_loop`` and passed through to
  ``_compute_snapshot``.  No ``datetime.now()`` inside formulas — this makes
  replay/mock testing with fixed timestamps deterministic.
- ``DataUnavailable`` is handled at the tick level (DEBUG log, skip tick).
- All other exceptions in the tick loop are logged at ERROR level and do NOT
  propagate (the loop continues).
- The minimum-hold filter for regime labels requires 3 consecutive identical
  labels before the "live" label is updated, preventing jitter on boundary
  crossings.
"""

from __future__ import annotations

import asyncio
import logging
import math
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Deque, Dict, Optional

from packages.common.polymarket_schemas import FeatureSnapshot
from services.features.polymarket.sources.binance import BinanceSource
from services.features.polymarket.sources.clob import CLOBSource, DataUnavailable

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal trade tape record
# ---------------------------------------------------------------------------


@dataclass
class TradeRecord:
    """Single trade entry for flow imbalance computation."""

    ts: datetime
    side: str   # "BUY" or "SELL"
    size: Decimal


# ---------------------------------------------------------------------------
# FeatureBuilder
# ---------------------------------------------------------------------------


class FeatureBuilder:
    """Async feature computation engine for a single Polymarket token.

    Parameters
    ----------
    clob:
        Connected (or to-be-connected) CLOBSource.
    binance:
        Started (or to-be-started) BinanceSource.
    market_id:
        Polymarket market condition ID.
    token_id:
        CLOB token ID (YES or NO) to subscribe to.
    market_open_ts:
        UTC datetime when the market opened (used for time-bucketing).
    market_close_ts:
        UTC datetime when the market closes (used for near-close flag).
    tick_seconds:
        How often (in seconds) to run the computation loop.
    """

    def __init__(
        self,
        clob: CLOBSource,
        binance: BinanceSource,
        market_id: str,
        token_id: str,
        market_open_ts: datetime,
        market_close_ts: datetime,
        tick_seconds: float = 5.0,
    ) -> None:
        self._clob = clob
        self._binance = binance
        self.market_id = market_id
        self.token_id = token_id
        self.market_open_ts = market_open_ts
        self.market_close_ts = market_close_ts
        self.tick_seconds = tick_seconds

        # Downstream consumers subscribe to this queue
        self.output_queue: asyncio.Queue[FeatureSnapshot] = asyncio.Queue(maxsize=100)

        # Internal state -------------------------------------------------------
        # Rolling trade tape for flow imbalance (last 300 trades max)
        self._trade_tape: Deque[TradeRecord] = deque(maxlen=300)

        # Regime minimum-hold filter: family_name -> deque of last 3 labels
        self._regime_hold: Dict[str, deque] = {
            "vol_regime": deque(maxlen=3),
            "trend_regime": deque(maxlen=3),
            "toxicity_regime": deque(maxlen=3),
            "spread_regime": deque(maxlen=3),
        }

        # Current "live" regime labels (updated only after 3 consecutive same)
        self._current_regimes: Dict[str, Optional[str]] = {
            "vol_regime": None,
            "trend_regime": None,
            "toxicity_regime": None,
            "spread_regime": None,
        }

        # Rolling spread history for median spread computation (24h at 1/tick)
        self._spread_history: Deque[Decimal] = deque(maxlen=1440)

        # Rolling liquidity score history for min-max normalization
        self._liq_history: Deque[float] = deque(maxlen=288)

        # Background task handle
        self._tick_task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Connect data sources and launch the background tick loop."""
        await self._clob.connect(self.token_id)
        await self._binance.start()
        self._tick_task = asyncio.create_task(
            self._tick_loop(), name=f"feature-builder-{self.token_id}"
        )
        logger.info(
            "FeatureBuilder started: market_id=%s token_id=%s tick=%.1fs",
            self.market_id,
            self.token_id,
            self.tick_seconds,
        )

    async def stop(self) -> None:
        """Stop the tick loop and disconnect data sources."""
        if self._tick_task and not self._tick_task.done():
            self._tick_task.cancel()
            try:
                await self._tick_task
            except asyncio.CancelledError:
                pass
        self._tick_task = None

        await self._clob.disconnect()
        await self._binance.stop()
        logger.info(
            "FeatureBuilder stopped: market_id=%s token_id=%s",
            self.market_id,
            self.token_id,
        )

    # ------------------------------------------------------------------
    # Tick loop
    # ------------------------------------------------------------------

    async def _tick_loop(self) -> None:
        """Main computation loop; runs every ``tick_seconds``."""
        while True:
            try:
                await asyncio.sleep(self.tick_seconds)
            except asyncio.CancelledError:
                logger.debug("FeatureBuilder tick loop cancelled")
                return

            # Capture timestamp once for deterministic computation
            captured_at = datetime.now(tz=timezone.utc)

            try:
                snapshot = await self._compute_snapshot(captured_at)
            except DataUnavailable as exc:
                logger.debug(
                    "FeatureBuilder: DataUnavailable on tick (skipping): %s", exc
                )
                continue
            except asyncio.CancelledError:
                return
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "FeatureBuilder: unexpected error on tick at %s: %s",
                    captured_at.isoformat(),
                    exc,
                    exc_info=True,
                )
                continue

            try:
                self.output_queue.put_nowait(snapshot)
            except asyncio.QueueFull:
                logger.warning(
                    "FeatureBuilder: output_queue full (maxsize=100); dropping snapshot at %s",
                    captured_at.isoformat(),
                )

    # ------------------------------------------------------------------
    # Main computation
    # ------------------------------------------------------------------

    async def _compute_snapshot(self, captured_at: datetime) -> FeatureSnapshot:
        """Compute all 4 feature families and return a FeatureSnapshot.

        Parameters
        ----------
        captured_at:
            The wall-clock UTC time assigned to this snapshot.  Must be passed
            in from the tick loop — never call ``datetime.now()`` here.
        """
        # ------------------------------------------------------------------
        # Pull raw data
        # ------------------------------------------------------------------
        ob = await self._clob.get_orderbook_state()   # may raise DataUnavailable

        # BinanceSource getters raise DataUnavailable if buffers are empty
        btc_price = self._binance.get_btc_price()
        hour_open = self._binance.get_hour_open()
        klines = self._binance.get_kline_buffer()
        premium_index = self._binance.get_premium_index()

        # Async REST lookups
        fee_rate = await self._clob.fetch_fee_rate(self.token_id)
        reward_cfg = await self._clob.fetch_reward_config(self.token_id)

        # ------------------------------------------------------------------
        # Family 1 — Market State
        # ------------------------------------------------------------------
        best_bid = ob.best_bid
        best_ask = ob.best_ask
        mid_price = (best_bid + best_ask) / Decimal("2")
        spread = best_ask - best_bid

        if spread <= Decimal("0.10"):
            implied_probability = mid_price
        else:
            implied_probability = ob.last_trade_price if ob.last_trade_price is not None else mid_price

        spread_bps = (spread / mid_price * Decimal("10000")) if mid_price != Decimal("0") else Decimal("0")

        time_to_close_seconds = (self.market_close_ts - captured_at).total_seconds()
        time_since_open_seconds = (captured_at - self.market_open_ts).total_seconds()

        book_depth_bid_5tick = ob.bids_depth_5tick
        book_depth_ask_5tick = ob.asks_depth_5tick

        time_since_last_trade = (
            (captured_at - ob.last_trade_ts).total_seconds()
            if ob.last_trade_ts is not None
            else 0.0
        )
        time_since_last_price_change = (
            (captured_at - ob.last_price_change_ts).total_seconds()
            if ob.last_price_change_ts is not None
            else 0.0
        )

        # ------------------------------------------------------------------
        # Family 2 — Microstructure
        # ------------------------------------------------------------------
        depth_bid = book_depth_bid_5tick
        depth_ask = book_depth_ask_5tick
        order_book_imbalance = (depth_bid - depth_ask) / (depth_bid + depth_ask + Decimal("1e-9"))

        # Flow imbalance from trade tape
        now_ts = captured_at
        buy_vol_1m = Decimal("0")
        sell_vol_1m = Decimal("0")
        buy_vol_5m = Decimal("0")
        sell_vol_5m = Decimal("0")
        total_vol_5m = Decimal("0")
        buy_count_1m = 0
        total_count_1m = 0
        buy_vol_all = Decimal("0")
        sell_vol_all = Decimal("0")

        for trade in self._trade_tape:
            age = (now_ts - trade.ts).total_seconds()
            if age <= 60.0:
                if trade.side == "BUY":
                    buy_vol_1m += trade.size
                    buy_count_1m += 1
                else:
                    sell_vol_1m += trade.size
                total_count_1m += 1
            if age <= 300.0:
                if trade.side == "BUY":
                    buy_vol_5m += trade.size
                else:
                    sell_vol_5m += trade.size
                total_vol_5m += trade.size
            buy_vol_all += trade.size if trade.side == "BUY" else Decimal("0")
            sell_vol_all += trade.size if trade.side == "SELL" else Decimal("0")

        trade_flow_imbalance_1m = buy_vol_1m - sell_vol_1m
        trade_flow_imbalance_5m = buy_vol_5m - sell_vol_5m

        total_tape_vol = buy_vol_all + sell_vol_all
        if total_tape_vol > Decimal("0") and total_vol_5m >= Decimal("0"):
            last_5min_volume_share = total_vol_5m / total_tape_vol
        else:
            last_5min_volume_share = Decimal("0")

        aggressor_buy_fraction_1m = (
            Decimal(str(buy_count_1m)) / Decimal(str(total_count_1m))
            if total_count_1m > 0
            else Decimal("0")
        )

        vpin_denominator = total_tape_vol + Decimal("1e-9")
        vpin_proxy = abs(buy_vol_all - sell_vol_all) / vpin_denominator

        # Reward config
        reward_eligible = reward_cfg.eligible
        reward_max_spread = reward_cfg.max_spread
        reward_min_size = reward_cfg.min_size

        # ------------------------------------------------------------------
        # Family 3 — Probabilistic (BTC-derived)
        # ------------------------------------------------------------------

        # Distance to hour open (log return)
        try:
            btc_price_f = float(btc_price)
            hour_open_f = float(hour_open)
            if btc_price_f > 0 and hour_open_f > 0:
                btc_distance_to_open = Decimal(str(math.log(btc_price_f / hour_open_f)))
            else:
                btc_distance_to_open = Decimal("0")
        except (ValueError, ZeroDivisionError):
            btc_distance_to_open = Decimal("0")

        # Realized volatility: sum of squared log-returns over N most-recent bars
        def _rv(n_bars: int) -> Decimal:
            """Sum of squared log-returns over last ``n_bars`` 1-minute klines."""
            if len(klines) < n_bars + 1:
                return Decimal("0")
            relevant = klines[-(n_bars + 1):]
            total = 0.0
            for i in range(1, len(relevant)):
                c_prev = float(relevant[i - 1].close)
                c_curr = float(relevant[i].close)
                if c_prev > 0 and c_curr > 0:
                    lr = math.log(c_curr / c_prev)
                    total += lr * lr
            return Decimal(str(total))

        btc_rv_1m = _rv(1)
        btc_rv_5m = _rv(5)
        btc_rv_15m = _rv(15)

        # 5-minute momentum: log(close[-1] / close[-6])
        if len(klines) >= 6:
            try:
                c_last = float(klines[-1].close)
                c_6ago = float(klines[-6].close)
                btc_momentum_5m_f = math.log(c_last / c_6ago) if c_last > 0 and c_6ago > 0 else 0.0
            except (ValueError, ZeroDivisionError):
                btc_momentum_5m_f = 0.0
        else:
            btc_momentum_5m_f = 0.0
        btc_momentum_5m = Decimal(str(btc_momentum_5m_f))

        # Sign persistence: fraction of last 5 kline log-returns that are positive
        if len(klines) >= 2:
            n_last = min(5, len(klines) - 1)
            positive_count = 0
            for i in range(len(klines) - n_last, len(klines)):
                c_prev = float(klines[i - 1].close)
                c_curr = float(klines[i].close)
                if c_prev > 0 and c_curr > 0:
                    if math.log(c_curr / c_prev) > 0:
                        positive_count += 1
            btc_sign_persistence_5m_f = positive_count / n_last if n_last >= 2 else 0.0
        else:
            btc_sign_persistence_5m_f = 0.0
        btc_sign_persistence_5m = Decimal(str(btc_sign_persistence_5m_f))

        btc_funding_rate = premium_index.last_funding_rate
        btc_basis_proxy = (
            (premium_index.mark_price - premium_index.index_price) / premium_index.index_price
            if premium_index.index_price != Decimal("0")
            else Decimal("0")
        )

        # ------------------------------------------------------------------
        # Family 4 — Regime (with minimum-hold filter)
        # ------------------------------------------------------------------
        btc_rv_1m_f = float(btc_rv_1m)
        btc_rv_5m_f = float(btc_rv_5m)
        vpin_f = float(vpin_proxy)

        # Raw regime computations
        if btc_rv_1m_f < 0.0001:
            raw_vol_regime = "low"
        elif btc_rv_1m_f > 0.001:
            raw_vol_regime = "high"
        else:
            raw_vol_regime = "medium"

        persistence_f = btc_sign_persistence_5m_f
        if persistence_f > 0.7:
            raw_trend_regime = "trending"
        elif persistence_f < 0.3:
            raw_trend_regime = "mean_reverting"
        else:
            raw_trend_regime = "neutral"

        if vpin_f < 0.2:
            raw_toxicity_regime = "low"
        elif vpin_f > 0.4:
            raw_toxicity_regime = "high"
        else:
            raw_toxicity_regime = "medium"

        # Spread regime: compare vs rolling median of _spread_history
        self._spread_history.append(spread)
        if len(self._spread_history) >= 3:
            sorted_spreads = sorted(self._spread_history)
            n = len(sorted_spreads)
            median_spread = (
                sorted_spreads[n // 2]
                if n % 2 == 1
                else (sorted_spreads[n // 2 - 1] + sorted_spreads[n // 2]) / Decimal("2")
            )
            if spread < median_spread * Decimal("0.8"):
                raw_spread_regime = "tight"
            elif spread > median_spread * Decimal("1.2"):
                raw_spread_regime = "wide"
            else:
                raw_spread_regime = "normal"
        else:
            # Cold start: no history yet
            raw_spread_regime = None

        # Apply minimum-hold filter to volatile regimes
        def _apply_hold_filter(family: str, raw_label: Optional[str]) -> Optional[str]:
            """Return the filtered (stable) label for a regime family."""
            if raw_label is None:
                # Cold start: return current value or None
                return self._current_regimes[family]
            buf = self._regime_hold[family]
            buf.append(raw_label)
            # Only update if last 3 are all the same new label
            if len(buf) == 3 and all(x == raw_label for x in buf):
                self._current_regimes[family] = raw_label
            return self._current_regimes[family]

        vol_regime_filtered = _apply_hold_filter("vol_regime", raw_vol_regime)
        trend_regime_filtered = _apply_hold_filter("trend_regime", raw_trend_regime)
        toxicity_regime_filtered = _apply_hold_filter("toxicity_regime", raw_toxicity_regime)
        spread_regime_filtered = _apply_hold_filter("spread_regime", raw_spread_regime)

        # Fall back to defaults for cold start
        vol_regime = vol_regime_filtered or raw_vol_regime
        trend_regime = trend_regime_filtered or raw_trend_regime
        toxicity_regime = toxicity_regime_filtered or raw_toxicity_regime
        spread_regime = spread_regime_filtered or "normal"

        # Non-volatile regime features (no hold filter needed)
        if time_since_open_seconds < 1200:
            time_bucket = "early"
        elif time_since_open_seconds < 2400:
            time_bucket = "mid"
        else:
            time_bucket = "late"

        near_close_flag = time_to_close_seconds <= 600

        # Liquidity score: depth_bid / (spread * btc_rv_5m + 1e-9), normalized to 0-1
        raw_liq = float(depth_bid) / (float(spread) * btc_rv_5m_f + 1e-9)
        self._liq_history.append(raw_liq)
        if len(self._liq_history) >= 2:
            liq_min = min(self._liq_history)
            liq_max = max(self._liq_history)
            liq_range = liq_max - liq_min
            if liq_range > 0:
                liquidity_score = Decimal(str((raw_liq - liq_min) / liq_range))
            else:
                liquidity_score = Decimal("0.5")
        else:
            liquidity_score = Decimal("0.5")

        # Competitive pressure: 1 / (spread_bps + 1e-9), normalized
        # Use raw value / 1000 if no history is available; otherwise min-max from history
        raw_cp = float(Decimal("1") / (spread_bps + Decimal("1e-9")))
        competitive_pressure = Decimal(str(raw_cp / 1000.0))

        # ------------------------------------------------------------------
        # Staleness flag
        # ------------------------------------------------------------------
        clob_age = (captured_at - ob.received_at).total_seconds()
        binance_ts = self._binance.source_timestamp
        binance_age = (
            (captured_at - binance_ts).total_seconds()
            if binance_ts is not None
            else 0.0
        )
        data_staleness_flag = clob_age > 30 or binance_age > 30

        # ------------------------------------------------------------------
        # Assemble FeatureSnapshot
        # ------------------------------------------------------------------
        return FeatureSnapshot(
            market_id=self.market_id,
            token_id=self.token_id,
            captured_at=captured_at,
            time_to_close_seconds=time_to_close_seconds,
            time_since_open_seconds=time_since_open_seconds,
            # Family 1
            mid_price=mid_price,
            implied_probability=implied_probability,
            spread=spread,
            spread_bps=spread_bps,
            book_depth_bid_5tick=book_depth_bid_5tick,
            book_depth_ask_5tick=book_depth_ask_5tick,
            time_since_last_trade=time_since_last_trade,
            time_since_last_price_change=time_since_last_price_change,
            # Family 2
            order_book_imbalance=order_book_imbalance,
            trade_flow_imbalance_1m=trade_flow_imbalance_1m,
            trade_flow_imbalance_5m=trade_flow_imbalance_5m,
            last_5min_volume_share=last_5min_volume_share,
            aggressor_buy_fraction_1m=aggressor_buy_fraction_1m,
            vpin_proxy=vpin_proxy,
            fee_rate_current=fee_rate,
            reward_eligible=reward_eligible,
            reward_max_spread=reward_max_spread,
            reward_min_size=reward_min_size,
            # Family 3
            btc_distance_to_open=btc_distance_to_open,
            btc_rv_1m=btc_rv_1m,
            btc_rv_5m=btc_rv_5m,
            btc_rv_15m=btc_rv_15m,
            btc_momentum_5m=btc_momentum_5m,
            btc_sign_persistence_5m=btc_sign_persistence_5m,
            btc_funding_rate=btc_funding_rate,
            btc_basis_proxy=btc_basis_proxy,
            # Family 4
            vol_regime=vol_regime,
            trend_regime=trend_regime,
            time_bucket=time_bucket,
            near_close_flag=near_close_flag,
            toxicity_regime=toxicity_regime,
            spread_regime=spread_regime,
            liquidity_score=liquidity_score,
            competitive_pressure=competitive_pressure,
            # Quality
            data_staleness_flag=data_staleness_flag,
        )
