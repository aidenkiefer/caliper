from decimal import Decimal

from packages.common.market_schemas import MarketType, SignalType, UnifiedSignal
from packages.common.schemas import TradingMode
from packages.strategies.poly_mm_v2 import PolyMMStrategyV2

from ._sprint16_fixtures import make_portfolio, make_regime, make_snapshot


def test_poly_mm_v2_emits_mm_signal_with_inventory_skew():
    strategy = PolyMMStrategyV2(
        "poly_mm_v2",
        {
            "market_id": "btc-hourly-1",
            "quote_spread": "0.02",
            "quote_size": "50",
            "inventory_cap": "200",
            "inventory_skew_phi": "0.01",
        },
    )
    strategy.initialize(TradingMode.PAPER)
    strategy.on_market_data(make_snapshot())
    strategy.on_regime_state(make_regime("R1"))
    strategy.update_inventory(Decimal("10"))

    signals = strategy.generate_signals(make_portfolio())

    assert len(signals) == 1
    signal = signals[0]
    assert isinstance(signal, UnifiedSignal)
    assert signal.market_type == MarketType.PREDICTION
    assert signal.signal_type == SignalType.MARKET_MAKING
    assert signal.direction == "none"
    assert Decimal(signal.metadata["inventory_skew"]) == Decimal("0.10")
    assert Decimal(signal.metadata["bid_price"]) < Decimal("0.55")
    assert Decimal(signal.metadata["ask_price"]) < Decimal("0.57")


def test_poly_mm_v2_widens_near_close_and_suppresses_r3():
    strategy = PolyMMStrategyV2(
        "poly_mm_v2",
        {
            "market_id": "btc-hourly-1",
            "quote_spread": "0.02",
            "quote_size": "50",
            "inventory_cap": "200",
            "inventory_skew_phi": "0.01",
        },
    )
    strategy.initialize(TradingMode.PAPER)
    strategy.on_market_data(make_snapshot(time_to_close_seconds=300.0))
    strategy.on_regime_state(make_regime("R3"))
    strategy.update_inventory(Decimal("10"))

    assert strategy.generate_signals(make_portfolio()) == []

    strategy.on_regime_state(make_regime("R1"))
    signals = strategy.generate_signals(make_portfolio())
    assert len(signals) == 1
    signal = signals[0]
    assert Decimal(signal.metadata["effective_spread"]) == Decimal("0.04")
    assert Decimal(signal.metadata["bid_size"]) == Decimal("30")
    assert Decimal(signal.metadata["ask_size"]) == Decimal("30")

