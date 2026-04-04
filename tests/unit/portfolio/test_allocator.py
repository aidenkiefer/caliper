from decimal import Decimal

import pytest

from packages.common.market_schemas import MarketType, SignalType, UnifiedSignal
from services.portfolio.allocator import AllocationResult, Allocator, CapitalBudget


def _make_signal(
    asset_id, direction, market_type=MarketType.EQUITY, confidence=Decimal("0.8")
):
    return UnifiedSignal(
        asset_id=asset_id,
        market_type=market_type,
        signal_type=SignalType.DIRECTIONAL,
        direction=direction,
        confidence=confidence,
        horizon_seconds=3600,
        strategy_id="test",
    )


def test_allocator_basic_long():
    budget = CapitalBudget(
        total_equity=Decimal("100000"),
        market_budgets={MarketType.EQUITY: Decimal("0.80")},
        max_single_position_pct=Decimal("0.05"),
    )
    allocator = Allocator(budget)
    signals = [_make_signal("AAPL", "long")]
    results = allocator.allocate(signals, current_price_map={"AAPL": Decimal("150")})
    assert len(results) == 1
    r = results[0]
    assert isinstance(r, AllocationResult)
    assert r.asset_id == "AAPL"
    assert r.direction == "long"
    assert r.target_quantity > 0


def test_allocator_respects_market_budget():
    # PREDICTION budget = 2%; signal for large size should be capped
    budget = CapitalBudget(
        total_equity=Decimal("100000"),
        market_budgets={
            MarketType.EQUITY: Decimal("0.80"),
            MarketType.PREDICTION: Decimal("0.02"),
        },
        max_single_position_pct=Decimal("0.05"),
    )
    allocator = Allocator(budget)
    signals = [_make_signal("BTC-UP", "long", MarketType.PREDICTION)]
    results = allocator.allocate(signals, current_price_map={"BTC-UP": Decimal("0.60")})
    # Max notional = 2% of 100000 = $2000; qty <= $2000 / $0.60 = 3333
    assert results[0].target_quantity <= Decimal("3334")


def test_allocator_skips_none_direction():
    budget = CapitalBudget(
        total_equity=Decimal("100000"),
        market_budgets={MarketType.PREDICTION: Decimal("0.02")},
        max_single_position_pct=Decimal("0.05"),
    )
    allocator = Allocator(budget)
    signals = [_make_signal("BTC-UP", "none", MarketType.PREDICTION)]
    results = allocator.allocate(signals, current_price_map={"BTC-UP": Decimal("0.60")})
    # "none" direction = market-making intent; allocator passes through with qty=0
    assert results[0].target_quantity == Decimal("0")
    assert results[0].pass_through is True


def test_allocator_no_budget_for_market_rejects():
    budget = CapitalBudget(
        total_equity=Decimal("100000"),
        market_budgets={MarketType.EQUITY: Decimal("0.80")},
        max_single_position_pct=Decimal("0.05"),
    )
    allocator = Allocator(budget)
    signals = [_make_signal("BTC-UP", "long", MarketType.PREDICTION)]
    results = allocator.allocate(signals, current_price_map={"BTC-UP": Decimal("0.60")})
    assert len(results) == 0
