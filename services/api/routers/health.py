"""
Health check endpoints.

Provides system health status for monitoring and alerting.
Includes broker connection status and risk manager status.
"""

import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter

from packages.common.api_schemas import HealthResponse, ServiceHealth

router = APIRouter()


# ============================================================================
# Health Check State (would be wired to actual services in production)
# ============================================================================

# Broker connection state (mock)
_broker_connected = True
_broker_mode = os.getenv("TRADING_MODE", "PAPER")
_broker_name = "alpaca"
_last_broker_check: Optional[datetime] = None

# Risk manager state (mock)
_kill_switch_active = False
_circuit_breaker_state = "closed"
_daily_drawdown_pct = "0.50"
_total_drawdown_pct = "2.30"


def _check_broker_health() -> ServiceHealth:
    """Check broker connection health."""
    global _last_broker_check
    now = datetime.now(timezone.utc)
    _last_broker_check = now
    
    # In production, would actually ping broker API
    if _broker_connected:
        return ServiceHealth(
            status="healthy",
            broker=_broker_name,
            mode=_broker_mode,
            latency_ms=45,  # Mock latency
            last_update=now,
        )
    else:
        return ServiceHealth(
            status="unhealthy",
            broker=_broker_name,
            mode=_broker_mode,
            latency_ms=None,
            last_update=now,
        )


def _check_risk_health() -> ServiceHealth:
    """Check risk manager health."""
    now = datetime.now(timezone.utc)
    
    # Determine status based on kill switch and circuit breaker
    if _kill_switch_active:
        status = "unhealthy"
    elif _circuit_breaker_state == "open":
        status = "unhealthy"
    elif _circuit_breaker_state == "half_open":
        status = "degraded"
    else:
        status = "healthy"
    
    return ServiceHealth(
        status=status,
        last_update=now,
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="System health check",
    description="""
    Returns overall system health status and per-service health.
    
    **Services checked:**
    - `database`: Database connectivity and latency
    - `data_feed`: Market data feed status and staleness
    - `broker_connection`: Broker API connectivity and mode (PAPER/LIVE)
    - `risk_manager`: Risk limits and kill switch status
    - `redis`: Cache/queue status
    
    **Overall status:**
    - `healthy`: All services healthy
    - `degraded`: Some services degraded but operational
    - `unhealthy`: Critical service failure
    """,
)
async def get_health() -> HealthResponse:
    """
    Get system health status.
    
    Returns health information for all services including
    broker connection status and risk manager status.
    """
    now = datetime.now(timezone.utc)
    
    # Build service health checks
    services = {
        "database": ServiceHealth(
            status="healthy",
            latency_ms=12,
        ),
        "data_feed": ServiceHealth(
            status="healthy",
            last_update=now,
            staleness_seconds=10,
        ),
        "broker_connection": _check_broker_health(),
        "risk_manager": _check_risk_health(),
        "redis": ServiceHealth(
            status="healthy",
        ),
    }
    
    # Determine overall status
    statuses = [s.status for s in services.values()]
    if all(s == "healthy" for s in statuses):
        overall = "healthy"
    elif any(s == "unhealthy" for s in statuses):
        overall = "unhealthy"
    else:
        overall = "degraded"
    
    return HealthResponse(
        status=overall,
        services=services,
        timestamp=now,
    )


@router.get(
    "/health/broker",
    summary="Broker connection health",
    description="Detailed broker connection health check.",
)
async def get_broker_health() -> dict:
    """Get detailed broker connection health."""
    health = _check_broker_health()
    
    return {
        "status": health.status,
        "broker": health.broker,
        "mode": health.mode,
        "connected": health.status == "healthy",
        "latency_ms": health.latency_ms,
        "last_check": health.last_update,
        "details": {
            "paper_trading": health.mode == "PAPER",
            "account_status": "ACTIVE" if health.status == "healthy" else "UNKNOWN",
        },
    }


@router.get(
    "/health/risk",
    summary="Risk manager health",
    description="Detailed risk manager health check including kill switch and circuit breaker status.",
)
async def get_risk_health() -> dict:
    """Get detailed risk manager health."""
    health = _check_risk_health()
    
    return {
        "status": health.status,
        "kill_switch": {
            "active": _kill_switch_active,
            "scope": "global" if _kill_switch_active else None,
        },
        "circuit_breaker": {
            "state": _circuit_breaker_state,
            "tripped": _circuit_breaker_state == "open",
        },
        "drawdown": {
            "daily_pct": _daily_drawdown_pct,
            "total_pct": _total_drawdown_pct,
        },
        "thresholds": {
            "daily_halt_pct": "3.0",
            "total_halt_pct": "10.0",
        },
    }
