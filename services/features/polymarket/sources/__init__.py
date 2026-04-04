"""
Data sources for the Polymarket feature pipeline (Sprint 12).

Exports
-------
CLOBSource        — async CLOB data source (WebSocket buffer + REST lookups)
OrderbookState    — dataclass snapshot of the live orderbook
RewardConfig      — dataclass for market reward eligibility config
DataUnavailable   — raised when no buffered data is available yet
"""

from services.features.polymarket.sources.clob import (
    CLOBSource,
    DataUnavailable,
    OrderbookState,
    RewardConfig,
)

__all__ = [
    "CLOBSource",
    "DataUnavailable",
    "OrderbookState",
    "RewardConfig",
]
