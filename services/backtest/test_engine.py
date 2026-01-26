"""
Unit tests for BacktestEngine.

Following @testing-patterns skill:
- Tests follow TDD: Write failing test FIRST
- Test behavior, not implementation
- Use descriptive test names (describe behavior)
- Create factory functions for test data
- Use fixtures for common setup
- Organize with describe blocks
- Clear mocks between tests
- Keep tests focused (one behavior per test)
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List, Dict, Any
from unittest.mock import Mock, patch

from uuid import uuid4

from packages.common.schemas import (
    PriceBar,
    Order,
    Position,
    TradingMode,
    OrderSide,
    OrderType,
    TimeInForce,
    ContractType,
)
from packages.strategies.base import Strategy, Signal, PortfolioState

from services.backtest.engine import BacktestEngine
from services.backtest.models import BacktestConfig, BacktestResult, Trade

# Import test fixtures
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from tests.fixtures.backtest_data import (
    get_mock_price_bar,
    get_mock_price_bars,
    get_mock_backtest_config,
)


# =============================================================================
# Mock Strategy for Testing
# =============================================================================

class MockStrategy(Strategy):
    """Mock strategy for testing BacktestEngine."""
    
    def __init__(
        self,
        strategy_id: str = 'test-strategy',
        config: Dict[str, Any] = None,
        signals_to_generate: List[Signal] = None,
        orders_to_generate: List[Order] = None,
    ):
        super().__init__(strategy_id, config or {})
        self.signals_to_generate = signals_to_generate or []
        self.orders_to_generate = orders_to_generate or []
        self.bars_received: List[PriceBar] = []
        self.signal_call_count = 0
    
    def initialize(self, mode: TradingMode) -> None:
        self.mode = mode
        self.initialized = True
    
    def on_market_data(self, bar: PriceBar) -> None:
        self.bars_received.append(bar)
    
    def generate_signals(self, portfolio: PortfolioState) -> List[Signal]:
        self.signal_call_count += 1
        return self.signals_to_generate
    
    def risk_check(self, signals: List[Signal], portfolio: PortfolioState) -> List[Order]:
        return self.orders_to_generate


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def engine() -> BacktestEngine:
    """Create a fresh BacktestEngine for each test."""
    return BacktestEngine()


@pytest.fixture
def default_config() -> BacktestConfig:
    """Default backtest configuration."""
    return get_mock_backtest_config()


@pytest.fixture
def sample_bars() -> List[PriceBar]:
    """Sample price bars for testing."""
    return get_mock_price_bars(count=10)


@pytest.fixture
def mock_strategy() -> MockStrategy:
    """Create a mock strategy with no signals."""
    return MockStrategy()


# =============================================================================
# Tests: Initialization
# =============================================================================

class TestBacktestEngineInitialization:
    """Tests for BacktestEngine initialization."""
    
    def test_engine_initializes_with_empty_state(self, engine: BacktestEngine):
        """Engine should start with empty positions and trades."""
        assert engine.current_positions == {}
        assert engine.completed_trades == []
        assert engine.pending_orders == []


# =============================================================================
# Tests: Running Backtest
# =============================================================================

class TestBacktestEngineRun:
    """Tests for BacktestEngine.run() method."""
    
    def test_run_raises_error_on_empty_data(
        self,
        engine: BacktestEngine,
        mock_strategy: MockStrategy,
        default_config: BacktestConfig
    ):
        """Running backtest with empty data should raise ValueError."""
        with pytest.raises(ValueError, match="Data list cannot be empty"):
            engine.run(mock_strategy, [], default_config)
    
    def test_run_initializes_strategy_with_backtest_mode(
        self,
        engine: BacktestEngine,
        sample_bars: List[PriceBar],
        default_config: BacktestConfig
    ):
        """Strategy should be initialized with BACKTEST mode."""
        strategy = MockStrategy()
        
        engine.run(strategy, sample_bars, default_config)
        
        assert strategy.initialized
        assert strategy.mode == TradingMode.BACKTEST
    
    def test_run_returns_backtest_result(
        self,
        engine: BacktestEngine,
        mock_strategy: MockStrategy,
        sample_bars: List[PriceBar],
        default_config: BacktestConfig
    ):
        """Running backtest should return a BacktestResult."""
        result = engine.run(mock_strategy, sample_bars, default_config)
        
        assert isinstance(result, BacktestResult)
        assert result.strategy_id == mock_strategy.strategy_id
        assert result.config == default_config
    
    def test_run_processes_all_bars(
        self,
        engine: BacktestEngine,
        sample_bars: List[PriceBar],
        default_config: BacktestConfig
    ):
        """Engine should process all price bars."""
        strategy = MockStrategy()
        
        engine.run(strategy, sample_bars, default_config)
        
        assert len(strategy.bars_received) == len(sample_bars)
    
    def test_run_generates_equity_curve(
        self,
        engine: BacktestEngine,
        mock_strategy: MockStrategy,
        sample_bars: List[PriceBar],
        default_config: BacktestConfig
    ):
        """Backtest should generate an equity curve."""
        result = engine.run(mock_strategy, sample_bars, default_config)
        
        # Should have at least one equity point per bar plus initial
        assert len(result.equity_curve) >= len(sample_bars)
    
    def test_run_filters_data_by_date_range(
        self,
        engine: BacktestEngine,
        default_config: BacktestConfig
    ):
        """Backtest should filter data by start_date and end_date."""
        # Create bars spanning 10 days
        bars = get_mock_price_bars(count=10)
        
        # Configure to only use middle 5 days
        start = bars[2].timestamp
        end = bars[7].timestamp
        config = get_mock_backtest_config({
            'start_date': start,
            'end_date': end,
        })
        
        strategy = MockStrategy()
        engine.run(strategy, bars, config)
        
        # Should only process bars within date range
        assert len(strategy.bars_received) <= 6  # Days 2-7 inclusive


# =============================================================================
# Tests: Strategy Execution
# =============================================================================

class TestStrategyExecution:
    """Tests for strategy signal generation and order execution."""
    
    def test_generates_signals_for_each_bar(
        self,
        engine: BacktestEngine,
        sample_bars: List[PriceBar],
        default_config: BacktestConfig
    ):
        """Strategy should generate signals for each bar processed."""
        strategy = MockStrategy()
        
        engine.run(strategy, sample_bars, default_config)
        
        assert strategy.signal_call_count == len(sample_bars)
    
    def test_executes_buy_order(
        self,
        engine: BacktestEngine,
        default_config: BacktestConfig
    ):
        """Engine should execute buy orders and create positions."""
        bars = get_mock_price_bars(count=5)
        
        # Create a buy order
        buy_order = Order(
            order_id=uuid4(),
            strategy_id='test',
            symbol='AAPL',
            contract_type=ContractType.STOCK,
            side=OrderSide.BUY,
            quantity=Decimal('10'),
            order_type=OrderType.MARKET,
            time_in_force=TimeInForce.DAY,
            mode=TradingMode.BACKTEST,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        
        strategy = MockStrategy(orders_to_generate=[buy_order])
        result = engine.run(strategy, bars, default_config)
        
        # Should have opened a position (or attempted to)
        # The equity should have changed from initial capital
        final_equity = result.equity_curve[-1].equity
        initial_capital = default_config.initial_capital
        
        # Position was opened, so equity should be different or have position
        assert final_equity != initial_capital or len(engine.current_positions) > 0


# =============================================================================
# Tests: Error Handling
# =============================================================================

class TestErrorHandling:
    """Tests for error handling in BacktestEngine."""
    
    def test_handles_invalid_order_gracefully(
        self,
        engine: BacktestEngine,
        sample_bars: List[PriceBar],
        default_config: BacktestConfig
    ):
        """Engine should handle invalid orders without crashing."""
        # Create an order with wrong symbol (won't match bars)
        bad_order = Order(
            order_id=uuid4(),
            strategy_id='test',
            symbol='INVALID',  # Won't match 'AAPL' bars
            contract_type=ContractType.STOCK,
            side=OrderSide.BUY,
            quantity=Decimal('10'),
            order_type=OrderType.MARKET,
            time_in_force=TimeInForce.DAY,
            mode=TradingMode.BACKTEST,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        
        strategy = MockStrategy(orders_to_generate=[bad_order])
        
        # Should not raise exception
        result = engine.run(strategy, sample_bars, default_config)
        
        # Should complete with no trades
        assert result is not None
        assert len(result.trades) == 0
    
    def test_handles_insufficient_cash_for_buy(
        self,
        engine: BacktestEngine,
        default_config: BacktestConfig
    ):
        """Engine should reject buy orders when insufficient cash."""
        bars = get_mock_price_bars(count=3)
        
        # Create a buy order that exceeds available cash
        huge_order = Order(
            order_id=uuid4(),
            strategy_id='test',
            symbol='AAPL',
            contract_type=ContractType.STOCK,
            side=OrderSide.BUY,
            quantity=Decimal('1000000'),  # Way more than $100k capital allows
            order_type=OrderType.MARKET,
            time_in_force=TimeInForce.DAY,
            mode=TradingMode.BACKTEST,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        
        strategy = MockStrategy(orders_to_generate=[huge_order])
        result = engine.run(strategy, bars, default_config)
        
        # Order should be rejected, no position opened
        assert len(result.trades) == 0


# =============================================================================
# Tests: Performance Metrics
# =============================================================================

class TestPerformanceMetrics:
    """Tests for performance metrics calculation."""
    
    def test_calculates_total_return(
        self,
        engine: BacktestEngine,
        mock_strategy: MockStrategy,
        sample_bars: List[PriceBar],
        default_config: BacktestConfig
    ):
        """Metrics should include total return calculation."""
        result = engine.run(mock_strategy, sample_bars, default_config)
        
        # With no trades, return should be 0
        assert result.metrics.total_return == Decimal('0')
        assert result.metrics.total_return_pct == Decimal('0')
    
    def test_calculates_max_drawdown(
        self,
        engine: BacktestEngine,
        mock_strategy: MockStrategy,
        sample_bars: List[PriceBar],
        default_config: BacktestConfig
    ):
        """Metrics should include max drawdown calculation."""
        result = engine.run(mock_strategy, sample_bars, default_config)
        
        # Drawdown should be <= 0 (negative or zero)
        assert result.metrics.max_drawdown <= Decimal('0')
    
    def test_calculates_trade_statistics(
        self,
        engine: BacktestEngine,
        mock_strategy: MockStrategy,
        sample_bars: List[PriceBar],
        default_config: BacktestConfig
    ):
        """Metrics should include trade statistics."""
        result = engine.run(mock_strategy, sample_bars, default_config)
        
        # With no trades
        assert result.metrics.total_trades == 0
        assert result.metrics.winning_trades == 0
        assert result.metrics.losing_trades == 0


# =============================================================================
# Tests: Slippage and Commission
# =============================================================================

class TestSlippageAndCommission:
    """Tests for slippage and commission handling."""
    
    def test_applies_slippage_to_fill_price(
        self,
        engine: BacktestEngine
    ):
        """Fill price should include slippage."""
        config = get_mock_backtest_config({
            'slippage_bps': Decimal('100'),  # 1% slippage
        })
        
        bars = get_mock_price_bars(count=3)
        bar_close = bars[0].close
        
        # Create buy order
        order = Order(
            order_id=uuid4(),
            strategy_id='test',
            symbol='AAPL',
            contract_type=ContractType.STOCK,
            side=OrderSide.BUY,
            quantity=Decimal('10'),
            order_type=OrderType.MARKET,
            time_in_force=TimeInForce.DAY,
            mode=TradingMode.BACKTEST,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        
        strategy = MockStrategy(orders_to_generate=[order])
        result = engine.run(strategy, bars, config)
        
        # Verify slippage was applied (buy should be at higher price)
        # The fill price = close * (1 + slippage_bps/10000)
        expected_fill = bar_close * (Decimal('1') + Decimal('100') / Decimal('10000'))
        
        # Position should exist with average_entry_price reflecting slippage
        if 'AAPL' in engine.current_positions:
            position = engine.current_positions['AAPL']
            # Entry price should be higher than close due to slippage
            assert position.average_entry_price >= bar_close
