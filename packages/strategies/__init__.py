"""Strategy plugins package."""

from .base import Strategy, Signal, PortfolioState
from .sma_crossover import SMACrossoverStrategy
from .ml_direction_v1 import MLDirectionStrategyV1
from packages.common.market_schemas import UnifiedSignal, MarketType

__all__ = [
    "Strategy",
    "Signal",  # legacy — use UnifiedSignal in new code
    "PortfolioState",
    "SMACrossoverStrategy",
    "MLDirectionStrategyV1",
    "UnifiedSignal",
    "MarketType",
]

__version__ = "0.1.0"
