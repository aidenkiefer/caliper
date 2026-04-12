# services/signal_aggregation/weighter.py
from __future__ import annotations

from decimal import Decimal
from typing import Dict

WEIGHT_MIN = Decimal("0.10")
WEIGHT_MAX = Decimal("0.70")
MAX_WEEKLY_CHANGE = Decimal("0.05")


class SignalWeighter:
    """Updates composite signal weights based on recent predictive power."""

    def __init__(
        self,
        initial_weights: Dict[str, Decimal] | None = None,
    ) -> None:
        self.weights: Dict[str, Decimal] = initial_weights or {
            "model": Decimal("0.50"),
            "wallet": Decimal("0.30"),
            "micro": Decimal("0.20"),
        }

    def update(self, correlation_scores: Dict[str, Decimal]) -> Dict[str, Decimal]:
        """
        Shift weights toward components with higher recent correlation.
        Bounded per component, max weekly change = 0.05.
        """
        total_corr = sum(correlation_scores.get(k, Decimal("0")) for k in self.weights)
        if total_corr <= Decimal("0"):
            return dict(self.weights)

        new_weights: Dict[str, Decimal] = {}
        for key in self.weights:
            target_share = correlation_scores.get(key, Decimal("0")) / total_corr
            current = self.weights[key]
            delta = target_share - current
            abs_delta = abs(delta)
            capped_delta = min(abs_delta, MAX_WEEKLY_CHANGE)
            if target_share > current:
                new_w = current + capped_delta
            else:
                new_w = current - capped_delta
            new_weights[key] = max(WEIGHT_MIN, min(WEIGHT_MAX, new_w))

        # Re-normalize to sum to 1.0, then re-clamp to ensure bounds hold
        total = sum(new_weights.values())
        normalized = {k: v / total for k, v in new_weights.items()}

        # Second bounds pass after normalization
        clamped = {k: max(WEIGHT_MIN, min(WEIGHT_MAX, v)) for k, v in normalized.items()}
        final_total = sum(clamped.values())
        self.weights = {k: v / final_total for k, v in clamped.items()}
        return dict(self.weights)
