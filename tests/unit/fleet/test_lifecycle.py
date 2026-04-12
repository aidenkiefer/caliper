import pytest
from decimal import Decimal
from datetime import datetime, timezone

from services.fleet.lifecycle import (
    LifecycleAction,
    LifecycleManager,
    LifecycleRule,
    StrategyEvaluationSnapshot,
)


def _make_snapshot(
    strategy_id: str,
    sharpe_7d: float,
    drawdown_7d: float,
    active_days: int = 30,
    win_rate: float = 0.60,
    max_drawdown: float = 0.10,
    is_live: bool = False,
    paused_days: int = 0,
) -> StrategyEvaluationSnapshot:
    return StrategyEvaluationSnapshot(
        strategy_id=strategy_id,
        sharpe_7d=Decimal(str(sharpe_7d)),
        drawdown_7d=Decimal(str(drawdown_7d)),
        active_paper_days=active_days,
        win_rate=Decimal(str(win_rate)),
        max_drawdown=Decimal(str(max_drawdown)),
        is_live=is_live,
        paused_days=paused_days,
    )


def test_pause_rule_triggers_on_low_sharpe() -> None:
    """AC-8: PAUSE auto-triggers when Sharpe < -0.5."""
    manager = LifecycleManager()
    snapshot = _make_snapshot("strat1", sharpe_7d=-0.8, drawdown_7d=0.10)
    events = manager.evaluate([snapshot])
    pause_events = [e for e in events if e.action == LifecycleAction.PAUSE and e.strategy_id == "strat1"]
    assert len(pause_events) == 1
    assert pause_events[0].requires_human_approval is False


def test_pause_rule_triggers_on_high_drawdown() -> None:
    """AC-8: PAUSE auto-triggers when 7d drawdown > 0.20."""
    manager = LifecycleManager()
    snapshot = _make_snapshot("strat1", sharpe_7d=0.5, drawdown_7d=0.25)
    events = manager.evaluate([snapshot])
    pause_events = [e for e in events if e.action == LifecycleAction.PAUSE and e.strategy_id == "strat1"]
    assert len(pause_events) == 1


def test_promote_rule_creates_pending_not_auto() -> None:
    """AC-8: PROMOTE creates pending notification, does NOT auto-execute."""
    manager = LifecycleManager()
    snapshot = _make_snapshot(
        "strat2",
        sharpe_7d=1.2,
        drawdown_7d=0.05,
        active_days=35,
        win_rate=0.60,
        max_drawdown=0.10,
    )
    events = manager.evaluate([snapshot])
    promote_events = [e for e in events if e.action == LifecycleAction.PROMOTE]
    assert len(promote_events) == 1
    assert promote_events[0].requires_human_approval is True
    assert promote_events[0].auto_executed is False


def test_demote_rule_triggers_on_live_drawdown() -> None:
    """AC-8: DEMOTE auto-triggers when live strategy drawdown > 0.15."""
    manager = LifecycleManager()
    snapshot = _make_snapshot("live_strat", sharpe_7d=0.8, drawdown_7d=0.18, is_live=True)
    events = manager.evaluate([snapshot])
    demote_events = [e for e in events if e.action == LifecycleAction.DEMOTE]
    assert len(demote_events) == 1
    assert demote_events[0].requires_human_approval is False


def test_no_action_for_healthy_strategy() -> None:
    manager = LifecycleManager()
    snapshot = _make_snapshot("healthy", sharpe_7d=0.8, drawdown_7d=0.05)
    events = manager.evaluate([snapshot])
    assert events == []
