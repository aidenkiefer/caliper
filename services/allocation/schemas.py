from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Literal

from pydantic import BaseModel, Field

from services.regime.schemas import RegimeState


class CapitalBudgetModel(BaseModel):
    """Pydantic-friendly representation of services.portfolio.allocator.CapitalBudget."""

    total_equity: Decimal
    market_budgets: Dict[str, Decimal]
    max_single_position_pct: Decimal = Decimal("0.05")


class PerformanceMatrix(BaseModel):
    computed_at: datetime
    strategies: List[str]
    regimes: List[str]
    mu: Dict[str, Dict[str, Decimal]]
    sigma: Dict[str, Dict[str, Decimal]]
    drawdown: Dict[str, Dict[str, Decimal]]
    cost: Dict[str, Dict[str, Decimal]]
    covariance: Dict[str, List[List[float]]]


AllocationMethod = Literal["risk_parity", "hrp", "kelly", "blended"]


class AllocationDecision(BaseModel):
    decided_at: datetime
    regime: RegimeState
    weights: Dict[str, Decimal]
    method_used: AllocationMethod
    confidence: float = Field(..., ge=0, le=1)
    hard_constraints_applied: List[str]
    capital_budget: CapitalBudgetModel

