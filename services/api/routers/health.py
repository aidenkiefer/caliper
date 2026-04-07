"""
Health check endpoints.

Provides system health status for monitoring and alerting.
Includes broker connection status and risk manager status.
"""

import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from packages.common.api_schemas import HealthResponse, ServiceHealth
from services.api.dependencies import get_db

router = APIRouter()


def _check_database_health(db: Session) -> ServiceHealth:
    now = datetime.now(timezone.utc)
    start = datetime.now(timezone.utc)
    try:
        db.execute(text("SELECT 1")).fetchone()
        end = datetime.now(timezone.utc)
        latency_ms = int((end - start).total_seconds() * 1000)
        return ServiceHealth(status="healthy", latency_ms=latency_ms, last_update=now)
    except SQLAlchemyError:
        return ServiceHealth(status="unhealthy", latency_ms=None, last_update=now)


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
async def get_health(db: Session = Depends(get_db)) -> HealthResponse:
    """
    Get system health status.

    Returns health information for all services including
    broker connection status and risk manager status.
    """
    now = datetime.now(timezone.utc)

    # NOTE: Only report a service as "healthy" if we actually check it.
    broker_mode = os.getenv("TRADING_MODE", "PAPER")
    broker_name = os.getenv("BROKER_NAME", "alpaca")

    # Build service health checks (minimal real checks today).
    # - database is real (SELECT 1)
    # - other services are marked degraded until wired to real probes
    def _degraded() -> ServiceHealth:
        return ServiceHealth(status="degraded", last_update=now)

    services = {
        "database": _check_database_health(db),
        "data_feed": _degraded(),
        "broker_connection": ServiceHealth(
            status="degraded",
            broker=broker_name,
            mode=broker_mode,
            last_update=now,
        ),
        "risk_manager": _degraded(),
        "redis": _degraded(),
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
    now = datetime.now(timezone.utc)
    broker_mode = os.getenv("TRADING_MODE", "PAPER")
    broker_name = os.getenv("BROKER_NAME", "alpaca")
    health = ServiceHealth(status="degraded", broker=broker_name, mode=broker_mode, last_update=now)

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
    now = datetime.now(timezone.utc)
    health = ServiceHealth(status="degraded", last_update=now)

    return {
        "status": health.status,
        "kill_switch": {
            "active": None,
            "scope": None,
        },
        "circuit_breaker": {
            "state": None,
            "tripped": None,
        },
        "drawdown": {
            "daily_pct": None,
            "total_pct": None,
        },
        "thresholds": {
            "daily_halt_pct": "3.0",
            "total_halt_pct": "10.0",
        },
    }
