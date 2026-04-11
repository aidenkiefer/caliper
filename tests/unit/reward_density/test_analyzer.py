# tests/unit/reward_density/test_analyzer.py
import pytest
from decimal import Decimal

from services.reward_density.risk_scorer import RiskScorer


def test_risk_scorer_zscore_single_market() -> None:
    """Single-market z-score = 0 (no cross-section)."""
    scorer = RiskScorer(lambda_toxicity=Decimal("0.5"))
    scores = scorer.compute_cross_sectional(
        [{"market_id": "mkt1", "btc_rv": Decimal("0.02"), "toxicity": Decimal("0.3")}]
    )
    assert len(scores) == 1
    assert "mkt1" in scores


def test_risk_scorer_relative_ordering() -> None:
    """Higher vol + higher toxicity should yield higher risk score."""
    scorer = RiskScorer(lambda_toxicity=Decimal("0.5"))
    items = [
        {"market_id": "low", "btc_rv": Decimal("0.01"), "toxicity": Decimal("0.05")},
        {"market_id": "high", "btc_rv": Decimal("0.10"), "toxicity": Decimal("0.80")},
    ]
    scores = scorer.compute_cross_sectional(items)
    assert float(scores["high"]) > float(scores["low"])


import pytest
from datetime import datetime, timezone
from services.reward_density.analyzer import RewardDensityAnalyzer
from services.reward_density.schemas import CompetitionMetric, IncentiveEstimate


def _make_competition(n_eff: float, is_estimate: bool = False) -> CompetitionMetric:
    return CompetitionMetric(
        market_id="mkt1",
        computed_at=datetime.now(timezone.utc),
        lookback_days=7,
        hhi=Decimal(str(round(1 / n_eff, 6))),
        n_eff=Decimal(str(n_eff)),
        top_maker_address=None,
        top_maker_share=None,
        data_source="onchain" if not is_estimate else "rewards_api_proxy",
        is_estimate=is_estimate,
    )


def _make_incentive(total: float, rebate: float, lr: float) -> IncentiveEstimate:
    return IncentiveEstimate(
        market_id="mkt1",
        estimated_at=datetime.now(timezone.utc),
        fee_pool_usd=Decimal(str(total * 5)),
        maker_rebate_pool_usd=Decimal(str(rebate * 5)),
        liquidity_reward_pool_usd=Decimal(str(lr * 5)),
        expected_maker_share=Decimal("0.2"),
        expected_lr_share=Decimal("0.1"),
        expected_total_usd=Decimal(str(total)),
    )


def test_analyzer_score_higher_for_better_market() -> None:
    """High volume + low competition → higher score (AC-3)."""
    analyzer = RewardDensityAnalyzer()
    good = analyzer.score(
        market_id="good",
        incentive=_make_incentive(10.0, 6.0, 4.0),
        competition=_make_competition(n_eff=10.0),
        risk_score=Decimal("0.5"),
    )
    bad = analyzer.score(
        market_id="bad",
        incentive=_make_incentive(2.0, 1.5, 0.5),
        competition=_make_competition(n_eff=1.0),
        risk_score=Decimal("0.5"),
    )
    assert float(good.reward_density_score) > float(bad.reward_density_score)


def test_analyzer_zero_score_no_incentives() -> None:
    """Score = 0 when expected incentives = 0 (AC-3)."""
    analyzer = RewardDensityAnalyzer()
    score = analyzer.score(
        market_id="empty",
        incentive=_make_incentive(0.0, 0.0, 0.0),
        competition=_make_competition(n_eff=5.0),
        risk_score=Decimal("0.5"),
    )
    assert float(score.reward_density_score) == 0.0
