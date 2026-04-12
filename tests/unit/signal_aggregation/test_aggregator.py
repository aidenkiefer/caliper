import pytest
from decimal import Decimal
from datetime import datetime, timezone

from services.signal_aggregation.aggregator import SignalAggregator
from services.signal_aggregation.schemas import AggregatedSignal
from services.signal_aggregation.weighter import SignalWeighter


def test_final_signal_zero_when_all_components_zero() -> None:
    """AC-7: FinalSignal = 0 when all components are 0."""
    agg = SignalAggregator()
    result = agg.aggregate(
        market_id="mkt1",
        model_signal=Decimal("0"),
        wallet_signal=Decimal("0"),
        microstructure_signal=Decimal("0"),
        history=[
            {"model": Decimal("0"), "wallet": Decimal("0"), "micro": Decimal("0")}
        ] * 5,
    )
    assert float(result.final_signal) == pytest.approx(0.0, abs=1e-9)


def test_aggregator_applies_zscoring() -> None:
    """AC-7: z-scoring normalises components before weighting."""
    history = [
        {"model": Decimal(str(i)), "wallet": Decimal("0"), "micro": Decimal("0")}
        for i in range(-5, 6)
    ]
    agg = SignalAggregator()
    result = agg.aggregate(
        market_id="mkt1",
        model_signal=Decimal("5"),
        wallet_signal=Decimal("0"),
        microstructure_signal=Decimal("0"),
        history=history,
    )
    # z-scored model signal: history mean=0, compute std
    values = list(range(-5, 6))
    mean = sum(values) / len(values)  # = 0
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    std = variance ** 0.5
    expected_z_model = (5 - mean) / std
    assert float(result.model_component) == pytest.approx(expected_z_model, rel=0.05)


def test_weight_learning_increases_better_predictor() -> None:
    """AC-7: weight learning increases w1 when ModelSignal has higher predictive power."""
    weighter = SignalWeighter(
        initial_weights={"model": Decimal("0.50"), "wallet": Decimal("0.30"), "micro": Decimal("0.20")}
    )
    correlation_scores = {"model": Decimal("0.8"), "wallet": Decimal("0.1"), "micro": Decimal("0.1")}
    new_weights = weighter.update(correlation_scores)
    assert new_weights["model"] > Decimal("0.50")
    assert new_weights["model"] <= Decimal("0.70")  # bounded


def test_aggregated_signal_threshold_met() -> None:
    agg = SignalAggregator(threshold=Decimal("0.3"))
    # Use history with variation so z-scores can be computed meaningfully
    history = [
        {"model": Decimal(str(i)), "wallet": Decimal(str(i)), "micro": Decimal(str(i))}
        for i in range(-5, 6)
    ]
    result = agg.aggregate(
        market_id="mkt1",
        model_signal=Decimal("10"),
        wallet_signal=Decimal("10"),
        microstructure_signal=Decimal("10"),
        history=history,
    )
    assert result.threshold_met is True
