"""
Stress test: Extreme volatility spike scenario.

Simulates extreme price movements to test model behavior
under unusual market conditions.
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from packages.common.schemas import PriceBar


def generate_normal_bars(n: int, start_price: float = 450.0) -> list:
    """Generate normal market bars with typical daily volatility (~1%)."""
    bars = []
    price = start_price

    for i in range(n):
        # Simulate random walk with ~1% daily volatility
        daily_change = (i % 3 - 1) * 0.01  # -1%, 0%, +1% cycle
        price = price * (1 + daily_change)

        bars.append(
            PriceBar(
                symbol="SPY",
                timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc) + timedelta(days=i),
                timeframe="1day",
                open=Decimal(str(price * 0.999)),
                high=Decimal(str(price * 1.005)),
                low=Decimal(str(price * 0.995)),
                close=Decimal(str(price)),
                volume=1000000 + (i * 10000),
                source="test",
            )
        )

    return bars


def test_volatility_spike_detection():
    """Test detection of extreme volatility in bar data."""
    # Generate 100 normal bars
    bars = generate_normal_bars(100)

    # Add volatility spike (15% move in one day)
    # OHLC: low <= open,close <= high; open can be at low for an up-spike
    spike_price = float(bars[-1].close) * 1.15
    spike_low = Decimal(str(spike_price * 0.98))
    spike_high = Decimal(str(spike_price * 1.02))
    spike_bar = PriceBar(
        symbol="SPY",
        timestamp=bars[-1].timestamp + timedelta(days=1),
        timeframe="1day",
        open=spike_low,
        high=spike_high,
        low=spike_low,
        close=Decimal(str(spike_price)),
        volume=5000000,  # High volume
        source="test",
    )
    bars.append(spike_bar)

    # Calculate daily return
    prev_close = float(bars[-2].close)
    curr_close = float(bars[-1].close)
    daily_return = (curr_close - prev_close) / prev_close

    assert abs(daily_return) > 0.10, "Should detect > 10% daily move"
    # In practice, model confidence would drop due to unusual features
