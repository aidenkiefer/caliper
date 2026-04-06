from datetime import datetime, timezone
from decimal import Decimal

from packages.common.market_schemas import SignalType
from packages.common.schemas import TradingMode
from packages.strategies.poly_regime_v1 import PolyRegimeStrategyV1

from ._sprint16_fixtures import make_portfolio, make_prediction, make_regime, make_snapshot


def test_poly_regime_v1_r5_abstains_and_r4_cancels():
    strategy = PolyRegimeStrategyV1(
        "poly_regime_v1",
        {"market_id": "btc-hourly-1", "quote_spread": "0.02", "quote_size": "50"},
    )
    strategy.initialize(TradingMode.PAPER)
    strategy.on_market_data(make_snapshot())
    strategy.on_prediction(make_prediction("0.08", "0.05"))

    strategy.on_regime_state(make_regime("R5"))
    r5_signal = strategy.generate_signals(make_portfolio())[0]
    assert r5_signal.direction == "none"
    assert r5_signal.metadata["action"] == "abstain"
    assert r5_signal.signal_type == SignalType.DIRECTIONAL

    strategy.on_regime_state(make_regime("R4"))
    r4_signal = strategy.generate_signals(make_portfolio())[0]
    assert r4_signal.direction == "none"
    assert r4_signal.metadata["action"] == "cancel_all"
    assert r4_signal.signal_type == SignalType.MARKET_MAKING


def test_poly_regime_v1_r1_uses_hybrid_and_r3_cancels_quotes():
    strategy = PolyRegimeStrategyV1(
        "poly_regime_v1",
        {"market_id": "btc-hourly-1", "quote_spread": "0.02", "quote_size": "50"},
    )
    strategy.initialize(TradingMode.PAPER)
    strategy.on_market_data(make_snapshot())
    strategy.on_prediction(make_prediction("0.08", "0.05"))

    strategy.on_regime_state(make_regime("R1"))
    r1_signal = strategy.generate_signals(make_portfolio())[0]
    assert r1_signal.signal_type == SignalType.HYBRID
    assert r1_signal.direction == "long"

    strategy.on_regime_state(make_regime("R3"))
    r3_signal = strategy.generate_signals(make_portfolio())[0]
    assert r3_signal.metadata["action"] == "cancel_all"
    assert r3_signal.metadata["hold_position"] is True
    assert r3_signal.direction == "none"

