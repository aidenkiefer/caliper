from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import List, Optional


class LifecycleAction(str, Enum):
    PROMOTE = "promote"
    PAUSE = "pause"
    RETIRE = "retire"
    CLONE = "clone"
    DEMOTE = "demote"


class LifecycleRule(str, Enum):
    DEMOTE_LIVE_DRAWDOWN = "demote_live_drawdown"
    PAUSE_UNDERPERFORMER = "pause_underperformer"
    RETIRE_ZOMBIE = "retire_zombie"
    PROMOTE_CANDIDATE = "promote_candidate"


@dataclass
class StrategyEvaluationSnapshot:
    strategy_id: str
    sharpe_7d: Decimal
    drawdown_7d: Decimal
    active_paper_days: int
    win_rate: Decimal
    max_drawdown: Decimal
    is_live: bool = False
    paused_days: int = 0


@dataclass
class LifecycleEvent:
    strategy_id: str
    action: LifecycleAction
    rule_id: str
    triggered_at: datetime
    requires_human_approval: bool
    auto_executed: bool
    notes: str = ""


class LifecycleManager:
    """Evaluates lifecycle rules and produces LifecycleEvents."""

    def evaluate(
        self,
        snapshots: List[StrategyEvaluationSnapshot],
    ) -> List[LifecycleEvent]:
        now = datetime.now(timezone.utc)
        events: List[LifecycleEvent] = []

        for snap in snapshots:
            # DEMOTE: live strategy with 7d drawdown > 0.15 (auto)
            if snap.is_live and snap.drawdown_7d > Decimal("0.15"):
                events.append(
                    LifecycleEvent(
                        strategy_id=snap.strategy_id,
                        action=LifecycleAction.DEMOTE,
                        rule_id=LifecycleRule.DEMOTE_LIVE_DRAWDOWN,
                        triggered_at=now,
                        requires_human_approval=False,
                        auto_executed=True,
                        notes=f"Live drawdown {snap.drawdown_7d} > 0.15",
                    )
                )
                continue  # demoted strategies skip other rules

            # PAUSE: 7d Sharpe < -0.5 OR 7d drawdown > 0.20 (auto)
            if snap.sharpe_7d < Decimal("-0.5") or snap.drawdown_7d > Decimal("0.20"):
                events.append(
                    LifecycleEvent(
                        strategy_id=snap.strategy_id,
                        action=LifecycleAction.PAUSE,
                        rule_id=LifecycleRule.PAUSE_UNDERPERFORMER,
                        triggered_at=now,
                        requires_human_approval=False,
                        auto_executed=True,
                        notes=f"Sharpe={snap.sharpe_7d}, Drawdown={snap.drawdown_7d}",
                    )
                )
                continue

            # RETIRE: paused > 14 days with no improvement (human approval)
            if snap.paused_days > 14:
                events.append(
                    LifecycleEvent(
                        strategy_id=snap.strategy_id,
                        action=LifecycleAction.RETIRE,
                        rule_id=LifecycleRule.RETIRE_ZOMBIE,
                        triggered_at=now,
                        requires_human_approval=True,
                        auto_executed=False,
                        notes=f"Paused for {snap.paused_days} days",
                    )
                )
                continue

            # PROMOTE: Sharpe > 1.0, win_rate > 0.55, max_drawdown < 0.15, >= 28 days paper
            if (
                snap.sharpe_7d > Decimal("1.0")
                and snap.win_rate > Decimal("0.55")
                and snap.max_drawdown < Decimal("0.15")
                and snap.active_paper_days >= 28
            ):
                events.append(
                    LifecycleEvent(
                        strategy_id=snap.strategy_id,
                        action=LifecycleAction.PROMOTE,
                        rule_id=LifecycleRule.PROMOTE_CANDIDATE,
                        triggered_at=now,
                        requires_human_approval=True,
                        auto_executed=False,
                        notes="Meets all promotion criteria",
                    )
                )

        return events
