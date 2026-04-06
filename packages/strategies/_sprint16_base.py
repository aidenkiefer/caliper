from __future__ import annotations

from typing import List

from packages.common.market_schemas import MarketType, UnifiedSignal
from packages.common.schemas import Order, TradingMode
from packages.strategies.base import PortfolioState, Strategy


class Sprint16PredictionStrategyBase(Strategy):
    market_type = MarketType.PREDICTION

    def initialize(self, mode: TradingMode) -> None:
        self.initialized = True
        self.mode = mode

    def risk_check(
        self, signals: List[UnifiedSignal], portfolio: PortfolioState
    ) -> List[Order]:
        return []

