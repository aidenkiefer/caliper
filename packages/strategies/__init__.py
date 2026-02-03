"""Strategy plugins package."""

from .base import Strategy, Signal, PortfolioState
from .sma_crossover import SMACrossoverStrategy
from .ml_direction_v1 import MLDirectionStrategyV1

__all__ = [
    "Strategy",
    "Signal",
    "PortfolioState",
    "SMACrossoverStrategy",
    "MLDirectionStrategyV1",
]

__version__ = "0.1.0"
