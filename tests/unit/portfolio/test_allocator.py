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
    # PREDICTION budget = 2% of $100,000 = $2,000 max notional
    # confidence=0.8 scales notional: effective = min(2%*100k, 5%*100k) * 0.8 = $1,600
    # qty = floor($1,600 / $0.60) = 2666
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
    assert len(results) == 1
    # Max notional for PREDICTION = 2% * $100,000 = $2,000; confidence=0.8 scales to $1,600
    # $1,600 / $0.60 = 2666.67 → floor = 2666
    assert results[0].target_quantity == Decimal("2666")


def test_allocator_multi_signal_respects_total_market_budget():
    # 3 EQUITY signals; budget = 10% of $10,000 = $1,000; each at price $100
    # confidence=1.0, max_single_position_pct=0.1 → each could take $1,000 notional
    # But total EQUITY budget is $1,000, so only the first signal gets filled; rest are dropped
    budget = CapitalBudget(
        total_equity=Decimal("10000"),
        market_budgets={MarketType.EQUITY: Decimal("0.10")},
        max_single_position_pct=Decimal("0.10"),
    )
    allocator = Allocator(budget)
    signals = [
        _make_signal("AAPL", "long", MarketType.EQUITY, confidence=Decimal("1.0")),
        _make_signal("MSFT", "long", MarketType.EQUITY, confidence=Decimal("1.0")),
        _make_signal("GOOG", "long", MarketType.EQUITY, confidence=Decimal("1.0")),
    ]
    results = allocator.allocate(
        signals,
        current_price_map={
            "AAPL": Decimal("100"),
            "MSFT": Decimal("100"),
            "GOOG": Decimal("100"),
        },
    )
    # First signal: budget=$1000, notional=$1000, qty=10
    # Second signal: remaining=$0, skipped
    assert len(results) == 1
    assert results[0].asset_id == "AAPL"
    assert results[0].target_quantity == Decimal("10")


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
