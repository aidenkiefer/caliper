from decimal import Decimal

import pytest

from services.portfolio.sizing import (
    clamp,
    fixed_fraction_size,
    kelly_size,
)


def test_fixed_fraction_size_basic():
    # 2% of $100,000 portfolio at price $150 → $2000 / $150 = 13.33 → floor 13
    qty = fixed_fraction_size(
        portfolio_equity=Decimal("100000"),
        fraction=Decimal("0.02"),
        price=Decimal("150"),
    )
    assert qty == Decimal("13")


def test_fixed_fraction_size_zero_price():
    with pytest.raises(ValueError, match="price must be positive"):
        fixed_fraction_size(Decimal("100000"), Decimal("0.02"), Decimal("0"))


def test_clamp_within_bounds():
    assert clamp(Decimal("5"), Decimal("1"), Decimal("10")) == Decimal("5")


def test_clamp_below_min():
    assert clamp(Decimal("0"), Decimal("1"), Decimal("10")) == Decimal("1")


def test_clamp_above_max():
    assert clamp(Decimal("15"), Decimal("1"), Decimal("10")) == Decimal("10")


def test_kelly_size_positive_edge():
    # Kelly: f = (p*(b+1) - 1) / b  where b = win_loss_ratio
    # p=0.6, b=1 → f=(0.6*2 - 1)/1 = 0.2
    size = kelly_size(
        win_probability=Decimal("0.6"),
        win_loss_ratio=Decimal("1.0"),
        portfolio_equity=Decimal("100000"),
        price=Decimal("100"),
        max_fraction=Decimal("0.2"),
    )
    assert size == Decimal("200")  # 0.2 * 100000 / 100


def test_kelly_size_negative_edge_returns_zero():
    # p=0.3, b=1 → f=negative → return 0
    size = kelly_size(
        win_probability=Decimal("0.3"),
        win_loss_ratio=Decimal("1.0"),
        portfolio_equity=Decimal("100000"),
        price=Decimal("100"),
        max_fraction=Decimal("0.2"),
    )
    assert size == Decimal("0")
