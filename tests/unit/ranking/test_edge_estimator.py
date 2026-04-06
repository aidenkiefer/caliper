from __future__ import annotations

import math
from decimal import Decimal

from services.ranking.edge import EdgeEstimator, EdgeEstimatorConfig
from services.ranking.schemas import CandidateMarket


def _candidate(**kwargs):
    data = {
        "market_id": "cand-1",
        "condition_id": "cond-1",
        "token_id": "token-1",
        "side": "YES",
        "spread": Decimal("0.04"),
        "book_depth_bid_5tick": Decimal("100"),
        "book_depth_ask_5tick": Decimal("100"),
        "p_pm": Decimal("0.60"),
        "fee_rate_bps": Decimal("0"),
        "fees_enabled": True,
        "staleness_seconds": 0.0,
    }
    data.update(kwargs)
    return CandidateMarket(**data)


def test_edge_estimator_fallback_and_raw_ev() -> None:
    estimator = EdgeEstimator()
    edge = estimator.estimate(_candidate(p_hat=None), size=Decimal("0"))
    assert edge.low_confidence is True
    assert edge.p_hat == Decimal("0.5")
    assert edge.ev_raw == Decimal("-0.1")
    assert edge.ev_adj == Decimal("-0.12")


def test_edge_estimator_applies_staleness_decay() -> None:
    estimator = EdgeEstimator(EdgeEstimatorConfig(staleness_threshold_seconds=30.0, decay_rate=0.1))
    edge = estimator.estimate(
        _candidate(p_hat=Decimal("0.8"), p_pm=Decimal("0.5"), spread=Decimal("0.0")),
        size=Decimal("0"),
        staleness_seconds=60.0,
    )
    expected = 0.3 * math.exp(-0.1 * 30.0)
    assert math.isclose(float(edge.ev_adj), expected, rel_tol=1e-9, abs_tol=1e-9)
    assert math.isclose(edge.decay_factor, math.exp(-3.0), rel_tol=1e-9, abs_tol=1e-9)

