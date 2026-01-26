"""
Buy & Hold Baseline Strategy

Buys at the start and holds until the end.
"""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from packages.common.schemas import PriceBar
from services.backtest.models import (
    BacktestConfig,
    BacktestResult,
    PerformanceMetrics,
    EquityPoint,
    Trade,
)


class BuyAndHoldBaseline:
    """
    Baseline strategy: buy at start, hold until end.
    """
    
    def __init__(self, symbol: str = "SPY"):
        """
        Initialize buy & hold baseline.
        
        Args:
            symbol: Symbol to buy and hold (default: SPY)
        """
        self.symbol = symbol
    
    def run(
        self,
        config: BacktestConfig,
        price_bars: list[PriceBar],
        strategy_id: str = "baseline-buy-and-hold",
    ) -> BacktestResult:
        """
        Run buy & hold baseline.
        
        Args:
            config: Backtest configuration
            price_bars: Historical price bars (must be for same symbol)
            strategy_id: Strategy identifier
            
        Returns:
            BacktestResult
        """
        if not price_bars:
            raise ValueError("price_bars cannot be empty")
        
        # Filter bars to date range if specified
        filtered_bars = price_bars
        if config.start_date:
            filtered_bars = [b for b in filtered_bars if b.timestamp >= config.start_date]
        if config.end_date:
            filtered_bars = [b for b in filtered_bars if b.timestamp <= config.end_date]
        
        if not filtered_bars:
            raise ValueError("No price bars in date range")
        
        start_date = filtered_bars[0].timestamp
        end_date = filtered_bars[-1].timestamp
        
        # Buy at first bar's close
        entry_price = filtered_bars[0].close
        shares = (config.initial_capital - config.commission_per_trade) / entry_price
        
        # Exit at last bar's close
        exit_price = filtered_bars[-1].close
        
        # Calculate P&L
        gross_pnl = (exit_price - entry_price) * shares
        total_commission = config.commission_per_trade * Decimal("2")  # Entry + exit
        net_pnl = gross_pnl - total_commission
        final_equity = config.initial_capital + net_pnl
        
        # Create single trade
        trade = Trade(
            symbol=self.symbol,
            entry_time=start_date,
            exit_time=end_date,
            entry_price=entry_price,
            exit_price=exit_price,
            quantity=shares,
            commission=total_commission,
            pnl=net_pnl,
            return_pct=(net_pnl / config.initial_capital) * Decimal("100"),
        )
        
        # Create equity curve (simplified: start, end, and key points)
        equity_curve = [
            EquityPoint(
                timestamp=start_date,
                equity=config.initial_capital,
                cash=config.initial_capital - (entry_price * shares) - config.commission_per_trade,
                unrealized_pnl=Decimal("0"),
            ),
        ]
        
        # Add midpoint if there are enough bars
        if len(filtered_bars) > 1:
            mid_idx = len(filtered_bars) // 2
            mid_bar = filtered_bars[mid_idx]
            mid_equity = config.initial_capital + ((mid_bar.close - entry_price) * shares) - config.commission_per_trade
            equity_curve.append(
                EquityPoint(
                    timestamp=mid_bar.timestamp,
                    equity=mid_equity,
                    cash=config.initial_capital - (entry_price * shares) - config.commission_per_trade,
                    unrealized_pnl=(mid_bar.close - entry_price) * shares,
                )
            )
        
        equity_curve.append(
            EquityPoint(
                timestamp=end_date,
                equity=final_equity,
                cash=final_equity,
                unrealized_pnl=Decimal("0"),
            )
        )
        
        # Performance metrics
        total_return = net_pnl / config.initial_capital
        metrics = PerformanceMetrics(
            total_return=total_return,
            total_return_pct=total_return * Decimal("100"),
            sharpe_ratio=None,  # Would need to calculate from equity curve
            max_drawdown=self._calculate_max_drawdown(equity_curve),
            max_drawdown_pct=self._calculate_max_drawdown_pct(equity_curve),
            win_rate=Decimal("1.0") if net_pnl > 0 else Decimal("0.0"),
            total_trades=1,
            winning_trades=1 if net_pnl > 0 else 0,
            losing_trades=0 if net_pnl > 0 else 1,
            avg_win=net_pnl if net_pnl > 0 else None,
            avg_loss=None if net_pnl > 0 else net_pnl,
            profit_factor=Decimal("999") if net_pnl > 0 else Decimal("0"),
        )
        
        return BacktestResult(
            backtest_id=uuid4(),
            strategy_id=strategy_id,
            config=config,
            equity_curve=equity_curve,
            trades=[trade],
            metrics=metrics,
            start_time=start_date,
            end_time=end_date,
            metadata={"baseline_type": "buy_and_hold", "symbol": self.symbol},
        )
    
    def _calculate_max_drawdown(self, equity_curve: list[EquityPoint]) -> Decimal:
        """Calculate max drawdown from equity curve."""
        if not equity_curve:
            return Decimal("0")
        
        peak = equity_curve[0].equity
        max_dd = Decimal("0")
        
        for point in equity_curve:
            if point.equity > peak:
                peak = point.equity
            dd = point.equity - peak
            if dd < max_dd:
                max_dd = dd
        
        return max_dd
    
    def _calculate_max_drawdown_pct(self, equity_curve: list[EquityPoint]) -> Decimal:
        """Calculate max drawdown percentage."""
        if not equity_curve:
            return Decimal("0")
        
        peak = equity_curve[0].equity
        max_dd_pct = Decimal("0")
        
        for point in equity_curve:
            if point.equity > peak:
                peak = point.equity
            if peak > 0:
                dd_pct = ((point.equity - peak) / peak) * Decimal("100")
                if dd_pct < max_dd_pct:
                    max_dd_pct = dd_pct
        
        return max_dd_pct
