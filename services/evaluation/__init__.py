"""Caliper evaluation engine — per-strategy metrics, regime breakdown, baselines (Sprint 13)"""

from services.evaluation.metrics import compute_metrics
from services.evaluation.regime_matrix import compute_regime_metrics
from services.evaluation.report import build_report
from services.evaluation.schemas import (
    EvaluationReport,
    RegimeMetrics,
    StrategyMetrics,
    StrategyRanking,
)

__all__ = [
    "StrategyMetrics",
    "RegimeMetrics",
    "EvaluationReport",
    "StrategyRanking",
    "compute_metrics",
    "compute_regime_metrics",
    "build_report",
]
