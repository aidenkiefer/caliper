from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Tuple

from services.evaluation.metrics import compute_metrics
from services.evaluation.regime_matrix import compute_regime_metrics
from services.evaluation.schemas import EvaluationReport, RegimeMetrics, StrategyMetrics, StrategyRanking
from services.simulation.schemas import SimFill


def build_report(
    strategy_results: Dict[str, Tuple[List[Decimal], List[SimFill]]],
    snapshots: Dict[str, List[Any]],
    period_start: datetime,
    period_end: datetime,
) -> EvaluationReport:
    """Build a full EvaluationReport for multiple strategies."""
    per_strategy: Dict[str, StrategyMetrics] = {}
    regime_breakdown: Dict[str, List[RegimeMetrics]] = {}

    for strat_id, (pnl_series, fills) in strategy_results.items():
        metrics = compute_metrics(
            strategy_id=strat_id,
            pnl_series=pnl_series,
            fills=fills,
            period_start=period_start,
            period_end=period_end,
        )
        per_strategy[strat_id] = metrics

        strat_snapshots = snapshots.get(strat_id, [])
        regime_metrics = compute_regime_metrics(
            strategy_id=strat_id,
            pnl_series=pnl_series,
            fills=fills,
            snapshots=strat_snapshots,
            period_start=period_start,
            period_end=period_end,
        )
        regime_breakdown[strat_id] = regime_metrics

    # Rank by composite score: 0.4*sharpe + 0.3*win_rate + 0.2*consistency + 0.1*profit_factor
    def _normalize(vals: List[Decimal]) -> List[Decimal]:
        if not vals:
            return vals
        mn, mx = min(vals), max(vals)
        if mx == mn:
            return [Decimal("0.5")] * len(vals)
        return [(v - mn) / (mx - mn) for v in vals]

    strat_ids = list(per_strategy.keys())
    sharpes = _normalize([per_strategy[s].sharpe_ratio for s in strat_ids])
    win_rates = _normalize([per_strategy[s].win_rate for s in strat_ids])
    consistencies = _normalize([per_strategy[s].consistency_score for s in strat_ids])
    pfs = _normalize([per_strategy[s].profit_factor for s in strat_ids])

    scores = [
        Decimal("0.4") * sharpes[i]
        + Decimal("0.3") * win_rates[i]
        + Decimal("0.2") * consistencies[i]
        + Decimal("0.1") * pfs[i]
        for i in range(len(strat_ids))
    ]
    ranked = sorted(zip(strat_ids, scores), key=lambda x: x[1], reverse=True)
    rankings = [StrategyRanking(strategy_id=s, rank=i + 1, composite_score=sc) for i, (s, sc) in enumerate(ranked)]

    return EvaluationReport(
        report_id=uuid.uuid4(),
        generated_at=datetime.now(tz=timezone.utc),
        strategy_ids=strat_ids,
        period_start=period_start,
        period_end=period_end,
        per_strategy=per_strategy,
        regime_breakdown=regime_breakdown,
        rankings=rankings,
        baseline_comparison={},
    )
