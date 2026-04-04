"""
Data sources for the Polymarket feature pipeline (Sprint 12).

Exports
-------
CLOBSource        — async CLOB data source (WebSocket buffer + REST lookups)
OrderbookState    — dataclass snapshot of the live orderbook
RewardConfig      — dataclass for market reward eligibility config
DataUnavailable   — raised when no buffered data is available yet
BinanceSource     — async Binance kline + premium index data source
KlineBar          — named-tuple for one 1-minute OHLCV kline
PremiumIndex      — dataclass for perpetual futures premium index snapshot
"""

from services.features.polymarket.sources.clob import (
    CLOBSource,
    DataUnavailable,
    OrderbookState,
    RewardConfig,
)
from services.features.polymarket.sources.binance import (
    BinanceSource,
    KlineBar,
    PremiumIndex,
)

__all__ = [
    "CLOBSource",
    "DataUnavailable",
    "OrderbookState",
    "RewardConfig",
    "BinanceSource",
    "KlineBar",
    "PremiumIndex",
]
