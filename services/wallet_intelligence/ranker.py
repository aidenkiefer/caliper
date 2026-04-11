# services/wallet_intelligence/ranker.py
from __future__ import annotations

from decimal import Decimal
from typing import List


class WalletRanker:
    """Ranks wallets by risk-adjusted PnL consistency."""

    def compute_wallet_score(
        self,
        daily_pnls_7d: List[Decimal],
        active_days_7d: int,
    ) -> Decimal:
        """WalletScore = PnL_7d / max(StdDev, ε) * sqrt(active_days)."""
        if not daily_pnls_7d:
            return Decimal("0")

        pnl_7d = sum(daily_pnls_7d)
        n = Decimal(str(len(daily_pnls_7d)))
        mean = pnl_7d / n
        variance = sum((p - mean) ** 2 for p in daily_pnls_7d) / n
        std = variance.sqrt() if variance > Decimal("0") else Decimal("0.0001")
        eps = Decimal("0.0001")
        active = Decimal(str(max(active_days_7d, 1)))

        return (pnl_7d / max(std, eps)) * active.sqrt()
