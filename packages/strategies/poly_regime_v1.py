from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional

from packages.common.market_schemas import SignalType, UnifiedSignal
from services.regime.schemas import RegimeState

from ._sprint16_utils import (
    get_regime_label,
    get_reward_eligible,
    get_reward_max_spread,
    get_snapshot_inventory_yes,
    get_snapshot_midpoint,
    get_snapshot_spread,
    make_maker_quotes,
    now_utc,
    reward_size_multiplier,
)
from .base import PortfolioState
from .poly_hybrid_v1 import PolyHybridStrategyV1


class PolyRegimeStrategyV1(PolyHybridStrategyV1):
    """Regime-aware strategy that changes quoting policy by current regime."""

    def __init__(self, strategy_id: str, config: Dict[str, Any]) -> None:
        super().__init__(strategy_id, config)
        self._last_regime_label: Optional[str] = None

    def on_regime_state(self, regime_state: RegimeState) -> None:
        self._regime_state = regime_state
        self._last_regime_label = get_regime_label(regime_state)

    def generate_signals(self, portfolio: PortfolioState) -> List[UnifiedSignal]:
        snapshot = self._latest_snapshot
        if snapshot is None:
            return []

        regime = self._last_regime_label or get_regime_label(self._regime_state or getattr(snapshot, "regime_state", None))
        if regime == "R4":
            return [
                UnifiedSignal(
                    asset_id=self._market_id,
                    market_type=self.market_type,
                    signal_type=SignalType.MARKET_MAKING,
                    direction="none",
                    confidence=Decimal("0"),
                    horizon_seconds=self._horizon_seconds,
                    strategy_id=self.strategy_id,
                    metadata={
                        "action": "cancel_all",
                        "regime": "R4",
                        "reason": "connectivity_override",
                        "generated_at": now_utc().isoformat(),
                    },
                )
            ]

        if regime == "R5":
            return [
                UnifiedSignal(
                    asset_id=self._market_id,
                    market_type=self.market_type,
                    signal_type=SignalType.DIRECTIONAL,
                    direction="none",
                    confidence=Decimal("0"),
                    horizon_seconds=self._horizon_seconds,
                    strategy_id=self.strategy_id,
                    metadata={
                        "action": "abstain",
                        "regime": "R5",
                        "reason": "dead_market",
                        "generated_at": now_utc().isoformat(),
                    },
                )
            ]

        if regime == "R3":
            return [
                UnifiedSignal(
                    asset_id=self._market_id,
                    market_type=self.market_type,
                    signal_type=SignalType.MARKET_MAKING,
                    direction="none",
                    confidence=Decimal("0"),
                    horizon_seconds=self._horizon_seconds,
                    strategy_id=self.strategy_id,
                    metadata={
                        "action": "cancel_all",
                        "regime": "R3",
                        "reason": "near_close_toxic",
                        "hold_position": True,
                        "generated_at": now_utc().isoformat(),
                    },
                )
            ]

        midpoint = get_snapshot_midpoint(snapshot)
        spread = get_snapshot_spread(snapshot)
        if midpoint is None or spread is None:
            return []

        inventory_yes = get_snapshot_inventory_yes(snapshot)
        quote_multiplier = Decimal("1.5") if regime == "R2" else Decimal("1")
        size_multiplier = Decimal("0.75") if regime == "R2" else Decimal("1")

        if regime == "R1":
            return super().generate_signals(portfolio)

        bid_price, ask_price, _, effective_spread = make_maker_quotes(
            midpoint=midpoint,
            spread=spread * quote_multiplier,
            inventory_yes=inventory_yes,
            phi=self._inventory_phi,
        )

        size_factor = reward_size_multiplier(
            get_snapshot_spread(snapshot),
            get_reward_eligible(snapshot),
            get_reward_max_spread(snapshot),
        )
        bid_size = self._quote_size * size_multiplier * size_factor
        ask_size = self._quote_size * size_multiplier * size_factor

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
                    "quote_spread": str(spread * quote_multiplier),
                    "effective_spread": str(effective_spread),
                    "mode": "defensive_mm",
                    "regime": regime,
                    "generated_at": now_utc().isoformat(),
                },
            )
        ]
