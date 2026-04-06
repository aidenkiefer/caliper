from __future__ import annotations

from decimal import Decimal
from typing import Dict


def risk_parity_weights(
    sigma_by_strategy: Dict[str, Decimal],
    *,
    total_weight_cap: Decimal = Decimal("1"),
) -> Dict[str, Decimal]:
    """
    Risk parity baseline: weights proportional to 1/sigma.

    Weights are normalized to sum to <= total_weight_cap.
    """
    inv: Dict[str, Decimal] = {}
    for s, sig in sigma_by_strategy.items():
        if sig is None or sig <= Decimal("0"):
            continue
        inv[s] = Decimal("1") / sig

    if not inv:
        return {s: Decimal("0") for s in sigma_by_strategy}

    total = sum(inv.values(), Decimal("0"))
    if total <= Decimal("0"):
        return {s: Decimal("0") for s in sigma_by_strategy}

    weights: Dict[str, Decimal] = {s: (inv.get(s, Decimal("0")) / total) * total_weight_cap for s in sigma_by_strategy}
    # Ensure numerical safety
    for s in list(weights.keys()):
        if weights[s] < Decimal("0"):
            weights[s] = Decimal("0")
    return weights

