"""
Test fixtures for backtesting.

Factory functions following @testing-patterns skill:
- get_mock_x(overrides?: Partial<X>) pattern
- Sensible defaults with override capability
- Keeps tests DRY and maintainable
"""

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List
from uuid import uuid4

from packages.common.schemas import PriceBar
from services.backtest.models import (
    BacktestConfig,
    Trade,
    EquityPoint,
    PerformanceMetrics,
    BacktestResult,
)


def get_mock_price_bar(overrides: Optional[Dict[str, Any]] = None) -> PriceBar:
    """
    Factory function for PriceBar test data.
    
    Args:
        overrides: Optional dictionary of fields to override
        
    Returns:
        PriceBar with sensible defaults, overridden by provided values
        
    Example:
        >>> bar = get_mock_price_bar({'close': Decimal('155.00')})
        >>> assert bar.close == Decimal('155.00')
    """
    defaults = {
        'symbol': 'AAPL',
        'exchange': 'NASDAQ',
        'timestamp': datetime(2024, 1, 15, 14, 30, 0, tzinfo=timezone.utc),
        'timeframe': '1day',
        'open': Decimal('150.00'),
        'high': Decimal('152.00'),
        'low': Decimal('149.00'),
        'close': Decimal('151.00'),
        'volume': 1000000,
        'vwap': Decimal('150.50'),
        'trade_count': 5000,
        'source': 'alpaca',
    }
    
    if overrides:
        defaults.update(overrides)
    
    return PriceBar(**defaults)


def get_mock_price_bars(
    count: int = 100,
    start_date: Optional[datetime] = None,
    start_price: Decimal = Decimal('150.00'),
    symbol: str = 'AAPL',
    trend: str = 'random'
) -> List[PriceBar]:
    """
    Generate a list of mock price bars for testing.
    
    Args:
        count: Number of bars to generate
        start_date: Starting date (defaults to 2024-01-01)
        start_price: Starting close price
        symbol: Stock symbol
        trend: 'up', 'down', or 'random'
        
    Returns:
        List of PriceBar objects
    """
    import random
    
    if start_date is None:
        start_date = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    
    bars = []
    current_price = float(start_price)
    
    for i in range(count):
        # Calculate price movement
        if trend == 'up':
            change_pct = random.uniform(0.0, 0.02)
        elif trend == 'down':
            change_pct = random.uniform(-0.02, 0.0)
        else:
            change_pct = random.uniform(-0.02, 0.02)
        
        current_price = current_price * (1 + change_pct)
        
        # Generate OHLC with realistic relationships
        open_price = current_price * random.uniform(0.98, 1.02)
        high_price = max(open_price, current_price) * random.uniform(1.0, 1.01)
        low_price = min(open_price, current_price) * random.uniform(0.99, 1.0)
        close_price = current_price
        
        bar = get_mock_price_bar({
            'symbol': symbol,
            'timestamp': start_date + timedelta(days=i),
            'open': Decimal(str(round(open_price, 2))),
            'high': Decimal(str(round(high_price, 2))),
            'low': Decimal(str(round(low_price, 2))),
            'close': Decimal(str(round(close_price, 2))),
            'volume': random.randint(500000, 2000000),
        })
        bars.append(bar)
    
    return bars


def get_mock_backtest_config(overrides: Optional[Dict[str, Any]] = None) -> BacktestConfig:
    """
    Factory function for BacktestConfig test data.
    
    Args:
        overrides: Optional dictionary of fields to override
        
    Returns:
        BacktestConfig with sensible defaults
        
    Example:
        >>> config = get_mock_backtest_config({'initial_capital': Decimal('50000')})
        >>> assert config.initial_capital == Decimal('50000')
    """
    defaults = {
        'initial_capital': Decimal('100000'),
        'commission_per_trade': Decimal('1.00'),
        'slippage_bps': Decimal('10'),
        'start_date': None,
        'end_date': None,
    }
    
    if overrides:
        defaults.update(overrides)
    
    return BacktestConfig(**defaults)


def get_mock_trade(overrides: Optional[Dict[str, Any]] = None) -> Trade:
    """
    Factory function for Trade test data.
    
    Args:
        overrides: Optional dictionary of fields to override
        
    Returns:
        Trade with sensible defaults
        
    Example:
        >>> trade = get_mock_trade({'pnl': Decimal('500')})
        >>> assert trade.pnl == Decimal('500')
    """
    entry_time = datetime(2024, 1, 15, 9, 30, 0, tzinfo=timezone.utc)
    exit_time = datetime(2024, 1, 20, 16, 0, 0, tzinfo=timezone.utc)
    
    defaults = {
        'trade_id': uuid4(),
        'symbol': 'AAPL',
        'entry_time': entry_time,
        'exit_time': exit_time,
        'entry_price': Decimal('150.00'),
        'exit_price': Decimal('155.00'),
        'quantity': Decimal('100'),
        'commission': Decimal('2.00'),
        'pnl': Decimal('498.00'),  # (155-150)*100 - 2 = 498
        'return_pct': Decimal('3.33'),
    }
    
    if overrides:
        defaults.update(overrides)
    
    return Trade(**defaults)


def get_mock_equity_point(overrides: Optional[Dict[str, Any]] = None) -> EquityPoint:
    """
    Factory function for EquityPoint test data.
    
    Args:
        overrides: Optional dictionary of fields to override
        
    Returns:
        EquityPoint with sensible defaults
    """
    defaults = {
        'timestamp': datetime(2024, 1, 15, 16, 0, 0, tzinfo=timezone.utc),
        'equity': Decimal('100000'),
        'cash': Decimal('80000'),
        'unrealized_pnl': Decimal('0'),
    }
    
    if overrides:
        defaults.update(overrides)
    
    return EquityPoint(**defaults)


def get_mock_performance_metrics(overrides: Optional[Dict[str, Any]] = None) -> PerformanceMetrics:
    """
    Factory function for PerformanceMetrics test data.
    
    Args:
        overrides: Optional dictionary of fields to override
        
    Returns:
        PerformanceMetrics with sensible defaults
    """
    defaults = {
        'total_return': Decimal('0.15'),
        'total_return_pct': Decimal('15.00'),
        'sharpe_ratio': Decimal('1.5'),
        'max_drawdown': Decimal('-5000'),
        'max_drawdown_pct': Decimal('-5.00'),
        'win_rate': Decimal('0.60'),
        'total_trades': 10,
        'winning_trades': 6,
        'losing_trades': 4,
        'avg_win': Decimal('500'),
        'avg_loss': Decimal('-250'),
        'profit_factor': Decimal('2.0'),
    }
    
    if overrides:
        defaults.update(overrides)
    
    return PerformanceMetrics(**defaults)


def get_sample_aapl_bars(days: int = 100) -> List[PriceBar]:
    """
    Get realistic AAPL price data for integration tests.
    
    This generates deterministic data based on historical AAPL patterns:
    - Starting price around $150
    - Daily volatility around 1-2%
    - Slight upward trend
    
    Args:
        days: Number of trading days of data
        
    Returns:
        List of PriceBar objects simulating AAPL price history
    """
    import random
    
    # Set seed for deterministic results in tests
    random.seed(42)
    
    start_date = datetime(2024, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
    start_price = Decimal('150.00')
    
    bars = []
    current_price = float(start_price)
    
    for i in range(days):
        # Skip weekends for realism
        current_date = start_date + timedelta(days=i)
        if current_date.weekday() >= 5:
            continue
        
        # Slight upward bias (0.05% daily on average)
        daily_return = random.gauss(0.0005, 0.015)
        current_price = current_price * (1 + daily_return)
        
        # Generate realistic OHLC
        intraday_volatility = abs(random.gauss(0, 0.008))
        open_price = current_price * (1 + random.gauss(0, 0.003))
        high_price = max(open_price, current_price) * (1 + intraday_volatility)
        low_price = min(open_price, current_price) * (1 - intraday_volatility)
        
        bar = get_mock_price_bar({
            'symbol': 'AAPL',
            'timestamp': current_date,
            'open': Decimal(str(round(open_price, 2))),
            'high': Decimal(str(round(high_price, 2))),
            'low': Decimal(str(round(low_price, 2))),
            'close': Decimal(str(round(current_price, 2))),
            'volume': random.randint(50000000, 100000000),
            'trade_count': random.randint(300000, 600000),
        })
        bars.append(bar)
    
    # Reset random seed
    random.seed()
    
    return bars


# Known-good test scenario for P&L validation
# Buy 100 shares @ $150, Sell @ $155, Commission $2 total → P&L = $498
KNOWN_GOOD_PNL_SCENARIO = {
    'entry_price': Decimal('150.00'),
    'exit_price': Decimal('155.00'),
    'quantity': Decimal('100'),
    'commission': Decimal('2.00'),
    'expected_pnl': Decimal('498.00'),  # (155-150)*100 - 2
}
