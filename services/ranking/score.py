# services/ranking/score.py
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class RankingWeights:
    """Composite score weights. Sprint 17 adds w_density (w_D = 0.15),
    other weights scaled down proportionally from Sprint 16 values."""

    ev: float = 0.34
    risk: float = 0.255
    liquidity: float = 0.17
    confidence: float = 0.085
    density: float = 0.15


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def composite_score(
    *,
    ev_adj: Decimal | float,
    sigma: Decimal | float,
    feasibility: float,
    confidence: float,
    reward_density: float = 0.0,
    weights: RankingWeights | None = None,
) -> float:
    """Compute the cross-sectional ranking score (Sprint 17: adds density term)."""

    weight = weights or RankingWeights()
    ev = float(ev_adj)
    if ev < 0.0:
        return 0.0

    sigma_value = max(float(sigma), 1e-9)
    feasibility_value = _clamp(float(feasibility))
    confidence_value = _clamp(float(confidence))
    density_value = max(float(reward_density), 0.0)

    return (
        weight.ev * ev
        + weight.risk * (ev / sigma_value)
        + weight.liquidity * feasibility_value
        + weight.confidence * confidence_value
        + weight.density * density_value
    )
