# services/signal_aggregation/aggregator.py
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Literal

from services.signal_aggregation.schemas import AggregatedSignal
from services.signal_aggregation.weighter import SignalWeighter

_STRONG = Decimal("0.7")
_MODERATE = Decimal("0.4")


def _zscore_value(value: Decimal, history: List[Decimal]) -> Decimal:
    """Z-score a single value against a list of historical values (population std)."""
    if len(history) < 2:
        return Decimal("0")
    n = Decimal(str(len(history)))
    mean = sum(history) / n
    variance = sum((h - mean) ** 2 for h in history) / n
    if variance == Decimal("0"):
        return Decimal("0")
    return (value - mean) / variance.sqrt()


class SignalAggregator:
    """Combines model, wallet, and microstructure signals into a composite."""

    def __init__(
        self,
        weighter: SignalWeighter | None = None,
        threshold: Decimal = Decimal("0.3"),
    ) -> None:
        self._weighter = weighter or SignalWeighter()
        self.threshold = threshold

    def aggregate(
        self,
        market_id: str,
        model_signal: Decimal,
        wallet_signal: Decimal,
        microstructure_signal: Decimal,
        history: List[Dict[str, Decimal]],
    ) -> AggregatedSignal:
        """
        history: list of dicts with keys 'model', 'wallet', 'micro'
                 (rolling window of past values for z-scoring).
        """
        model_hist = [h["model"] for h in history]
        wallet_hist = [h["wallet"] for h in history]
        micro_hist = [h["micro"] for h in history]

        z_model = _zscore_value(model_signal, model_hist)
        z_wallet = _zscore_value(wallet_signal, wallet_hist)
        z_micro = _zscore_value(microstructure_signal, micro_hist)

        w = self._weighter.weights
        w1 = w.get("model", Decimal("0.50"))
        w2 = w.get("wallet", Decimal("0.30"))
        w3 = w.get("micro", Decimal("0.20"))

        final = w1 * z_model + w2 * z_wallet + w3 * z_micro
        final = max(Decimal("-1"), min(Decimal("1"), final))

        abs_final = abs(final)
        if abs_final >= _STRONG:
            strength: Literal["strong", "moderate", "weak", "none"] = "strong"
        elif abs_final >= _MODERATE:
            strength = "moderate"
        elif abs_final >= self.threshold:
            strength = "weak"
        else:
            strength = "none"

        return AggregatedSignal(
            market_id=market_id,
            aggregated_at=datetime.now(timezone.utc),
            final_signal=final,
            model_component=z_model,
            wallet_component=z_wallet,
            microstructure_component=z_micro,
            weights={"model": w1, "wallet": w2, "micro": w3},
            threshold_met=abs(final) >= self.threshold,
            signal_strength=strength,
        )
