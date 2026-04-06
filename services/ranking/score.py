from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class RankingWeights:
    """Composite score weights from the sprint spec."""

    ev: float = 0.40
    risk: float = 0.30
    liquidity: float = 0.20
    confidence: float = 0.10


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def composite_score(
    *,
    ev_adj: Decimal | float,
    sigma: Decimal | float,
    feasibility: float,
    confidence: float,
    weights: RankingWeights | None = None,
) -> float:
    """Compute the cross-sectional ranking score."""

    weight = weights or RankingWeights()
    ev = float(ev_adj)
    if ev < 0.0:
        return 0.0

    sigma_value = max(float(sigma), 1e-9)
    feasibility_value = _clamp(float(feasibility))
    confidence_value = _clamp(float(confidence))

    return (
        weight.ev * ev
        + weight.risk * (ev / sigma_value)
        + weight.liquidity * feasibility_value
        + weight.confidence * confidence_value
    )

