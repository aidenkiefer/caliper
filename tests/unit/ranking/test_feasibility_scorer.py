from __future__ import annotations

from decimal import Decimal

from services.ranking.feasibility import FeasibilityScorer, FeasibilityScorerConfig
from services.ranking.schemas import CandidateMarket


def _candidate(**kwargs):
    data = {
        "market_id": "cand-1",
        "condition_id": "cond-1",
        "token_id": "token-1",
        "side": "YES",
        "spread_bps": Decimal("10"),
        "book_depth_bid_5tick": Decimal("100"),
        "book_depth_ask_5tick": Decimal("100"),
        "recent_trade_intensity": Decimal("0.9"),
        "queue_position_proxy": Decimal("0.1"),
        "metadata": {"btc_rv_5m": 0.001},
    }
    data.update(kwargs)
    return CandidateMarket(**data)


def test_feasibility_score_is_bounded_and_exclusion_triggers() -> None:
    scorer = FeasibilityScorer()
    report = scorer.score(_candidate())
    assert 0.0 <= report.feasibility_score <= 1.0
    assert report.exclude is False


def test_feasibility_below_threshold_excludes() -> None:
    scorer = FeasibilityScorer(FeasibilityScorerConfig(exclusion_threshold=0.2))
    report = scorer.score(
        _candidate(
            book_depth_bid_5tick=Decimal("0"),
            book_depth_ask_5tick=Decimal("0"),
            recent_trade_intensity=Decimal("0"),
            queue_position_proxy=Decimal("1"),
            metadata={"btc_rv_5m": 0.01},
        )
    )
    assert report.feasibility_score == 0.0
    assert report.exclude is True

