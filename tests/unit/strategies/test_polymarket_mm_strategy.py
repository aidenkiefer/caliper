from decimal import Decimal
import pytest
from packages.common.market_schemas import MarketType, SignalType, UnifiedSignal
from packages.common.schemas import TradingMode
from packages.strategies.polymarket_mm_strategy import PolymarketMMStrategy
from packages.strategies.base import PortfolioState


def _make_ob_state(midpoint=None, spread=None):
    """Minimal stub matching what DataFeed.get_current_state() returns."""
    class State:
        pass
    s = State()
    s.midpoint = Decimal(str(midpoint)) if midpoint is not None else None
    s.spread = Decimal(str(spread)) if spread is not None else None
    return s


_CONFIG = {
    "market_id": "BTC-UP-2026-04-04T15",
    "quote_spread": "0.02",
    "quote_size": "50",
    "inventory_cap": "200",
}


def test_mm_strategy_market_type():
    s = PolymarketMMStrategy("pm_mm_test", _CONFIG)
    assert s.market_type == MarketType.PREDICTION


def test_mm_strategy_generates_mm_signal():
    s = PolymarketMMStrategy("pm_mm_test", _CONFIG)
    s.initialize(TradingMode.LIVE)
    s.on_market_data(_make_ob_state(midpoint="0.55", spread="0.02"))
    portfolio = PortfolioState(equity=Decimal("1000"), cash=Decimal("1000"), positions=[])
    signals = s.generate_signals(portfolio)
    assert len(signals) == 1
    sig = signals[0]
    assert isinstance(sig, UnifiedSignal)
    assert sig.signal_type == SignalType.MARKET_MAKING
    assert sig.direction == "none"
    assert sig.market_type == MarketType.PREDICTION
    assert "bid_price" in sig.metadata
    assert "ask_price" in sig.metadata
    assert "bid_size" in sig.metadata
    assert "ask_size" in sig.metadata


def test_mm_strategy_suppresses_when_no_data():
    s = PolymarketMMStrategy("pm_mm_test", _CONFIG)
    s.initialize(TradingMode.LIVE)
    # No on_market_data call → no state
    portfolio = PortfolioState(equity=Decimal("1000"), cash=Decimal("1000"), positions=[])
    signals = s.generate_signals(portfolio)
    assert signals == []


def test_mm_strategy_suppresses_when_stale_midpoint():
    s = PolymarketMMStrategy("pm_mm_test", _CONFIG)
    s.initialize(TradingMode.LIVE)
    s.on_market_data(_make_ob_state(midpoint=None, spread=None))
    portfolio = PortfolioState(equity=Decimal("1000"), cash=Decimal("1000"), positions=[])
    signals = s.generate_signals(portfolio)
    assert signals == []


def test_mm_strategy_suppresses_when_spread_too_wide():
    s = PolymarketMMStrategy("pm_mm_test", _CONFIG)
    s.initialize(TradingMode.LIVE)
    s.on_market_data(_make_ob_state(midpoint="0.50", spread="0.15"))  # > 0.10 max
    portfolio = PortfolioState(equity=Decimal("1000"), cash=Decimal("1000"), positions=[])
    signals = s.generate_signals(portfolio)
    assert signals == []


def test_mm_strategy_suppresses_bid_when_inventory_at_cap():
    s = PolymarketMMStrategy("pm_mm_test", _CONFIG)
    s.initialize(TradingMode.LIVE)
    s.update_inventory(Decimal("200"))  # at cap
    s.on_market_data(_make_ob_state(midpoint="0.55", spread="0.02"))
    portfolio = PortfolioState(equity=Decimal("1000"), cash=Decimal("1000"), positions=[])
    signals = s.generate_signals(portfolio)
    # bid suppressed (at cap), ask_size = quote_size (inventory > 0)
    assert len(signals) == 1
    sig = signals[0]
    assert sig.metadata["bid_size"] == "0"
    assert sig.metadata["ask_size"] == "50"


def test_mm_strategy_risk_check_returns_empty():
    """MM strategy risk_check always returns [] — executor handles orders directly."""
    s = PolymarketMMStrategy("pm_mm_test", _CONFIG)
    s.initialize(TradingMode.LIVE)
    portfolio = PortfolioState(equity=Decimal("1000"), cash=Decimal("1000"), positions=[])
    result = s.risk_check([], portfolio)
    assert result == []
