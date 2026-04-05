from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, List

from services.evaluation.metrics import compute_metrics
from services.evaluation.schemas import RegimeMetrics
from services.simulation.schemas import SimFill

# Regime dimensions and their FeatureSnapshot attribute names
REGIME_DIMENSIONS = [
    "vol_regime",
    "toxicity_regime",
    "near_close_flag",
    "time_bucket",
    "spread_regime",
]


def compute_regime_metrics(
    strategy_id: str,
    pnl_series: List[Decimal],
    fills: List[SimFill],
    snapshots: List[Any],  # List[FeatureSnapshot] — avoid hard import cycle
    period_start: datetime,
    period_end: datetime,
) -> List[RegimeMetrics]:
    """
    Compute StrategyMetrics conditioned on each regime label.
    snapshots must be aligned with pnl_series (one per hour).
    """
    result: List[RegimeMetrics] = []

    for dim in REGIME_DIMENSIONS:
        # Collect unique label values
        label_map: dict[str, list[int]] = {}
        for i, snap in enumerate(snapshots[:len(pnl_series)]):
            if snap is None:
                continue
            val = getattr(snap, dim, None)
            if val is None:
                continue
            label = f"{dim}={val}"
            label_map.setdefault(label, []).append(i)

        for label, indices in label_map.items():
            subset_pnl = [pnl_series[i] for i in indices]
            subset_fills: List[SimFill] = []  # fills not easily aligned to hours; pass empty
            if not subset_pnl:
                continue
            metrics = compute_metrics(
                strategy_id=strategy_id,
                pnl_series=subset_pnl,
                fills=subset_fills,
                period_start=period_start,
                period_end=period_end,
            )
            result.append(RegimeMetrics(
                strategy_id=strategy_id,
                regime=label,
                metrics=metrics,
                sample_hours=len(indices),
            ))

    return result
