# services/reward_density/risk_scorer.py
from __future__ import annotations

from decimal import Decimal
from typing import Dict, List


class RiskScorer:
    """Computes cross-sectional risk scores using z-scored vol + toxicity."""

    def __init__(self, lambda_toxicity: Decimal = Decimal("0.5")) -> None:
        self.lambda_toxicity = lambda_toxicity

    @staticmethod
    def _zscore(values: List[Decimal]) -> List[Decimal]:
        if len(values) <= 1:
            return [Decimal("0")] * len(values)
        mean = sum(values) / Decimal(str(len(values)))
        variance = sum((v - mean) ** 2 for v in values) / Decimal(str(len(values)))
        std = variance.sqrt() if variance > Decimal("0") else Decimal("1")
        return [(v - mean) / std for v in values]

    def compute_cross_sectional(
        self,
        items: List[Dict],
    ) -> Dict[str, Decimal]:
        """
        items: list of dicts with keys 'market_id', 'btc_rv', 'toxicity'.
        Returns {market_id: risk_score}.
        """
        if not items:
            return {}

        vols = [item["btc_rv"] for item in items]
        toxicities = [item["toxicity"] for item in items]

        z_vol = self._zscore(vols)
        z_tox = self._zscore(toxicities)

        result: Dict[str, Decimal] = {}
        for item, zv, zt in zip(items, z_vol, z_tox):
            score = zv + self.lambda_toxicity * zt
            result[item["market_id"]] = score
        return result
