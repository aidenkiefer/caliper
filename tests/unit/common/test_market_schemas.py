from decimal import Decimal

import pytest

from packages.common.market_schemas import (
    MarketType,
    SignalType,
    UnifiedSignal,
)


def test_market_type_values():
    assert MarketType.EQUITY == "EQUITY"
    assert MarketType.PREDICTION == "PREDICTION"
    assert MarketType.CRYPTO == "CRYPTO"


def test_signal_type_values():
    assert SignalType.DIRECTIONAL == "DIRECTIONAL"
    assert SignalType.MARKET_MAKING == "MARKET_MAKING"
    assert SignalType.HYBRID == "HYBRID"


def test_unified_signal_directional():
    s = UnifiedSignal(
        asset_id="AAPL",
        market_type=MarketType.EQUITY,
        signal_type=SignalType.DIRECTIONAL,
        direction="long",
        confidence=Decimal("0.75"),
        horizon_seconds=3600,
        strategy_id="sma_v1",
    )
    assert s.asset_id == "AAPL"
    assert s.confidence == Decimal("0.75")
    assert s.metadata == {}


def test_unified_signal_market_making():
    s = UnifiedSignal(
        asset_id="BTC-UP-2026-04-04T15",
        market_type=MarketType.PREDICTION,
        signal_type=SignalType.MARKET_MAKING,
        direction="none",
        confidence=Decimal("1.0"),
        horizon_seconds=3600,
        strategy_id="polymarket_mm_v1",
        metadata={"quote_spread": "0.02", "inventory_yes": "50"},
    )
    assert s.signal_type == SignalType.MARKET_MAKING
    assert s.metadata["quote_spread"] == "0.02"


def test_unified_signal_confidence_validation():
    with pytest.raises(Exception):
        UnifiedSignal(
            asset_id="AAPL",
            market_type=MarketType.EQUITY,
            signal_type=SignalType.DIRECTIONAL,
            direction="long",
            confidence=Decimal("1.5"),  # out of range
            horizon_seconds=3600,
            strategy_id="sma_v1",
        )


def test_unified_signal_direction_validation():
    with pytest.raises(Exception):
        UnifiedSignal(
            asset_id="AAPL",
            market_type=MarketType.EQUITY,
            signal_type=SignalType.DIRECTIONAL,
            direction="sideways",  # invalid
            confidence=Decimal("0.6"),
            horizon_seconds=3600,
            strategy_id="sma_v1",
        )
