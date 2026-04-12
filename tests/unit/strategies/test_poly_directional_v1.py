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


from services.signal_aggregation.schemas import AggregatedSignal as _AggSig
from decimal import Decimal as _Dec
from datetime import datetime as _dt, timezone as _tz


def _make_agg_signal(threshold_met: bool, final: float = 0.5) -> _AggSig:
    return _AggSig(
        market_id="mkt1",
        aggregated_at=_dt.now(_tz.utc),
        final_signal=_Dec(str(final)),
        model_component=_Dec("0.5"),
        wallet_component=_Dec("0.3"),
        microstructure_component=_Dec("0.2"),
        weights={"model": _Dec("0.5"), "wallet": _Dec("0.3"), "micro": _Dec("0.2")},
        threshold_met=threshold_met,
        signal_strength="moderate" if threshold_met else "none",
    )


def _make_directional_strategy_with_prediction() -> PolyDirectionalStrategyV1:
    """Create a directional strategy with an active prediction that would generate a signal."""
    from packages.common.schemas import TradingMode
    strategy = PolyDirectionalStrategyV1(
        "poly_directional_v1",
        {"market_id": "btc-hourly-1", "min_hold_seconds": 120, "max_position_usd": "1000"},
    )
    strategy.initialize(TradingMode.PAPER)
    strategy.on_feature_snapshot(make_snapshot())
    strategy.on_regime_state(make_regime("R1"))
    strategy.on_prediction(make_prediction("0.08", "0.05", _dt(2026, 1, 1, 12, 0, tzinfo=_tz.utc)))
    return strategy


def test_directional_suppressed_when_agg_signal_not_met() -> None:
    """Strategy suppresses signals when AggregatedSignal threshold not met."""
    strategy = _make_directional_strategy_with_prediction()
    strategy.on_aggregated_signal(_make_agg_signal(threshold_met=False))
    signals = strategy.generate_signals(make_portfolio())
    assert signals == []


def test_directional_passes_when_agg_signal_met() -> None:
    """Strategy emits signals normally when AggregatedSignal threshold is met."""
    strategy = _make_directional_strategy_with_prediction()
    strategy.on_aggregated_signal(_make_agg_signal(threshold_met=True))
    signals = strategy.generate_signals(make_portfolio())
    assert len(signals) == 1
    assert signals[0].direction == "long"


def test_directional_passes_when_no_agg_signal() -> None:
    """Strategy emits signals normally when no AggregatedSignal has been set."""
    strategy = _make_directional_strategy_with_prediction()
    signals = strategy.generate_signals(make_portfolio())
    assert len(signals) == 1

