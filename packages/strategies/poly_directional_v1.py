from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from packages.common.market_schemas import SignalType, UnifiedSignal
from packages.common.polymarket_schemas import FeatureSnapshot
from packages.common.schemas import Order
from services.ml.probability_model.schemas import PredictionRecord
from services.regime.schemas import RegimeState
from services.signal_aggregation.schemas import AggregatedSignal

from ._sprint16_base import Sprint16PredictionStrategyBase
from ._sprint16_utils import (
    edge_confidence,
    get_prediction_edge,
    get_regime_label,
    get_snapshot_time_to_close_seconds,
    now_utc,
)
from .base import PortfolioState


class PolyDirectionalStrategyV1(Sprint16PredictionStrategyBase):
    """Directional strategy that turns Sprint 14 edge into long/short signals."""

    def __init__(self, strategy_id: str, config: Dict[str, Any]) -> None:
        super().__init__(strategy_id, config)
        self._market_id = config["market_id"]
        self._horizon_seconds = int(config.get("horizon_seconds", 60))
        self._min_hold_seconds = int(config.get("min_hold_seconds", 120))
        self._max_position_usd = Decimal(str(config.get("max_position_usd", "1000")))
        self._latest_prediction: Optional[PredictionRecord] = None
        self._latest_snapshot: Optional[FeatureSnapshot] = None
        self._regime_state: Optional[RegimeState] = None
        self._aggregated_signal: Optional[AggregatedSignal] = None
        self._last_emitted_direction: Optional[str] = None
        self._last_emitted_at: Optional[datetime] = None

    def initialize(self, mode) -> None:
        super().initialize(mode)
        self._latest_prediction = None
        self._latest_snapshot = None
        self._regime_state = None
        self._aggregated_signal = None
        self._last_emitted_direction = None
        self._last_emitted_at = None

    def on_market_data(self, prediction: PredictionRecord) -> None:
        self._latest_prediction = prediction

    def on_prediction(self, prediction: PredictionRecord) -> None:
        self._latest_prediction = prediction

    def on_feature_snapshot(self, snapshot: FeatureSnapshot) -> None:
        self._latest_snapshot = snapshot

    def on_regime_state(self, regime_state: RegimeState) -> None:
        self._regime_state = regime_state

    def on_aggregated_signal(self, signal: AggregatedSignal) -> None:
        self._aggregated_signal = signal

    def generate_signals(self, portfolio: PortfolioState) -> List[UnifiedSignal]:
        prediction = self._latest_prediction
        if prediction is None:
            return []

        regime_label = get_regime_label(self._regime_state or getattr(prediction, "regime_state", None))
        if regime_label not in {"R1", "R2"}:
            return []

        mispricing, threshold = get_prediction_edge(prediction)
        if mispricing is None or threshold is None or abs(mispricing) <= threshold:
            return []

        # If an aggregated signal is present and its threshold is not met, suppress
        if self._aggregated_signal is not None and not self._aggregated_signal.threshold_met:
            return []

        direction = "long" if mispricing > 0 else "short"
        predicted_at = getattr(prediction, "predicted_at", now_utc())

        if (
            self._last_emitted_direction == direction
            and self._last_emitted_at is not None
            and (predicted_at - self._last_emitted_at).total_seconds() < self._min_hold_seconds
        ):
            return []

        time_to_close_seconds = (
            get_snapshot_time_to_close_seconds(self._latest_snapshot)
            if self._latest_snapshot is not None
            else None
        )

        signal = UnifiedSignal(
            asset_id=self._market_id,
            market_type=self.market_type,
            signal_type=SignalType.DIRECTIONAL,
            direction=direction,
            confidence=edge_confidence(mispricing, threshold),
            horizon_seconds=self._horizon_seconds,
            strategy_id=self.strategy_id,
            metadata={
                "market_id": getattr(prediction, "market_id", self._market_id),
                "token_id": getattr(prediction, "token_id", None),
                "mispricing": str(mispricing),
                "threshold": str(threshold),
                "p_hat": str(getattr(prediction, "p_hat", "")),
                "implied_probability": str(getattr(prediction, "implied_probability", "")),
                "prediction_confidence": str(getattr(prediction, "confidence", "")),
                "time_to_close_seconds": None if time_to_close_seconds is None else str(time_to_close_seconds),
                "regime": regime_label,
                "generated_at": now_utc().isoformat(),
            },
        )

        self._last_emitted_direction = direction
        self._last_emitted_at = predicted_at
        return [signal]

    def risk_check(
        self, signals: List[UnifiedSignal], portfolio: PortfolioState
    ) -> List[Order]:
        for signal in signals:
            time_to_close = signal.metadata.get("time_to_close_seconds")
            if time_to_close is None:
                continue
            if Decimal(str(time_to_close)) < Decimal("120"):
                return []
        return []

