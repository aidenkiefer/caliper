"""
Test script for SMA Crossover Strategy.

Verifies that the strategy generates signals correctly on static data.
"""

from datetime import datetime, timedelta
from decimal import Decimal

from packages.common.schemas import PriceBar, TradingMode
from .sma_crossover import SMACrossoverStrategy
from .base import PortfolioState


def create_test_bars(symbol: str = "AAPL", days: int = 100) -> list[PriceBar]:
    """Create test price bars with a clear trend."""
    bars = []
    base_price = 150.0
    
    for i in range(days):
        # Create a trend: prices go up, then down (to trigger crossovers)
        if i < 30:
            # Initial uptrend
            price = base_price + (i * 0.5)
        elif i < 60:
            # Strong uptrend (should trigger golden cross)
            price = base_price + 15 + ((i - 30) * 1.0)
        else:
            # Downtrend (should trigger death cross)
            price = base_price + 45 - ((i - 60) * 0.8)
        
        bar = PriceBar(
            symbol=symbol,
            exchange=None,
            timestamp=datetime.now() - timedelta(days=days-i),
            timeframe="1day",
            open=Decimal(str(price)),
            high=Decimal(str(price * 1.02)),
            low=Decimal(str(price * 0.98)),
            close=Decimal(str(price)),
            volume=1000000,
            source="test"
        )
        bars.append(bar)
    
    return bars


def test_strategy_signals():
    """Test that strategy generates signals correctly."""
    print("=" * 60)
    print("Testing SMA Crossover Strategy")
    print("=" * 60)
    
    # Create strategy
    config = {
        'short_period': 20,
        'long_period': 50,
        'position_size_pct': 0.1,
        'min_signal_strength': 0.5,
    }
    
    strategy = SMACrossoverStrategy("test_sma", config)
    strategy.initialize(TradingMode.BACKTEST)
    
    # Create test data
    bars = create_test_bars("AAPL", days=100)
    
    print(f"\nCreated {len(bars)} test bars")
    print(f"Price range: ${float(bars[0].close):.2f} to ${float(bars[-1].close):.2f}")
    
    # Feed bars to strategy
    signals_generated = []
    
    for i, bar in enumerate(bars):
        strategy.on_market_data(bar)
        
        # Generate signals every 5 bars (simulate periodic signal generation)
        if i % 5 == 0 and i >= 50:  # Need at least 50 bars for long SMA
            portfolio = PortfolioState(
                equity=Decimal("100000"),
                cash=Decimal("100000"),
                positions=[],
            )
            
            signals = strategy.generate_signals(portfolio)
            
            if signals:
                for signal in signals:
                    signals_generated.append((i, signal))
                    print(f"\nBar {i} ({bar.timestamp.date()}): {signal}")
                    print(f"  Reason: {signal.reason}")
    
    # Verify we got signals
    assert len(signals_generated) > 0, "Strategy should generate at least one signal"
    
    print(f"\n✅ Strategy generated {len(signals_generated)} signals")
    
    # Test risk check
    print("\n" + "=" * 60)
    print("Testing Risk Check")
    print("=" * 60)
    
    # Get latest signals
    if signals_generated:
        latest_bar_idx, latest_signal = signals_generated[-1]
        
        portfolio = PortfolioState(
            equity=Decimal("100000"),
            cash=Decimal("50000"),
            positions=[],
        )
        
        orders = strategy.risk_check([latest_signal], portfolio)
        
        if orders:
            order = orders[0]
            print(f"\n✅ Risk check approved order:")
            print(f"  Symbol: {order.symbol}")
            print(f"  Side: {order.side}")
            print(f"  Quantity: {order.quantity}")
            print(f"  Order Type: {order.order_type}")
        else:
            print("\n⚠️  Risk check filtered out signal (this is OK if signal strength was too low)")
    
    # Test strategy state
    state = strategy.get_state()
    print(f"\n✅ Strategy state: {state}")
    
    print("\n" + "=" * 60)
    print("✅ All strategy tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    test_strategy_signals()
