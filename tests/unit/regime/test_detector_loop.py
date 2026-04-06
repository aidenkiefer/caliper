from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from services.regime.classifiers.threshold import ThresholdRegimeClassifier
from services.regime.detector import RegimeDetector, RegimeDetectorConfig


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


def test_detector_min_hold_requires_three_ticks_for_non_safety_switches() -> None:
    threshold = ThresholdRegimeClassifier()
    detector = RegimeDetector(
        threshold=threshold,
        hmm=None,
        store=None,
        config=RegimeDetectorConfig(min_hold_ticks=3),
    )

    # Start in R1
    s_r1 = Snap()
    st1 = detector.detect(s_r1)
    assert st1.primary_regime == "R1"

    # Propose R2 (choppy) twice: should stay in R1
    s_r2 = Snap(btc_rv_5m=Decimal("0.01"), btc_sign_persistence_5m=Decimal("0.1"))
    st2 = detector.detect(s_r2)
    st3 = detector.detect(s_r2)
    assert st2.primary_regime == "R1"
    assert st3.primary_regime == "R1"

    # Third tick flips
    st4 = detector.detect(s_r2)
    assert st4.primary_regime == "R2"


def test_detector_safety_overrides_apply_immediately() -> None:
    detector = RegimeDetector(config=RegimeDetectorConfig(min_hold_ticks=3))
    s_r1 = Snap()
    assert detector.detect(s_r1).primary_regime == "R1"

    # R3 is safety override, should switch immediately
    s_r3 = Snap(near_close_flag=True)
    assert detector.detect(s_r3).primary_regime == "R3"

