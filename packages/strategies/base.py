"""
Base strategy interface and abstract classes.

All trading strategies must implement this interface.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime
from decimal import Decimal

from packages.common.schemas import Order, Position, TradingMode
from packages.common.market_schemas import MarketType, UnifiedSignal


class Signal:
    """
    Legacy signal class — retained for backward compatibility with the ML
    inference adapter. New strategies should emit UnifiedSignal instead.
    """

    def __init__(
        self,
        symbol: str,
        side: str,
        strength: float,
        price=None,
        quantity=None,
        reason=None,
    ):
        self.symbol = symbol
        self.side = side
        self.strength = strength
        self.price = price
        self.quantity = quantity
        self.reason = reason
        self.timestamp = datetime.now()

    def __repr__(self):
        return f"Signal({self.symbol}, {self.side}, strength={self.strength:.2f})"


class PortfolioState:
    """Current portfolio state passed to strategies each cycle."""

    def __init__(
        self,
        equity: Decimal,
        cash: Decimal,
        positions: List[Position],
        unrealized_pnl: Decimal = Decimal(0),
    ):
        self.equity = equity
        self.cash = cash
        self.positions = positions
        self.unrealized_pnl = unrealized_pnl


class Strategy(ABC):
    """
    Abstract base class for all trading strategies (equity, prediction, hybrid).

    generate_signals() now returns List[UnifiedSignal] so the portfolio
    allocator and global risk manager can process any strategy uniformly.

    Subclasses MUST declare:
        market_type: MarketType  (class attribute)
    """

    # Subclasses MUST declare the market surface they operate on.
    market_type: MarketType

    def __init__(self, strategy_id: str, config: Dict[str, Any]):
        self.strategy_id = strategy_id
        self.config = config
        self.initialized = False
        self.mode: Optional[TradingMode] = None

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if not getattr(cls, "__abstractmethods__", None):
            if not isinstance(getattr(cls, "market_type", None), MarketType):
                raise TypeError(
                    f"{cls.__name__} must declare a 'market_type: MarketType' class attribute. "
                    f"Example: market_type = MarketType.EQUITY"
                )

    @abstractmethod
    def initialize(self, mode: TradingMode) -> None:
        """Called once before the strategy starts processing data."""
        pass

    @abstractmethod
    def on_market_data(self, bar) -> None:
        """
        Process incoming market data.

        `bar` type is intentionally untyped here so strategies can accept
        PriceBar (equity) or an orderbook snapshot (prediction) depending on
        their market_type.
        """
        pass

    @abstractmethod
    def generate_signals(self, portfolio: PortfolioState) -> List[UnifiedSignal]:
        """
        Generate UnifiedSignal objects for the portfolio allocator.

        Every signal must carry strategy_id, market_type, signal_type,
        direction, confidence, and horizon_seconds.
        """
        pass

    @abstractmethod
    def risk_check(
        self, signals: List[UnifiedSignal], portfolio: PortfolioState
    ) -> List[Order]:
        """
        Strategy-level guard: filter/size signals into Orders.

        The GlobalRiskManager (services/risk/global_risk_manager.py) applies
        a second, portfolio-wide check after this method. This layer handles
        strategy-specific constraints only.
        """
        pass

    def on_fill(self, fill: Order) -> None:
        """Handle order fill notification. Override as needed."""
        pass

    def daily_close(self) -> None:
        """End-of-day hook. Override as needed."""
        pass

    def get_state(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "market_type": self.market_type.value if hasattr(self, "market_type") else None,
            "initialized": self.initialized,
            "mode": self.mode.value if self.mode else None,
        }
