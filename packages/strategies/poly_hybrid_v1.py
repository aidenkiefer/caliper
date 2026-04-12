from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional

from packages.common.market_schemas import SignalType, UnifiedSignal
from packages.common.polymarket_schemas import FeatureSnapshot
from services.ml.probability_model.schemas import PredictionRecord
from services.regime.schemas import RegimeState
from services.signal_aggregation.schemas import AggregatedSignal

from ._sprint16_base import Sprint16PredictionStrategyBase
from ._sprint16_utils import (
    edge_confidence,
    get_prediction_edge,
    get_regime_label,
    get_reward_eligible,
    get_reward_max_spread,
    get_snapshot_inventory_yes,
    get_snapshot_midpoint,
    get_snapshot_spread,
    get_snapshot_time_to_close_seconds,
    make_maker_quotes,
    now_utc,
    reward_size_multiplier,
    to_decimal,
)
from .base import PortfolioState


class PolyHybridStrategyV1(Sprint16PredictionStrategyBase):
    """Maker-first strategy that skews quotes toward a directional edge."""

    def __init__(self, strategy_id: str, config: Dict[str, Any]) -> None:
        super().__init__(strategy_id, config)
        self._market_id = config["market_id"]
        self._quote_spread = to_decimal(config.get("quote_spread", "0.02"), Decimal("0.02")) or Decimal("0.02")
        self._quote_size = to_decimal(config.get("quote_size", "50"), Decimal("50")) or Decimal("50")
        self._inventory_phi = to_decimal(
            config.get("inventory_skew_phi", "0.001"), Decimal("0.001")
        ) or Decimal("0.001")
        self._horizon_seconds = int(config.get("horizon_seconds", 60))
        self._latest_snapshot: Optional[FeatureSnapshot] = None
        self._latest_prediction: Optional[PredictionRecord] = None
        self._regime_state: Optional[RegimeState] = None
        self._aggregated_signal: Optional[AggregatedSignal] = None

    def initialize(self, mode) -> None:
        super().initialize(mode)
        self._latest_snapshot = None
        self._latest_prediction = None
        self._regime_state = None
        self._aggregated_signal = None

    def on_market_data(self, snapshot: FeatureSnapshot) -> None:
        self._latest_snapshot = snapshot

    def on_prediction(self, prediction: PredictionRecord) -> None:
        self._latest_prediction = prediction

    def on_regime_state(self, regime_state: RegimeState) -> None:
        self._regime_state = regime_state

    def on_aggregated_signal(self, signal: AggregatedSignal) -> None:
        self._aggregated_signal = signal

    def generate_signals(self, portfolio: PortfolioState) -> List[UnifiedSignal]:
        snapshot = self._latest_snapshot
        if snapshot is None:
            return []

        midpoint = get_snapshot_midpoint(snapshot)
        spread = get_snapshot_spread(snapshot)
        if midpoint is None or spread is None:
            return []

        inventory_yes = get_snapshot_inventory_yes(snapshot)
        near_close = (
            get_snapshot_time_to_close_seconds(snapshot) is not None
            and get_snapshot_time_to_close_seconds(snapshot) <= 600
        )
        effective_spread = self._quote_spread * (Decimal("2") if near_close else Decimal("1"))
        bid_factor = Decimal("1")
        ask_factor = Decimal("1")
        direction = "none"
        favorable_side = None
        unfavorable_side = None

        prediction = self._latest_prediction
        mispricing, threshold = get_prediction_edge(prediction) if prediction is not None else (None, None)
        directional_edge = mispricing is not None and threshold is not None and abs(mispricing) > threshold
        if directional_edge:
            if mispricing > 0:
                direction = "long"
                favorable_side = "bid"
                unfavorable_side = "ask"
                bid_factor = Decimal("0.5")
                ask_factor = Decimal("1.5")
            else:
                direction = "short"
                favorable_side = "ask"
                unfavorable_side = "bid"
                bid_factor = Decimal("1.5")
                ask_factor = Decimal("0.5")

        # Lean on aggregated signal for directional confirmation
        if self._aggregated_signal is not None and self._aggregated_signal.threshold_met:
            agg_final = float(self._aggregated_signal.final_signal)
            # Positive final_signal biases toward bullish lean (tighten bid, widen ask)
            lean_factor = Decimal(str(round(agg_final * 0.1, 4)))
            bid_factor = bid_factor - lean_factor
            ask_factor = ask_factor + lean_factor

        bid_price, ask_price, _, actual_spread = make_maker_quotes(
            midpoint=midpoint,
            spread=effective_spread,
            inventory_yes=inventory_yes,
            phi=self._inventory_phi,
            bid_factor=bid_factor,
            ask_factor=ask_factor,
        )

        size_multiplier = reward_size_multiplier(
            get_snapshot_spread(snapshot),
            get_reward_eligible(snapshot),
            get_reward_max_spread(snapshot),
        )

        if direction == "long":
            bid_size = self._quote_size * Decimal("1.5") * size_multiplier
            ask_size = self._quote_size * Decimal("0.5") * size_multiplier
        elif direction == "short":
            bid_size = self._quote_size * Decimal("0.5") * size_multiplier
            ask_size = self._quote_size * Decimal("1.5") * size_multiplier
        else:
            bid_size = self._quote_size * size_multiplier
            ask_size = self._quote_size * size_multiplier

        if bid_size <= 0 and ask_size <= 0:
            return []

        metadata = {
            "bid_price": str(bid_price),
            "ask_price": str(ask_price),
            "bid_size": str(bid_size),
            "ask_size": str(ask_size),
            "inventory_yes": str(inventory_yes),
            "quote_spread": str(self._quote_spread),
            "effective_spread": str(actual_spread),
            "directional_lean": direction,
            "favorable_side": favorable_side,
            "unfavorable_side": unfavorable_side,
            "reward_multiplier": str(size_multiplier),
            "never_taker": True,
            "regime": get_regime_label(self._regime_state),
            "generated_at": now_utc().isoformat(),
        }
        if prediction is not None:
            metadata.update({"mispricing": str(mispricing), "threshold": str(threshold)})

        signal_type = SignalType.HYBRID if direction != "none" else SignalType.MARKET_MAKING
        confidence = edge_confidence(mispricing, threshold) if prediction is not None else Decimal("1")
        return [
            UnifiedSignal(
                asset_id=self._market_id,
                market_type=self.market_type,
                signal_type=signal_type,
                direction=direction,
                confidence=confidence,
                horizon_seconds=self._horizon_seconds,
                strategy_id=self.strategy_id,
                metadata=metadata,
            )
        ]
