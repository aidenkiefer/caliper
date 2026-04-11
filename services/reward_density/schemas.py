# services/reward_density/schemas.py
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel


class IncentiveEstimate(BaseModel):
    market_id: str
    estimated_at: datetime
    fee_pool_usd: Decimal
    maker_rebate_pool_usd: Decimal
    liquidity_reward_pool_usd: Decimal
    expected_maker_share: Decimal
    expected_lr_share: Decimal
    expected_total_usd: Decimal


class CompetitionMetric(BaseModel):
    market_id: str
    computed_at: datetime
    lookback_days: int
    hhi: Decimal
    n_eff: Decimal
    top_maker_address: Optional[str] = None
    top_maker_share: Optional[Decimal] = None
    data_source: Literal["onchain", "rewards_api_proxy"]
    is_estimate: bool


class RewardDensityScore(BaseModel):
    market_id: str
    scored_at: datetime
    expected_incentives_usd: Decimal
    maker_rebate_estimate: Decimal
    liquidity_reward_estimate: Decimal
    competition: Decimal        # N_eff
    risk_score: Decimal
    reward_density_score: Decimal
    alpha: Decimal
    beta: Decimal
    confidence: Literal["high", "medium", "low"]
