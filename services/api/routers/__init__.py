"""
API routers package.

Each router handles a specific resource/domain.
"""

from . import (
    alerts,
    health,
    metrics,
    strategies,
    runs,
    positions,
    orders,
    controls,
    drift,
    explanations,
    baselines,
    recommendations,
    models,
    paper,
    polymarket,
    features,
    simulation,
    probability,
    regime,
    ranking,
    fleet,
)

__all__ = [
    "alerts",
    "health",
    "metrics",
    "strategies",
    "runs",
    "positions",
    "orders",
    "controls",
    "drift",
    "explanations",
    "baselines",
    "recommendations",
    "models",
    "paper",
    "polymarket",
    "features",
    "simulation",
    "probability",
    "regime",
    "ranking",
    "fleet",
]
