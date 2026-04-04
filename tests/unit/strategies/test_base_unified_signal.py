from decimal import Decimal
import pytest
from packages.common.market_schemas import MarketType, SignalType, UnifiedSignal
from packages.common.schemas import TradingMode, PriceBar
from packages.strategies.base import Strategy, PortfolioState
from datetime import datetime, timezone


class MinimalStrategy(Strategy):
    """Concrete strategy for testing the base class contract."""
    market_type = MarketType.EQUITY

    def initialize(self, mode: TradingMode) -> None:
        self.initialized = True
        self.mode = mode

    def on_market_data(self, bar: PriceBar) -> None:
        pass

    def generate_signals(self, portfolio: PortfolioState):
        return [
            UnifiedSignal(
                asset_id="AAPL",
                market_type=MarketType.EQUITY,
                signal_type=SignalType.DIRECTIONAL,
                direction="long",
                confidence=Decimal("0.8"),
                horizon_seconds=3600,
                strategy_id=self.strategy_id,
            )
        ]

    def risk_check(self, signals, portfolio):
        return []


def test_strategy_generate_signals_returns_unified_signal():
    s = MinimalStrategy("test_strategy", {})
    s.initialize(TradingMode.PAPER)
    bar = PriceBar(
        symbol="AAPL",
        timestamp=datetime.now(timezone.utc),
        open=Decimal("150"),
        high=Decimal("152"),
        low=Decimal("149"),
        close=Decimal("151"),
        volume=1000,
        timeframe="1day",
        source="test",
    )
    s.on_market_data(bar)
    portfolio = PortfolioState(
        equity=Decimal("100000"),
        cash=Decimal("100000"),
        positions=[],
    )
    signals = s.generate_signals(portfolio)
    assert len(signals) == 1
    assert isinstance(signals[0], UnifiedSignal)
    assert signals[0].strategy_id == "test_strategy"
    assert signals[0].market_type == MarketType.EQUITY


def test_strategy_market_type_declared():
    s = MinimalStrategy("test_strategy", {})
    assert hasattr(s, "market_type")
    assert s.market_type == MarketType.EQUITY


def test_strategy_get_state_includes_market_type():
    s = MinimalStrategy("test_strategy", {})
    state = s.get_state()
    assert "market_type" in state
    assert state["market_type"] == "EQUITY"


def test_strategy_missing_market_type_raises():
    """Concrete subclass without market_type should raise TypeError."""
    with pytest.raises(TypeError, match="market_type"):
        class BadStrategy(Strategy):
            def initialize(self, mode): pass
            def on_market_data(self, bar): pass
            def generate_signals(self, portfolio): return []
            def risk_check(self, signals, portfolio): return []
