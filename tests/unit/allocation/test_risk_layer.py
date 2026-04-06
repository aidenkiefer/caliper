from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from services.allocation.risk_layer import apply_hard_constraints, alpha_from_entropy
from services.regime.schemas import RegimeQualityReport, RegimeState


def _regime(primary: str, entropy: float = 0.0) -> RegimeState:
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


def test_alpha_uniform_posterior_is_zeroish() -> None:
    # entropy = log(4) => alpha ~ 0
    import math

    a = alpha_from_entropy(math.log(4), n_states=4)
    assert a <= 1e-9


def test_hard_constraints_r4_zeroes_all() -> None:
    weights = {"a": Decimal("0.2"), "b": Decimal("0.2")}
    out, applied = apply_hard_constraints(
        weights=weights,
        regime=_regime("R4"),
        mm_strategy_ids=[],
        portfolio_drawdown=Decimal("0"),
        strategy_drawdowns=None,
        prev_weights=None,
    )
    assert out == {"a": Decimal("0"), "b": Decimal("0")}
    assert "regime_R4_override" in applied


def test_hard_constraints_portfolio_kill_switch() -> None:
    weights = {"a": Decimal("0.2")}
    out, applied = apply_hard_constraints(
        weights=weights,
        regime=_regime("R1"),
        mm_strategy_ids=[],
        portfolio_drawdown=Decimal("0.15"),
        strategy_drawdowns=None,
        prev_weights=None,
    )
    assert out["a"] == Decimal("0")
    assert "kill_switch_drawdown_0.15" in applied


def test_hard_constraints_r3_zeros_mm_strategies() -> None:
    weights = {"mm1": Decimal("0.2"), "dir1": Decimal("0.2")}
    out, applied = apply_hard_constraints(
        weights=weights,
        regime=_regime("R3"),
        mm_strategy_ids=["mm1"],
        portfolio_drawdown=Decimal("0"),
        strategy_drawdowns=None,
        prev_weights=None,
    )
    assert out["mm1"] == Decimal("0")
    assert out["dir1"] == Decimal("0.2")
    assert "regime_R3_mm_zero" in applied

