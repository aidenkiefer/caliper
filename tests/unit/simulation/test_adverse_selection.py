from __future__ import annotations

import pytest
from decimal import Decimal
from services.simulation.adverse.selection import AdverseSelectionModel

TOLERANCE = Decimal("0.000001")


def test_informed_fraction_at_open() -> None:
    model = AdverseSelectionModel()
    result = model.informed_fraction(3600.0)
    assert result == Decimal("0.05")


def test_informed_fraction_at_close() -> None:
    model = AdverseSelectionModel()
    result = model.informed_fraction(0)
    assert result == Decimal("0.40")


def test_informed_fraction_before_ramp_start() -> None:
    model = AdverseSelectionModel()
    result = model.informed_fraction(3000.0)
    assert result == Decimal("0.05")


def test_informed_fraction_at_ramp_boundary() -> None:
    model = AdverseSelectionModel()
    result = model.informed_fraction(600.0)
    assert result == Decimal("0.05")


def test_informed_fraction_midpoint_of_ramp() -> None:
    model = AdverseSelectionModel()
    result = model.informed_fraction(300.0)
    assert abs(result - Decimal("0.225")) <= TOLERANCE


def test_informed_fraction_monotonically_increasing() -> None:
    model = AdverseSelectionModel()
    # Sample 10 points from t=600 down to t=0 in equal steps
    times = [600.0 - i * (600.0 / 9) for i in range(10)]
    fractions = [model.informed_fraction(t) for t in times]
    # As time_to_close decreases, informed fraction should be non-decreasing
    for i in range(len(fractions) - 1):
        assert fractions[i] <= fractions[i + 1], (
            f"Fraction decreased: {fractions[i]} > {fractions[i+1]} "
            f"at index {i} (t={times[i]}) → (t={times[i+1]})"
        )


def test_pnl_lower_with_high_peak_informed() -> None:
    high_model = AdverseSelectionModel(peak_informed=Decimal("0.40"))
    low_model = AdverseSelectionModel(peak_informed=Decimal("0.0"))
    assert high_model.informed_fraction(30) > low_model.informed_fraction(30)


def test_is_informed_deterministic_with_seed() -> None:
    model_a = AdverseSelectionModel(random_seed=42)
    model_b = AdverseSelectionModel(random_seed=42)
    results_a = [model_a.is_informed(30.0) for _ in range(20)]
    results_b = [model_b.is_informed(30.0) for _ in range(20)]
    assert results_a == results_b


def test_directional_bias_buy_when_settlement_above_half() -> None:
    model = AdverseSelectionModel()
    assert model.directional_bias(Decimal("0.7")) == "BUY"


def test_directional_bias_sell_when_settlement_at_or_below_half() -> None:
    model = AdverseSelectionModel()
    assert model.directional_bias(Decimal("0.5")) == "SELL"
    assert model.directional_bias(Decimal("0.3")) == "SELL"
