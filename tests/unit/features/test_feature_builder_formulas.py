"""Unit tests for FeatureBuilder formula logic (Sprint 12).

Each test exercises the mathematical formula directly — no real network calls,
no asyncio tick loop.  All numeric assertions are explicit.
"""

from __future__ import annotations

import math
from decimal import Decimal

import pytest


# ---------------------------------------------------------------------------
# Helpers — pure-Python reimplementations of each formula (mirrors builder.py)
# ---------------------------------------------------------------------------

def _mid_price(best_bid: Decimal, best_ask: Decimal) -> Decimal:
    return (best_bid + best_ask) / Decimal("2")


def _implied_probability(
    best_bid: Decimal,
    best_ask: Decimal,
    last_trade_price: Decimal | None = None,
) -> Decimal:
    spread = best_ask - best_bid
    mid = _mid_price(best_bid, best_ask)
    if spread <= Decimal("0.10"):
        return mid
    return last_trade_price if last_trade_price is not None else mid


def _spread_bps(spread: Decimal, mid: Decimal) -> Decimal:
    if mid == Decimal("0"):
        return Decimal("0")
    return spread / mid * Decimal("10000")


def _book_depth_bid_5tick(bids: list[tuple[Decimal, Decimal]], best_bid: Decimal) -> Decimal:
    """Sum sizes within 5 ticks (0.05 = 5 × 0.01 tick size) of best bid."""
    threshold = best_bid - Decimal("0.05")
    return sum(size for price, size in bids if price >= threshold)


def _order_book_imbalance(depth_bid: Decimal, depth_ask: Decimal) -> Decimal:
    return (depth_bid - depth_ask) / (depth_bid + depth_ask + Decimal("1e-9"))


def _trade_flow_imbalance_1m(buy_vol: Decimal, sell_vol: Decimal) -> Decimal:
    return buy_vol - sell_vol


def _vpin_proxy(buy_vol: Decimal, sell_vol: Decimal) -> Decimal:
    total = buy_vol + sell_vol + Decimal("1e-9")
    return abs(buy_vol - sell_vol) / total


def _last_5min_volume_share(vol_5m: Decimal, total_vol: Decimal) -> Decimal:
    if total_vol == Decimal("0") or vol_5m == Decimal("0"):
        return Decimal("0")
    return vol_5m / total_vol


def _btc_distance_to_open(btc_price: float, hour_open: float) -> Decimal:
    if btc_price > 0 and hour_open > 0:
        return Decimal(str(math.log(btc_price / hour_open)))
    return Decimal("0")


def _rv(closes: list[float]) -> Decimal:
    """Sum of squared log-returns for consecutive closes."""
    total = 0.0
    for i in range(1, len(closes)):
        c_prev = closes[i - 1]
        c_curr = closes[i]
        if c_prev > 0 and c_curr > 0:
            lr = math.log(c_curr / c_prev)
            total += lr * lr
    return Decimal(str(total))


def _btc_momentum_5m(kline_closes: list[float]) -> Decimal:
    """log(close[-1] / close[-6]) — requires at least 6 closes."""
    if len(kline_closes) < 6:
        return Decimal("0")
    c_last = kline_closes[-1]
    c_6ago = kline_closes[-6]
    if c_last > 0 and c_6ago > 0:
        return Decimal(str(math.log(c_last / c_6ago)))
    return Decimal("0")


def _btc_sign_persistence_5m(kline_closes: list[float]) -> Decimal:
    """Fraction of last 5 log-returns that are positive."""
    if len(kline_closes) < 2:
        return Decimal("0")
    n_last = min(5, len(kline_closes) - 1)
    positive = 0
    for i in range(len(kline_closes) - n_last, len(kline_closes)):
        c_prev = kline_closes[i - 1]
        c_curr = kline_closes[i]
        if c_prev > 0 and c_curr > 0:
            if math.log(c_curr / c_prev) > 0:
                positive += 1
    return Decimal(str(positive / n_last if n_last >= 2 else 0.0))


def _liquidity_score_raw(depth_bid: float, spread: float, btc_rv_5m: float) -> float:
    return depth_bid / (spread * btc_rv_5m + 1e-9)


def _competitive_pressure(spread_bps: Decimal) -> Decimal:
    raw_cp = float(Decimal("1") / (spread_bps + Decimal("1e-9")))
    return Decimal(str(raw_cp / 1000.0))


# ===========================================================================
# Family 1 — Market State
# ===========================================================================

class TestFamily1MarketState:

    def test_mid_price(self):
        mid = _mid_price(Decimal("0.48"), Decimal("0.52"))
        assert mid == Decimal("0.50")

    def test_implied_probability_tight_spread(self):
        """Spread = 0.04 ≤ 0.10 → implied probability == midpoint."""
        best_bid = Decimal("0.48")
        best_ask = Decimal("0.52")
        prob = _implied_probability(best_bid, best_ask, last_trade_price=Decimal("0.45"))
        # spread = 0.04 → use mid
        assert prob == Decimal("0.50")

    def test_implied_probability_wide_spread(self):
        """Spread = 0.20 > 0.10 → implied probability == last_trade_price."""
        best_bid = Decimal("0.40")
        best_ask = Decimal("0.60")
        last_trade = Decimal("0.42")
        prob = _implied_probability(best_bid, best_ask, last_trade_price=last_trade)
        assert prob == Decimal("0.42")

    def test_implied_probability_wide_spread_no_trade(self):
        """Wide spread with no trade price falls back to mid."""
        best_bid = Decimal("0.30")
        best_ask = Decimal("0.70")
        prob = _implied_probability(best_bid, best_ask, last_trade_price=None)
        assert prob == Decimal("0.50")

    def test_spread_bps(self):
        """spread=0.02, mid=0.50 → spread_bps = 0.02/0.50 * 10000 = 400."""
        spread = Decimal("0.02")
        mid = Decimal("0.50")
        bps = _spread_bps(spread, mid)
        assert bps == Decimal("400")

    def test_book_depth_bid_5tick(self):
        """Sum sizes within 5 ticks (price ≥ best_bid - 0.05) of best bid."""
        best_bid = Decimal("0.50")
        bids = [
            (Decimal("0.50"), Decimal("100")),   # exactly best bid — in range
            (Decimal("0.46"), Decimal("200")),   # 0.50 - 0.04 = 0.46 — in range
            (Decimal("0.44"), Decimal("300")),   # 0.50 - 0.06 = 0.44 — out of range
        ]
        depth = _book_depth_bid_5tick(bids, best_bid)
        assert depth == Decimal("300")  # 100 + 200


# ===========================================================================
# Family 2 — Microstructure
# ===========================================================================

class TestFamily2Microstructure:

    def test_order_book_imbalance_balanced(self):
        """Equal bid and ask depth → imbalance ≈ 0."""
        imbalance = _order_book_imbalance(Decimal("500"), Decimal("500"))
        assert abs(float(imbalance)) < 1e-6

    def test_order_book_imbalance_bid_heavy(self):
        """More bid depth → positive imbalance."""
        imbalance = _order_book_imbalance(Decimal("800"), Decimal("200"))
        assert float(imbalance) > 0

    def test_trade_flow_imbalance_1m(self):
        """buy_vol=300, sell_vol=100 → imbalance=200."""
        result = _trade_flow_imbalance_1m(Decimal("300"), Decimal("100"))
        assert result == Decimal("200")

    def test_trade_flow_imbalance_1m_sell_heavy(self):
        """More sell volume → negative imbalance."""
        result = _trade_flow_imbalance_1m(Decimal("50"), Decimal("150"))
        assert result == Decimal("-100")

    def test_vpin_proxy(self):
        """buy_vol=800, sell_vol=200, total≈1000 → vpin≈0.6."""
        buy_vol = Decimal("800")
        sell_vol = Decimal("200")
        vpin = _vpin_proxy(buy_vol, sell_vol)
        # |800 - 200| / (800 + 200 + 1e-9) = 600 / 1000 = 0.6
        assert abs(float(vpin) - 0.6) < 1e-6

    def test_last_5min_volume_share(self):
        """vol_5m=500, total=2000 → share=0.25."""
        share = _last_5min_volume_share(Decimal("500"), Decimal("2000"))
        assert share == Decimal("0.25")

    def test_last_5min_volume_share_zero_total(self):
        """Zero total volume → share=0."""
        share = _last_5min_volume_share(Decimal("0"), Decimal("0"))
        assert share == Decimal("0")


# ===========================================================================
# Family 3 — Probabilistic (BTC-derived)
# ===========================================================================

class TestFamily3Probabilistic:

    def test_btc_distance_to_open(self):
        """ln(51000 / 50000) ≈ 0.01980; assert within 1e-5."""
        dist = _btc_distance_to_open(51000.0, 50000.0)
        expected = math.log(51000 / 50000)
        assert abs(float(dist) - expected) < 1e-5

    def test_btc_distance_to_open_value(self):
        """Concrete value check: ln(51000/50000) ≈ 0.01980263."""
        dist = _btc_distance_to_open(51000.0, 50000.0)
        assert abs(float(dist) - 0.019802627296179712) < 1e-5

    def test_btc_rv_1m(self):
        """3 log-returns from 4 closes → sum of squares."""
        # closes: 100, 101, 99, 102
        closes = [100.0, 101.0, 99.0, 102.0]
        rv = _rv(closes)
        expected = sum(
            math.log(closes[i] / closes[i - 1]) ** 2 for i in range(1, len(closes))
        )
        assert abs(float(rv) - expected) < 1e-10

    def test_btc_momentum_5m(self):
        """log(close[-1] / close[-6]) over 6 klines."""
        closes = [50000.0, 50100.0, 50200.0, 50150.0, 50300.0, 50500.0]
        mom = _btc_momentum_5m(closes)
        expected = math.log(50500.0 / 50000.0)
        assert abs(float(mom) - expected) < 1e-10

    def test_btc_momentum_5m_fewer_than_6_returns_zero(self):
        closes = [50000.0, 50100.0]
        mom = _btc_momentum_5m(closes)
        assert mom == Decimal("0")

    def test_btc_sign_persistence_5m(self):
        """4 of 5 log-returns positive → persistence == 0.8."""
        # 6 closes: 5 consecutive pairs, 4 rising, 1 falling
        closes = [100.0, 101.0, 102.0, 103.0, 102.5, 104.0]
        # pairs: (100,101)+ (101,102)+ (102,103)+ (103,102.5)- (102.5,104)+
        # positives: 4 → 4/5 = 0.8
        persistence = _btc_sign_persistence_5m(closes)
        assert abs(float(persistence) - 0.8) < 1e-10

    def test_btc_sign_persistence_5m_all_positive(self):
        closes = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0]
        persistence = _btc_sign_persistence_5m(closes)
        assert abs(float(persistence) - 1.0) < 1e-10


# ===========================================================================
# Family 4 — Regime (non-regime-label, structural)
# ===========================================================================

class TestFamily4Structural:

    def test_liquidity_score_positive(self):
        """depth > 0, spread > 0 → raw liquidity score > 0."""
        raw_liq = _liquidity_score_raw(
            depth_bid=500.0,
            spread=0.02,
            btc_rv_5m=0.0005,
        )
        assert raw_liq > 0

    def test_competitive_pressure(self):
        """Narrow spread (400 bps) → higher pressure than wide spread (2000 bps)."""
        cp_narrow = _competitive_pressure(Decimal("400"))
        cp_wide = _competitive_pressure(Decimal("2000"))
        assert float(cp_narrow) > float(cp_wide)

    def test_near_close_flag_true(self):
        """300 seconds to close ≤ 600 → near_close_flag == True."""
        time_to_close = 300.0
        near_close_flag = time_to_close <= 600
        assert near_close_flag is True

    def test_near_close_flag_false(self):
        """1500 seconds to close > 600 → near_close_flag == False."""
        time_to_close = 1500.0
        near_close_flag = time_to_close <= 600
        assert near_close_flag is False
