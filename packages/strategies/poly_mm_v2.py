from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional

from packages.common.market_schemas import SignalType, UnifiedSignal
from packages.common.polymarket_schemas import FeatureSnapshot
from services.regime.schemas import RegimeState

from ._sprint16_base import Sprint16PredictionStrategyBase
from ._sprint16_utils import (
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


class PolyMMStrategyV2(Sprint16PredictionStrategyBase):
    """Sprint 16 maker strategy with inventory skew and reward-aware sizing."""

    def __init__(self, strategy_id: str, config: Dict[str, Any]) -> None:
        super().__init__(strategy_id, config)
        self._market_id = config["market_id"]
        self._quote_spread = to_decimal(config.get("quote_spread", "0.02"), Decimal("0.02")) or Decimal("0.02")
        self._quote_size = to_decimal(config.get("quote_size", "50"), Decimal("50")) or Decimal("50")
        self._inventory_cap = to_decimal(config.get("inventory_cap", "200"), Decimal("200")) or Decimal("200")
        self._inventory_phi = to_decimal(
            config.get("inventory_skew_phi", "0.001"), Decimal("0.001")
        ) or Decimal("0.001")
        self._max_quoted_spread = to_decimal(
            config.get("max_quoted_spread", "0.10"), Decimal("0.10")
        ) or Decimal("0.10")
        self._horizon_seconds = int(config.get("horizon_seconds", 60))
        self._snapshot: Optional[FeatureSnapshot] = None
        self._regime_state: Optional[RegimeState] = None
        self._inventory_yes = Decimal("0")

    def initialize(self, mode) -> None:
        super().initialize(mode)
        self._snapshot = None
        self._regime_state = None
        self._inventory_yes = Decimal("0")

    def on_market_data(self, snapshot: FeatureSnapshot) -> None:
        self._snapshot = snapshot
        self._inventory_yes = get_snapshot_inventory_yes(snapshot)

    def update_inventory(self, inventory_yes: Decimal) -> None:
        self._inventory_yes = Decimal(str(inventory_yes))

    def on_regime_state(self, regime_state: RegimeState) -> None:
        self._regime_state = regime_state

    def generate_signals(self, portfolio: PortfolioState) -> List[UnifiedSignal]:
        snapshot = self._snapshot
        if snapshot is None:
            return []

        midpoint = get_snapshot_midpoint(snapshot)
        if midpoint is None:
            return []

        regime_label = get_regime_label(self._regime_state or getattr(snapshot, "regime_state", None))
        if regime_label == "R3":
            return []

        quote_spread = self._quote_spread
        time_to_close_seconds = get_snapshot_time_to_close_seconds(snapshot)
        near_close = time_to_close_seconds is not None and time_to_close_seconds <= 600
        effective_spread = quote_spread * (Decimal("2") if near_close else Decimal("1"))
        if effective_spread > self._max_quoted_spread:
            return []

        bid_price, ask_price, _, actual_spread = make_maker_quotes(
            midpoint=midpoint,
            spread=effective_spread,
            inventory_yes=self._inventory_yes,
            phi=self._inventory_phi,
        )

        size_multiplier = reward_size_multiplier(
            get_snapshot_spread(snapshot),
            get_reward_eligible(snapshot),
            get_reward_max_spread(snapshot),
        )
        bid_size = self._quote_size * size_multiplier
        ask_size = self._quote_size * size_multiplier

        if self._inventory_yes >= self._inventory_cap:
            bid_size = Decimal("0")
        if self._inventory_yes <= Decimal("0"):
            ask_size = Decimal("0")

        if bid_size <= 0 and ask_size <= 0:
            return []

        return [
            UnifiedSignal(
                asset_id=self._market_id,
                market_type=self.market_type,
                signal_type=SignalType.MARKET_MAKING,
                direction="none",
                confidence=Decimal("1"),
                horizon_seconds=self._horizon_seconds,
                strategy_id=self.strategy_id,
                metadata={
                    "bid_price": str(bid_price),
                    "ask_price": str(ask_price),
                    "bid_size": str(bid_size),
                    "ask_size": str(ask_size),
                    "inventory_yes": str(self._inventory_yes),
                    "inventory_skew": str(self._inventory_phi * self._inventory_yes),
                    "midpoint": str(midpoint),
                    "quote_spread": str(quote_spread),
                    "effective_spread": str(actual_spread),
                    "reward_eligible": get_reward_eligible(snapshot),
                    "reward_multiplier": str(size_multiplier),
                    "regime": regime_label,
                    "generated_at": now_utc().isoformat(),
                },
            )
        ]
