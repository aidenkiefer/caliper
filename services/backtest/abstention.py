"""
Abstention tracking for backtest engine.

Tracks when strategies abstain from trading and calculates metrics.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field


class AbstentionMetrics(BaseModel):
    """Metrics related to abstentions."""

    total_signals: int = Field(ge=0, description="Total signals generated")
    abstentions: int = Field(ge=0, description="Number of abstentions")
    abstention_rate: Decimal = Field(ge=0, le=1, description="Abstention rate (0.0 to 1.0)")
    opportunity_cost: Optional[Decimal] = Field(
        None, description="Estimated opportunity cost of abstentions"
    )


class AbstentionTracker:
    """
    Tracks abstentions during backtest execution.
    """

    def __init__(self):
        """Initialize abstention tracker."""
        self.total_signals = 0
        self.abstentions = 0
        self.abstention_timestamps: List[datetime] = []

    def record_signal(self, signal_side: str) -> None:
        """
        Record a signal (including abstentions).

        Args:
            signal_side: Signal side ('BUY', 'SELL', or 'ABSTAIN')
        """
        self.total_signals += 1

        if signal_side == "ABSTAIN":
            self.abstentions += 1
            self.abstention_timestamps.append(datetime.utcnow())

    def get_metrics(self) -> AbstentionMetrics:
        """Get abstention metrics."""
        if self.total_signals == 0:
            abstention_rate = Decimal("0")
        else:
            abstention_rate = Decimal(str(self.abstentions)) / Decimal(str(self.total_signals))

        return AbstentionMetrics(
            total_signals=self.total_signals,
            abstentions=self.abstentions,
            abstention_rate=abstention_rate,
            opportunity_cost=None,  # Would need market data to calculate
        )
