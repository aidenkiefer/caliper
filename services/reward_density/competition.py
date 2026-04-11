# services/reward_density/competition.py
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional

from services.reward_density.onchain.polygon_client import OrderFilledEvent
from services.reward_density.schemas import CompetitionMetric


class CompetitionEstimator:
    """Compute maker HHI from on-chain OrderFilled events."""

    def __init__(self, lookback_days: int = 7) -> None:
        self.lookback_days = lookback_days

    def compute(
        self,
        market_id: str,
        events: List[OrderFilledEvent],
        *,
        fallback_n_eff: Optional[Decimal] = None,
    ) -> CompetitionMetric:
        now = datetime.now(timezone.utc)

        if not events:
            n_eff = fallback_n_eff or Decimal("5")
            return CompetitionMetric(
                market_id=market_id,
                computed_at=now,
                lookback_days=self.lookback_days,
                hhi=Decimal("1") / n_eff,
                n_eff=n_eff,
                top_maker_address=None,
                top_maker_share=None,
                data_source="rewards_api_proxy",
                is_estimate=True,
            )

        fee_by_maker: Dict[str, int] = defaultdict(int)
        for evt in events:
            fee_by_maker[evt.maker] += evt.fee

        total_fee = sum(fee_by_maker.values())
        if total_fee == 0:
            n_eff = fallback_n_eff or Decimal(str(len(fee_by_maker)))
            return CompetitionMetric(
                market_id=market_id,
                computed_at=now,
                lookback_days=self.lookback_days,
                hhi=Decimal("1") / n_eff,
                n_eff=n_eff,
                top_maker_address=None,
                top_maker_share=None,
                data_source="onchain",
                is_estimate=True,
            )

        shares: Dict[str, Decimal] = {
            maker: Decimal(str(fee)) / Decimal(str(total_fee))
            for maker, fee in fee_by_maker.items()
        }
        hhi = sum(w * w for w in shares.values())
        n_eff = Decimal("1") / hhi

        top_maker = max(shares, key=lambda k: shares[k])
        return CompetitionMetric(
            market_id=market_id,
            computed_at=now,
            lookback_days=self.lookback_days,
            hhi=hhi,
            n_eff=n_eff,
            top_maker_address=top_maker,
            top_maker_share=shares[top_maker],
            data_source="onchain",
            is_estimate=False,
        )
