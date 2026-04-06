from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, List

from services.evaluation.metrics import compute_metrics
from services.evaluation.schemas import RegimeMetrics
from services.simulation.schemas import SimFill

# Regime dimensions and their FeatureSnapshot attribute names (or derived labels)
REGIME_DIMENSIONS = [
    "vol_regime",
    "toxicity_regime",
    "near_close_flag",
    "time_bucket",
    "spread_regime",
    # Sprint 15: semantic regime label (derived from threshold logic).
    "primary_regime",
]


def _primary_regime_from_snapshot(
    snapshot: Any,
    *,
    api_latency_ms: float = 0.0,
    heartbeat_miss_count: int = 0,
) -> str:
    """Return Sprint 15 semantic regime label R1..R5 from a FeatureSnapshot-like object.

    This duplicates the deterministic threshold logic from Sprint 15's regime service
    without importing services/regime to avoid circular dependencies.

    For offline evaluation runs, connectivity metrics are assumed healthy defaults
    (api_latency_ms=0, heartbeat_miss_count=0) unless explicitly provided (either via
    parameters or fields on the snapshot).
    """

    # Connectivity: highest priority (R4)
    if api_latency_ms >= 2000.0 or heartbeat_miss_count >= 2:
        return "R4"

    # Dead market (R5)
    spread_bps = getattr(snapshot, "spread_bps", None)
    depth_bid = getattr(snapshot, "book_depth_bid_5tick", None)
    depth_ask = getattr(snapshot, "book_depth_ask_5tick", None)
    try:
        if spread_bps is not None and float(spread_bps) >= 500.0:
            return "R5"
    except Exception:
        # If spread_bps cannot be interpreted as a float, ignore and continue.
        pass
    try:
        if depth_bid is not None and depth_ask is not None:
            if min(float(depth_bid), float(depth_ask)) < 10.0:
                return "R5"
    except Exception:
        pass

    # Near-close toxic (R3)
    time_to_close_seconds = getattr(snapshot, "time_to_close_seconds", None)
    near_close_flag = getattr(snapshot, "near_close_flag", None)
    toxicity_regime = getattr(snapshot, "toxicity_regime", None)
    vpin_proxy = getattr(snapshot, "vpin_proxy", None)

    try:
        if bool(near_close_flag):
            return "R3"
    except Exception:
        pass
    if toxicity_regime == "high":
        return "R3"
    try:
        if time_to_close_seconds is not None and float(time_to_close_seconds) <= 600.0:
            return "R3"
    except Exception:
        pass
    try:
        if vpin_proxy is not None and float(vpin_proxy) >= 0.65:
            return "R3"
    except Exception:
        pass

    # Choppy (R2)
    btc_rv_5m = getattr(snapshot, "btc_rv_5m", None)
    btc_sign_persistence_5m = getattr(snapshot, "btc_sign_persistence_5m", None)
    try:
        if btc_rv_5m is not None and btc_sign_persistence_5m is not None:
            if float(btc_rv_5m) >= 0.002 and float(btc_sign_persistence_5m) < 0.6:
                return "R2"
    except Exception:
        pass

    # Favorable (R1): everything else
    return "R1"


def compute_regime_metrics(
    strategy_id: str,
    pnl_series: List[Decimal],
    fills: List[SimFill],
    snapshots: List[Any],  # List[FeatureSnapshot] - avoid hard import cycle
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
            if dim == "primary_regime":
                # Offline evaluation default: "healthy connectivity", unless metrics exist.
                api_latency_ms = 0.0
                heartbeat_miss_count = 0
                try:
                    api_latency_ms = float(getattr(snap, "api_latency_ms", 0.0) or 0.0)
                except Exception:
                    api_latency_ms = 0.0
                try:
                    heartbeat_miss_count = int(getattr(snap, "heartbeat_miss_count", 0) or 0)
                except Exception:
                    heartbeat_miss_count = 0

                val = _primary_regime_from_snapshot(
                    snap,
                    api_latency_ms=api_latency_ms,
                    heartbeat_miss_count=heartbeat_miss_count,
                )
            else:
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
