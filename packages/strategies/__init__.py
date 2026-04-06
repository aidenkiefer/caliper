"""Strategy plugins package."""

from packages.common.market_schemas import MarketType, UnifiedSignal

from .base import PortfolioState, Signal, Strategy
from .ml_direction_v1 import MLDirectionStrategyV1
from .poly_directional_v1 import PolyDirectionalStrategyV1
from .poly_hybrid_v1 import PolyHybridStrategyV1
from .poly_mm_v2 import PolyMMStrategyV2
from .poly_regime_v1 import PolyRegimeStrategyV1
from .polymarket_mm_strategy import PolymarketMMStrategy
from .sma_crossover import SMACrossoverStrategy

__all__ = [
    "Strategy",
    "Signal",
    "PortfolioState",
    "SMACrossoverStrategy",
    "MLDirectionStrategyV1",
    "PolymarketMMStrategy",
    "PolyMMStrategyV2",
    "PolyDirectionalStrategyV1",
    "PolyHybridStrategyV1",
    "PolyRegimeStrategyV1",
    "UnifiedSignal",
    "MarketType",
]

__version__ = "0.2.0"

