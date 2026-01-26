"""
Technical indicator calculators.

Since pandas-ta requires Python 3.12+, we implement indicators manually
using pandas and numpy for Python 3.11 compatibility.
"""

import pandas as pd
import numpy as np
from typing import Optional


def sma(series: pd.Series, period: int) -> pd.Series:
    """
    Simple Moving Average (SMA).
    
    Args:
        series: Price series (typically close prices)
        period: Number of periods for moving average
        
    Returns:
        Series with SMA values
    """
    return series.rolling(window=period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    """
    Exponential Moving Average (EMA).
    
    Args:
        series: Price series
        period: Number of periods for EMA
        
    Returns:
        Series with EMA values
    """
    return series.ewm(span=period, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Relative Strength Index (RSI).
    
    RSI measures the speed and magnitude of price changes.
    Values range from 0 to 100:
    - RSI > 70: Overbought (potential sell signal)
    - RSI < 30: Oversold (potential buy signal)
    
    Args:
        series: Price series (typically close prices)
        period: Number of periods (default: 14)
        
    Returns:
        Series with RSI values (0-100)
    """
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def macd(
    series: pd.Series,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> pd.DataFrame:
    """
    Moving Average Convergence Divergence (MACD).
    
    MACD is a trend-following momentum indicator.
    
    Args:
        series: Price series (typically close prices)
        fast_period: Fast EMA period (default: 12)
        slow_period: Slow EMA period (default: 26)
        signal_period: Signal line EMA period (default: 9)
        
    Returns:
        DataFrame with columns: 'macd', 'signal', 'histogram'
    """
    ema_fast = ema(series, fast_period)
    ema_slow = ema(series, slow_period)
    
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal_period)
    histogram = macd_line - signal_line
    
    return pd.DataFrame({
        'macd': macd_line,
        'signal': signal_line,
        'histogram': histogram
    })


def bollinger_bands(
    series: pd.Series,
    period: int = 20,
    num_std: float = 2.0
) -> pd.DataFrame:
    """
    Bollinger Bands.
    
    Bollinger Bands consist of:
    - Middle band: SMA
    - Upper band: SMA + (num_std * standard deviation)
    - Lower band: SMA - (num_std * standard deviation)
    
    Args:
        series: Price series (typically close prices)
        period: Number of periods for SMA (default: 20)
        num_std: Number of standard deviations (default: 2.0)
        
    Returns:
        DataFrame with columns: 'upper', 'middle', 'lower'
    """
    middle = sma(series, period)
    std = series.rolling(window=period).std()
    
    upper = middle + (std * num_std)
    lower = middle - (std * num_std)
    
    return pd.DataFrame({
        'upper': upper,
        'middle': middle,
        'lower': lower
    })


def atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14
) -> pd.Series:
    """
    Average True Range (ATR).
    
    ATR measures market volatility.
    
    Args:
        high: High prices
        low: Low prices
        close: Close prices
        period: Number of periods (default: 14)
        
    Returns:
        Series with ATR values
    """
    high_low = high - low
    high_close = np.abs(high - close.shift())
    low_close = np.abs(low - close.shift())
    
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = true_range.rolling(window=period).mean()
    
    return atr


def stochastic(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    k_period: int = 14,
    d_period: int = 3
) -> pd.DataFrame:
    """
    Stochastic Oscillator (%K and %D).
    
    Measures momentum by comparing closing price to price range.
    Values range from 0 to 100.
    
    Args:
        high: High prices
        low: Low prices
        close: Close prices
        k_period: %K period (default: 14)
        d_period: %D period (default: 3)
        
    Returns:
        DataFrame with columns: 'k', 'd'
    """
    lowest_low = low.rolling(window=k_period).min()
    highest_high = high.rolling(window=k_period).max()
    
    k = 100 * ((close - lowest_low) / (highest_high - lowest_low))
    d = k.rolling(window=d_period).mean()
    
    return pd.DataFrame({
        'k': k,
        'd': d
    })
