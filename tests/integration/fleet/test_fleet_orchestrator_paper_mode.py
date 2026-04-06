from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Any, Dict, List

from packages.common.market_schemas import MarketType, SignalType, UnifiedSignal
from packages.common.schemas import TradingMode
from packages.strategies.base import PortfolioState, Strategy
from services.fleet.orchestrator import FleetOrchestrator
from services.fleet.registry import StrategyRegistry
from services.fleet.schemas import PaperTrade
from services.portfolio.allocator import Allocator, CapitalBudget


class FakePaperTradeStore:
    def __init__(self) -> None:
        self.writes: List[PaperTrade] = []

    async def write_fill(self, trade: PaperTrade) -> None:
        self.writes.append(trade)


class FakeExecutionAdapter:
    def __init__(self) -> None:
        self.place_order_called = False

    async def place_order(self, *_args: Any, **_kwargs: Any) -> None:
        self.place_order_called = True


class MakerStrategy(Strategy):
    market_type = MarketType.PREDICTION

    def initialize(self, mode: TradingMode) -> None:
        self.mode = mode
        self.initialized = True

    def on_market_data(self, bar: Any) -> None:
        self._bar = bar

    def generate_signals(self, portfolio: PortfolioState):
        return [
            UnifiedSignal(
                strategy_id=self.strategy_id,
                asset_id="market-1",
                market_type=MarketType.PREDICTION,
                signal_type=SignalType.MARKET_MAKING,
                direction="none",
                confidence=Decimal("1"),
                horizon_seconds=60,
                metadata={
                    "bid_price": "0.48",
                    "ask_price": "0.52",
                    "bid_size": "3",
                    "ask_size": "2",
                },
            )
        ]

    def risk_check(self, signals, portfolio):
        return []


class DirectionalStrategy(Strategy):
    market_type = MarketType.PREDICTION

    def initialize(self, mode: TradingMode) -> None:
        self.mode = mode
        self.initialized = True

    def on_market_data(self, bar: Any) -> None:
        self._bar = bar

    def generate_signals(self, portfolio: PortfolioState):
        return [
            UnifiedSignal(
                strategy_id=self.strategy_id,
                asset_id="market-2",
                market_type=MarketType.PREDICTION,
                signal_type=SignalType.DIRECTIONAL,
                direction="long",
                confidence=Decimal("0.75"),
                horizon_seconds=120,
                metadata={"order_quantity": "5"},
            )
        ]

    def risk_check(self, signals, portfolio):
        return []


def _portfolio() -> PortfolioState:
    return PortfolioState(
        equity=Decimal("100000"),
        cash=Decimal("75000"),
        positions=[],
        unrealized_pnl=Decimal("0"),
    )


def test_fleet_orchestrator_paper_mode_records_fills_without_execution() -> None:
    registry = StrategyRegistry({"maker": MakerStrategy, "directional": DirectionalStrategy})
    strategies = registry.build({"maker": {}, "directional": {}})
    allocator = Allocator(
        CapitalBudget(
            total_equity=Decimal("100000"),
            market_budgets={MarketType.PREDICTION: Decimal("0.02")},
            max_single_position_pct=Decimal("0.05"),
        )
    )
    store = FakePaperTradeStore()
    adapter = FakeExecutionAdapter()
    orchestrator = FleetOrchestrator(
        strategies=strategies,
        allocator=allocator,
        paper_store=store,
        execution_adapter=adapter,
        paper_mode=True,
    )

    status = asyncio.run(
        orchestrator.process_cycle(
            market_data={"maker": {"mid": 0.5}, "directional": {"mid": 0.51}},
            portfolio=_portfolio(),
            current_price_map={"market-1": Decimal("0.50"), "market-2": Decimal("0.51")},
            allocation_decision={"maker": Decimal("1"), "directional": Decimal("1")},
        )
    )

    assert adapter.place_order_called is False
    assert len(store.writes) == 3
    assert len(orchestrator.paper_trades) == 3
    assert len(status.strategies) == 2
    assert status.paper_mode is True
    assert {trade.side for trade in store.writes} == {"BUY", "SELL"}
    assert any(trade.strategy_id == "directional" for trade in store.writes)

