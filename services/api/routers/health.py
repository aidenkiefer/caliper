"""
Health check endpoints.

Provides system health status for monitoring and alerting.
"""

from datetime import datetime, timezone

from fastapi import APIRouter

from packages.common.api_schemas import HealthResponse, ServiceHealth

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="System health check",
    description="Returns overall system health status and per-service health.",
)
async def get_health() -> HealthResponse:
    """
    Get system health status.
    
    Returns health information for all services:
    - database: Database connectivity and latency
    - data_feed: Market data feed status
    - broker_connection: Broker API status
    - redis: Cache/queue status
    """
    now = datetime.now(timezone.utc)
    
    # TODO: Wire to actual service health checks
    # For now, return mock healthy status
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
        "broker_connection": ServiceHealth(
            status="healthy",
            broker="alpaca",
            mode="PAPER",
        ),
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
