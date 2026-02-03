"""
Regret calculation: compare strategy performance vs baselines.
"""

from decimal import Decimal
from typing import Dict, Optional
from pydantic import BaseModel, Field

from services.backtest.models import BacktestResult


class RegretMetrics(BaseModel):
    """Regret metrics vs baselines."""

    strategy_id: str
    strategy_return: Decimal = Field(description="Strategy total return")

    # Baseline returns
    hold_cash_return: Decimal = Field(description="Hold cash baseline return")
    buy_and_hold_return: Decimal = Field(description="Buy & hold baseline return")
    random_return: Optional[Decimal] = Field(None, description="Random baseline return")

    # Regret calculations
    regret_vs_cash: Decimal = Field(description="Regret vs hold cash (strategy - cash)")
    regret_vs_buy_hold: Decimal = Field(description="Regret vs buy & hold")
    regret_vs_random: Optional[Decimal] = Field(None, description="Regret vs random")

    # Best baseline
    best_baseline_return: Decimal = Field(description="Best baseline return")
    regret_vs_best: Decimal = Field(description="Regret vs best baseline")

    # Relative performance
    outperforms_cash: bool = Field(description="Strategy outperforms cash")
    outperforms_buy_hold: bool = Field(description="Strategy outperforms buy & hold")
    outperforms_random: Optional[bool] = Field(None, description="Strategy outperforms random")
    outperforms_best: bool = Field(description="Strategy outperforms best baseline")


class RegretCalculator:
    """
    Calculates regret metrics comparing strategy vs baselines.
    """

    def calculate(
        self,
        strategy_result: BacktestResult,
        baseline_results: Dict[str, BacktestResult],
    ) -> RegretMetrics:
        """
        Calculate regret metrics.

        Args:
            strategy_result: Strategy backtest result
            baseline_results: Dict mapping baseline names to results
                Expected keys: "hold_cash", "buy_and_hold", optionally "random"

        Returns:
            RegretMetrics
        """
        strategy_return = strategy_result.metrics.total_return

        # Get baseline returns
        hold_cash_return = (
            baseline_results.get("hold_cash", {}).metrics.total_return
            if "hold_cash" in baseline_results
            else Decimal("0")
        )
        buy_and_hold_return = (
            baseline_results.get("buy_and_hold", {}).metrics.total_return
            if "buy_and_hold" in baseline_results
            else Decimal("0")
        )
        random_return = (
            baseline_results.get("random", {}).metrics.total_return
            if "random" in baseline_results
            else None
        )

        # Calculate regret (strategy return - baseline return)
        regret_vs_cash = strategy_return - hold_cash_return
        regret_vs_buy_hold = strategy_return - buy_and_hold_return
        regret_vs_random = strategy_return - random_return if random_return is not None else None

        # Find best baseline
        baseline_returns = {
            "cash": hold_cash_return,
            "buy_and_hold": buy_and_hold_return,
        }
        if random_return is not None:
            baseline_returns["random"] = random_return

        best_baseline_name = max(baseline_returns, key=baseline_returns.get)
        best_baseline_return = baseline_returns[best_baseline_name]
        regret_vs_best = strategy_return - best_baseline_return

        return RegretMetrics(
            strategy_id=strategy_result.strategy_id,
            strategy_return=strategy_return,
            hold_cash_return=hold_cash_return,
            buy_and_hold_return=buy_and_hold_return,
            random_return=random_return,
            regret_vs_cash=regret_vs_cash,
            regret_vs_buy_hold=regret_vs_buy_hold,
            regret_vs_random=regret_vs_random,
            best_baseline_return=best_baseline_return,
            regret_vs_best=regret_vs_best,
            outperforms_cash=regret_vs_cash > 0,
            outperforms_buy_hold=regret_vs_buy_hold > 0,
            outperforms_random=regret_vs_random > 0 if regret_vs_random is not None else None,
            outperforms_best=regret_vs_best > 0,
        )
