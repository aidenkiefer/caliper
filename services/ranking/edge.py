from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from services.ranking.schemas import CandidateMarket, EdgeEstimate


def _to_decimal(value: Decimal | float | int | str | None, default: str = "0") -> Decimal:
    if value is None:
        return Decimal(default)
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True)
class EdgeEstimatorConfig:
    staleness_threshold_seconds: float = 30.0
    decay_rate: float = 0.05
    default_size: Decimal = Decimal("1")


class EdgeEstimator:
    """Cost-adjusted EV estimator for one candidate market."""

    def __init__(self, config: EdgeEstimatorConfig | None = None) -> None:
        self._config = config or EdgeEstimatorConfig()

    def estimate(
        self,
        candidate: CandidateMarket,
        *,
        p_hat: Optional[Decimal | float] = None,
        p_pm: Optional[Decimal | float] = None,
        size: Decimal | float | None = None,
        staleness_seconds: Optional[float] = None,
    ) -> EdgeEstimate:
        size_value = _to_decimal(size, default=str(self._config.default_size))
        p_hat_value = _to_decimal(p_hat if p_hat is not None else candidate.p_hat, default="0.5")
        p_pm_value = _to_decimal(p_pm if p_pm is not None else candidate.p_pm, default="0.5")
        half_spread = _to_decimal(candidate.spread, default="0") / Decimal("2")
        staleness = float(candidate.staleness_seconds if staleness_seconds is None else staleness_seconds)
        low_confidence = p_hat is None and candidate.p_hat is None

        ev_raw = p_hat_value - p_pm_value
        slippage_estimate = self._slippage(candidate=candidate, size=size_value)
        fee_edge = self._fee_edge(candidate=candidate, size=size_value)

        ev_adj_value = ev_raw - half_spread - slippage_estimate - fee_edge
        effective_staleness = max(staleness - self._config.staleness_threshold_seconds, 0.0)
        decay_factor = math.exp(-self._config.decay_rate * effective_staleness) if effective_staleness > 0 else 1.0
        ev_adj_value = ev_adj_value * Decimal(str(decay_factor))

        return EdgeEstimate(
            p_hat=p_hat_value,
            p_pm=p_pm_value,
            ev_raw=ev_raw,
            ev_adj=ev_adj_value,
            half_spread=half_spread,
            slippage_estimate=slippage_estimate,
            fee_edge=fee_edge,
            staleness_seconds=staleness,
            decay_factor=decay_factor,
            low_confidence=low_confidence,
        )

    def _slippage(self, *, candidate: CandidateMarket, size: Decimal) -> Decimal:
        depth = max(
            float(candidate.book_depth_bid_5tick + candidate.book_depth_ask_5tick),
            1e-9,
        )
        spread = max(float(candidate.spread), 0.0)
        size_value = max(float(size), 0.0)
        slippage = (size_value / (depth + size_value)) * (spread / 2.0)
        return Decimal(str(slippage))

    def _fee_edge(self, *, candidate: CandidateMarket, size: Decimal) -> Decimal:
        if not candidate.fees_enabled:
            return Decimal("0")
        fee_rate_bps = candidate.fee_rate_bps or Decimal("0")
        fee_edge = (float(fee_rate_bps) / 10000.0) * max(float(size), 0.0)
        return Decimal(str(fee_edge))

