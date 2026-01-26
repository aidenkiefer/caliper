"""
Random Controlled Baseline Strategy

Random trades with same risk controls as main strategy.
Demonstrates value-add of actual strategy vs random.
"""

from datetime import datetime
from decimal import Decimal
from uuid import uuid4
import random

from packages.common.schemas import PriceBar
from services.backtest.models import (
    BacktestConfig,
    BacktestResult,
    PerformanceMetrics,
    EquityPoint,
    Trade,
)


class RandomControlledBaseline:
    """
    Random baseline with risk controls.
    """
    
    def __init__(self, max_risk_per_trade: Decimal = Decimal("0.02"), seed: int = 42):
        """
        Initialize random baseline.
        
        Args:
            max_risk_per_trade: Maximum risk per trade (default: 2%)
            seed: Random seed for reproducibility
        """
        self.max_risk_per_trade = max_risk_per_trade
        self.seed = seed
        random.seed(seed)
    
    def run(
        self,
        config: BacktestConfig,
        price_bars: list[PriceBar],
        strategy_id: str = "baseline-random",
    ) -> BacktestResult:
        """
        Run random baseline with risk controls.
        
        Args:
            config: Backtest configuration
            price_bars: Historical price bars
            strategy_id: Strategy identifier
            
        Returns:
            BacktestResult
        """
        if not price_bars:
            raise ValueError("price_bars cannot be empty")
        
        # Filter bars to date range
        filtered_bars = price_bars
        if config.start_date:
            filtered_bars = [b for b in filtered_bars if b.timestamp >= config.start_date]
        if config.end_date:
            filtered_bars = [b for b in filtered_bars if b.timestamp <= config.end_date]
        
        if not filtered_bars:
            raise ValueError("No price bars in date range")
        
        start_date = filtered_bars[0].timestamp
        end_date = filtered_bars[-1].timestamp
        
        # Simple random strategy: randomly buy/sell every N bars
        trades: list[Trade] = []
        equity_curve: list[EquityPoint] = []
        cash = config.initial_capital
        position: dict[str, Decimal] = {}  # symbol -> quantity
        current_equity = config.initial_capital
        
        # Trade every 10 bars (can be made configurable)
        trade_frequency = 10
        
        for i, bar in enumerate(filtered_bars):
            # Randomly decide to trade
            if i % trade_frequency == 0 and random.random() < 0.3:  # 30% chance to trade
                symbol = bar.symbol
                action = random.choice(["BUY", "SELL"])
                
                if action == "BUY" and cash > config.commission_per_trade:
                    # Calculate position size based on risk
                    risk_amount = current_equity * self.max_risk_per_trade
                    stop_loss_pct = Decimal("0.05")  # 5% stop loss
                    max_loss_per_share = bar.close * stop_loss_pct
                    
                    if max_loss_per_share > 0:
                        shares = risk_amount / max_loss_per_share
                        cost = shares * bar.close + config.commission_per_trade
                        
                        if cost <= cash:
                            position[symbol] = position.get(symbol, Decimal("0")) + shares
                            cash -= cost
                
                elif action == "SELL" and symbol in position and position[symbol] > 0:
                    # Close position
                    shares = position[symbol]
                    proceeds = shares * bar.close - config.commission_per_trade
                    cash += proceeds
                    position.pop(symbol)
            
            # Calculate current equity
            position_value = sum(
                pos_qty * filtered_bars[min(i + j, len(filtered_bars) - 1)].close
                for j, (sym, pos_qty) in enumerate(position.items())
                if i + j < len(filtered_bars)
            )
            current_equity = cash + position_value
            
            # Add equity point (sample every 20 bars to keep curve manageable)
            if i % 20 == 0 or i == len(filtered_bars) - 1:
                equity_curve.append(
                    EquityPoint(
                        timestamp=bar.timestamp,
                        equity=current_equity,
                        cash=cash,
                        unrealized_pnl=position_value - sum(
                            pos_qty * filtered_bars[0].close
                            for pos_qty in position.values()
                        ),
                    )
                )
        
        # Close any remaining positions at end
        if position and filtered_bars:
            final_bar = filtered_bars[-1]
            for symbol, shares in position.items():
                proceeds = shares * final_bar.close - config.commission_per_trade
                cash += proceeds
        
        final_equity = cash
        
        # Calculate metrics (simplified - would need to track actual trades)
        total_return = (final_equity - config.initial_capital) / config.initial_capital
        
        metrics = PerformanceMetrics(
            total_return=total_return,
            total_return_pct=total_return * Decimal("100"),
            sharpe_ratio=None,
            max_drawdown=self._calculate_max_drawdown(equity_curve),
            max_drawdown_pct=self._calculate_max_drawdown_pct(equity_curve),
            win_rate=Decimal("0.5"),  # Approximate for random
            total_trades=len(trades),
            winning_trades=len([t for t in trades if t.pnl > 0]),
            losing_trades=len([t for t in trades if t.pnl < 0]),
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
            metadata={
                "baseline_type": "random_controlled",
                "max_risk_per_trade": str(self.max_risk_per_trade),
                "seed": self.seed,
            },
        )
    
    def _calculate_max_drawdown(self, equity_curve: list[EquityPoint]) -> Decimal:
        """Calculate max drawdown."""
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
