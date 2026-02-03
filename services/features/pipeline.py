"""
Feature pipeline for computing technical indicators and ML features.

This module provides a unified interface for computing features from price data.
"""

from typing import Dict, List, Optional
import pandas as pd
from datetime import datetime, timedelta

from packages.common.schemas import PriceBar
from .indicators import sma, ema, rsi, macd, bollinger_bands, atr, stochastic


class FeaturePipeline:
    """
    Feature pipeline for computing technical indicators.

    Takes price bars and computes a comprehensive set of features
    for use in ML models and strategies.
    """

    def __init__(self):
        """Initialize the feature pipeline."""
        self.feature_cache: Dict[str, pd.DataFrame] = {}

    def compute_features(
        self, bars: List[PriceBar], lookback_days: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Compute features from price bars.

        Args:
            bars: List of PriceBar objects
            lookback_days: Optional limit on how many days to use

        Returns:
            DataFrame with OHLCV data and computed indicators
        """
        if not bars:
            raise ValueError("bars list cannot be empty")

        # Convert bars to DataFrame
        df = pd.DataFrame(
            [
                {
                    "timestamp": bar.timestamp,
                    "open": float(bar.open),
                    "high": float(bar.high),
                    "low": float(bar.low),
                    "close": float(bar.close),
                    "volume": bar.volume,
                }
                for bar in bars
            ]
        )

        # Sort by timestamp
        df = df.sort_values("timestamp").reset_index(drop=True)

        # Limit lookback if specified
        if lookback_days:
            cutoff_date = df["timestamp"].max() - timedelta(days=lookback_days)
            df = df[df["timestamp"] >= cutoff_date].reset_index(drop=True)

        # Compute technical indicators
        df = self._add_indicators(df)

        # Add derived features
        df = self._add_derived_features(df)

        return df

    def _add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicators to the DataFrame."""
        close = df["close"]
        high = df["high"]
        low = df["low"]
        volume = df["volume"]

        df = self._add_moving_averages(df, close)
        df = self._add_momentum_indicators(df, close, high, low)
        df = self._add_volume_indicators(df, volume)

        return df

    def _add_moving_averages(self, df: pd.DataFrame, close: pd.Series) -> pd.DataFrame:
        """Add moving average indicators."""
        df["sma_20"] = sma(close, 20)
        df["sma_50"] = sma(close, 50)
        df["sma_200"] = sma(close, 200)
        df["ema_12"] = ema(close, 12)
        df["ema_26"] = ema(close, 26)
        return df

    def _add_momentum_indicators(
        self, df: pd.DataFrame, close: pd.Series, high: pd.Series, low: pd.Series
    ) -> pd.DataFrame:
        """Add momentum and volatility indicators."""
        df["rsi_14"] = rsi(close, 14)

        macd_df = macd(close, fast_period=12, slow_period=26, signal_period=9)
        df["macd"] = macd_df["macd"]
        df["macd_signal"] = macd_df["signal"]
        df["macd_histogram"] = macd_df["histogram"]

        bb_df = bollinger_bands(close, period=20, num_std=2.0)
        df["bb_upper"] = bb_df["upper"]
        df["bb_middle"] = bb_df["middle"]
        df["bb_lower"] = bb_df["lower"]
        df["bb_width"] = (bb_df["upper"] - bb_df["lower"]) / bb_df["middle"]
        df["bb_position"] = (close - bb_df["lower"]) / (bb_df["upper"] - bb_df["lower"])

        df["atr_14"] = atr(high, low, close, period=14)

        stoch_df = stochastic(high, low, close, k_period=14, d_period=3)
        df["stoch_k"] = stoch_df["k"]
        df["stoch_d"] = stoch_df["d"]

        return df

    def _add_volume_indicators(self, df: pd.DataFrame, volume: pd.Series) -> pd.DataFrame:
        """Add volume-based indicators."""
        df["volume_sma_20"] = sma(volume, 20)
        df["volume_ratio"] = volume / df["volume_sma_20"]
        return df

    def _add_derived_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add derived features (returns, volatility, etc.)."""
        # Price returns
        df["returns"] = df["close"].pct_change()
        df["returns_1d"] = df["close"].pct_change(1)
        df["returns_5d"] = df["close"].pct_change(5)
        df["returns_10d"] = df["close"].pct_change(10)

        # Volatility (rolling standard deviation of returns)
        df["volatility_10d"] = df["returns"].rolling(window=10).std()
        df["volatility_20d"] = df["returns"].rolling(window=20).std()

        # Price position within daily range
        df["price_position"] = (df["close"] - df["low"]) / (df["high"] - df["low"])

        # High-Low spread
        df["hl_spread"] = (df["high"] - df["low"]) / df["close"]

        # Moving average crossovers
        df["sma_cross_20_50"] = (df["sma_20"] > df["sma_50"]).astype(int)
        df["sma_cross_50_200"] = (df["sma_50"] > df["sma_200"]).astype(int)

        return df

    def get_feature_names(self) -> List[str]:
        """
        Get list of all feature names computed by the pipeline.

        Returns:
            List of feature column names
        """
        # Base features
        base_features = ["open", "high", "low", "close", "volume"]

        # Indicator features
        indicator_features = [
            "sma_20",
            "sma_50",
            "sma_200",
            "ema_12",
            "ema_26",
            "rsi_14",
            "macd",
            "macd_signal",
            "macd_histogram",
            "bb_upper",
            "bb_middle",
            "bb_lower",
            "bb_width",
            "bb_position",
            "atr_14",
            "stoch_k",
            "stoch_d",
            "volume_sma_20",
            "volume_ratio",
        ]

        # Derived features
        derived_features = [
            "returns",
            "returns_1d",
            "returns_5d",
            "returns_10d",
            "volatility_10d",
            "volatility_20d",
            "price_position",
            "hl_spread",
            "sma_cross_20_50",
            "sma_cross_50_200",
        ]

        return base_features + indicator_features + derived_features
