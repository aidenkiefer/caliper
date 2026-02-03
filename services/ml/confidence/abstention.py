"""
Abstention decision logic and tracking.
"""

from datetime import datetime
from typing import Optional
from types import SimpleNamespace
from pydantic import BaseModel, Field
from .gating import AbstentionDecision, Signal


class AbstentionTracker:
    """
    Tracks abstention decisions and rates.
    """

    def __init__(self, strategy_id: str):
        """Initialize tracker for a strategy."""
        self.strategy_id = strategy_id
        self.total_predictions = 0
        self.abstentions = 0
        self.abstention_reasons: dict[str, int] = {}

    def record_decision(self, signal: Signal, reason: Optional[str] = None) -> None:
        """Record a prediction decision."""
        self.total_predictions += 1

        if signal == Signal.ABSTAIN:
            self.abstentions += 1
            if reason:
                self.abstention_reasons[reason] = self.abstention_reasons.get(reason, 0) + 1

    def record_signal(self, signal_side: str) -> None:
        """Record a signal by side string (BUY, SELL, ABSTAIN). Used by tests and backtest-style callers."""
        try:
            signal = Signal(signal_side)
        except ValueError:
            signal = Signal.BUY
        self.record_decision(signal)

    def get_abstention_rate(self) -> float:
        """Get abstention rate (0.0 to 1.0)."""
        if self.total_predictions == 0:
            return 0.0
        return self.abstentions / self.total_predictions

    def get_metrics(self) -> SimpleNamespace:
        """Return metrics compatible with backtest-style callers (total_signals, abstentions, abstention_rate)."""
        return SimpleNamespace(
            total_signals=self.total_predictions,
            abstentions=self.abstentions,
            abstention_rate=self.get_abstention_rate(),
        )

    def get_abstention_decision(
        self,
        reason: str,
        confidence: float,
        threshold: float,
    ) -> AbstentionDecision:
        """Create an abstention decision record."""
        return AbstentionDecision(
            strategy_id=self.strategy_id,
            reason=reason,
            confidence=confidence,
            threshold=threshold,
            timestamp=datetime.utcnow().isoformat(),
        )
