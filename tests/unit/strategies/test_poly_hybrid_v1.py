from datetime import datetime, timezone
from decimal import Decimal

from packages.common.market_schemas import MarketType, SignalType
from packages.common.schemas import TradingMode
from packages.strategies.poly_hybrid_v1 import PolyHybridStrategyV1

from ._sprint16_fixtures import make_portfolio, make_prediction, make_snapshot


def test_poly_hybrid_v1_tightens_favorable_side_and_stays_maker_only():
    strategy = PolyHybridStrategyV1(
        "poly_hybrid_v1",
        {"market_id": "btc-hourly-1", "quote_spread": "0.02", "quote_size": "50"},
    )
    strategy.initialize(TradingMode.PAPER)
    strategy.on_market_data(make_snapshot(reward_eligible=False))
    strategy.on_prediction(make_prediction("0.08", "0.05", datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)))

    signals = strategy.generate_signals(make_portfolio())
    assert len(signals) == 1
    signal = signals[0]
    assert signal.market_type == MarketType.PREDICTION
    assert signal.signal_type == SignalType.HYBRID
    assert signal.direction == "long"
    assert signal.metadata["never_taker"] is True
    assert Decimal(signal.metadata["bid_price"]) > Decimal("0.54")
    assert Decimal(signal.metadata["ask_price"]) > Decimal("0.56")
    assert Decimal(signal.metadata["bid_size"]) > Decimal(signal.metadata["ask_size"])


def test_poly_hybrid_v1_reverts_to_symmetry_without_edge():
    strategy = PolyHybridStrategyV1(
        "poly_hybrid_v1",
        {"market_id": "btc-hourly-1", "quote_spread": "0.02", "quote_size": "50"},
    )
    strategy.initialize(TradingMode.PAPER)
    strategy.on_market_data(make_snapshot(reward_eligible=False))
    strategy.on_prediction(make_prediction("0.01", "0.05"))

    signal = strategy.generate_signals(make_portfolio())[0]
    assert signal.direction == "none"
    assert signal.signal_type == SignalType.MARKET_MAKING
    assert Decimal(signal.metadata["bid_size"]) == Decimal(signal.metadata["ask_size"])
