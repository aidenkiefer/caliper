from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np

from services.allocation.schemas import PerformanceMatrix
from services.evaluation.schemas import EvaluationReport, RegimeMetrics

logger = logging.getLogger(__name__)


_HALF_LIFE_DAYS = 7.0
_LAMBDA_PER_HOUR = math.log(2.0) / (_HALF_LIFE_DAYS * 24.0)


def _decay_weight(delta_hours: float) -> float:
    return float(math.exp(-_LAMBDA_PER_HOUR * max(delta_hours, 0.0)))


def ledoit_wolf_covariance(samples: np.ndarray) -> np.ndarray:
    """
    Compute a Ledoit-Wolf shrunk covariance estimate.

    samples: shape (n_samples, n_features)
    """
    from sklearn.covariance import LedoitWolf

    X = np.asarray(samples, dtype=float)
    if X.ndim != 2:
        raise ValueError("samples must be 2D")
    if X.shape[0] < 2:
        return np.eye(X.shape[1], dtype=float)
    return LedoitWolf().fit(X).covariance_


def discounted_mean(
    returns: np.ndarray,
    *,
    hours_ago: np.ndarray,
) -> float:
    """
    Exponentially-discounted mean with half-life of 7 days.

    Parameters
    ----------
    returns:
        Shape (n_samples,)
    hours_ago:
        Shape (n_samples,) with non-negative hours back from "now".
    """
    r = np.asarray(returns, dtype=float)
    h = np.asarray(hours_ago, dtype=float)
    if r.shape != h.shape or r.ndim != 1:
        raise ValueError("returns and hours_ago must be 1D arrays of the same shape")
    w = np.exp(-_LAMBDA_PER_HOUR * np.maximum(h, 0.0))
    s = float(w.sum())
    if s <= 0:
        return 0.0
    return float((w * r).sum() / s)


def discounted_mu_sigma(
    samples: np.ndarray,
    *,
    hours_ago: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute discounted mean and (non-discounted) std per column.

    Discount is applied only to mu; sigma is a simple sample std for now.
    """
    X = np.asarray(samples, dtype=float)
    if X.ndim != 2:
        raise ValueError("samples must be 2D")
    mu = np.asarray([discounted_mean(X[:, i], hours_ago=hours_ago) for i in range(X.shape[1])], dtype=float)
    sigma = np.std(X, axis=0, ddof=1) if X.shape[0] >= 2 else np.ones(X.shape[1], dtype=float)
    sigma = np.maximum(sigma, 1e-12)
    return mu, sigma


def _extract_primary_regime_metrics(
    regime_breakdown: List[RegimeMetrics],
) -> Dict[str, RegimeMetrics]:
    """
    Return mapping {\"R1\": RegimeMetrics, ...} from a strategy's regime_breakdown list.

    Expects labels of the form \"primary_regime=Rk\" produced by Sprint 15 evaluation slicing.
    """
    out: Dict[str, RegimeMetrics] = {}
    for rm in regime_breakdown:
        if not isinstance(rm.regime, str):
            continue
        if not rm.regime.startswith("primary_regime="):
            continue
        _, val = rm.regime.split("=", 1)
        out[val] = rm
    return out


@dataclass(frozen=True)
class PerformanceMatrixBuilder:
    """
    Build a regime-conditioned PerformanceMatrix from EvaluationReports.

    Note: pm.evaluation_reports currently stores aggregated metrics; this builder
    uses per-report regime slices as proxies for expected return and volatility.
    """

    regimes: Tuple[str, ...] = ("R1", "R2", "R3", "R4", "R5")

    def build(self, reports: List[EvaluationReport]) -> PerformanceMatrix:
        if not reports:
            return PerformanceMatrix(
                computed_at=datetime.now(timezone.utc),
                strategies=[],
                regimes=list(self.regimes),
                mu={},
                sigma={},
                drawdown={},
                cost={},
                covariance={},
            )

        # Most recent report defines the strategy universe.
        reports_sorted = sorted(reports, key=lambda r: r.generated_at)
        latest = reports_sorted[-1]
        strategies = list(latest.strategy_ids)
        regimes = list(self.regimes)

        mu: Dict[str, Dict[str, Decimal]] = {s: {r: Decimal("0") for r in regimes} for s in strategies}
        sigma: Dict[str, Dict[str, Decimal]] = {s: {r: Decimal("1") for r in regimes} for s in strategies}
        drawdown: Dict[str, Dict[str, Decimal]] = {s: {r: Decimal("0") for r in regimes} for s in strategies}
        cost: Dict[str, Dict[str, Decimal]] = {s: {r: Decimal("0") for r in regimes} for s in strategies}

        # Discounted aggregates across reports.
        now = datetime.now(timezone.utc)
        weight_sum: Dict[Tuple[str, str], float] = {(s, r): 0.0 for s in strategies for r in regimes}
        mu_sum: Dict[Tuple[str, str], float] = {(s, r): 0.0 for s in strategies for r in regimes}
        dd_max: Dict[Tuple[str, str], Decimal] = {(s, r): Decimal("0") for s in strategies for r in regimes}

        for rep in reports_sorted:
            delta_hours = (now - rep.generated_at).total_seconds() / 3600.0
            w = _decay_weight(delta_hours)
            for s in strategies:
                breakdown = rep.regime_breakdown.get(s, [])
                by_regime = _extract_primary_regime_metrics(breakdown)
                for r in regimes:
                    rm = by_regime.get(r)
                    if rm is None or rm.sample_hours <= 0:
                        continue
                    # Use per-hour pnl as expected return proxy.
                    mu_hour = float(rm.metrics.total_pnl) / float(max(rm.sample_hours, 1))
                    key = (s, r)
                    mu_sum[key] += w * mu_hour
                    weight_sum[key] += w
                    if rm.metrics.max_drawdown > dd_max[key]:
                        dd_max[key] = rm.metrics.max_drawdown

        for s in strategies:
            for r in regimes:
                key = (s, r)
                if weight_sum[key] > 0:
                    mu_hour = mu_sum[key] / weight_sum[key]
                    mu[s][r] = Decimal(str(mu_hour))
                drawdown[s][r] = dd_max[key]
                # Simple volatility proxy: drawdown per hour + |mu|
                dd_per_hour = float(dd_max[key]) / 24.0 if dd_max[key] > 0 else 0.0
                sig = max(abs(float(mu[s][r])) + dd_per_hour, 1e-9)
                sigma[s][r] = Decimal(str(sig))

        # Covariance: default to diagonal matrices by regime (can be upgraded later).
        covariance: Dict[str, List[List[float]]] = {}
        for r in regimes:
            sigs = np.asarray([float(sigma[s][r]) for s in strategies], dtype=float)
            cov = np.diag(sigs ** 2)
            covariance[r] = cov.tolist()

        return PerformanceMatrix(
            computed_at=now,
            strategies=strategies,
            regimes=regimes,
            mu=mu,
            sigma=sigma,
            drawdown=drawdown,
            cost=cost,
            covariance=covariance,
        )


async def load_latest_evaluation_reports(db_url: str, limit: int = 30) -> List[EvaluationReport]:
    """
    Load the latest EvaluationReport JSON blobs from pm.evaluation_reports.
    """
    import asyncpg

    sql = """
        SELECT report
        FROM pm.evaluation_reports
        ORDER BY generated_at DESC
        LIMIT $1
    """
    conn = await asyncpg.connect(db_url)
    try:
        rows = await conn.fetch(sql, limit)
    finally:
        await conn.close()

    out: List[EvaluationReport] = []
    for row in rows:
        try:
            payload = row["report"]
            # asyncpg may return dict for JSONB; accept both.
            if isinstance(payload, str):
                payload = json.loads(payload)
            out.append(EvaluationReport.model_validate(payload))
        except Exception as exc:
            logger.error("Failed to parse EvaluationReport row: %s", exc)
    return out
