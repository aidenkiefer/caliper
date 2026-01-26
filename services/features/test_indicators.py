"""
Test script to verify indicator calculations.

Compares our implementations against known-good values.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from .indicators import sma, ema, rsi, macd, bollinger_bands


def create_test_data(days: int = 100) -> pd.DataFrame:
    """Create synthetic price data for testing."""
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
    
    # Generate random walk price data
    np.random.seed(42)
    returns = np.random.normal(0.001, 0.02, days)  # Small positive drift
    prices = 100 * (1 + returns).cumprod()
    
    # Add some volatility
    highs = prices * (1 + np.abs(np.random.normal(0, 0.01, days)))
    lows = prices * (1 - np.abs(np.random.normal(0, 0.01, days)))
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': highs,
        'low': lows,
        'close': prices,
        'volume': np.random.randint(1000000, 10000000, days),
    })
    
    return df


def test_sma():
    """Test Simple Moving Average."""
    print("Testing SMA...")
    df = create_test_data(50)
    
    sma_20 = sma(df['close'], 20)
    
    # Verify SMA properties
    assert not sma_20.iloc[:19].notna().any(), "SMA should be NaN for first 19 values"
    assert sma_20.iloc[19] == df['close'].iloc[:20].mean(), "SMA(20) should equal mean of first 20 values"
    assert sma_20.iloc[-1] == df['close'].iloc[-20:].mean(), "Last SMA should equal mean of last 20 values"
    
    print("✅ SMA test passed")


def test_rsi():
    """Test Relative Strength Index."""
    print("Testing RSI...")
    df = create_test_data(30)
    
    rsi_14 = rsi(df['close'], 14)
    
    # Verify RSI properties
    assert not rsi_14.iloc[:13].notna().any(), "RSI should be NaN for first 13 values"
    assert all(0 <= val <= 100 for val in rsi_14.dropna()), "RSI should be between 0 and 100"
    
    print("✅ RSI test passed")


def test_macd():
    """Test MACD."""
    print("Testing MACD...")
    df = create_test_data(50)
    
    macd_result = macd(df['close'])
    
    # Verify MACD structure
    assert 'macd' in macd_result.columns
    assert 'signal' in macd_result.columns
    assert 'histogram' in macd_result.columns
    
    # Verify histogram = macd - signal
    assert np.allclose(
        macd_result['histogram'],
        macd_result['macd'] - macd_result['signal'],
        equal_nan=True
    ), "Histogram should equal MACD - Signal"
    
    print("✅ MACD test passed")


def test_bollinger_bands():
    """Test Bollinger Bands."""
    print("Testing Bollinger Bands...")
    df = create_test_data(50)
    
    bb = bollinger_bands(df['close'])
    
    # Verify structure
    assert 'upper' in bb.columns
    assert 'middle' in bb.columns
    assert 'lower' in bb.columns
    
    # Verify middle = SMA
    sma_20 = sma(df['close'], 20)
    assert np.allclose(bb['middle'], sma_20, equal_nan=True), "Middle band should equal SMA"
    
    # Verify upper > middle > lower
    valid_mask = bb['upper'].notna()
    assert all(bb.loc[valid_mask, 'upper'] >= bb.loc[valid_mask, 'middle']), "Upper should be >= Middle"
    assert all(bb.loc[valid_mask, 'middle'] >= bb.loc[valid_mask, 'lower']), "Middle should be >= Lower"
    
    print("✅ Bollinger Bands test passed")


def run_all_tests():
    """Run all indicator tests."""
    print("=" * 50)
    print("Running Indicator Verification Tests")
    print("=" * 50)
    
    try:
        test_sma()
        test_rsi()
        test_macd()
        test_bollinger_bands()
        
        print("=" * 50)
        print("✅ All indicator tests passed!")
        print("=" * 50)
        
    except AssertionError as e:
        print(f"❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    run_all_tests()
