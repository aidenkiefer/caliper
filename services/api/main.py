"""
FastAPI application entry point.

This module creates and configures the FastAPI application with:
- CORS middleware for dashboard access
- API routers for all endpoints
- OpenAPI documentation at /docs
- Lifespan events for startup/shutdown
- Exception handlers for consistent error responses
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator
from uuid import uuid4

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .routers import health, metrics, strategies, runs, positions, orders, controls, drift, explanations, baselines, recommendations


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Lifespan context manager for startup and shutdown events.
    
    Use this to initialize database connections, cache clients, etc.
    """
    # Startup: Initialize resources
    # TODO: Initialize database connection pool
    # TODO: Initialize Redis client
    yield
    # Shutdown: Clean up resources
    # TODO: Close database connections
    # TODO: Close Redis connections


# Create FastAPI app
app = FastAPI(
    title="Quant Trading Platform API",
    description="REST API for the quantitative ML trading platform dashboard",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# ============================================================================
# Exception Handlers
# ============================================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Handle validation errors with consistent error format."""
    details = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        details.append({
            "field": field,
            "message": error["msg"],
        })
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request parameters",
                "details": details,
            },
            "request_id": str(uuid4()),
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle unexpected errors with consistent error format."""
    # Log the error (in production, use proper logging)
    # logger.error(f"Unexpected error: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
            },
            "request_id": str(uuid4()),
        },
    )

# Configure CORS for dashboard access
# Note: For production, replace with specific origins
CORS_ORIGINS = [
    "http://localhost:3000",      # Local Next.js dev
    "http://127.0.0.1:3000",      # Alternative localhost
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app",  # Vercel preview deployments
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers with /v1 prefix
API_V1_PREFIX = "/v1"

app.include_router(
    health.router,
    prefix=API_V1_PREFIX,
    tags=["health"],
)

app.include_router(
    metrics.router,
    prefix=API_V1_PREFIX,
    tags=["metrics"],
)

app.include_router(
    strategies.router,
    prefix=API_V1_PREFIX,
    tags=["strategies"],
)

app.include_router(
    runs.router,
    prefix=API_V1_PREFIX,
    tags=["runs"],
)

app.include_router(
    positions.router,
    prefix=API_V1_PREFIX,
    tags=["positions"],
)

app.include_router(
    orders.router,
    prefix=API_V1_PREFIX,
    tags=["orders"],
)

app.include_router(
    controls.router,
    prefix=API_V1_PREFIX,
    tags=["controls"],
)

app.include_router(
    drift.router,
    prefix=API_V1_PREFIX,
    tags=["drift"],
)

app.include_router(
    explanations.router,
    prefix=API_V1_PREFIX,
    tags=["explanations"],
)

app.include_router(
    baselines.router,
    prefix=API_V1_PREFIX,
    tags=["baselines"],
)

app.include_router(
    recommendations.router,
    prefix=API_V1_PREFIX,
    tags=["recommendations"],
)


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint - redirect to docs."""
    return {
        "message": "Quant Trading Platform API",
        "version": "1.0.0",
        "docs": "/docs",
    }
