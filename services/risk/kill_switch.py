"""
Kill switch mechanism for emergency trading halt.

Supports both system-wide and strategy-level kill switches.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Set
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class KillSwitchStatus(str, Enum):
    """Kill switch status."""

    INACTIVE = "inactive"
    ACTIVE = "active"


class KillSwitchEvent(BaseModel):
    """Record of a kill switch event."""

    event_id: UUID = Field(default_factory=uuid4)
    event_type: str = Field(..., description="activated, deactivated")
    scope: str = Field(..., description="global, strategy")
    strategy_id: Optional[str] = Field(None, description="Strategy ID if strategy-scoped")
    reason: str = Field(..., description="Reason for activation/deactivation")
    triggered_by: str = Field(..., description="user, system, circuit_breaker")
    admin_code: Optional[str] = Field(None, description="Admin code used for deactivation")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class KillSwitch:
    """
    Kill switch mechanism for emergency trading halt.

    Features:
    - Global (system-wide) kill switch
    - Strategy-level kill switches
    - Requires admin code to deactivate
    - Audit trail of all events

    Kill Switch Protocol (from docs/risk-policy.md):
    1. Cancel all pending orders
    2. Halt all strategy execution
    3. Freeze positions (default) or flatten (configurable)
    4. Send CRITICAL alert
    5. Require manual admin reset
    """

    # Default admin code (should be configured via environment)
    DEFAULT_ADMIN_CODE = "EMERGENCY_OVERRIDE_2026"

    def __init__(self, admin_code: Optional[str] = None):
        """
        Initialize kill switch.

        Args:
            admin_code: Admin code required to deactivate kill switch
        """
        self._admin_code = admin_code or self.DEFAULT_ADMIN_CODE

        # Global kill switch state
        self._global_active = False
        self._global_reason: Optional[str] = None
        self._global_activated_at: Optional[datetime] = None
        self._global_triggered_by: Optional[str] = None

        # Strategy-level kill switches
        self._strategy_switches: Dict[str, bool] = {}
        self._strategy_reasons: Dict[str, str] = {}
        self._strategy_activated_at: Dict[str, datetime] = {}
        self._strategy_triggered_by: Dict[str, str] = {}

        # Event history
        self._events: List[KillSwitchEvent] = []

    def is_active(self, strategy_id: Optional[str] = None) -> bool:
        """
        Check if kill switch is active.

        Args:
            strategy_id: If provided, check strategy-level switch

        Returns:
            True if kill switch is active
        """
        # Global always takes precedence
        if self._global_active:
            return True

        # Check strategy-specific
        if strategy_id:
            return self._strategy_switches.get(strategy_id, False)

        return False

    def get_status(self, strategy_id: Optional[str] = None) -> KillSwitchStatus:
        """Get kill switch status."""
        return KillSwitchStatus.ACTIVE if self.is_active(strategy_id) else KillSwitchStatus.INACTIVE

    def activate_global(
        self,
        reason: str,
        triggered_by: str = "system",
    ) -> KillSwitchEvent:
        """
        Activate global kill switch.

        Args:
            reason: Reason for activation
            triggered_by: Who/what triggered activation

        Returns:
            KillSwitchEvent record
        """
        self._global_active = True
        self._global_reason = reason
        self._global_activated_at = datetime.now(timezone.utc)
        self._global_triggered_by = triggered_by

        event = KillSwitchEvent(
            event_type="activated",
            scope="global",
            reason=reason,
            triggered_by=triggered_by,
        )
        self._events.append(event)

        return event

    def deactivate_global(
        self,
        admin_code: str,
        reason: str = "Manual deactivation",
    ) -> KillSwitchEvent:
        """
        Deactivate global kill switch.

        Args:
            admin_code: Admin code for authentication
            reason: Reason for deactivation

        Returns:
            KillSwitchEvent record

        Raises:
            PermissionError: If admin code is invalid
        """
        if admin_code != self._admin_code:
            raise PermissionError("Invalid admin code for kill switch deactivation")

        if not self._global_active:
            raise ValueError("Global kill switch is not active")

        self._global_active = False
        previous_reason = self._global_reason
        self._global_reason = None
        self._global_activated_at = None
        self._global_triggered_by = None

        event = KillSwitchEvent(
            event_type="deactivated",
            scope="global",
            reason=f"{reason} (was: {previous_reason})",
            triggered_by="admin",
            admin_code=admin_code[:4] + "****",  # Mask admin code
        )
        self._events.append(event)

        return event

    def activate_strategy(
        self,
        strategy_id: str,
        reason: str,
        triggered_by: str = "system",
    ) -> KillSwitchEvent:
        """
        Activate kill switch for a specific strategy.

        Args:
            strategy_id: Strategy to halt
            reason: Reason for activation
            triggered_by: Who/what triggered activation

        Returns:
            KillSwitchEvent record
        """
        self._strategy_switches[strategy_id] = True
        self._strategy_reasons[strategy_id] = reason
        self._strategy_activated_at[strategy_id] = datetime.now(timezone.utc)
        self._strategy_triggered_by[strategy_id] = triggered_by

        event = KillSwitchEvent(
            event_type="activated",
            scope="strategy",
            strategy_id=strategy_id,
            reason=reason,
            triggered_by=triggered_by,
        )
        self._events.append(event)

        return event

    def deactivate_strategy(
        self,
        strategy_id: str,
        admin_code: str,
        reason: str = "Manual deactivation",
    ) -> KillSwitchEvent:
        """
        Deactivate kill switch for a specific strategy.

        Args:
            strategy_id: Strategy to resume
            admin_code: Admin code for authentication
            reason: Reason for deactivation

        Returns:
            KillSwitchEvent record

        Raises:
            PermissionError: If admin code is invalid
            ValueError: If strategy kill switch not active
        """
        if admin_code != self._admin_code:
            raise PermissionError("Invalid admin code for kill switch deactivation")

        if not self._strategy_switches.get(strategy_id, False):
            raise ValueError(f"Kill switch for strategy {strategy_id} is not active")

        previous_reason = self._strategy_reasons.get(strategy_id, "Unknown")

        self._strategy_switches[strategy_id] = False
        self._strategy_reasons.pop(strategy_id, None)
        self._strategy_activated_at.pop(strategy_id, None)
        self._strategy_triggered_by.pop(strategy_id, None)

        event = KillSwitchEvent(
            event_type="deactivated",
            scope="strategy",
            strategy_id=strategy_id,
            reason=f"{reason} (was: {previous_reason})",
            triggered_by="admin",
            admin_code=admin_code[:4] + "****",  # Mask admin code
        )
        self._events.append(event)

        return event

    def get_active_strategies(self) -> List[str]:
        """Get list of strategies with active kill switches."""
        return [sid for sid, active in self._strategy_switches.items() if active]

    def get_global_info(self) -> Optional[Dict]:
        """Get global kill switch info if active."""
        if not self._global_active:
            return None

        return {
            "active": True,
            "reason": self._global_reason,
            "activated_at": self._global_activated_at,
            "triggered_by": self._global_triggered_by,
        }

    def get_strategy_info(self, strategy_id: str) -> Optional[Dict]:
        """Get strategy kill switch info if active."""
        if not self._strategy_switches.get(strategy_id, False):
            return None

        return {
            "active": True,
            "strategy_id": strategy_id,
            "reason": self._strategy_reasons.get(strategy_id),
            "activated_at": self._strategy_activated_at.get(strategy_id),
            "triggered_by": self._strategy_triggered_by.get(strategy_id),
        }

    def get_events(
        self,
        limit: int = 100,
        strategy_id: Optional[str] = None,
    ) -> List[KillSwitchEvent]:
        """
        Get kill switch event history.

        Args:
            limit: Maximum events to return
            strategy_id: Filter by strategy

        Returns:
            List of KillSwitchEvent records
        """
        events = self._events

        if strategy_id:
            events = [e for e in events if e.strategy_id == strategy_id or e.scope == "global"]

        return events[-limit:]

    def get_summary(self) -> Dict:
        """Get summary of kill switch status."""
        return {
            "global": {
                "status": self.get_status(),
                "active": self._global_active,
                "reason": self._global_reason,
                "activated_at": self._global_activated_at,
            },
            "strategies": {
                sid: {
                    "active": True,
                    "reason": self._strategy_reasons.get(sid),
                    "activated_at": self._strategy_activated_at.get(sid),
                }
                for sid in self.get_active_strategies()
            },
            "total_events": len(self._events),
        }
