from __future__ import annotations

from decimal import Decimal
from typing import Dict, List

import numpy as np


def bounded_kelly_weights(
    mu: List[float],
    cov: List[List[float]],
    strategies: List[str],
    *,
    max_weight: float = 0.40,
    total_weight_cap: float = 1.0,
) -> Dict[str, Decimal]:
    """
    Bounded Kelly weights (risk-aware, long-only).

    Uses w ∝ inv(C) * mu, then clamps to [0, max_weight] and scales to <= total_weight_cap.
    """
    if len(mu) != len(strategies):
        raise ValueError("mu length must match strategies")
    C = np.asarray(cov, dtype=float)
    if C.shape[0] != C.shape[1] or C.shape[0] != len(strategies):
        raise ValueError("cov dimension must match strategies length")

    mu_vec = np.asarray(mu, dtype=float)
    inv = np.linalg.pinv(C)
    raw = inv @ mu_vec
    raw = np.maximum(raw, 0.0)
    raw = np.minimum(raw, float(max_weight))

    s = float(raw.sum())
    if s <= 0:
        return {sid: Decimal("0") for sid in strategies}

    scaled = raw / s * float(total_weight_cap)
    # Re-apply cap after scaling (rare edge) and renormalize.
    scaled = np.minimum(scaled, float(max_weight))
    s2 = float(scaled.sum())
    if s2 > float(total_weight_cap) and s2 > 0:
        scaled = scaled / s2 * float(total_weight_cap)

    return {strategies[i]: Decimal(str(float(scaled[i]))) for i in range(len(strategies))}

