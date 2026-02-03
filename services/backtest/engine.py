"""
Backtest engine for executing trading strategies on historical data.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Dict, Any, Tuple
from uuid import uuid4

import numpy as np

from packages.common.schemas import (
    PriceBar,
    Order,
    Position,
    TradingMode,
    OrderSide,
    OrderStatus,
    OrderType,
    TimeInForce,
    ContractType,
)
from packages.strategies.base import Strategy, PortfolioState, Signal

from .models import (
    BacktestConfig,
    BacktestResult,
    PerformanceMetrics,
    Trade,
    EquityPoint,
)
from .abstention import AbstentionTracker


class BacktestEngine:
    """
    Backtesting engine that executes strategies on historical data.

    Features:
    - Strategy execution loop
    - Order fill simulation (with slippage and commission)
    - Position tracking
    - P&L calculation
    - Performance metrics
    """

    def __init__(self):
        """Initialize the backtest engine."""
        self.current_positions: Dict[str, Position] = {}
        self.equity_curve: List[EquityPoint] = []
        self.completed_trades: List[Trade] = []
        self.pending_orders: List[Order] = []
        self.abstention_tracker = AbstentionTracker()

    def run(
        self, strategy: Strategy, data: List[PriceBar], config: BacktestConfig
    ) -> BacktestResult:
        """
        Run a backtest on historical data.

        Args:
            strategy: Strategy instance to backtest
            data: Historical price bars (must be sorted by timestamp)
            config: Backtest configuration

        Returns:
            BacktestResult with equity curve, trades, and metrics
        """
        if not data:
            raise ValueError("Data list cannot be empty")

        self._reset_state(config.initial_capital)
        strategy.initialize(TradingMode.BACKTEST)

        start_time = datetime.now(timezone.utc)
        filtered_data = self._filter_data_by_dates(data, config.start_date, config.end_date)

        for bar in filtered_data:
            self._process_bar(strategy, bar, config)

        end_time = datetime.now(timezone.utc)
        metrics = self._calculate_metrics(config.initial_capital)

        # Add abstention metrics to metadata
        abstention_metrics = self.abstention_tracker.get_metrics()
        metadata = {
            "abstention_metrics": {
                "total_signals": abstention_metrics.total_signals,
                "abstentions": abstention_metrics.abstentions,
                "abstention_rate": str(abstention_metrics.abstention_rate),
            }
        }

        return BacktestResult(
            strategy_id=strategy.strategy_id,
            config=config,
            equity_curve=self.equity_curve.copy(),
            trades=self.completed_trades.copy(),
            metrics=metrics,
            start_time=start_time,
            end_time=end_time,
            metadata=metadata,
        )

    def _reset_state(self, initial_capital: Decimal) -> None:
        """Reset engine state for a new backtest."""
        self.current_positions = {}
        self.equity_curve = [
            EquityPoint(
                timestamp=datetime.now(timezone.utc),
                equity=initial_capital,
                cash=initial_capital,
                unrealized_pnl=Decimal("0"),
            )
        ]
        self.completed_trades = []
        self.pending_orders = []
        self.abstention_tracker = AbstentionTracker()

    def _filter_data_by_dates(
        self, data: List[PriceBar], start_date: Optional[datetime], end_date: Optional[datetime]
    ) -> List[PriceBar]:
        """Filter data by start and end dates."""
        filtered = data

        if start_date:
            filtered = [bar for bar in filtered if bar.timestamp >= start_date]

        if end_date:
            filtered = [bar for bar in filtered if bar.timestamp <= end_date]

        return filtered

    def _process_bar(self, strategy: Strategy, bar: PriceBar, config: BacktestConfig) -> None:
        """Process a single price bar."""
        strategy.on_market_data(bar)

        portfolio = self._get_portfolio_state(bar)
        signals = strategy.generate_signals(portfolio)

        # Track abstentions
        for signal in signals:
            if signal.side == "ABSTAIN":
                self.abstention_tracker.record_signal("ABSTAIN")
            else:
                self.abstention_tracker.record_signal(signal.side)

        # Filter out ABSTAIN signals before risk check
        actionable_signals = [s for s in signals if s.side != "ABSTAIN"]
        orders = strategy.risk_check(actionable_signals, portfolio)

        for order in orders:
            try:
                order_with_id = self._ensure_order_id(order)
                self._execute_order(order_with_id, bar, config)
            except Exception as e:
                # Skip orders that can't be processed
                continue

        self._update_equity_curve(bar)

    def _get_portfolio_state(self, current_bar: PriceBar) -> PortfolioState:
        """Get current portfolio state for strategy decision-making."""
        cash = self._calculate_cash()
        positions = list(self.current_positions.values())
        equity = cash + self._calculate_positions_value(current_bar)
        unrealized_pnl = self._calculate_unrealized_pnl(current_bar)

        return PortfolioState(
            equity=equity,
            cash=cash,
            positions=positions,
            unrealized_pnl=unrealized_pnl,
        )

    def _calculate_cash(self) -> Decimal:
        """Calculate current cash balance."""
        if not self.equity_curve:
            return Decimal("0")
        return self.equity_curve[-1].cash

    def _calculate_positions_value(self, bar: PriceBar) -> Decimal:
        """Calculate total value of all positions."""
        total_value = Decimal("0")
        for position in self.current_positions.values():
            if position.symbol == bar.symbol:
                total_value += position.quantity * bar.close
            elif position.current_price:
                total_value += position.quantity * position.current_price
        return total_value

    def _calculate_unrealized_pnl(self, bar: PriceBar) -> Decimal:
        """Calculate unrealized P&L for all positions."""
        total_pnl = Decimal("0")
        for position in self.current_positions.values():
            if position.symbol == bar.symbol and position.current_price:
                total_pnl += position.unrealized_pnl or Decimal("0")
            elif position.unrealized_pnl:
                total_pnl += position.unrealized_pnl
        return total_pnl

    def _execute_order(self, order: Order, bar: PriceBar, config: BacktestConfig) -> None:
        """Execute an order with fill simulation."""
        if order.symbol != bar.symbol:
            return

        fill_price = self._calculate_fill_price(order, bar, config)
        commission = config.commission_per_trade

        if order.side == OrderSide.BUY:
            self._execute_buy(order, fill_price, commission, bar.timestamp)
        elif order.side == OrderSide.SELL:
            self._execute_sell(order, fill_price, commission, bar.timestamp)

    def _ensure_order_id(self, order: Order) -> Order:
        """Ensure order has an ID, generating one if needed."""
        # If order_id is None or invalid, create new Order with generated ID
        try:
            if order.order_id is None:
                order_dict = order.model_dump()
                order_dict["order_id"] = uuid4()
                return Order(**order_dict)
        except (AttributeError, ValueError, TypeError):
            # Fallback: create new Order from order's attributes
            order_dict = {
                "order_id": uuid4(),
                "strategy_id": order.strategy_id,
                "symbol": order.symbol,
                "contract_type": order.contract_type,
                "side": order.side,
                "quantity": order.quantity,
                "order_type": order.order_type,
                "limit_price": order.limit_price,
                "stop_price": order.stop_price,
                "time_in_force": order.time_in_force,
                "status": order.status,
                "mode": order.mode,
                "created_at": order.created_at,
                "updated_at": order.updated_at,
            }
            return Order(**order_dict)
        return order

    def _calculate_fill_price(self, order: Order, bar: PriceBar, config: BacktestConfig) -> Decimal:
        """Calculate fill price with slippage."""
        base_price = bar.close
        slippage_pct = config.slippage_bps / Decimal("10000")

        if order.side == OrderSide.BUY:
            return base_price * (Decimal("1") + slippage_pct)
        else:
            return base_price * (Decimal("1") - slippage_pct)

    def _execute_buy(
        self, order: Order, fill_price: Decimal, commission: Decimal, timestamp: datetime
    ) -> None:
        """Execute a buy order."""
        cost = order.quantity * fill_price + commission
        cash = self._calculate_cash()

        if cost > cash:
            return

        position = self._get_or_create_position(order, fill_price, timestamp)
        position.quantity += order.quantity
        position.average_entry_price = self._update_average_price(
            position, fill_price, order.quantity
        )
        position.cost_basis = (position.cost_basis or Decimal("0")) + cost
        position.updated_at = timestamp

        self._update_equity_after_trade(cost)

    def _execute_sell(
        self, order: Order, fill_price: Decimal, commission: Decimal, timestamp: datetime
    ) -> None:
        """Execute a sell order."""
        position = self.current_positions.get(order.symbol)
        if not position or position.quantity <= 0:
            return

        quantity_to_sell = min(order.quantity, position.quantity)
        proceeds = quantity_to_sell * fill_price - commission

        if quantity_to_sell == position.quantity:
            self._close_position(position, fill_price, commission, timestamp)
        else:
            position.quantity -= quantity_to_sell
            position.cost_basis = (position.cost_basis or Decimal("0")) - (
                position.average_entry_price * quantity_to_sell + commission
            )
            position.updated_at = timestamp

        self._update_equity_after_trade(proceeds)

    def _get_or_create_position(
        self, order: Order, fill_price: Decimal, timestamp: datetime
    ) -> Position:
        """Get existing position or create new one."""
        if order.symbol in self.current_positions:
            return self.current_positions[order.symbol]

        position = Position(
            position_id=uuid4(),
            strategy_id=order.strategy_id,
            symbol=order.symbol,
            contract_type=order.contract_type,
            quantity=Decimal("0"),
            average_entry_price=fill_price,
            current_price=fill_price,
            unrealized_pnl=Decimal("0"),
            realized_pnl=Decimal("0"),
            cost_basis=Decimal("0"),
            market_value=Decimal("0"),
            mode=TradingMode.BACKTEST,
            opened_at=timestamp,
            updated_at=timestamp,
        )
        self.current_positions[order.symbol] = position
        return position

    def _update_average_price(
        self, position: Position, new_price: Decimal, new_quantity: Decimal
    ) -> Decimal:
        """Update average entry price when adding to position."""
        total_quantity = position.quantity + new_quantity
        if total_quantity == 0:
            return new_price

        old_value = position.quantity * position.average_entry_price
        new_value = new_quantity * new_price
        return (old_value + new_value) / total_quantity

    def _close_position(
        self, position: Position, exit_price: Decimal, commission: Decimal, timestamp: datetime
    ) -> None:
        """Close a position and record the trade."""
        entry_price = position.average_entry_price
        quantity = position.quantity

        pnl = (exit_price - entry_price) * quantity - commission * Decimal("2")
        return_pct = ((exit_price - entry_price) / entry_price) * Decimal("100")

        trade = Trade(
            symbol=position.symbol,
            entry_time=position.opened_at,
            exit_time=timestamp,
            entry_price=entry_price,
            exit_price=exit_price,
            quantity=quantity,
            commission=commission * Decimal("2"),
            pnl=pnl,
            return_pct=return_pct,
        )

        self.completed_trades.append(trade)
        del self.current_positions[position.symbol]

    def _update_equity_after_trade(self, cash_change: Decimal) -> None:
        """Update cash balance after a trade."""
        if not self.equity_curve:
            return

        last_point = self.equity_curve[-1]
        new_cash = last_point.cash + cash_change
        last_point.cash = new_cash

    def _update_equity_curve(self, bar: PriceBar) -> None:
        """Update equity curve with current bar."""
        cash = self._calculate_cash()
        positions_value = self._calculate_positions_value(bar)
        equity = cash + positions_value
        unrealized_pnl = self._calculate_unrealized_pnl(bar)

        point = EquityPoint(
            timestamp=bar.timestamp,
            equity=equity,
            cash=cash,
            unrealized_pnl=unrealized_pnl,
        )
        self.equity_curve.append(point)

    def _calculate_metrics(self, initial_capital: Decimal) -> PerformanceMetrics:
        """Calculate performance metrics from backtest results."""
        if not self.equity_curve:
            return self._empty_metrics()

        final_equity = self.equity_curve[-1].equity
        total_return = (final_equity - initial_capital) / initial_capital
        total_return_pct = total_return * Decimal("100")

        drawdown = self._calculate_max_drawdown(initial_capital)
        sharpe = self._calculate_sharpe_ratio()
        (
            win_rate,
            winning_trades,
            losing_trades,
            avg_win,
            avg_loss,
            profit_factor,
        ) = self._calculate_trade_stats()

        return PerformanceMetrics(
            total_return=total_return,
            total_return_pct=total_return_pct,
            sharpe_ratio=sharpe,
            max_drawdown=drawdown,
            max_drawdown_pct=drawdown / initial_capital * Decimal("100"),
            win_rate=win_rate,
            total_trades=len(self.completed_trades),
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
        )

    def _empty_metrics(self) -> PerformanceMetrics:
        """Return empty metrics when no trades occurred."""
        return PerformanceMetrics(
            total_return=Decimal("0"),
            total_return_pct=Decimal("0"),
            sharpe_ratio=None,
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

    def _calculate_max_drawdown(self, initial_capital: Decimal) -> Decimal:
        """Calculate maximum drawdown."""
        if not self.equity_curve:
            return Decimal("0")

        peak = initial_capital
        max_dd = Decimal("0")

        for point in self.equity_curve:
            if point.equity > peak:
                peak = point.equity
            drawdown = point.equity - peak
            if drawdown < max_dd:
                max_dd = drawdown

        return max_dd

    def _calculate_sharpe_ratio(self) -> Optional[Decimal]:
        """Calculate annualized Sharpe ratio."""
        if len(self.equity_curve) < 2:
            return None

        returns = []
        for i in range(1, len(self.equity_curve)):
            prev_equity = self.equity_curve[i - 1].equity
            curr_equity = self.equity_curve[i].equity
            if prev_equity > 0:
                daily_return = (curr_equity - prev_equity) / prev_equity
                returns.append(float(daily_return))

        if not returns or len(returns) < 2:
            return None

        returns_array = np.array(returns)
        mean_return = np.mean(returns_array)
        std_return = np.std(returns_array)

        if std_return == 0:
            return None

        sharpe = Decimal(str(mean_return / std_return * np.sqrt(252)))
        return sharpe

    def _calculate_trade_stats(
        self,
    ) -> Tuple[Decimal, int, int, Optional[Decimal], Optional[Decimal], Optional[Decimal]]:
        """Calculate trade statistics."""
        if not self.completed_trades:
            return Decimal("0"), 0, 0, None, None, None

        winning_trades = [t for t in self.completed_trades if t.pnl > 0]
        losing_trades = [t for t in self.completed_trades if t.pnl < 0]

        win_rate = Decimal(len(winning_trades)) / Decimal(len(self.completed_trades))

        avg_win = (
            Decimal(str(np.mean([float(t.pnl) for t in winning_trades])))
            if winning_trades
            else None
        )

        avg_loss = (
            Decimal(str(np.mean([float(t.pnl) for t in losing_trades]))) if losing_trades else None
        )

        gross_profit = sum(t.pnl for t in winning_trades)
        gross_loss = abs(sum(t.pnl for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else None

        return win_rate, len(winning_trades), len(losing_trades), avg_win, avg_loss, profit_factor
