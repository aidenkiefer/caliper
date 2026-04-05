from __future__ import annotations

import random
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal, Optional


@dataclass
class AdverseSelectionModel:
    """
    Models the increasing proportion of informed order flow near market close.
    Informed fraction pi(t) rises linearly from baseline_informed (at open)
    to peak_informed (at close) over the last ramp_start_minutes before close.
    """
    baseline_informed: Decimal = field(default_factory=lambda: Decimal("0.05"))
    peak_informed: Decimal = field(default_factory=lambda: Decimal("0.40"))
    ramp_start_minutes: int = 10
    random_seed: Optional[int] = None

    def __post_init__(self) -> None:
        self._rng = random.Random(self.random_seed)

    def informed_fraction(self, time_to_close_seconds: float) -> Decimal:
        """
        Returns the informed fraction at the given time before close.
        - At time_to_close >= ramp_start_minutes * 60: returns baseline_informed
        - At time_to_close <= 0: returns peak_informed
        - Between 0 and ramp_start: linear interpolation
        Formula: frac = peak + (baseline - peak) * (time_to_close / (ramp_start * 60))
        """
        ramp_duration = self.ramp_start_minutes * 60.0
        if time_to_close_seconds >= ramp_duration:
            return self.baseline_informed
        if time_to_close_seconds <= 0:
            return self.peak_informed
        t = Decimal(str(time_to_close_seconds))
        rd = Decimal(str(ramp_duration))
        return self.peak_informed + (self.baseline_informed - self.peak_informed) * (t / rd)

    def is_informed(self, time_to_close_seconds: float) -> bool:
        """Bernoulli trial: returns True with probability = informed_fraction(t)."""
        frac = float(self.informed_fraction(time_to_close_seconds))
        return self._rng.random() < frac

    def directional_bias(self, expected_settlement: Decimal) -> Literal["BUY", "SELL"]:
        """Informed flow bets on the expected settlement direction."""
        if expected_settlement > Decimal("0.5"):
            return "BUY"
        return "SELL"

    def sample_order_direction(
        self,
        time_to_close_seconds: float,
        expected_settlement: Decimal,
    ) -> Literal["BUY", "SELL"]:
        """
        Returns BUY or SELL.
        If informed: returns directional_bias(expected_settlement).
        If uninformed: random 50/50.
        """
        if self.is_informed(time_to_close_seconds):
            return self.directional_bias(expected_settlement)
        return "BUY" if self._rng.random() < 0.5 else "SELL"
