"""Unit tests for services/polymarket/fee_model.py."""

from datetime import date
from decimal import Decimal

import pytest

from services.polymarket.fee_model import FeeModel
from services.polymarket.constants import FEE_REGIME_CHANGE_DATE

# Convenience dates
_PRE_REFORM = date(2026, 3, 29)   # one day before regime change
_POST_REFORM = date(2026, 3, 30)  # exactly on reform date (inclusive)
_AFTER_REFORM = date(2026, 4, 1)  # well after reform


# ---------------------------------------------------------------------------
# Pre-reform tests
# ---------------------------------------------------------------------------

class TestPreReform:
    """Fee model behaviour before March 30, 2026."""

    def test_pre_reform_taker_fee(self):
        """Flat 2% taker fee on contract value."""
        model = FeeModel(as_of_date=_PRE_REFORM)
        price = Decimal("0.6")
        size = Decimal("100")
        fee = model.compute_fee(price, size, is_maker=False, fees_enabled=True)
        expected = price * size * Decimal("0.02")  # 0.6 × 100 × 0.02 = 1.20
        assert fee == expected

    def test_pre_reform_maker_fee(self):
        """Makers pay no fee pre-reform."""
        model = FeeModel(as_of_date=_PRE_REFORM)
        fee = model.compute_fee(
            Decimal("0.6"), Decimal("100"), is_maker=True, fees_enabled=True
        )
        assert fee == Decimal("0")

    def test_pre_reform_no_rebate(self):
        """Maker rebate is always zero before the reform date."""
        model = FeeModel(as_of_date=_PRE_REFORM)
        rebate = model.compute_rebate(Decimal("0.5"), Decimal("200"))
        assert rebate == Decimal("0")

    def test_pre_reform_taker_fee_midpoint(self):
        """Flat 2% applies at p=0.5 pre-reform (no curve adjustment)."""
        model = FeeModel(as_of_date=_PRE_REFORM)
        price = Decimal("0.5")
        size = Decimal("50")
        fee = model.compute_fee(price, size, is_maker=False, fees_enabled=True)
        assert fee == Decimal("0.5") * Decimal("50") * Decimal("0.02")


# ---------------------------------------------------------------------------
# Post-reform tests
# ---------------------------------------------------------------------------

class TestPostReform:
    """Fee model behaviour on and after March 30, 2026."""

    def test_post_reform_taker_at_midpoint(self):
        """At p=0.5 the curve factor is 1.0 → fee = price × size × 0.02."""
        model = FeeModel(as_of_date=_POST_REFORM)
        price = Decimal("0.5")
        size = Decimal("100")
        fee = model.compute_fee(price, size, is_maker=False, fees_enabled=True)
        # curve_factor = 1 - 2|0.5 - 0.5| = 1.0
        expected = price * size * Decimal("0.02") * Decimal("1")
        assert fee == expected  # 0.5 × 100 × 0.02 × 1 = 1.00

    def test_post_reform_taker_at_low_extreme(self):
        """At p=0.01 the curve factor is nearly 0 → tiny fee."""
        model = FeeModel(as_of_date=_POST_REFORM)
        price = Decimal("0.01")
        size = Decimal("1000")
        fee = model.compute_fee(price, size, is_maker=False, fees_enabled=True)
        # curve_factor = 1 - 2|0.01 - 0.5| = 1 - 2×0.49 = 0.02
        expected = price * size * Decimal("0.02") * Decimal("0.02")
        assert fee == expected

    def test_post_reform_taker_at_high_extreme(self):
        """At p=0.99 the curve factor is nearly 0 → tiny fee."""
        model = FeeModel(as_of_date=_POST_REFORM)
        price = Decimal("0.99")
        size = Decimal("1000")
        fee = model.compute_fee(price, size, is_maker=False, fees_enabled=True)
        # curve_factor = 1 - 2|0.99 - 0.5| = 1 - 2×0.49 = 0.02
        expected = price * size * Decimal("0.02") * Decimal("0.02")
        assert fee == expected

    def test_post_reform_maker_no_fee(self):
        """Makers still pay no fee post-reform."""
        model = FeeModel(as_of_date=_AFTER_REFORM)
        fee = model.compute_fee(
            Decimal("0.5"), Decimal("100"), is_maker=True, fees_enabled=True
        )
        assert fee == Decimal("0")

    def test_post_reform_maker_rebate_at_midpoint(self):
        """At p=0.5 maker rebate = price × size × 0.01 (curve factor = 1)."""
        model = FeeModel(as_of_date=_POST_REFORM)
        price = Decimal("0.5")
        size = Decimal("100")
        rebate = model.compute_rebate(price, size)
        expected = price * size * Decimal("0.01") * Decimal("1")
        assert rebate == expected  # 0.5 × 100 × 0.01 = 0.50

    def test_post_reform_maker_rebate_at_extreme(self):
        """At p=0.99 rebate is near zero."""
        model = FeeModel(as_of_date=_POST_REFORM)
        price = Decimal("0.99")
        size = Decimal("1000")
        rebate = model.compute_rebate(price, size)
        # curve_factor = 0.02
        expected = price * size * Decimal("0.01") * Decimal("0.02")
        assert rebate == expected

    def test_reform_date_is_post_reform(self):
        """The change date itself uses the new regime (>=)."""
        assert FeeModel(as_of_date=FEE_REGIME_CHANGE_DATE)._is_post_reform is True

    def test_day_before_reform_is_pre_reform(self):
        """One day before the change uses the old regime."""
        assert FeeModel(as_of_date=_PRE_REFORM)._is_post_reform is False


# ---------------------------------------------------------------------------
# fees_enabled=False
# ---------------------------------------------------------------------------

class TestFeesDisabled:
    def test_fees_disabled_taker_pre_reform(self):
        """fees_enabled=False → fee is 0 regardless of regime or role."""
        model = FeeModel(as_of_date=_PRE_REFORM)
        fee = model.compute_fee(
            Decimal("0.5"), Decimal("100"), is_maker=False, fees_enabled=False
        )
        assert fee == Decimal("0")

    def test_fees_disabled_taker_post_reform(self):
        model = FeeModel(as_of_date=_POST_REFORM)
        fee = model.compute_fee(
            Decimal("0.5"), Decimal("100"), is_maker=False, fees_enabled=False
        )
        assert fee == Decimal("0")


# ---------------------------------------------------------------------------
# Net P&L computation
# ---------------------------------------------------------------------------

class TestNetPnl:
    def test_net_pnl_computation(self):
        """gross_pnl=10, fees=2, rebates=0.5 → net=8.5."""
        model = FeeModel(as_of_date=_PRE_REFORM)
        net = model.compute_net_pnl(
            gross_pnl=Decimal("10"),
            fees_paid=Decimal("2"),
            rebates_earned=Decimal("0.5"),
        )
        assert net == Decimal("8.5")

    def test_net_pnl_no_fees_no_rebates(self):
        model = FeeModel(as_of_date=_PRE_REFORM)
        net = model.compute_net_pnl(
            gross_pnl=Decimal("5"),
            fees_paid=Decimal("0"),
            rebates_earned=Decimal("0"),
        )
        assert net == Decimal("5")

    def test_net_pnl_negative_gross(self):
        model = FeeModel(as_of_date=_PRE_REFORM)
        net = model.compute_net_pnl(
            gross_pnl=Decimal("-3"),
            fees_paid=Decimal("1"),
            rebates_earned=Decimal("0"),
        )
        assert net == Decimal("-4")


# ---------------------------------------------------------------------------
# Fee curve factor edge cases
# ---------------------------------------------------------------------------

class TestFeeCurveFactor:
    """Internal _fee_curve_factor helper edge cases."""

    def test_curve_factor_at_half(self):
        assert FeeModel._fee_curve_factor(Decimal("0.5")) == Decimal("1")

    def test_curve_factor_at_zero(self):
        """Exactly at p=0 the factor is 0."""
        assert FeeModel._fee_curve_factor(Decimal("0")) == Decimal("0")

    def test_curve_factor_at_one(self):
        """Exactly at p=1 the factor is 0."""
        assert FeeModel._fee_curve_factor(Decimal("1")) == Decimal("0")

    def test_curve_factor_never_negative(self):
        """Factor is clamped to 0 even for out-of-range prices."""
        # Prices outside [0,1] should not produce negative factors
        factor = FeeModel._fee_curve_factor(Decimal("1.5"))
        assert factor == Decimal("0")
