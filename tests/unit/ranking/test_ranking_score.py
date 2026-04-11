from __future__ import annotations

from decimal import Decimal

from services.ranking.score import RankingWeights, composite_score


def test_composite_score_caps_negative_edge() -> None:
    assert composite_score(ev_adj=Decimal("-0.01"), sigma=Decimal("1"), feasibility=0.8, confidence=0.9) == 0.0


def test_composite_score_matches_weighted_formula() -> None:
    weights = RankingWeights(ev=0.4, risk=0.3, liquidity=0.2, confidence=0.1)
    score = composite_score(
        ev_adj=Decimal("0.25"),
        sigma=Decimal("2"),
        feasibility=0.5,
        confidence=0.8,
        weights=weights,
    )
    expected = 0.4 * 0.25 + 0.3 * (0.25 / 2.0) + 0.2 * 0.5 + 0.1 * 0.8
    assert abs(score - expected) < 1e-12


def test_composite_score_includes_reward_density() -> None:
    from services.ranking.score import RankingWeights, composite_score
    weights = RankingWeights()
    score_with = composite_score(
        ev_adj=Decimal("0.25"),
        sigma=Decimal("2"),
        feasibility=0.5,
        confidence=0.8,
        reward_density=1.0,
        weights=weights,
    )
    score_without = composite_score(
        ev_adj=Decimal("0.25"),
        sigma=Decimal("2"),
        feasibility=0.5,
        confidence=0.8,
        reward_density=0.0,
        weights=weights,
    )
    assert score_with > score_without

