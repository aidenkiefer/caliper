from __future__ import annotations

import math
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

import numpy as np

from services.regime.schemas import RegimeState


def clamp_decimal(x: Decimal, lo: Decimal, hi: Decimal) -> Decimal:
    return max(lo, min(hi, x))


def entropy_alpha(entropy: float, *, k: int = 4) -> float:
    """
    Convert posterior entropy into blending coefficient alpha in [0,1].

    alpha = clamp(1 - entropy/log(k), 0, 1)
    """
    denom = math.log(max(k, 2))
    if denom <= 0:
        return 0.0
    a = 1.0 - float(entropy) / denom
    return float(max(0.0, min(a, 1.0)))


def apply_turnover_smoothing(
    new_weights: Dict[str, Decimal],
    prev_weights: Optional[Dict[str, Decimal]],
    *,
    beta: Decimal = Decimal("0.50"),
) -> Dict[str, Decimal]:
    if prev_weights is None:
        return dict(new_weights)
    beta = clamp_decimal(beta, Decimal("0"), Decimal("1"))
    out: Dict[str, Decimal] = {}
    keys = set(new_weights) | set(prev_weights)
    for k in keys:
        nw = new_weights.get(k, Decimal("0"))
        pw = prev_weights.get(k, Decimal("0"))
        out[k] = (Decimal("1") - beta) * pw + beta * nw
    return out


def apply_vol_target(
    weights: Dict[str, Decimal],
    *,
    portfolio_vol_annualized: Optional[float],
    target_vol: float = 0.10,
) -> Dict[str, Decimal]:
    if portfolio_vol_annualized is None or portfolio_vol_annualized <= 0:
        return dict(weights)
    if portfolio_vol_annualized <= target_vol:
        return dict(weights)
    scale = target_vol / portfolio_vol_annualized
    return {k: v * Decimal(str(scale)) for k, v in weights.items()}


def enforce_hard_constraints(
    weights: Dict[str, Decimal],
    *,
    regime: RegimeState,
    mm_strategy_ids: Optional[List[str]] = None,
    portfolio_drawdown: Optional[Decimal] = None,
    strategy_drawdown: Optional[Dict[str, Decimal]] = None,
    prev_weights: Optional[Dict[str, Decimal]] = None,
    max_single_weight: Decimal = Decimal("0.40"),
    max_weight_increase_per_cycle: Decimal = Decimal("0.10"),
) -> Tuple[Dict[str, Decimal], List[str]]:
    """
    Apply Sprint 15 hard constraints (AC-7).
    """
    applied: List[str] = []

    # Kill switch: portfolio drawdown >= 0.15 -> all 0
    if portfolio_drawdown is not None and portfolio_drawdown >= Decimal("0.15"):
        applied.append("kill_switch_drawdown_0.15")
        return ({k: Decimal("0") for k in weights}, applied)

    # Regime R4 override: all 0
    if regime.primary_regime == "R4":
        applied.append("regime_R4_override")
        return ({k: Decimal("0") for k in weights}, applied)

    out = dict(weights)

    # Regime R3 override: MM strategies -> 0
    if regime.primary_regime == "R3" and mm_strategy_ids:
        for sid in mm_strategy_ids:
            if sid in out and out[sid] != Decimal("0"):
                out[sid] = Decimal("0")
        applied.append("regime_R3_mm_zero")

    # Strategy drawdown >= 0.20 -> 0
    if strategy_drawdown:
        for sid, dd in strategy_drawdown.items():
            if dd is not None and dd >= Decimal("0.20"):
                if sid in out and out[sid] != Decimal("0"):
                    out[sid] = Decimal("0")
        applied.append("strategy_drawdown_0.20")

    # Per-strategy cap 0.40
    for sid in list(out.keys()):
        if out[sid] > max_single_weight:
            out[sid] = max_single_weight
            applied.append("max_single_weight_0.40")

    # Capital velocity cap: weight increase per cycle <= 0.10
    if prev_weights is not None:
        for sid in list(out.keys()):
            prev = prev_weights.get(sid, Decimal("0"))
            if out[sid] - prev > max_weight_increase_per_cycle:
                out[sid] = prev + max_weight_increase_per_cycle
                applied.append("capital_velocity_0.10")

    # Ensure weights sum <= 1
    total = sum(out.values(), Decimal("0"))
    if total > Decimal("1") and total > Decimal("0"):
        scale = Decimal("1") / total
        out = {k: v * scale for k, v in out.items()}
        applied.append("renormalize_sum_leq_1")

    return out, applied


# ---------------------------------------------------------------------------
# Compatibility wrappers (used by AllocationEngine)
# ---------------------------------------------------------------------------


def alpha_from_entropy(entropy: float, *, n_states: int = 4) -> float:
    """Compatibility wrapper for AllocationEngine: entropy -> alpha in [0,1]."""
    return entropy_alpha(entropy, k=n_states)


def apply_hard_constraints(
    *,
    weights: Dict[str, Decimal],
    regime: RegimeState,
    mm_strategy_ids,
    portfolio_drawdown: Decimal = Decimal("0"),
    strategy_drawdowns: Optional[Dict[str, Decimal]] = None,
    prev_weights: Optional[Dict[str, Decimal]] = None,
) -> Tuple[Dict[str, Decimal], List[str]]:
    return enforce_hard_constraints(
        weights,
        regime=regime,
        mm_strategy_ids=list(mm_strategy_ids) if mm_strategy_ids is not None else None,
        portfolio_drawdown=portfolio_drawdown,
        strategy_drawdown=strategy_drawdowns,
        prev_weights=prev_weights,
    )


def apply_soft_constraints(
    *,
    weights: Dict[str, Decimal],
    prev_weights: Optional[Dict[str, Decimal]] = None,
    covariance: Optional[List[List[float]]] = None,
) -> Dict[str, Decimal]:
    # Turnover smoothing first.
    out = apply_turnover_smoothing(weights, prev_weights, beta=Decimal("0.50"))

    # Vol targeting using covariance if provided.
    portfolio_vol_annualized: Optional[float] = None
    if covariance is not None and out:
        try:
            keys = sorted(out.keys())
            w = np.asarray([float(out[k]) for k in keys], dtype=float)
            cov = np.asarray(covariance, dtype=float)
            if cov.shape == (len(keys), len(keys)):
                var = float(w.T @ cov @ w)
                vol_daily = math.sqrt(max(var, 0.0))
                portfolio_vol_annualized = vol_daily * math.sqrt(365.0)
        except Exception:
            portfolio_vol_annualized = None

    out = apply_vol_target(out, portfolio_vol_annualized=portfolio_vol_annualized, target_vol=0.10)

    # Ensure sum <= 1.
    total = sum(out.values(), Decimal("0"))
    if total > Decimal("1") and total > Decimal("0"):
        scale = Decimal("1") / total
        out = {k: v * scale for k, v in out.items()}
    return out
