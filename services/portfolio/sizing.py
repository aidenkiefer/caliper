"""
Position sizing helpers.

All functions take Decimal inputs and return Decimal quantities.
"""

from decimal import ROUND_DOWN, Decimal


def clamp(value: Decimal, min_val: Decimal, max_val: Decimal) -> Decimal:
    """Clamp value to [min_val, max_val]."""
    return max(min_val, min(max_val, value))


def fixed_fraction_size(
    portfolio_equity: Decimal,
    fraction: Decimal,
    price: Decimal,
) -> Decimal:
    """
    Size a position as a fixed fraction of portfolio equity.

    Returns shares (floored to whole number). Raises ValueError if price <= 0.
    """
    if price <= Decimal("0"):
        raise ValueError("price must be positive")
    notional = portfolio_equity * fraction
    return (notional / price).to_integral_value(rounding=ROUND_DOWN)


def kelly_size(
    win_probability: Decimal,
    win_loss_ratio: Decimal,
    portfolio_equity: Decimal,
    price: Decimal,
    max_fraction: Decimal = Decimal("0.25"),
) -> Decimal:
    """
    Kelly criterion sizing, capped at max_fraction.

    kelly_f = (p * (b + 1) - 1) / b  where b = win_loss_ratio.
    Returns 0 if kelly_f <= 0 (negative or zero edge).
    """
    if win_loss_ratio <= Decimal("0"):
        return Decimal("0")
    kelly_f = (win_probability * (win_loss_ratio + 1) - 1) / win_loss_ratio
    if kelly_f <= Decimal("0"):
        return Decimal("0")
    fraction = clamp(kelly_f, Decimal("0"), max_fraction)
    return fixed_fraction_size(portfolio_equity, fraction, price)
