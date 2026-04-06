from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Sequence

import numpy as np
from scipy.cluster.hierarchy import linkage, leaves_list


def _cov_to_corr(cov: np.ndarray) -> np.ndarray:
    cov = np.asarray(cov, dtype=float)
    std = np.sqrt(np.clip(np.diag(cov), 1e-12, None))
    outer = np.outer(std, std)
    return cov / np.clip(outer, 1e-12, None)


def _quasi_diag(cov: np.ndarray) -> List[int]:
    corr = _cov_to_corr(cov)
    dist = np.sqrt(0.5 * (1.0 - np.clip(corr, -1.0, 1.0)))
    # Condensed distance matrix for linkage
    triu = dist[np.triu_indices(dist.shape[0], k=1)]
    Z = linkage(triu, method="single")
    return list(leaves_list(Z))


def _cluster_var(cov: np.ndarray, indices: Sequence[int]) -> float:
    sub = cov[np.ix_(indices, indices)]
    # Inverse-variance allocation within cluster to estimate cluster variance
    ivp = 1.0 / np.clip(np.diag(sub), 1e-12, None)
    w = ivp / ivp.sum()
    return float(w @ sub @ w)


def hrp_weights(cov: List[List[float]], strategies: List[str]) -> Dict[str, Decimal]:
    """
    Hierarchical Risk Parity (Lopez de Prado).

    Deterministic for fixed inputs; tie behavior is governed by scipy linkage.
    """
    C = np.asarray(cov, dtype=float)
    n = C.shape[0]
    if n == 0:
        return {}
    if n != len(strategies):
        raise ValueError("cov dimension must match strategies length")
    if n == 1:
        return {strategies[0]: Decimal("1")}

    order = _quasi_diag(C)
    ordered = order

    weights = np.ones(n, dtype=float)
    clusters: List[List[int]] = [ordered]
    while clusters:
        cluster = clusters.pop(0)
        if len(cluster) <= 1:
            continue
        split = len(cluster) // 2
        left = cluster[:split]
        right = cluster[split:]

        var_left = _cluster_var(C, left)
        var_right = _cluster_var(C, right)
        if var_left <= 0 or var_right <= 0:
            alpha = 0.5
        else:
            alpha = 1.0 - (var_left / (var_left + var_right))

        weights[left] *= alpha
        weights[right] *= (1.0 - alpha)

        clusters.append(left)
        clusters.append(right)

    # Map to strategies and normalize
    out: Dict[str, Decimal] = {strategies[i]: Decimal(str(weights[i])) for i in range(n)}
    total = sum(out.values(), Decimal("0"))
    if total > Decimal("0"):
        out = {k: v / total for k, v in out.items()}
    return out

