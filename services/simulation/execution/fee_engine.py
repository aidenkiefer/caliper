from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from services.simulation.schemas import PnLComponents, SimFill


@dataclass
class FeeRegime:
    fee_rate: Decimal
    exponent: int           # 2 for pre-Mar30, 1 for post-Mar30
    maker_rebate_pct: Decimal  # fraction of fee equivalent that is rebated

    @classmethod
    def pre_mar30_crypto(cls) -> "FeeRegime":
        return cls(
            fee_rate=Decimal("0.25"),
            exponent=2,
            maker_rebate_pct=Decimal("0.20"),
        )

    @classmethod
    def post_mar30_crypto(cls) -> "FeeRegime":
        return cls(
            fee_rate=Decimal("0.072"),
            exponent=1,
            maker_rebate_pct=Decimal("0.20"),
        )

    @classmethod
    def for_date(cls, market_created_at: datetime, current_date: date) -> "FeeRegime":
        """
        Returns post_mar30_crypto only if BOTH the market was created on or after
        2026-03-30 AND current_date >= 2026-03-30. Otherwise pre_mar30_crypto.
        Markets created before the cutoff retain pre-Mar-30 rates indefinitely.
        """
        cutoff = date(2026, 3, 30)
        market_date = market_created_at.date() if isinstance(market_created_at, datetime) else market_created_at
        if market_date >= cutoff and current_date >= cutoff:
            return cls.post_mar30_crypto()
        return cls.pre_mar30_crypto()


class FeeEngine:
    def __init__(
        self,
        regime: FeeRegime,
        lr_pool_per_hour: Decimal = Decimal("50"),
    ) -> None:
        self.regime = regime
        self.lr_pool_per_hour = lr_pool_per_hour

    def taker_fee(self, shares: Decimal, price: Decimal) -> Decimal:
        """
        taker_fee = shares * price * fee_rate * (price * (1 - price)) ** exponent
        """
        if price <= 0 or shares <= 0:
            return Decimal(0)
        factor = (price * (Decimal(1) - price)) ** self.regime.exponent
        return shares * price * self.regime.fee_rate * factor

    def maker_rebate_estimate(
        self,
        fill: SimFill,
        total_fee_equivalent_in_market: Decimal,
        rebate_pool: Decimal,
    ) -> Decimal:
        """
        Estimate the maker rebate for a single fill.
        rebate = (your_fee_eq / total_fee_eq) * rebate_pool
        Sets fill.rebate_estimated = True.
        """
        if total_fee_equivalent_in_market <= 0:
            fill.rebate_estimated = True
            return Decimal(0)
        your_fee_eq = (
            fill.fill_size
            * fill.fill_price
            * self.regime.fee_rate
            * (fill.fill_price * (Decimal(1) - fill.fill_price)) ** self.regime.exponent
        )
        rebate = (your_fee_eq / total_fee_equivalent_in_market) * rebate_pool
        fill.rebate_estimated = True
        return rebate

    def liquidity_reward_credit(
        self,
        bid_size: Decimal,
        ask_size: Decimal,
        spread: Decimal,
        max_spread: Decimal,
        min_size: Decimal = Decimal("1"),
    ) -> Decimal:
        """
        quote_score = min(bid_size, ask_size) * max(0, 1 - spread / max_spread)
        Returns 0 if bid_size or ask_size is 0, or if spread >= max_spread.
        """
        if bid_size <= 0 or ask_size <= 0:
            return Decimal(0)
        if max_spread <= 0 or spread >= max_spread:
            return Decimal(0)
        spread_fraction = Decimal(1) - (spread / max_spread)
        if spread_fraction <= 0:
            return Decimal(0)
        return min(bid_size, ask_size) * spread_fraction

    def compute_pnl_components(
        self,
        fills: List[SimFill],
        mark_prices: List[Decimal],
    ) -> PnLComponents:
        """
        Compute full PnL attribution from fills and mark prices.
        mark_prices should be one per fill (mid_at_fill or final mark).
        """
        spread_capture = Decimal(0)
        taker_fee_total = Decimal(0)
        inventory_drift = Decimal(0)
        # For inventory_drift: track position and compute mark-to-market changes
        position = Decimal(0)
        prev_mark = Decimal(0)

        for i, fill in enumerate(fills):
            mark = mark_prices[i] if i < len(mark_prices) else fill.mid_at_fill
            # Spread capture: (fill_price - mid_at_fill) * size * side_sign
            side_sign = Decimal(1) if fill.side == "BUY" else Decimal(-1)
            spread_capture += (fill.fill_price - fill.mid_at_fill) * fill.fill_size * side_sign

            # Taker fee (negative = cost)
            if not fill.maker_fill:
                taker_fee_total += self.taker_fee(fill.fill_size, fill.fill_price)

            # Inventory drift: mark-to-market change on existing position
            if i > 0:
                inventory_drift += position * (mark - prev_mark)

            # Update position
            position += fill.fill_size * side_sign
            prev_mark = mark

        return PnLComponents(
            spread_capture=spread_capture,
            inventory_drift=inventory_drift,
            maker_rebate=Decimal(0),   # estimated separately
            liquidity_reward=Decimal(0),  # estimated separately
            taker_fee=taker_fee_total,    # subtracted in PnLComponents.total
            ops_cost=Decimal(0),
        )
