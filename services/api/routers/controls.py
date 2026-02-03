"""
Controls API router for kill switch and mode transitions.

Endpoints:
- POST /v1/controls/kill-switch - Activate/deactivate kill switch
- POST /v1/controls/mode-transition - Transition strategy between modes
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, status

from packages.common.execution_schemas import (
    KillSwitchAction,
    KillSwitchData,
    KillSwitchRequest,
    KillSwitchResponse,
    ModeTransitionData,
    ModeTransitionRequest,
    ModeTransitionResponse,
    TradingMode,
)

router = APIRouter(prefix="/controls", tags=["controls"])


# ============================================================================
# In-memory state (mock for now - would be backed by database in production)
# ============================================================================

# Kill switch state
_global_kill_switch_active = False
_global_kill_switch_reason: Optional[str] = None
_global_kill_switch_activated_at: Optional[datetime] = None

_strategy_kill_switches: dict[str, bool] = {}
_strategy_kill_switch_reasons: dict[str, str] = {}
_strategy_kill_switch_activated_at: dict[str, datetime] = {}

# Strategy modes
_strategy_modes: dict[str, TradingMode] = {}

# Valid approval codes (would be from secure storage in production)
VALID_APPROVAL_CODES = {"ABC123", "LIVE_APPROVAL_2026", "EMERGENCY_OVERRIDE_2026"}
VALID_ADMIN_CODES = {"EMERGENCY_OVERRIDE_2026", "ADMIN_RESET_2026"}


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
async def control_kill_switch(request: KillSwitchRequest) -> KillSwitchResponse:
    """Activate or deactivate kill switch."""
    global _global_kill_switch_active, _global_kill_switch_reason, _global_kill_switch_activated_at

    now = datetime.now(timezone.utc)

    if request.action == KillSwitchAction.ACTIVATE:
        # Activation
        if request.strategy_id:
            # Strategy-level
            _strategy_kill_switches[request.strategy_id] = True
            _strategy_kill_switch_reasons[request.strategy_id] = request.reason
            _strategy_kill_switch_activated_at[request.strategy_id] = now

            return KillSwitchResponse(
                message=f"Kill switch activated for {request.strategy_id}",
                data=KillSwitchData(
                    kill_switch_active=True,
                    scope="strategy",
                    affected_strategies=[request.strategy_id],
                    reason=request.reason,
                    activated_at=now,
                ),
            )
        else:
            # Global
            _global_kill_switch_active = True
            _global_kill_switch_reason = request.reason
            _global_kill_switch_activated_at = now

            # Get all registered strategies
            affected = list(_strategy_modes.keys()) or ["all"]

            return KillSwitchResponse(
                message="Global kill switch activated",
                data=KillSwitchData(
                    kill_switch_active=True,
                    scope="global",
                    affected_strategies=affected,
                    reason=request.reason,
                    activated_at=now,
                ),
            )

    else:
        # Deactivation - requires admin code
        if not request.admin_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="admin_code required for kill switch deactivation",
            )

        if request.admin_code not in VALID_ADMIN_CODES:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid admin code",
            )

        if request.strategy_id:
            # Strategy-level
            if not _strategy_kill_switches.get(request.strategy_id, False):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Kill switch for strategy {request.strategy_id} is not active",
                )

            _strategy_kill_switches[request.strategy_id] = False
            _strategy_kill_switch_reasons.pop(request.strategy_id, None)
            _strategy_kill_switch_activated_at.pop(request.strategy_id, None)

            return KillSwitchResponse(
                message=f"Kill switch deactivated for {request.strategy_id}",
                data=KillSwitchData(
                    kill_switch_active=False,
                    scope="strategy",
                    affected_strategies=[request.strategy_id],
                    reason=request.reason,
                    activated_at=None,
                ),
            )
        else:
            # Global
            if not _global_kill_switch_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Global kill switch is not active",
                )

            _global_kill_switch_active = False
            _global_kill_switch_reason = None
            _global_kill_switch_activated_at = None

            return KillSwitchResponse(
                message="Global kill switch deactivated",
                data=KillSwitchData(
                    kill_switch_active=False,
                    scope="global",
                    affected_strategies=[],
                    reason=request.reason,
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
        is_active = _strategy_kill_switches.get(strategy_id, False) or _global_kill_switch_active

        if _global_kill_switch_active:
            # Global takes precedence
            return KillSwitchResponse(
                message="Kill switch status",
                data=KillSwitchData(
                    kill_switch_active=True,
                    scope="global",
                    affected_strategies=[strategy_id],
                    reason=_global_kill_switch_reason,
                    activated_at=_global_kill_switch_activated_at,
                ),
            )
        elif _strategy_kill_switches.get(strategy_id, False):
            return KillSwitchResponse(
                message="Kill switch status",
                data=KillSwitchData(
                    kill_switch_active=True,
                    scope="strategy",
                    affected_strategies=[strategy_id],
                    reason=_strategy_kill_switch_reasons.get(strategy_id),
                    activated_at=_strategy_kill_switch_activated_at.get(strategy_id),
                ),
            )
        else:
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
        active_strategies = [s for s, active in _strategy_kill_switches.items() if active]

        return KillSwitchResponse(
            message="Kill switch status",
            data=KillSwitchData(
                kill_switch_active=_global_kill_switch_active,
                scope="global",
                affected_strategies=active_strategies
                if not _global_kill_switch_active
                else ["all"],
                reason=_global_kill_switch_reason,
                activated_at=_global_kill_switch_activated_at,
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
    # Validate approval code
    if request.approval_code not in VALID_APPROVAL_CODES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid approval code",
        )

    # Check kill switch
    if _global_kill_switch_active or _strategy_kill_switches.get(request.strategy_id, False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot transition mode while kill switch is active",
        )

    # Get current mode (default to PAPER for new strategies)
    current_mode = _strategy_modes.get(request.strategy_id, TradingMode.PAPER)

    # Validate from_mode matches current
    if current_mode != request.from_mode:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Strategy is in {current_mode.value} mode, not {request.from_mode.value}",
        )

    # Additional validation for LIVE transition
    if request.to_mode == TradingMode.LIVE:
        # In production, would check:
        # - Paper trading history (duration, performance)
        # - Risk parameters configured
        # - Backtesting results
        # For now, just require approval code
        pass

    # Perform transition
    now = datetime.now(timezone.utc)
    _strategy_modes[request.strategy_id] = request.to_mode

    return ModeTransitionResponse(
        message=f"Strategy transitioned to {request.to_mode.value} mode",
        data=ModeTransitionData(
            strategy_id=request.strategy_id,
            mode=request.to_mode,
            transitioned_at=now,
        ),
    )


@router.get(
    "/mode/{strategy_id}",
    summary="Get strategy trading mode",
)
async def get_strategy_mode(strategy_id: str) -> dict:
    """Get current trading mode for a strategy."""
    mode = _strategy_modes.get(strategy_id, TradingMode.PAPER)
    return {
        "strategy_id": strategy_id,
        "mode": mode.value,
    }
