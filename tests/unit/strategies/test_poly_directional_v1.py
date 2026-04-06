from datetime import datetime, timezone
from decimal import Decimal

from packages.common.market_schemas import MarketType, SignalType
from packages.common.schemas import TradingMode
from packages.strategies.poly_directional_v1 import PolyDirectionalStrategyV1

from ._sprint16_fixtures import make_portfolio, make_prediction, make_regime, make_snapshot


def test_poly_directional_v1_emits_long_and_short_signals():
    strategy = PolyDirectionalStrategyV1(
        "poly_directional_v1",
        {"market_id": "btc-hourly-1", "min_hold_seconds": 120, "max_position_usd": "1000"},
    )
    strategy.initialize(TradingMode.PAPER)
    strategy.on_feature_snapshot(make_snapshot())
    strategy.on_regime_state(make_regime("R1"))

    strategy.on_prediction(make_prediction("0.08", "0.05", datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)))
    long_signal = strategy.generate_signals(make_portfolio())
    assert len(long_signal) == 1
    assert long_signal[0].direction == "long"
    assert long_signal[0].signal_type == SignalType.DIRECTIONAL
    assert long_signal[0].market_type == MarketType.PREDICTION

    strategy.on_prediction(make_prediction("-0.09", "0.05", datetime(2026, 1, 1, 12, 5, tzinfo=timezone.utc)))
    short_signal = strategy.generate_signals(make_portfolio())
    assert len(short_signal) == 1
    assert short_signal[0].direction == "short"


def test_poly_directional_v1_respects_hold_and_rejects_close_time():
    strategy = PolyDirectionalStrategyV1(
        "poly_directional_v1",
        {"market_id": "btc-hourly-1", "min_hold_seconds": 120, "max_position_usd": "1000"},
    )
    strategy.initialize(TradingMode.PAPER)
    strategy.on_feature_snapshot(make_snapshot(time_to_close_seconds=90.0))
    strategy.on_regime_state(make_regime("R1"))

    first_at = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    strategy.on_prediction(make_prediction("0.08", "0.05", first_at))
    signals = strategy.generate_signals(make_portfolio())
    assert len(signals) == 1
    assert strategy.risk_check(signals, make_portfolio()) == []

    strategy.on_prediction(make_prediction("0.08", "0.05", first_at.replace(minute=1)))
    assert strategy.generate_signals(make_portfolio()) == []

