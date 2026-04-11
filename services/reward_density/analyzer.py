# services/reward_density/analyzer.py
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from services.reward_density.schemas import CompetitionMetric, IncentiveEstimate, RewardDensityScore


class RewardDensityAnalyzer:
    """Computes the composite reward density score for a candidate market."""

    def __init__(
        self,
        alpha: Decimal = Decimal("1.0"),
        beta: Decimal = Decimal("0.5"),
    ) -> None:
        self.alpha = alpha
        self.beta = beta

    def score(
        self,
        market_id: str,
        incentive: IncentiveEstimate,
        competition: CompetitionMetric,
        risk_score: Decimal,
    ) -> RewardDensityScore:
        incentives = incentive.expected_total_usd
        n_eff = competition.n_eff
        hhi = competition.hhi

        if incentives <= Decimal("0"):
            density = Decimal("0")
        else:
            safe_risk = max(risk_score, Decimal("0.000001"))
            safe_hhi = max(hhi, Decimal("0.000001"))
            denom = (safe_hhi ** self.alpha) * (safe_risk ** self.beta)
            density = incentives / denom if denom > Decimal("0") else Decimal("0")

        if not competition.is_estimate:
            confidence = "high"
        elif competition.is_estimate and float(n_eff) > 1:
            confidence = "medium"
        else:
            confidence = "low"

        return RewardDensityScore(
            market_id=market_id,
            scored_at=datetime.now(timezone.utc),
            expected_incentives_usd=incentives,
            maker_rebate_estimate=incentive.expected_maker_share * incentive.maker_rebate_pool_usd,
            liquidity_reward_estimate=incentive.expected_lr_share * incentive.liquidity_reward_pool_usd,
            competition=n_eff,
            risk_score=risk_score,
            reward_density_score=density,
            alpha=self.alpha,
            beta=self.beta,
            confidence=confidence,  # type: ignore[arg-type]
        )
