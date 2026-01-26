"""
Risk Management Service.

This service enforces trading risk limits and provides kill switches:
- Pre-trade order validation
- Portfolio-level limits (drawdown, capital, positions)
- Strategy-level limits (allocation, daily loss)
- Order-level limits (position sizing, sanity checks)
- Kill switch mechanism (system and strategy-level)
- Circuit breaker with automatic triggers
"""

from .manager import RiskManager, RiskCheckResult
from .limits import (
    PortfolioLimits,
    StrategyLimits,
    OrderLimits,
    RiskLimitViolation,
)
from .kill_switch import KillSwitch, KillSwitchStatus, KillSwitchEvent
from .circuit_breaker import CircuitBreaker, CircuitBreakerState, CircuitBreakerEvent

__all__ = [
    # Manager
    "RiskManager",
    "RiskCheckResult",
    # Limits
    "PortfolioLimits",
    "StrategyLimits",
    "OrderLimits",
    "RiskLimitViolation",
    # Kill Switch
    "KillSwitch",
    "KillSwitchStatus",
    "KillSwitchEvent",
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitBreakerState",
    "CircuitBreakerEvent",
]
