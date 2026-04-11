# services/reward_density/incentives.py
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from services.reward_density.schemas import IncentiveEstimate


def effective_fee_rate(price: Decimal) -> Decimal:
    """Post-March-30 crypto fee formula: price * 0.072 * (price*(1-price))^1."""
    return price * Decimal("0.072") * (price * (Decimal("1") - price))


class IncentiveEstimator:
    """Estimates maker rebates and liquidity rewards for a candidate market."""

    def compute_fee_pool(self, volume_7d_avg: Decimal, avg_price: Decimal) -> Decimal:
        rate = effective_fee_rate(avg_price)
        return volume_7d_avg * rate

    def compute_maker_rebate_pool(self, fee_pool: Decimal) -> Decimal:
        return Decimal("0.20") * fee_pool

    def _expected_maker_share(
        self,
        n_eff: Decimal,
        historical_fill_rate: Optional[Decimal],
    ) -> Decimal:
        base = Decimal("1") / max(n_eff, Decimal("1"))
        if historical_fill_rate is not None and historical_fill_rate > Decimal("0"):
            return (base + historical_fill_rate) / Decimal("2")
        return base

    def _expected_lr_share(
        self,
        n_eff: Decimal,
        lr_max_spread: Optional[Decimal],
        lr_min_size: Optional[Decimal],
        our_spread: Decimal,
        our_size: Decimal,
    ) -> Decimal:
        if lr_max_spread is None or lr_min_size is None:
            return Decimal("0")
        if our_spread > lr_max_spread:
            return Decimal("0")
        if our_size < lr_min_size:
            return Decimal("0")
        return Decimal("1") / max(n_eff, Decimal("1"))

    def estimate(
        self,
        market_id: str,
        volume_7d_avg: Decimal,
        avg_price: Decimal,
        n_eff: Decimal,
        historical_fill_rate: Optional[Decimal],
        lr_pool_per_day: Decimal,
        lr_max_spread: Optional[Decimal],
        lr_min_size: Optional[Decimal],
        our_spread: Decimal,
        our_size: Decimal,
        *,
        lookback_days: int = 7,
    ) -> IncentiveEstimate:
        fee_pool = self.compute_fee_pool(volume_7d_avg, avg_price)
        rebate_pool = self.compute_maker_rebate_pool(fee_pool)
        maker_share = self._expected_maker_share(n_eff, historical_fill_rate)

        lr_pool_total = lr_pool_per_day * Decimal(str(lookback_days))
        lr_share = self._expected_lr_share(n_eff, lr_max_spread, lr_min_size, our_spread, our_size)

        expected_rebate = rebate_pool * maker_share
        expected_lr = lr_pool_total * lr_share
        total = expected_rebate + expected_lr

        return IncentiveEstimate(
            market_id=market_id,
            estimated_at=datetime.now(timezone.utc),
            fee_pool_usd=fee_pool,
            maker_rebate_pool_usd=rebate_pool,
            liquidity_reward_pool_usd=lr_pool_total,
            expected_maker_share=maker_share,
            expected_lr_share=lr_share,
            expected_total_usd=total,
        )
