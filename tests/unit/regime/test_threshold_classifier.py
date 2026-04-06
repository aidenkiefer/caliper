from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from services.regime.classifiers.threshold import ThresholdRegimeClassifier
from services.regime.schemas import ConnectivityMetrics


@dataclass
class Snap:
    spread_bps: Decimal = Decimal("10")
    book_depth_bid_5tick: Decimal = Decimal("100")
    book_depth_ask_5tick: Decimal = Decimal("100")
    time_to_close_seconds: float = 3600.0
    near_close_flag: bool = False
    toxicity_regime: str = "low"
    vpin_proxy: Decimal = Decimal("0.1")
    btc_rv_5m: Decimal = Decimal("0.0001")
    btc_sign_persistence_5m: Decimal = Decimal("0.9")


def test_threshold_r4_connectivity_override() -> None:
    clf = ThresholdRegimeClassifier()
    snap = Snap()
    c = ConnectivityMetrics(api_latency_ms=2500.0, heartbeat_miss_count=0)
    assert clf.classify(snap, connectivity=c) == "R4"


def test_threshold_r5_dead_market_by_spread() -> None:
    clf = ThresholdRegimeClassifier()
    snap = Snap(spread_bps=Decimal("600"))
    assert clf.classify(snap) == "R5"


def test_threshold_r5_dead_market_by_depth() -> None:
    clf = ThresholdRegimeClassifier()
    snap = Snap(book_depth_bid_5tick=Decimal("5"), book_depth_ask_5tick=Decimal("50"))
    assert clf.classify(snap) == "R5"


def test_threshold_r3_near_close_flag() -> None:
    clf = ThresholdRegimeClassifier()
    snap = Snap(near_close_flag=True)
    assert clf.classify(snap) == "R3"


def test_threshold_r3_toxicity_regime_high() -> None:
    clf = ThresholdRegimeClassifier()
    snap = Snap(toxicity_regime="high")
    assert clf.classify(snap) == "R3"


def test_threshold_r3_vpin_threshold() -> None:
    clf = ThresholdRegimeClassifier()
    snap = Snap(vpin_proxy=Decimal("0.90"))
    assert clf.classify(snap) == "R3"


def test_threshold_r2_choppy() -> None:
    clf = ThresholdRegimeClassifier()
    snap = Snap(btc_rv_5m=Decimal("0.01"), btc_sign_persistence_5m=Decimal("0.1"))
    assert clf.classify(snap) == "R2"


def test_threshold_r1_favorable_default() -> None:
    clf = ThresholdRegimeClassifier()
    snap = Snap()
    assert clf.classify(snap) == "R1"

