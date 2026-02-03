"""
Hold Cash Baseline Strategy

Simply holds cash and earns no return (or risk-free rate if configured).
"""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from services.backtest.models import (
    BacktestConfig,
    BacktestResult,
    PerformanceMetrics,
    EquityPoint,
    Trade,
)


class HoldCashBaseline:
    """
    Baseline strategy that holds cash (no trading).
    """

    def __init__(self, risk_free_rate: Decimal = Decimal("0.0")):
        """
        Initialize hold cash baseline.

        Args:
            risk_free_rate: Annual risk-free rate (default: 0.0 = no return)
        """
        self.risk_free_rate = risk_free_rate

    def run(
        self,
        config: BacktestConfig,
        start_date: datetime,
        end_date: datetime,
        strategy_id: str = "baseline-hold-cash",
    ) -> BacktestResult:
        """
        Run hold cash baseline.

        Args:
            config: Backtest configuration
            start_date: Start date
            end_date: End date
            strategy_id: Strategy identifier

        Returns:
            BacktestResult with zero return (or risk-free rate)
        """
        # Calculate daily risk-free return if applicable
        days = (end_date - start_date).days
        if days > 0 and self.risk_free_rate > 0:
            daily_rate = self.risk_free_rate / Decimal("365")
            total_return = daily_rate * Decimal(str(days))
        else:
            total_return = Decimal("0.0")

        final_equity = config.initial_capital * (Decimal("1") + total_return)

        # Create equity curve (just start and end points)
        equity_curve = [
            EquityPoint(
                timestamp=start_date,
                equity=config.initial_capital,
                cash=config.initial_capital,
                unrealized_pnl=Decimal("0"),
            ),
            EquityPoint(
                timestamp=end_date,
                equity=final_equity,
                cash=final_equity,
                unrealized_pnl=Decimal("0"),
            ),
        ]

        # No trades
        trades: list[Trade] = []

        # Performance metrics
        metrics = PerformanceMetrics(
            total_return=total_return,
            total_return_pct=total_return * Decimal("100"),
            sharpe_ratio=None,  # No volatility
            max_drawdown=Decimal("0"),
            max_drawdown_pct=Decimal("0"),
            win_rate=Decimal("0"),
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            avg_win=None,
            avg_loss=None,
            profit_factor=None,
        )

        return BacktestResult(
            backtest_id=uuid4(),
            strategy_id=strategy_id,
            config=config,
            equity_curve=equity_curve,
            trades=trades,
            metrics=metrics,
            start_time=start_date,
            end_time=end_date,
            metadata={"baseline_type": "hold_cash", "risk_free_rate": str(self.risk_free_rate)},
        )
