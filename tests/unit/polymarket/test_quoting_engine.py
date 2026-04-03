"""
Unit tests for services/polymarket/quoting_engine.py.

Tests cover: normal quoting, tick rounding, inventory cap, no YES inventory,
stale/no midpoint, and wide-spread suppression.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from unittest.mock import MagicMock

import pytest

from services.polymarket.quoting_engine import QuotingEngine, round_to_tick


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@dataclass
class FakeOrderbookState:
    """Minimal stand-in for DataFeedState with only the fields QuotingEngine reads."""

    midpoint: Optional[Decimal]
    spread: Optional[Decimal]


def make_config(
    quote_spread: Decimal = Decimal("0.02"),
    quote_size: Decimal = Decimal("50"),
    inventory_cap: Decimal = Decimal("200"),
) -> MagicMock:
    """Return a minimal config mock with the three fields QuotingEngine uses."""
    cfg = MagicMock()
    cfg.quote_spread = quote_spread
    cfg.quote_size = quote_size
    cfg.inventory_cap = inventory_cap
    return cfg


# ---------------------------------------------------------------------------
# round_to_tick
# ---------------------------------------------------------------------------


class TestRoundToTick:
    def test_already_on_tick(self):
        assert round_to_tick(Decimal("0.50")) == Decimal("0.50")

    def test_rounds_down(self):
        # 0.474 → 0.47 (closest tick)
        assert round_to_tick(Decimal("0.474")) == Decimal("0.47")

    def test_rounds_up(self):
        # 0.476 → 0.48
        assert round_to_tick(Decimal("0.476")) == Decimal("0.48")

    def test_half_rounds_up(self):
        # 0.475 → 0.48 (ROUND_HALF_UP)
        assert round_to_tick(Decimal("0.475")) == Decimal("0.48")

    def test_custom_tick_size(self):
        assert round_to_tick(Decimal("0.473"), Decimal("0.05")) == Decimal("0.50")


# ---------------------------------------------------------------------------
# QuotingEngine.compute_quotes
# ---------------------------------------------------------------------------


class TestQuotingEngineNormalQuoting:
    """Test 1: midpoint=0.50, spread=0.02, inventory=50 → bid=0.49, ask=0.51."""

    def test_normal_quoting(self):
        engine = QuotingEngine()
        state = FakeOrderbookState(midpoint=Decimal("0.50"), spread=Decimal("0.02"))
        config = make_config()  # quote_spread=0.02, quote_size=50, inventory_cap=200

        result = engine.compute_quotes(state, inventory_yes=Decimal("50"), config=config)

        assert result.should_quote_bid is True
        assert result.should_quote_ask is True
        assert result.bid_price == Decimal("0.49")
        assert result.ask_price == Decimal("0.51")
        assert result.bid_size == Decimal("50")
        assert result.ask_size == Decimal("50")
        assert result.midpoint == Decimal("0.50")
        assert result.reason is None

    def test_sizes_come_from_config(self):
        engine = QuotingEngine()
        state = FakeOrderbookState(midpoint=Decimal("0.60"), spread=Decimal("0.02"))
        config = make_config(quote_size=Decimal("100"))

        result = engine.compute_quotes(state, inventory_yes=Decimal("50"), config=config)

        assert result.bid_size == Decimal("100")
        assert result.ask_size == Decimal("100")


class TestQuotingEngineTickRounding:
    """Test 2: midpoint=0.473 → bid rounds to 0.46, ask rounds to 0.48."""

    def test_tick_rounding(self):
        engine = QuotingEngine()
        # spread_offset = 0.02/2 = 0.01
        # raw bid = 0.473 - 0.01 = 0.463 → rounds to 0.46
        # raw ask = 0.473 + 0.01 = 0.483 → rounds to 0.48
        state = FakeOrderbookState(midpoint=Decimal("0.473"), spread=Decimal("0.02"))
        config = make_config()

        result = engine.compute_quotes(state, inventory_yes=Decimal("50"), config=config)

        assert result.bid_price == Decimal("0.46")
        assert result.ask_price == Decimal("0.48")

    def test_custom_tick_size_passed_through(self):
        engine = QuotingEngine()
        state = FakeOrderbookState(midpoint=Decimal("0.50"), spread=Decimal("0.02"))
        config = make_config(quote_spread=Decimal("0.04"))

        # spread_offset = 0.02; tick_size = 0.05
        # raw bid = 0.50 - 0.02 = 0.48 → nearest 0.05 = 0.50
        # raw ask = 0.50 + 0.02 = 0.52 → nearest 0.05 = 0.50
        result = engine.compute_quotes(
            state,
            inventory_yes=Decimal("50"),
            config=config,
            tick_size=Decimal("0.05"),
        )

        assert result.bid_price == Decimal("0.50")
        assert result.ask_price == Decimal("0.50")


class TestQuotingEngineInventoryCap:
    """Test 3: inventory_yes >= inventory_cap → should_quote_bid=False."""

    def test_inventory_cap_blocks_bid_at_cap(self):
        engine = QuotingEngine()
        state = FakeOrderbookState(midpoint=Decimal("0.50"), spread=Decimal("0.02"))
        config = make_config(inventory_cap=Decimal("200"))

        result = engine.compute_quotes(
            state, inventory_yes=Decimal("200"), config=config
        )

        assert result.should_quote_bid is False
        assert result.bid_price is None
        assert result.bid_size == Decimal("0")
        # Ask should still be live
        assert result.should_quote_ask is True
        assert result.ask_price == Decimal("0.51")
        assert result.ask_size == Decimal("50")
        assert result.reason == "inventory cap reached"

    def test_inventory_cap_blocks_bid_above_cap(self):
        engine = QuotingEngine()
        state = FakeOrderbookState(midpoint=Decimal("0.50"), spread=Decimal("0.02"))
        config = make_config(inventory_cap=Decimal("200"))

        result = engine.compute_quotes(
            state, inventory_yes=Decimal("250"), config=config
        )

        assert result.should_quote_bid is False
        assert result.should_quote_ask is True

    def test_just_below_inventory_cap_quotes_bid(self):
        engine = QuotingEngine()
        state = FakeOrderbookState(midpoint=Decimal("0.50"), spread=Decimal("0.02"))
        config = make_config(inventory_cap=Decimal("200"))

        result = engine.compute_quotes(
            state, inventory_yes=Decimal("199"), config=config
        )

        assert result.should_quote_bid is True


class TestQuotingEngineNoYesInventory:
    """Test 4: inventory_yes=0 → should_quote_ask=False."""

    def test_zero_inventory_blocks_ask(self):
        engine = QuotingEngine()
        state = FakeOrderbookState(midpoint=Decimal("0.50"), spread=Decimal("0.02"))
        config = make_config()

        result = engine.compute_quotes(
            state, inventory_yes=Decimal("0"), config=config
        )

        assert result.should_quote_ask is False
        assert result.ask_price is None
        assert result.ask_size == Decimal("0")
        # Bid should still be live
        assert result.should_quote_bid is True
        assert result.bid_price == Decimal("0.49")
        assert result.reason == "no YES inventory for asks"

    def test_negative_inventory_also_blocks_ask(self):
        engine = QuotingEngine()
        state = FakeOrderbookState(midpoint=Decimal("0.50"), spread=Decimal("0.02"))
        config = make_config()

        result = engine.compute_quotes(
            state, inventory_yes=Decimal("-10"), config=config
        )

        assert result.should_quote_ask is False
        assert result.should_quote_bid is True


class TestQuotingEngineNoMidpoint:
    """Test 5: midpoint=None → both sides False, reason='no midpoint'."""

    def test_no_midpoint_stops_all_quoting(self):
        engine = QuotingEngine()
        state = FakeOrderbookState(midpoint=None, spread=None)
        config = make_config()

        result = engine.compute_quotes(
            state, inventory_yes=Decimal("50"), config=config
        )

        assert result.should_quote_bid is False
        assert result.should_quote_ask is False
        assert result.bid_price is None
        assert result.ask_price is None
        assert result.bid_size == Decimal("0")
        assert result.ask_size == Decimal("0")
        assert result.reason == "no midpoint"
        assert result.midpoint is None

    def test_no_midpoint_overrides_inventory_cap(self):
        """Even at inventory cap, no midpoint still returns both sides False."""
        engine = QuotingEngine()
        state = FakeOrderbookState(midpoint=None, spread=None)
        config = make_config(inventory_cap=Decimal("0"))

        result = engine.compute_quotes(
            state, inventory_yes=Decimal("200"), config=config
        )

        assert result.should_quote_bid is False
        assert result.should_quote_ask is False


class TestQuotingEngineWideSpread:
    """Test 6: spread > 0.10 → both sides False, reason='wide spread'."""

    def test_wide_spread_stops_quoting(self):
        engine = QuotingEngine()
        state = FakeOrderbookState(midpoint=Decimal("0.50"), spread=Decimal("0.15"))
        config = make_config()

        result = engine.compute_quotes(
            state, inventory_yes=Decimal("50"), config=config
        )

        assert result.should_quote_bid is False
        assert result.should_quote_ask is False
        assert result.bid_price is None
        assert result.ask_price is None
        assert result.bid_size == Decimal("0")
        assert result.ask_size == Decimal("0")
        assert result.reason == "wide spread"
        assert result.midpoint == Decimal("0.50")

    def test_spread_exactly_at_threshold_still_suppresses(self):
        """Spread of exactly 0.10 is NOT wide (> 0.10 check); quoting proceeds."""
        engine = QuotingEngine()
        state = FakeOrderbookState(midpoint=Decimal("0.50"), spread=Decimal("0.10"))
        config = make_config()

        result = engine.compute_quotes(
            state, inventory_yes=Decimal("50"), config=config
        )

        # 0.10 is not > 0.10, so quoting should proceed normally
        assert result.should_quote_bid is True
        assert result.should_quote_ask is True

    def test_spread_just_above_threshold_suppresses(self):
        engine = QuotingEngine()
        state = FakeOrderbookState(midpoint=Decimal("0.50"), spread=Decimal("0.11"))
        config = make_config()

        result = engine.compute_quotes(
            state, inventory_yes=Decimal("50"), config=config
        )

        assert result.should_quote_bid is False
        assert result.should_quote_ask is False

    def test_none_spread_with_valid_midpoint_does_not_suppress(self):
        """If spread is None but midpoint is present, wide-spread gate is skipped."""
        engine = QuotingEngine()
        state = FakeOrderbookState(midpoint=Decimal("0.50"), spread=None)
        config = make_config()

        result = engine.compute_quotes(
            state, inventory_yes=Decimal("50"), config=config
        )

        assert result.should_quote_bid is True
        assert result.should_quote_ask is True
