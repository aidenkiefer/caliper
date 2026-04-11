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
