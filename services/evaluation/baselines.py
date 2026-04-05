from __future__ import annotations

import random
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List


@dataclass
class HoldCashBaseline:
    """Hold cash — PnL is always 0."""
    description: str = "Hold cash — PnL = 0 at all times"

    def compute(self, period_hours: int) -> List[Decimal]:
        return [Decimal("0")] * period_hours


@dataclass
class BuyAndHoldYesBaseline:
    """Buy YES at market open ask, hold to settlement."""
    description: str = "Buy and hold YES at market open ask"

    def compute(
        self,
        open_ask: Decimal,
        settlement_price: Decimal,
        period_hours: int,
    ) -> List[Decimal]:
        """
        At hour 0: buy YES at open_ask. PnL realized at final hour.
        Intermediate hours: 0 PnL (no mark-to-market, hold to settlement).
        Final hour: settlement_price - open_ask.
        """
        if period_hours <= 0:
            return []
        pnl = [Decimal("0")] * period_hours
        pnl[-1] = settlement_price - open_ask
        return pnl


@dataclass
class RandomMMBaseline:
    """
    Random market-making: quote at mid ± 1 tick, equal probability on each side.
    No inventory management. Measures value added by the real strategy's quoting policy.
    """
    description: str = "Random market-making at mid ± 1 tick"

    def compute(
        self,
        mid_prices: List[Decimal],
        tick_size: Decimal = Decimal("0.01"),
        assumed_size: Decimal = Decimal("10"),
        random_seed: int = 42,
    ) -> List[Decimal]:
        """
        For each hour: 50% fill probability on both bid and ask.
        Hourly PnL = tick_size * assumed_size per filled round-trip.
        Deterministic with random_seed.
        """
        rng = random.Random(random_seed)
        pnl_series: List[Decimal] = []
        for _mid in mid_prices:
            bid_filled = rng.random() < 0.5
            ask_filled = rng.random() < 0.5
            hourly_pnl = Decimal("0")
            if bid_filled and ask_filled:
                # Round trip: capture the spread
                hourly_pnl = tick_size * assumed_size * Decimal("2")
            elif bid_filled or ask_filled:
                # One side only: inventory exposure, simplified as 0 (no inventory model)
                hourly_pnl = Decimal("0")
            pnl_series.append(hourly_pnl)
        return pnl_series


class BaselineEvaluator:
    """Computes regret of a strategy vs each baseline."""

    def __init__(self) -> None:
        self._hold_cash = HoldCashBaseline()
        self._buy_hold = BuyAndHoldYesBaseline()
        self._random_mm = RandomMMBaseline()

    def compute_regrets(
        self,
        strategy_pnl: List[Decimal],
        open_ask: Decimal,
        settlement_price: Decimal,
        mid_prices: List[Decimal],
    ) -> Dict[str, Decimal]:
        """
        Returns regret = strategy_total_pnl - baseline_total_pnl for each baseline.
        Positive regret means strategy outperformed the baseline.
        """
        period_hours = len(strategy_pnl)
        strategy_total = sum(strategy_pnl, Decimal("0"))

        hold_cash_pnl = sum(self._hold_cash.compute(period_hours), Decimal("0"))
        buy_hold_pnl = sum(
            self._buy_hold.compute(open_ask, settlement_price, period_hours),
            Decimal("0"),
        )
        random_mm_pnl = sum(
            self._random_mm.compute(mid_prices[:period_hours]),
            Decimal("0"),
        )

        return {
            "hold_cash": strategy_total - hold_cash_pnl,
            "buy_and_hold": strategy_total - buy_hold_pnl,
            "random_mm": strategy_total - random_mm_pnl,
        }
