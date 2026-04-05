from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest

from services.simulation.execution.fee_engine import FeeEngine, FeeRegime
from services.simulation.schemas import SimFill

TOLERANCE = Decimal("0.000001")

FIXED_TS = datetime(2026, 4, 1, 9, 0, 0)


def make_fill(price="0.5", size="50", side="BUY", maker=True):
    return SimFill(
        fill_id="f1",
        order_id="o1",
        market_id="mkt-1",
        token_id="tok-1",
        side=side,
        fill_price=Decimal(price),
        fill_size=Decimal(size),
        fill_time=FIXED_TS,
        maker_fill=maker,
        slippage_vs_mid=Decimal(0),
        mid_at_fill=Decimal("0.5"),
        rebate_estimated=False,
    )


# ---------------------------------------------------------------------------
# Regime selection tests
# ---------------------------------------------------------------------------

def test_for_date_pre_mar30_market_pre_date():
    regime = FeeRegime.for_date(
        market_created_at=datetime(2026, 3, 1, 0, 0, 0),
        current_date=date(2026, 3, 15),
    )
    assert regime.fee_rate == Decimal("0.25")


def test_for_date_pre_mar30_market_post_date():
    # Market created before cutoff — retains pre-Mar-30 rates even when current date is past cutoff
    regime = FeeRegime.for_date(
        market_created_at=datetime(2026, 3, 1, 0, 0, 0),
        current_date=date(2026, 4, 1),
    )
    assert regime.fee_rate == Decimal("0.25")


def test_for_date_post_mar30_market_post_date():
    regime = FeeRegime.for_date(
        market_created_at=datetime(2026, 4, 1, 0, 0, 0),
        current_date=date(2026, 4, 1),
    )
    assert regime.fee_rate == Decimal("0.072")


# ---------------------------------------------------------------------------
# Taker fee — pre-Mar-30 (exponent=2)
# ---------------------------------------------------------------------------

def test_taker_fee_pre_mar30_reference_trade():
    engine = FeeEngine(regime=FeeRegime.pre_mar30_crypto())
    fee = engine.taker_fee(shares=Decimal("100"), price=Decimal("0.5"))
    # 100 * 0.5 * 0.25 * (0.5 * 0.5)^2 = 100 * 0.5 * 0.25 * 0.0625 = 0.78125
    assert abs(fee - Decimal("0.78125")) <= TOLERANCE


def test_taker_fee_zero_at_zero_price():
    engine = FeeEngine(regime=FeeRegime.pre_mar30_crypto())
    fee = engine.taker_fee(shares=Decimal("100"), price=Decimal("0"))
    assert fee == Decimal("0")


def test_taker_fee_zero_at_zero_shares():
    engine = FeeEngine(regime=FeeRegime.pre_mar30_crypto())
    fee = engine.taker_fee(shares=Decimal("0"), price=Decimal("0.5"))
    assert fee == Decimal("0")


# ---------------------------------------------------------------------------
# Taker fee — post-Mar-30 (exponent=1)
# ---------------------------------------------------------------------------

def test_taker_fee_post_mar30_reference_trade():
    engine = FeeEngine(regime=FeeRegime.post_mar30_crypto())
    fee = engine.taker_fee(shares=Decimal("100"), price=Decimal("0.5"))
    # 100 * 0.5 * 0.072 * (0.5 * 0.5)^1 = 100 * 0.5 * 0.072 * 0.25 = 0.9
    assert abs(fee - Decimal("0.9")) <= TOLERANCE


def test_pre_and_post_regimes_differ_for_same_trade():
    pre_engine = FeeEngine(regime=FeeRegime.pre_mar30_crypto())
    post_engine = FeeEngine(regime=FeeRegime.post_mar30_crypto())
    shares = Decimal("100")
    price = Decimal("0.5")
    pre_fee = pre_engine.taker_fee(shares=shares, price=price)
    post_fee = post_engine.taker_fee(shares=shares, price=price)
    assert pre_fee != post_fee


# ---------------------------------------------------------------------------
# Maker rebate
# ---------------------------------------------------------------------------

def test_maker_rebate_proportional_to_fee_equivalent():
    engine = FeeEngine(regime=FeeRegime.pre_mar30_crypto())
    fill = make_fill(price="0.5", size="50")
    total_fee_eq = Decimal("10")
    rebate_pool = Decimal("2")

    rebate = engine.maker_rebate_estimate(
        fill=fill,
        total_fee_equivalent_in_market=total_fee_eq,
        rebate_pool=rebate_pool,
    )

    # your_fee_eq = 50 * 0.5 * 0.25 * (0.5 * 0.5)^2
    your_fee_eq = (
        Decimal("50")
        * Decimal("0.5")
        * Decimal("0.25")
        * (Decimal("0.5") * Decimal("0.5")) ** 2
    )
    expected = (your_fee_eq / total_fee_eq) * rebate_pool
    assert abs(rebate - expected) <= TOLERANCE


def test_maker_rebate_zero_when_no_market_volume():
    engine = FeeEngine(regime=FeeRegime.pre_mar30_crypto())
    fill = make_fill()
    rebate = engine.maker_rebate_estimate(
        fill=fill,
        total_fee_equivalent_in_market=Decimal("0"),
        rebate_pool=Decimal("5"),
    )
    assert rebate == Decimal("0")


def test_maker_rebate_sets_estimated_flag():
    engine = FeeEngine(regime=FeeRegime.pre_mar30_crypto())
    fill = make_fill()
    assert fill.rebate_estimated is False
    engine.maker_rebate_estimate(
        fill=fill,
        total_fee_equivalent_in_market=Decimal("10"),
        rebate_pool=Decimal("2"),
    )
    assert fill.rebate_estimated is True


# ---------------------------------------------------------------------------
# Liquidity reward
# ---------------------------------------------------------------------------

def test_lr_credit_full_spread_capture():
    engine = FeeEngine(regime=FeeRegime.pre_mar30_crypto())
    credit = engine.liquidity_reward_credit(
        bid_size=Decimal("100"),
        ask_size=Decimal("100"),
        spread=Decimal("0"),
        max_spread=Decimal("0.05"),
    )
    assert abs(credit - Decimal("100")) <= TOLERANCE


def test_lr_credit_zero_when_spread_exceeds_max():
    engine = FeeEngine(regime=FeeRegime.pre_mar30_crypto())
    credit = engine.liquidity_reward_credit(
        bid_size=Decimal("100"),
        ask_size=Decimal("100"),
        spread=Decimal("0.05"),
        max_spread=Decimal("0.05"),
    )
    assert credit == Decimal("0")


def test_lr_credit_partial_spread():
    engine = FeeEngine(regime=FeeRegime.pre_mar30_crypto())
    bid_size = Decimal("80")
    ask_size = Decimal("120")
    spread = Decimal("0.025")
    max_spread = Decimal("0.05")
    credit = engine.liquidity_reward_credit(
        bid_size=bid_size,
        ask_size=ask_size,
        spread=spread,
        max_spread=max_spread,
    )
    # min(80, 120) * (1 - 0.025/0.05) = 80 * 0.5 = 40
    expected = min(bid_size, ask_size) * (Decimal(1) - spread / max_spread)
    assert abs(credit - expected) <= TOLERANCE
