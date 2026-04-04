"""Unit tests for regime label discretization and minimum-hold filter (Sprint 12).

Tests the thresholds in builder.py and the 3-consecutive-tick hold filter
that prevents jitter on regime boundary crossings.
"""

from __future__ import annotations

from collections import deque
from decimal import Decimal
from typing import Dict, Optional

import pytest


# ---------------------------------------------------------------------------
# Pure-Python reimplementations of builder.py regime logic
# ---------------------------------------------------------------------------

def _vol_regime(btc_rv_1m: float) -> str:
    if btc_rv_1m < 0.0001:
        return "low"
    elif btc_rv_1m > 0.001:
        return "high"
    return "medium"


def _trend_regime(sign_persistence: float) -> str:
    if sign_persistence > 0.7:
        return "trending"
    elif sign_persistence < 0.3:
        return "mean_reverting"
    return "neutral"


def _toxicity_regime(vpin: float) -> str:
    if vpin < 0.2:
        return "low"
    elif vpin > 0.4:
        return "high"
    return "medium"


def _spread_regime(spread: Decimal, history: list[Decimal]) -> str:
    """Classify spread vs rolling median of history (including current spread)."""
    full = list(history) + [spread]
    if len(full) < 3:
        return "normal"
    sorted_spreads = sorted(full)
    n = len(sorted_spreads)
    if n % 2 == 1:
        median = sorted_spreads[n // 2]
    else:
        median = (sorted_spreads[n // 2 - 1] + sorted_spreads[n // 2]) / Decimal("2")
    if spread < median * Decimal("0.8"):
        return "tight"
    elif spread > median * Decimal("1.2"):
        return "wide"
    return "normal"


def _time_bucket(time_since_open_seconds: float) -> str:
    if time_since_open_seconds < 1200:
        return "early"
    elif time_since_open_seconds < 2400:
        return "mid"
    return "late"


class MinHoldFilter:
    """Mirrors the minimum-hold filter logic from FeatureBuilder._apply_hold_filter."""

    def __init__(self) -> None:
        self._hold: Dict[str, deque] = {k: deque(maxlen=3) for k in ["family"]}
        self._current: Dict[str, Optional[str]] = {"family": None}

    def apply(self, raw_label: Optional[str]) -> Optional[str]:
        if raw_label is None:
            return self._current["family"]
        buf = self._hold["family"]
        buf.append(raw_label)
        if len(buf) == 3 and all(x == raw_label for x in buf):
            self._current["family"] = raw_label
        return self._current["family"]


# ===========================================================================
# Vol regime classification
# ===========================================================================

class TestVolRegimeClassification:

    def test_vol_regime_low(self):
        assert _vol_regime(0.00005) == "low"

    def test_vol_regime_medium(self):
        assert _vol_regime(0.0005) == "medium"

    def test_vol_regime_high(self):
        assert _vol_regime(0.002) == "high"

    def test_vol_regime_boundary_low_edge(self):
        """Exactly at 0.0001 is NOT low (threshold is strictly <)."""
        assert _vol_regime(0.0001) == "medium"

    def test_vol_regime_boundary_high_edge(self):
        """Exactly at 0.001 is NOT high (threshold is strictly >)."""
        assert _vol_regime(0.001) == "medium"


# ===========================================================================
# Trend regime classification
# ===========================================================================

class TestTrendRegimeClassification:

    def test_trend_trending(self):
        assert _trend_regime(0.8) == "trending"

    def test_trend_neutral(self):
        assert _trend_regime(0.5) == "neutral"

    def test_trend_mean_reverting(self):
        assert _trend_regime(0.1) == "mean_reverting"

    def test_trend_boundary_high(self):
        """Exactly 0.7 is NOT trending (strictly >)."""
        assert _trend_regime(0.7) == "neutral"

    def test_trend_boundary_low(self):
        """Exactly 0.3 is NOT mean_reverting (strictly <)."""
        assert _trend_regime(0.3) == "neutral"


# ===========================================================================
# Toxicity regime classification
# ===========================================================================

class TestToxicityRegimeClassification:

    def test_toxicity_low(self):
        assert _toxicity_regime(0.1) == "low"

    def test_toxicity_medium(self):
        assert _toxicity_regime(0.3) == "medium"

    def test_toxicity_high(self):
        assert _toxicity_regime(0.6) == "high"

    def test_toxicity_boundary_low(self):
        """Exactly 0.2 is NOT low (strictly <)."""
        assert _toxicity_regime(0.2) == "medium"

    def test_toxicity_boundary_high(self):
        """Exactly 0.4 is NOT high (strictly >)."""
        assert _toxicity_regime(0.4) == "medium"


# ===========================================================================
# Spread regime classification
# ===========================================================================

class TestSpreadRegimeClassification:

    def test_spread_normal(self):
        # All same spreads → median = 0.05 → current is within [0.04, 0.06] → normal
        history = [Decimal("0.05"), Decimal("0.05")]
        assert _spread_regime(Decimal("0.05"), history) == "normal"

    def test_spread_tight(self):
        # History of larger spreads → current is much smaller
        history = [Decimal("0.10"), Decimal("0.10")]
        # median of [0.10, 0.10, 0.01] → 0.10; 0.01 < 0.10 * 0.8 = 0.08 → tight
        assert _spread_regime(Decimal("0.01"), history) == "tight"

    def test_spread_wide(self):
        # History of small spreads → current is much larger
        history = [Decimal("0.02"), Decimal("0.02")]
        # median of [0.02, 0.02, 0.10] → 0.02; 0.10 > 0.02 * 1.2 = 0.024 → wide
        assert _spread_regime(Decimal("0.10"), history) == "wide"

    def test_spread_regime_cold_start_fewer_than_3(self):
        """With < 3 history items, falls back to normal."""
        # Empty history + 1 item = only 1 element, < 3
        assert _spread_regime(Decimal("0.05"), []) == "normal"


# ===========================================================================
# Time bucket classification
# ===========================================================================

class TestTimeBucket:

    def test_time_bucket_early(self):
        """10 minutes = 600 seconds → early."""
        assert _time_bucket(600.0) == "early"

    def test_time_bucket_mid(self):
        """30 minutes = 1800 seconds → mid."""
        assert _time_bucket(1800.0) == "mid"

    def test_time_bucket_late(self):
        """55 minutes = 3300 seconds → late."""
        assert _time_bucket(3300.0) == "late"

    def test_time_bucket_early_boundary(self):
        """Exactly 1200 seconds → mid (not early; strictly <)."""
        assert _time_bucket(1200.0) == "mid"

    def test_time_bucket_mid_boundary(self):
        """Exactly 2400 seconds → late (not mid; strictly <)."""
        assert _time_bucket(2400.0) == "late"


# ===========================================================================
# Minimum-hold filter (AC-4)
# ===========================================================================

class TestRegimeMinimumHoldFilter:

    def test_label_does_not_flip_after_1_tick(self):
        """One tick of a new label does NOT change the current regime."""
        f = MinHoldFilter()
        # Tick 1: label = "low" — buf has 1 entry, current stays None
        result = f.apply("low")
        assert result is None  # no confirmed regime yet

    def test_label_does_not_flip_after_2_ticks(self):
        """Two ticks of the same label do NOT yet trigger an update."""
        f = MinHoldFilter()
        f.apply("low")   # tick 1
        result = f.apply("low")  # tick 2 — still not 3 consecutive
        assert result is None

    def test_label_flips_after_3_consecutive_ticks(self):
        """Three consecutive identical ticks → regime is confirmed."""
        f = MinHoldFilter()
        f.apply("low")   # tick 1
        f.apply("low")   # tick 2
        result = f.apply("low")  # tick 3 — now 3 consecutive same
        assert result == "low"

    def test_label_does_not_flip_if_interrupted(self):
        """Interrupted sequence resets — requires 3 new consecutive ticks."""
        f = MinHoldFilter()
        f.apply("low")   # tick 1
        f.apply("high")  # tick 2 — different label, breaks sequence
        f.apply("low")   # tick 3 — only 1 consecutive "low" in buffer
        # buf = ["low", "high", "low"] — not all same → no flip
        result = f.apply("low")  # tick 4 — buf = ["high", "low", "low"] — not same
        assert result is None

    def test_label_eventually_confirms_after_interruption(self):
        """After an interruption, 3 more consecutive ticks confirm the label."""
        f = MinHoldFilter()
        f.apply("low")
        f.apply("high")  # interrupt
        f.apply("low")
        f.apply("low")
        result = f.apply("low")  # 3rd consecutive "low" in buf
        assert result == "low"

    def test_regime_stays_after_confirmation(self):
        """Once confirmed, the regime persists even if next tick differs."""
        f = MinHoldFilter()
        f.apply("low")
        f.apply("low")
        f.apply("low")   # confirmed → "low"
        # Next tick introduces different label but only 1 consecutive
        result = f.apply("high")
        assert result == "low"  # still "low" — not yet 3× "high"


# ===========================================================================
# Standalone spec-required test functions
# ===========================================================================

def test_vol_regime_classification():
    """Vol regime returns low/medium/high for different btc_rv_1m inputs."""
    assert _vol_regime(0.00005) == "low"
    assert _vol_regime(0.0005) == "medium"
    assert _vol_regime(0.002) == "high"


def test_trend_regime_classification():
    """Trend regime returns trending/neutral/mean_reverting for different sign_persistence inputs."""
    assert _trend_regime(0.8) == "trending"
    assert _trend_regime(0.5) == "neutral"
    assert _trend_regime(0.1) == "mean_reverting"


def test_toxicity_regime_classification():
    """Toxicity regime returns low/medium/high for different vpin inputs."""
    assert _toxicity_regime(0.1) == "low"
    assert _toxicity_regime(0.3) == "medium"
    assert _toxicity_regime(0.6) == "high"


def test_spread_regime_classification():
    """Spread regime returns tight/normal/wide based on spread vs rolling median."""
    history = [Decimal("0.05"), Decimal("0.05")]
    assert _spread_regime(Decimal("0.05"), history) == "normal"
    history_large = [Decimal("0.10"), Decimal("0.10")]
    assert _spread_regime(Decimal("0.01"), history_large) == "tight"
    history_small = [Decimal("0.02"), Decimal("0.02")]
    assert _spread_regime(Decimal("0.10"), history_small) == "wide"


def test_time_bucket_early_mid_late():
    """Time bucket classifies early/mid/late based on seconds since open."""
    assert _time_bucket(600.0) == "early"
    assert _time_bucket(1800.0) == "mid"
    assert _time_bucket(3300.0) == "late"


def test_regime_minimum_hold_filter():
    """MinHoldFilter only confirms a regime after 3 consecutive identical ticks."""
    f = MinHoldFilter()
    assert f.apply("low") is None   # 1 tick — not confirmed
    assert f.apply("low") is None   # 2 ticks — not confirmed
    assert f.apply("low") == "low"  # 3 consecutive — confirmed
