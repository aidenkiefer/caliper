from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class StrategyMetrics(BaseModel):
    strategy_id: str
    period_start: datetime
    period_end: datetime
    total_pnl: Decimal
    pnl_components: Dict[str, Decimal]
    sharpe_ratio: Decimal
    sortino_ratio: Decimal
    calmar_ratio: Decimal
    win_rate: Decimal
    profit_factor: Decimal
    max_drawdown: Decimal
    max_drawdown_duration_hours: int
    consistency_score: Decimal
    stability_score: Decimal
    total_volume_usd: Decimal
    fill_rate: Decimal
    maker_fill_rate: Decimal
    regret_vs_hold_cash: Decimal
    regret_vs_buy_and_hold: Decimal
    regret_vs_random: Decimal
    sharpe_confidence: Literal["low", "medium", "high"] = "high"
    data_points: int = 0


class RegimeMetrics(BaseModel):
    strategy_id: str
    regime: str
    metrics: StrategyMetrics
    sample_hours: int


class StrategyRanking(BaseModel):
    strategy_id: str
    rank: int
    composite_score: Decimal


class EvaluationReport(BaseModel):
    report_id: UUID
    generated_at: datetime
    strategy_ids: List[str]
    period_start: datetime
    period_end: datetime
    per_strategy: Dict[str, StrategyMetrics]
    regime_breakdown: Dict[str, List[RegimeMetrics]]
    rankings: List[StrategyRanking]
    baseline_comparison: Dict[str, Decimal]
