from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from services.allocation.engine import AllocationEngine
from services.allocation.schemas import CapitalBudgetModel, PerformanceMatrix
from services.regime.schemas import RegimeQualityReport, RegimeState


def _regime_state(label: str) -> RegimeState:
    q = RegimeQualityReport(
        computed_at=datetime.now(timezone.utc),
        posterior_entropy=0.0,
        switch_rate_per_hour=0.0,
        expected_duration_minutes=60.0,
        agreement_with_threshold=1.0,
        quality_score=1.0,
    )
    return RegimeState(
        detected_at=datetime.now(timezone.utc),
        market_id=None,
        primary_regime=label,  # type: ignore[arg-type]
        regime_probabilities={"R1": 1.0, "R2": 0.0, "R3": 0.0, "R4": 0.0, "R5": 0.0},
        quality=q,
        source="threshold",
    )


def test_allocation_engine_constraints_hold_over_multiple_ticks():
    matrix = PerformanceMatrix(
        computed_at=datetime.now(timezone.utc),
        strategies=["s1", "s2"],
        regimes=["R1", "R2", "R3", "R4", "R5"],
        mu={"s1": {"R1": Decimal("1")}, "s2": {"R1": Decimal("0.5")}},
        sigma={"s1": {"R1": Decimal("1")}, "s2": {"R1": Decimal("2")}},
        drawdown={"s1": {"R1": Decimal("0")}, "s2": {"R1": Decimal("0")}},
        cost={"s1": {"R1": Decimal("0")}, "s2": {"R1": Decimal("0")}},
        covariance={"R1": [[1.0, 0.0], [0.0, 4.0]]},
    )

    engine = AllocationEngine(
        capital_budget=CapitalBudgetModel(
            total_equity=Decimal("100000"),
            market_budgets={"PREDICTION": Decimal("0.02")},
            max_single_position_pct=Decimal("0.05"),
        ),
        mm_strategy_ids=["s1"],
    )

    for _ in range(10):
        decision = engine.decide(regime=_regime_state("R1"), matrix=matrix)
        total = sum(decision.weights.values(), Decimal("0"))
        assert total <= Decimal("1") + Decimal("1e-9")
        assert all(w <= Decimal("0.40") + Decimal("1e-9") for w in decision.weights.values())
