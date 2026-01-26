"""Strategy plugins package."""

from .base import Strategy, Signal, PortfolioState
from .sma_crossover import SMACrossoverStrategy

__all__ = [
    'Strategy',
    'Signal',
    'PortfolioState',
    'SMACrossoverStrategy',
]

__version__ = "0.1.0"
