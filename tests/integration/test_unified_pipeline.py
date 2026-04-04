"""
End-to-end smoke test: strategy → allocator → global risk → adapter stub.

Uses in-memory stubs — no network or DB required.
"""

from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from packages.common.market_schemas import MarketType, SignalType, UnifiedSignal
from services.execution.adapter import ExecutionAdapter
from services.execution.broker.base import (
    Account,
    Order,
    OrderResult,
    OrderSide,
    OrderStatus,
    OrderbookSnapshot,
    Position,
    TimeInForce,
    OrderType,
)
from services.portfolio.allocator import Allocator, CapitalBudget
from services.risk.global_risk_manager import GlobalRiskConfig, GlobalRiskManager


class StubAdapter(ExecutionAdapter):
    """In-memory execution adapter for testing."""

    def __init__(self):
        self.placed: list[Order] = []

    async def place_order(self, order: Order) -> OrderResult:
        self.placed.append(order)
        return OrderResult(
            broker_order_id="stub-001",
            client_order_id=order.client_order_id,
            status=OrderStatus.SUBMITTED,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            time_in_force=TimeInForce.DAY,
        )

    async def cancel_order(self, order_id: str) -> bool:
        return True

    async def get_positions(self) -> list[Position]:
        return []

    async def get_account(self) -> Account:
        return Account(
            account_id="stub",
            cash=Decimal("100000"),
            portfolio_value=Decimal("100000"),
            buying_power=Decimal("100000"),
            equity=Decimal("100000"),
            status="active",
        )

    async def get_order_status(self, order_id: str) -> OrderResult:
        return MagicMock()

    async def get_orders(self, status=None, limit=100):
        return []

    async def get_orderbook(self, asset_id: str) -> OrderbookSnapshot:
        return OrderbookSnapshot(asset_id=asset_id, bids=[], asks=[])

    def is_connected(self) -> bool:
        return True

    def is_paper(self) -> bool:
        return True


@pytest.mark.asyncio
async def test_unified_pipeline_equity_signal_to_adapter():
    """
    One directional equity signal travels through all 4 new layers
    and reaches the execution adapter.
    """
    signal = UnifiedSignal(
        asset_id="AAPL",
        market_type=MarketType.EQUITY,
        signal_type=SignalType.DIRECTIONAL,
        direction="long",
        confidence=Decimal("0.85"),
        horizon_seconds=3600,
        strategy_id="test_sma",
    )

    budget = CapitalBudget(
        total_equity=Decimal("100000"),
        market_budgets={MarketType.EQUITY: Decimal("0.80")},
        max_single_position_pct=Decimal("0.05"),
    )
    allocator = Allocator(budget)
    allocations = allocator.allocate([signal], current_price_map={"AAPL": Decimal("150")})
    assert len(allocations) == 1
    allocation = allocations[0]
    assert allocation.target_quantity > 0
    assert allocation.direction == "long"

    grm_config = GlobalRiskConfig(
        total_equity=Decimal("100000"),
        max_drawdown_pct=Decimal("10"),
    )
    grm = GlobalRiskManager(grm_config)
    risk_result = grm.check(allocation, current_drawdown_pct=Decimal("1"))
    assert risk_result.approved

    adapter = StubAdapter()
    order = Order(
        client_order_id=str(uuid4()),
        symbol=allocation.asset_id,
        side=OrderSide.BUY,
        quantity=allocation.target_quantity,
        order_type=OrderType.MARKET,
        time_in_force=TimeInForce.DAY,
    )
    result = await adapter.place_order(order)
    assert result.status == OrderStatus.SUBMITTED
    assert len(adapter.placed) == 1
    assert adapter.placed[0].symbol == "AAPL"


@pytest.mark.asyncio
async def test_unified_pipeline_kill_switch_blocks_trade():
    """Kill switch prevents any allocation from reaching the adapter."""
    signal = UnifiedSignal(
        asset_id="AAPL",
        market_type=MarketType.EQUITY,
        signal_type=SignalType.DIRECTIONAL,
        direction="long",
        confidence=Decimal("0.9"),
        horizon_seconds=3600,
        strategy_id="test_sma",
    )

    budget = CapitalBudget(
        total_equity=Decimal("100000"),
        market_budgets={MarketType.EQUITY: Decimal("0.80")},
        max_single_position_pct=Decimal("0.05"),
    )
    allocator = Allocator(budget)
    allocations = allocator.allocate([signal], current_price_map={"AAPL": Decimal("150")})
    assert len(allocations) == 1

    grm_config = GlobalRiskConfig(
        total_equity=Decimal("100000"),
        max_drawdown_pct=Decimal("10"),
        kill_switch_active=True,
    )
    grm = GlobalRiskManager(grm_config)
    risk_result = grm.check(allocations[0], current_drawdown_pct=Decimal("1"))
    assert not risk_result.approved
    assert risk_result.rejection_reason is not None
    assert "kill switch" in risk_result.rejection_reason.lower()

    adapter = StubAdapter()
    assert len(adapter.placed) == 0


@pytest.mark.asyncio
async def test_unified_pipeline_prediction_mm_signal_pass_through():
    """
    A MARKET_MAKING signal from a Polymarket strategy is passed through
    the allocator (as pass_through) and approved by global risk.
    """
    signal = UnifiedSignal(
        asset_id="BTC-UP-2026-04-04T15",
        market_type=MarketType.PREDICTION,
        signal_type=SignalType.MARKET_MAKING,
        direction="none",
        confidence=Decimal("1.0"),
        horizon_seconds=60,
        strategy_id="pm_mm_v1",
        metadata={
            "bid_price": "0.54",
            "ask_price": "0.56",
            "bid_size": "50",
            "ask_size": "50",
        },
    )

    budget = CapitalBudget(
        total_equity=Decimal("5000"),
        market_budgets={MarketType.PREDICTION: Decimal("0.10")},
        max_single_position_pct=Decimal("0.05"),
    )
    allocator = Allocator(budget)
    allocations = allocator.allocate(
        [signal],
        current_price_map={"BTC-UP-2026-04-04T15": Decimal("0.55")},
    )
    assert len(allocations) == 1
    allocation = allocations[0]
    assert allocation.pass_through is True
    assert allocation.target_quantity == Decimal("0")
    assert allocation.signal.metadata["bid_price"] == "0.54"

    grm_config = GlobalRiskConfig(
        total_equity=Decimal("5000"),
        max_drawdown_pct=Decimal("10"),
    )
    grm = GlobalRiskManager(grm_config)
    risk_result = grm.check(allocation, current_drawdown_pct=Decimal("0"))
    assert risk_result.approved
