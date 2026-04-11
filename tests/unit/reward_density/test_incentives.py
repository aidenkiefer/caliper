# tests/unit/reward_density/test_incentives.py
import pytest
from decimal import Decimal
from datetime import datetime, timezone

from services.reward_density.schemas import (
    RewardDensityScore,
    CompetitionMetric,
    IncentiveEstimate,
)


def test_reward_density_score_fields() -> None:
    score = RewardDensityScore(
        market_id="mkt1",
        scored_at=datetime.now(timezone.utc),
        expected_incentives_usd=Decimal("5.00"),
        maker_rebate_estimate=Decimal("3.00"),
        liquidity_reward_estimate=Decimal("2.00"),
        competition=Decimal("4.0"),
        risk_score=Decimal("1.5"),
        reward_density_score=Decimal("2.22"),
        alpha=Decimal("1.0"),
        beta=Decimal("0.5"),
        confidence="high",
    )
    assert score.market_id == "mkt1"
    assert score.confidence == "high"


def test_competition_metric_is_estimate_flag() -> None:
    m = CompetitionMetric(
        market_id="mkt1",
        computed_at=datetime.now(timezone.utc),
        lookback_days=7,
        hhi=Decimal("1.0"),
        n_eff=Decimal("1.0"),
        top_maker_address=None,
        top_maker_share=None,
        data_source="onchain",
        is_estimate=False,
    )
    assert m.hhi == Decimal("1.0")
    assert m.n_eff == Decimal("1.0")


from services.reward_density.incentives import IncentiveEstimator, effective_fee_rate


def test_effective_fee_rate_formula() -> None:
    # effective_fee_rate = price * 0.072 * (price * (1 - price))^1
    price = Decimal("0.5")
    expected = price * Decimal("0.072") * (price * (Decimal("1") - price))
    result = effective_fee_rate(price)
    assert float(result) == pytest.approx(float(expected), rel=1e-6)


def test_fee_rate_at_extreme_price() -> None:
    result = effective_fee_rate(Decimal("0.01"))
    assert result > 0


def test_rebate_pool_is_20pct_of_fee_pool() -> None:
    estimator = IncentiveEstimator()
    volume = Decimal("1000")
    price = Decimal("0.5")
    fee_pool = estimator.compute_fee_pool(volume, price)
    rebate = estimator.compute_maker_rebate_pool(fee_pool)
    assert float(rebate) == pytest.approx(float(fee_pool) * 0.20, rel=1e-6)


def test_rebate_pool_within_1pct() -> None:
    """AC-1: rebate_pool_i = 0.20 * fee_pool_i within 1%."""
    estimator = IncentiveEstimator()
    volume = Decimal("10000")
    price = Decimal("0.6")
    fee_pool = estimator.compute_fee_pool(volume, price)
    rebate = estimator.compute_maker_rebate_pool(fee_pool)
    direct = Decimal("0.20") * fee_pool
    assert abs(float(rebate) - float(direct)) / float(direct) < 0.01


def test_estimate_total_no_lr() -> None:
    """When market is not reward-eligible, LR contribution is 0."""
    estimator = IncentiveEstimator()
    result = estimator.estimate(
        market_id="mkt1",
        volume_7d_avg=Decimal("5000"),
        avg_price=Decimal("0.5"),
        n_eff=Decimal("5"),
        historical_fill_rate=Decimal("0.1"),
        lr_pool_per_day=Decimal("0"),
        lr_max_spread=None,
        lr_min_size=None,
        our_spread=Decimal("0.02"),
        our_size=Decimal("50"),
    )
    assert float(result.liquidity_reward_pool_usd) == 0.0
    assert float(result.expected_total_usd) > 0
