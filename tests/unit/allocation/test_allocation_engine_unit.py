from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from services.allocation.engine import AllocationEngine
from services.allocation.schemas import CapitalBudgetModel, PerformanceMatrix
from services.regime.schemas import RegimeQualityReport, RegimeState


def _regime(primary: str, entropy: float) -> RegimeState:
    ts = datetime.now(timezone.utc)
    return RegimeState(
        detected_at=ts,
        market_id=None,
        primary_regime=primary,  # type: ignore[arg-type]
        regime_probabilities={"R1": 1.0, "R2": 0.0, "R3": 0.0, "R4": 0.0, "R5": 0.0},
        quality=RegimeQualityReport(
            computed_at=ts,
            posterior_entropy=entropy,
            switch_rate_per_hour=0.0,
            expected_duration_minutes=0.0,
            agreement_with_threshold=1.0,
            quality_score=1.0,
        ),
        source="threshold",
    )


def test_allocation_engine_enforces_constraints_over_ticks() -> None:
    budget = CapitalBudgetModel(total_equity=Decimal("100000"), market_budgets={"PREDICTION": Decimal("0.02")})
    engine = AllocationEngine(capital_budget=budget, mm_strategy_ids=["mm1"])

    matrix = PerformanceMatrix(
        computed_at=datetime.now(timezone.utc),
        strategies=["mm1", "dir1"],
        regimes=["R1", "R2", "R3", "R4", "R5"],
        mu={"mm1": {"R1": Decimal("0")}, "dir1": {"R1": Decimal("0")}},
        sigma={"mm1": {"R1": Decimal("1")}, "dir1": {"R1": Decimal("2")}},
        drawdown={"mm1": {"R1": Decimal("0")}, "dir1": {"R1": Decimal("0")}},
        cost={"mm1": {"R1": Decimal("0")}, "dir1": {"R1": Decimal("0")}},
        covariance={"R1": [[1.0, 0.0], [0.0, 4.0]]},
    )

    # Tick 1: normal regime
    d1 = engine.decide(regime=_regime("R1", entropy=0.0), matrix=matrix)
    assert sum(d1.weights.values(), Decimal("0")) <= Decimal("1")

    # Tick 2: R3 should force MM to 0
    d2 = engine.decide(regime=_regime("R3", entropy=0.0), matrix=matrix)
    assert d2.weights["mm1"] == Decimal("0")

    # Tick 3: R4 forces all 0
    d3 = engine.decide(regime=_regime("R4", entropy=0.0), matrix=matrix)
    assert all(v == Decimal("0") for v in d3.weights.values())

