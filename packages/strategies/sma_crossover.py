"""
Simple Moving Average Crossover Strategy.

This is the "Starter Strategy" - a simple momentum strategy that:
- Buys when short SMA crosses above long SMA (golden cross)
- Sells when short SMA crosses below long SMA (death cross)
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from decimal import Decimal

import pandas as pd

from packages.common.schemas import (
    PriceBar,
    Order,
    Position,
    TradingMode,
    OrderSide,
    OrderType,
    TimeInForce,
)
from .base import Strategy, Signal, PortfolioState


class SMACrossoverStrategy(Strategy):
    """
    Simple Moving Average Crossover Strategy.

    Configuration:
        - short_period: Period for short SMA (default: 20)
        - long_period: Period for long SMA (default: 50)
        - position_size_pct: Percentage of equity per position (default: 0.1 = 10%)
        - min_signal_strength: Minimum signal strength to trade (default: 0.5)
    """

    def __init__(self, strategy_id: str, config: Dict[str, Any]):
        super().__init__(strategy_id, config)

        # Strategy parameters
        self.short_period = config.get("short_period", 20)
        self.long_period = config.get("long_period", 50)
        self.position_size_pct = Decimal(str(config.get("position_size_pct", 0.1)))
        self.min_signal_strength = config.get("min_signal_strength", 0.5)

        # Internal state
        self.price_history: List[PriceBar] = []
        self.current_position: Optional[Position] = None
        self.last_signal: Optional[str] = None  # 'BUY', 'SELL', or None

    def initialize(self, mode: TradingMode) -> None:
        """Initialize strategy."""
        self.mode = mode
        self.initialized = True
        self.price_history = []
        self.current_position = None
        self.last_signal = None

    def on_market_data(self, bar: PriceBar) -> None:
        """Store price bar in history."""
        self.price_history.append(bar)

        # Keep only recent history (last 200 bars for efficiency)
        if len(self.price_history) > 200:
            self.price_history = self.price_history[-200:]

    def generate_signals(self, portfolio: PortfolioState) -> List[Signal]:
        """
        Generate signals based on SMA crossover.

        Signal logic:
        - Need at least long_period bars to compute SMAs
        - Golden cross (short > long): BUY signal
        - Death cross (short < long): SELL signal
        """
        if len(self.price_history) < self.long_period + 1:
            return []

        short_sma, long_sma, prev_short_sma, prev_long_sma = self._calculate_smas()
        latest_bar = self.price_history[-1]

        return self._detect_crossover(
            short_sma, long_sma, prev_short_sma, prev_long_sma, latest_bar
        )

    def _calculate_smas(self) -> Tuple[float, float, float, float]:
        """Calculate current and previous SMA values."""
        recent_bars = self.price_history[-self.long_period - 1 :]
        df = pd.DataFrame(
            [
                {
                    "timestamp": bar.timestamp,
                    "close": float(bar.close),
                }
                for bar in recent_bars
            ]
        )

        short_sma = df["close"].rolling(window=self.short_period).mean().iloc[-1]
        long_sma = df["close"].rolling(window=self.long_period).mean().iloc[-1]
        prev_short_sma = df["close"].rolling(window=self.short_period).mean().iloc[-2]
        prev_long_sma = df["close"].rolling(window=self.long_period).mean().iloc[-2]

        return short_sma, long_sma, prev_short_sma, prev_long_sma

    def _detect_crossover(
        self,
        short_sma: float,
        long_sma: float,
        prev_short_sma: float,
        prev_long_sma: float,
        latest_bar: PriceBar,
    ) -> List[Signal]:
        """Detect SMA crossover and generate signals."""
        signals = []
        current_cross = short_sma > long_sma
        previous_cross = prev_short_sma > prev_long_sma

        if current_cross and not previous_cross:
            signals.append(self._create_buy_signal(latest_bar, short_sma, long_sma))
            self.last_signal = "BUY"
        elif not current_cross and previous_cross:
            signals.append(self._create_sell_signal(latest_bar, short_sma, long_sma))
            self.last_signal = "SELL"

        return signals

    def _create_buy_signal(self, bar: PriceBar, short_sma: float, long_sma: float) -> Signal:
        """Create BUY signal for golden cross."""
        return Signal(
            symbol=bar.symbol,
            side="BUY",
            strength=1.0,
            price=bar.close,
            reason=f"Golden cross: SMA({self.short_period})={short_sma:.2f} > SMA({self.long_period})={long_sma:.2f}",
        )

    def _create_sell_signal(self, bar: PriceBar, short_sma: float, long_sma: float) -> Signal:
        """Create SELL signal for death cross."""
        return Signal(
            symbol=bar.symbol,
            side="SELL",
            strength=1.0,
            price=bar.close,
            reason=f"Death cross: SMA({self.short_period})={short_sma:.2f} < SMA({self.long_period})={long_sma:.2f}",
        )

    def risk_check(self, signals: List[Signal], portfolio: PortfolioState) -> List[Order]:
        """
        Convert signals to orders with risk checks.

        Risk checks:
        - Filter by minimum signal strength
        - Calculate position size based on equity
        - Don't open new position if already have one
        """
        orders = []

        for signal in signals:
            # Filter by signal strength
            if signal.strength < self.min_signal_strength:
                continue

            # Check if we already have a position
            existing_position = next(
                (p for p in portfolio.positions if p.symbol == signal.symbol), None
            )

            # Calculate position size
            if signal.side == "BUY":
                # Don't buy if we already have a position
                if existing_position and existing_position.quantity > 0:
                    continue

                # Calculate quantity based on position size percentage
                order_value = portfolio.equity * self.position_size_pct
                quantity = Decimal(str(order_value / float(signal.price)))

                if quantity > 0:
                    order = Order(
                        order_id=None,  # Will be generated by execution engine
                        strategy_id=self.strategy_id,
                        symbol=signal.symbol,
                        contract_type="STOCK",
                        side=OrderSide.BUY,
                        quantity=quantity,
                        order_type=OrderType.MARKET,
                        time_in_force=TimeInForce.DAY,
                        mode=self.mode,
                        created_at=datetime.now(),
                        updated_at=datetime.now(),
                    )
                    orders.append(order)

            elif signal.side == "SELL":
                # Only sell if we have a position
                if not existing_position or existing_position.quantity <= 0:
                    continue

                # Sell entire position
                order = Order(
                    order_id=None,
                    strategy_id=self.strategy_id,
                    symbol=signal.symbol,
                    contract_type="STOCK",
                    side=OrderSide.SELL,
                    quantity=abs(existing_position.quantity),
                    order_type=OrderType.MARKET,
                    time_in_force=TimeInForce.DAY,
                    mode=self.mode,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )
                orders.append(order)

        return orders

    def on_fill(self, fill: Order) -> None:
        """Update position tracking when order is filled."""
        # This would be handled by the execution engine in a real system
        # For now, we just log it
        pass

    def get_state(self) -> Dict[str, Any]:
        """Get strategy state."""
        state = super().get_state()
        state.update(
            {
                "short_period": self.short_period,
                "long_period": self.long_period,
                "position_size_pct": float(self.position_size_pct),
                "price_history_length": len(self.price_history),
                "last_signal": self.last_signal,
            }
        )
        return state
