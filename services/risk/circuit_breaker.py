"""
Circuit breaker with automatic triggers.

Monitors drawdown and automatically triggers kill switch on threshold breach.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .kill_switch import KillSwitch


class CircuitBreakerState(str, Enum):
    """Circuit breaker state."""

    CLOSED = "closed"  # Normal operation
    HALF_OPEN = "half_open"  # Warning state, monitoring closely
    OPEN = "open"  # Tripped, trading halted


class CircuitBreakerEvent(BaseModel):
    """Record of a circuit breaker event."""

    event_id: UUID = Field(default_factory=uuid4)
    event_type: str = Field(..., description="warning, tripped, reset")
    state_from: CircuitBreakerState
    state_to: CircuitBreakerState
    trigger: str = Field(..., description="What triggered the state change")
    value: str = Field(..., description="Value that triggered the change")
    threshold: str = Field(..., description="Threshold that was crossed")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CircuitBreaker:
    """
    Circuit breaker that automatically triggers kill switch.

    Monitors:
    - Daily drawdown → warning at 2%, halt at 3%
    - Total drawdown → warning at 8%, kill switch at 10%

    State Machine:
    - CLOSED: Normal operation
    - HALF_OPEN: Warning state (drawdown between warning and halt threshold)
    - OPEN: Trading halted (kill switch triggered)

    Automatic Recovery:
    - From OPEN → requires manual reset (kill switch deactivation)
    - From HALF_OPEN → returns to CLOSED if drawdown improves
    """

    def __init__(
        self,
        kill_switch: Optional[KillSwitch] = None,
        daily_warning_pct: Decimal = Decimal("2.0"),
        daily_halt_pct: Decimal = Decimal("3.0"),
        total_warning_pct: Decimal = Decimal("8.0"),
        total_halt_pct: Decimal = Decimal("10.0"),
    ):
        """
        Initialize circuit breaker.

        Args:
            kill_switch: Kill switch to trigger on breach
            daily_warning_pct: Daily drawdown warning threshold
            daily_halt_pct: Daily drawdown halt threshold
            total_warning_pct: Total drawdown warning threshold
            total_halt_pct: Total drawdown halt threshold (triggers kill switch)
        """
        self._kill_switch = kill_switch or KillSwitch()

        # Thresholds
        self._daily_warning_pct = daily_warning_pct
        self._daily_halt_pct = daily_halt_pct
        self._total_warning_pct = total_warning_pct
        self._total_halt_pct = total_halt_pct

        # State
        self._state = CircuitBreakerState.CLOSED
        self._state_changed_at = datetime.now(timezone.utc)
        self._trip_reason: Optional[str] = None

        # Current values
        self._current_daily_drawdown_pct = Decimal("0.0")
        self._current_total_drawdown_pct = Decimal("0.0")

        # Event history
        self._events: List[CircuitBreakerEvent] = []

    @property
    def state(self) -> CircuitBreakerState:
        """Get current circuit breaker state."""
        return self._state

    def is_tripped(self) -> bool:
        """Check if circuit breaker is tripped (OPEN state)."""
        return self._state == CircuitBreakerState.OPEN

    def is_warning(self) -> bool:
        """Check if in warning state (HALF_OPEN)."""
        return self._state == CircuitBreakerState.HALF_OPEN

    def is_normal(self) -> bool:
        """Check if in normal operation (CLOSED)."""
        return self._state == CircuitBreakerState.CLOSED

    def update_drawdown(
        self,
        daily_drawdown_pct: Decimal,
        total_drawdown_pct: Decimal,
    ) -> CircuitBreakerState:
        """
        Update drawdown values and check thresholds.

        Args:
            daily_drawdown_pct: Current daily drawdown as positive %
            total_drawdown_pct: Current total drawdown as positive %

        Returns:
            Current circuit breaker state
        """
        self._current_daily_drawdown_pct = daily_drawdown_pct
        self._current_total_drawdown_pct = total_drawdown_pct

        old_state = self._state

        # Check for kill switch trigger (highest priority)
        if total_drawdown_pct >= self._total_halt_pct:
            self._transition_to(
                CircuitBreakerState.OPEN,
                f"Total drawdown of {total_drawdown_pct}% exceeded halt threshold",
                f"{total_drawdown_pct}%",
                f"{self._total_halt_pct}%",
            )
            # Trigger kill switch
            self._kill_switch.activate_global(
                reason=f"Circuit breaker: Total drawdown {total_drawdown_pct}% >= {self._total_halt_pct}%",
                triggered_by="circuit_breaker",
            )

        elif daily_drawdown_pct >= self._daily_halt_pct:
            self._transition_to(
                CircuitBreakerState.OPEN,
                f"Daily drawdown of {daily_drawdown_pct}% exceeded halt threshold",
                f"{daily_drawdown_pct}%",
                f"{self._daily_halt_pct}%",
            )
            # Trigger kill switch
            self._kill_switch.activate_global(
                reason=f"Circuit breaker: Daily drawdown {daily_drawdown_pct}% >= {self._daily_halt_pct}%",
                triggered_by="circuit_breaker",
            )

        # Check for warning state
        elif (
            total_drawdown_pct >= self._total_warning_pct
            or daily_drawdown_pct >= self._daily_warning_pct
        ):
            if self._state == CircuitBreakerState.CLOSED:
                trigger = []
                if daily_drawdown_pct >= self._daily_warning_pct:
                    trigger.append(f"daily drawdown {daily_drawdown_pct}%")
                if total_drawdown_pct >= self._total_warning_pct:
                    trigger.append(f"total drawdown {total_drawdown_pct}%")

                self._transition_to(
                    CircuitBreakerState.HALF_OPEN,
                    f"Warning: {', '.join(trigger)} approaching halt threshold",
                    f"daily={daily_drawdown_pct}%, total={total_drawdown_pct}%",
                    f"daily_warn={self._daily_warning_pct}%, total_warn={self._total_warning_pct}%",
                )

        # Check for recovery from warning state
        elif self._state == CircuitBreakerState.HALF_OPEN:
            self._transition_to(
                CircuitBreakerState.CLOSED,
                "Drawdown improved below warning thresholds",
                f"daily={daily_drawdown_pct}%, total={total_drawdown_pct}%",
                f"daily_warn={self._daily_warning_pct}%, total_warn={self._total_warning_pct}%",
            )

        return self._state

    def _transition_to(
        self,
        new_state: CircuitBreakerState,
        trigger: str,
        value: str,
        threshold: str,
    ) -> None:
        """Record state transition."""
        if new_state == self._state:
            return

        event_type = (
            "tripped"
            if new_state == CircuitBreakerState.OPEN
            else ("warning" if new_state == CircuitBreakerState.HALF_OPEN else "reset")
        )

        event = CircuitBreakerEvent(
            event_type=event_type,
            state_from=self._state,
            state_to=new_state,
            trigger=trigger,
            value=value,
            threshold=threshold,
        )
        self._events.append(event)

        self._state = new_state
        self._state_changed_at = datetime.now(timezone.utc)

        if new_state == CircuitBreakerState.OPEN:
            self._trip_reason = trigger

    def reset(
        self,
        admin_code: str,
    ) -> CircuitBreakerEvent:
        """
        Manually reset circuit breaker from OPEN state.

        Args:
            admin_code: Admin code for authorization

        Returns:
            CircuitBreakerEvent record

        Note: This also deactivates the kill switch.
        """
        if self._state != CircuitBreakerState.OPEN:
            raise ValueError("Circuit breaker is not in OPEN state")

        # Deactivate kill switch (will validate admin code)
        self._kill_switch.deactivate_global(
            admin_code=admin_code,
            reason="Circuit breaker manual reset",
        )

        old_state = self._state
        self._state = CircuitBreakerState.CLOSED
        self._state_changed_at = datetime.now(timezone.utc)

        previous_reason = self._trip_reason
        self._trip_reason = None

        event = CircuitBreakerEvent(
            event_type="reset",
            state_from=old_state,
            state_to=CircuitBreakerState.CLOSED,
            trigger=f"Manual reset (was: {previous_reason})",
            value="N/A",
            threshold="N/A",
        )
        self._events.append(event)

        return event

    def get_events(self, limit: int = 100) -> List[CircuitBreakerEvent]:
        """Get circuit breaker event history."""
        return self._events[-limit:]

    def get_status(self) -> Dict:
        """Get circuit breaker status summary."""
        return {
            "state": self._state,
            "is_tripped": self.is_tripped(),
            "is_warning": self.is_warning(),
            "state_changed_at": self._state_changed_at,
            "trip_reason": self._trip_reason,
            "current_drawdown": {
                "daily_pct": str(self._current_daily_drawdown_pct),
                "total_pct": str(self._current_total_drawdown_pct),
            },
            "thresholds": {
                "daily_warning_pct": str(self._daily_warning_pct),
                "daily_halt_pct": str(self._daily_halt_pct),
                "total_warning_pct": str(self._total_warning_pct),
                "total_halt_pct": str(self._total_halt_pct),
            },
            "total_events": len(self._events),
        }
