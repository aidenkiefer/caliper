"""
Controls API router for kill switch and mode transitions.

Endpoints:
- POST /v1/controls/kill-switch - Activate/deactivate kill switch
- POST /v1/controls/mode-transition - Transition strategy between modes
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from packages.common.execution_schemas import (
    KillSwitchAction,
    KillSwitchData,
    KillSwitchRequest,
    KillSwitchResponse,
    ModeTransitionRequest,
    ModeTransitionResponse,
    TradingMode,
)

from services.risk.manager import RiskManager
from services.api.dependencies import get_db
from services.api.routers.alerts import emit_alert_db_dedup
from packages.common.api_schemas import AlertSeverity

router = APIRouter(prefix="/controls", tags=["controls"])

_risk_manager = RiskManager()


# ============================================================================
# Kill Switch Endpoint
# ============================================================================


@router.post(
    "/kill-switch",
    response_model=KillSwitchResponse,
    summary="Activate or deactivate kill switch",
    description="""
    Manually trigger or release kill switch for a strategy or globally.
    
    **Activation:** Can be done by any admin user with a reason.
    
    **Deactivation:** Requires admin_code for authorization.
    
    **Scope:**
    - If `strategy_id` is omitted, affects global kill switch
    - If `strategy_id` is provided, affects only that strategy
    """,
)
async def control_kill_switch(request: KillSwitchRequest, db: Session = Depends(get_db)) -> KillSwitchResponse:
    """Activate or deactivate kill switch."""
    if request.action == KillSwitchAction.ACTIVATE:
        _risk_manager.activate_kill_switch(
            reason=request.reason,
            strategy_id=request.strategy_id,
            triggered_by="user",
        )

        try:
            emit_alert_db_dedup(
                db,
                AlertSeverity.CRITICAL,
                (
                    "Kill switch activated"
                    + (f" for strategy '{request.strategy_id}'" if request.strategy_id else " (global)")
                    + f": {request.reason}"
                ),
                source="risk",
                category="kill_switch",
                dedup_key=f"risk:kill_switch:activate:{request.strategy_id or 'global'}",
                context={
                    "scope": "strategy" if request.strategy_id else "global",
                    "strategy_id": request.strategy_id,
                },
                window_seconds=60,
            )
            db.commit()
        except SQLAlchemyError:
            db.rollback()
        except Exception:
            db.rollback()

        if request.strategy_id:
            info = _risk_manager.kill_switch.get_strategy_info(request.strategy_id) or {}
            return KillSwitchResponse(
                message=f"Kill switch activated for {request.strategy_id}",
                data=KillSwitchData(
                    kill_switch_active=True,
                    scope="strategy",
                    affected_strategies=[request.strategy_id],
                    reason=info.get("reason") or request.reason,
                    activated_at=info.get("activated_at"),
                ),
            )

        info = _risk_manager.kill_switch.get_global_info() or {}
        return KillSwitchResponse(
            message="Global kill switch activated",
            data=KillSwitchData(
                kill_switch_active=True,
                scope="global",
                affected_strategies=["all"],
                reason=info.get("reason") or request.reason,
                activated_at=info.get("activated_at"),
            ),
        )

    # Deactivation - requires admin code
    if not request.admin_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="admin_code required for kill switch deactivation",
        )

    try:
        _risk_manager.deactivate_kill_switch(
            admin_code=request.admin_code,
            strategy_id=request.strategy_id,
            reason=request.reason,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    try:
        emit_alert_db_dedup(
            db,
            AlertSeverity.INFO,
            (
                "Kill switch deactivated"
                + (f" for strategy '{request.strategy_id}'" if request.strategy_id else " (global)")
                + f": {request.reason}"
            ),
            source="risk",
            category="kill_switch",
            dedup_key=f"risk:kill_switch:deactivate:{request.strategy_id or 'global'}",
            context={
                "scope": "strategy" if request.strategy_id else "global",
                "strategy_id": request.strategy_id,
            },
            window_seconds=60,
        )
        db.commit()
    except SQLAlchemyError:
        db.rollback()
    except Exception:
        db.rollback()

    return KillSwitchResponse(
        message="Kill switch deactivated",
        data=KillSwitchData(
            kill_switch_active=False,
            scope="strategy" if request.strategy_id else "global",
            affected_strategies=[request.strategy_id] if request.strategy_id else [],
            reason=None,
            activated_at=None,
        ),
    )


@router.get(
    "/kill-switch",
    response_model=KillSwitchResponse,
    summary="Get kill switch status",
)
async def get_kill_switch_status(strategy_id: Optional[str] = None) -> KillSwitchResponse:
    """Get current kill switch status."""
    if strategy_id:
        if _risk_manager.kill_switch.is_active():
            info = _risk_manager.kill_switch.get_global_info() or {}
            return KillSwitchResponse(
                message="Kill switch status",
                data=KillSwitchData(
                    kill_switch_active=True,
                    scope="global",
                    affected_strategies=[strategy_id],
                    reason=info.get("reason"),
                    activated_at=info.get("activated_at"),
                ),
            )

        if _risk_manager.kill_switch.is_active(strategy_id):
            info = _risk_manager.kill_switch.get_strategy_info(strategy_id) or {}
            return KillSwitchResponse(
                message="Kill switch status",
                data=KillSwitchData(
                    kill_switch_active=True,
                    scope="strategy",
                    affected_strategies=[strategy_id],
                    reason=info.get("reason"),
                    activated_at=info.get("activated_at"),
                ),
            )

        return KillSwitchResponse(
            message="Kill switch status",
            data=KillSwitchData(
                kill_switch_active=False,
                scope="strategy",
                affected_strategies=[],
                reason=None,
                activated_at=None,
            ),
        )
    else:
        # Global status
        active_strategies = _risk_manager.kill_switch.get_active_strategies()
        global_info = _risk_manager.kill_switch.get_global_info() or {}
        return KillSwitchResponse(
            message="Kill switch status",
            data=KillSwitchData(
                kill_switch_active=_risk_manager.kill_switch.is_active(),
                scope="global",
                affected_strategies=active_strategies if not _risk_manager.kill_switch.is_active() else ["all"],
                reason=global_info.get("reason"),
                activated_at=global_info.get("activated_at"),
            ),
        )


# ============================================================================
# Mode Transition Endpoint
# ============================================================================


@router.post(
    "/mode-transition",
    response_model=ModeTransitionResponse,
    summary="Transition strategy between paper and live mode",
    description="""
    Transition a strategy between PAPER and LIVE trading modes.
    
    **Requirements:**
    - Valid approval_code (human approval checkpoint)
    - Strategy must be in the from_mode
    - Transitioning to LIVE requires additional validation
    
    **Validation for LIVE transition:**
    - Strategy must have completed paper trading period
    - No outstanding risk violations
    - Kill switch must not be active
    """,
)
async def transition_mode(request: ModeTransitionRequest) -> ModeTransitionResponse:
    """Transition strategy between modes."""
    raise HTTPException(
        status_code=501,
        detail="Mode transitions are not wired yet (PAPER-only Phase 1)",
    )


@router.get(
    "/mode/{strategy_id}",
    summary="Get strategy trading mode",
)
async def get_strategy_mode(strategy_id: str) -> dict:
    """Get current trading mode for a strategy."""
    mode = TradingMode.PAPER
    return {
        "strategy_id": strategy_id,
        "mode": mode.value,
    }
