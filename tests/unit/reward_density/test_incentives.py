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
