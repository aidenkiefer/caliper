from __future__ import annotations

import math
import statistics
from datetime import datetime
from decimal import Decimal

import pytest

from services.evaluation.metrics import _daily_pnl, _max_drawdown, compute_metrics
from services.evaluation.regime_matrix import compute_regime_metrics

PERIOD_START = datetime(2026, 3, 1, 0, 0, 0)
PERIOD_END = datetime(2026, 3, 31, 0, 0, 0)
STRAT_ID = "test-strategy"
TOLERANCE = Decimal("0.001")


class MockSnapshot:
    def __init__(
        self,
        vol_regime: str = "medium",
        toxicity_regime: str = "low",
        near_close_flag: bool = False,
        time_bucket: str = "mid",
        spread_regime: str = "normal",
    ):
        self.vol_regime = vol_regime
        self.toxicity_regime = toxicity_regime
        self.near_close_flag = near_close_flag
        self.time_bucket = time_bucket
        self.spread_regime = spread_regime


def _make_metrics(pnl_series):
    return compute_metrics(
        strategy_id=STRAT_ID,
        pnl_series=pnl_series,
        fills=[],
        period_start=PERIOD_START,
        period_end=PERIOD_END,
    )


# ---------------------------------------------------------------------------
# Sharpe ratio tests
# ---------------------------------------------------------------------------

def test_sharpe_positive_pnl_series():
    """720 hours all +1 → total daily PnL = 24/day, 30 days. Sharpe > 0."""
    pnl_series = [Decimal("1")] * 720
    metrics = _make_metrics(pnl_series)
    assert metrics.sharpe_ratio > Decimal("0")


def test_sharpe_zero_pnl_series():
    """720 hours all 0 → Sharpe == 0 (no variance)."""
    pnl_series = [Decimal("0")] * 720
    metrics = _make_metrics(pnl_series)
    assert metrics.sharpe_ratio == Decimal("0")


def test_sharpe_mixed_pnl_known_value():
    """
    30 daily values alternating +2 and -1.
    Each day = 24 hours at the same hourly rate.
    Verify Sharpe ≈ mean / std * sqrt(252).
    """
    # Build 720 hourly values: 15 days of +2/24 per hour, 15 days of -1/24
    # Actually we want daily PnL to alternate +2, -1 so we make 24-hour blocks
    hourly = []
    for day in range(30):
        value = Decimal("2") if day % 2 == 0 else Decimal("-1")
        # spread daily value across 24 hours
        per_hour = value / Decimal("24")
        hourly.extend([per_hour] * 24)

    metrics = _make_metrics(hourly)

    # Recompute expected Sharpe from daily series using Decimal arithmetic
    daily = [Decimal("2") if i % 2 == 0 else Decimal("-1") for i in range(30)]
    mean_d = statistics.mean(daily)
    std_d = statistics.stdev(daily)
    expected_sharpe = (mean_d - Decimal("0")) / std_d * Decimal(str(math.sqrt(252)))

    assert abs(metrics.sharpe_ratio - expected_sharpe) <= TOLERANCE


def test_sharpe_confidence_low_under_20_days():
    """AC-7: 19 daily values (456 hourly) → sharpe_confidence == 'low', data_points == 19."""
    pnl_series = [Decimal("1")] * (19 * 24)
    metrics = _make_metrics(pnl_series)
    assert metrics.sharpe_confidence == "low"
    assert metrics.data_points == 19


def test_sharpe_confidence_high_over_60_days():
    """61 daily values (1464 hourly) → sharpe_confidence == 'high'."""
    pnl_series = [Decimal("1")] * (61 * 24)
    metrics = _make_metrics(pnl_series)
    assert metrics.sharpe_confidence == "high"


# ---------------------------------------------------------------------------
# Sortino ratio test
# ---------------------------------------------------------------------------

def test_sortino_ignores_positive_returns():
    """
    Half days +5, half days -1 per day (spread across 24h).
    Sortino should be > Sharpe because downside std < overall std.
    """
    hourly = []
    for day in range(30):
        value = Decimal("5") if day % 2 == 0 else Decimal("-1")
        per_hour = value / Decimal("24")
        hourly.extend([per_hour] * 24)

    metrics = _make_metrics(hourly)
    assert metrics.sortino_ratio > metrics.sharpe_ratio


# ---------------------------------------------------------------------------
# Calmar ratio test
# ---------------------------------------------------------------------------

def test_calmar_known_drawdown():
    """
    pnl_series = [10]*24 + [-5]*24 + [3]*24
    Cumulative: rises to 240, falls to 120. Max drawdown = 120.
    Total PnL = 240 - 120 + 72 = 192.
    Calmar = 192 / 120 = 1.6
    """
    pnl_series = (
        [Decimal("10")] * 24
        + [Decimal("-5")] * 24
        + [Decimal("3")] * 24
    )
    metrics = _make_metrics(pnl_series)
    assert abs(metrics.calmar_ratio - Decimal("1.6")) <= TOLERANCE


# ---------------------------------------------------------------------------
# Max drawdown helper tests
# ---------------------------------------------------------------------------

def test_max_drawdown_simple_series():
    """[10, -5, -3, 0, 8] → cumulative [10, 5, 2, 2, 10]. Drawdown = 8."""
    series = [Decimal("10"), Decimal("-5"), Decimal("-3"), Decimal("0"), Decimal("8")]
    dd, _ = _max_drawdown(series)
    assert dd == Decimal("8")


def test_max_drawdown_duration_hours():
    """[10, -1, -1, -1, 5] → cumulative [10, 9, 8, 7, 12]. Below peak for 3 hours."""
    series = [Decimal("10"), Decimal("-1"), Decimal("-1"), Decimal("-1"), Decimal("5")]
    _, duration = _max_drawdown(series)
    assert duration == 3


# ---------------------------------------------------------------------------
# Win rate tests
# ---------------------------------------------------------------------------

def test_win_rate_all_positive():
    """100 hours all +1 → win_rate == 1."""
    pnl_series = [Decimal("1")] * 100
    metrics = _make_metrics(pnl_series)
    assert metrics.win_rate == Decimal("1")


# ---------------------------------------------------------------------------
# Profit factor tests
# ---------------------------------------------------------------------------

def test_profit_factor_no_losses():
    """All positive hours → profit_factor == 9999 (sentinel for infinite)."""
    pnl_series = [Decimal("1")] * 100
    metrics = _make_metrics(pnl_series)
    assert metrics.profit_factor == Decimal("9999")


# ---------------------------------------------------------------------------
# Regime matrix test (AC-6)
# ---------------------------------------------------------------------------

def test_regime_metrics_partitions_correctly():
    """
    AC-6: 720 hourly PnL values split across 3 vol_regime labels.
    compute_regime_metrics returns 3 RegimeMetrics for vol_regime.
    sum(sample_hours) == 720.
    """
    pnl_series = [Decimal("1")] * 720

    # First 240 high, next 240 medium, last 240 low
    snapshots = (
        [MockSnapshot(vol_regime="high")] * 240
        + [MockSnapshot(vol_regime="medium")] * 240
        + [MockSnapshot(vol_regime="low")] * 240
    )

    regime_metrics = compute_regime_metrics(
        strategy_id=STRAT_ID,
        pnl_series=pnl_series,
        fills=[],
        snapshots=snapshots,
        period_start=PERIOD_START,
        period_end=PERIOD_END,
    )

    vol_regime_metrics = [rm for rm in regime_metrics if rm.regime.startswith("vol_regime=")]
    assert len(vol_regime_metrics) == 3
    assert sum(rm.sample_hours for rm in vol_regime_metrics) == 720
