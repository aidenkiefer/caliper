"""
Orders API router for order submission and tracking.

Endpoints:
- POST /v1/orders - Submit a new order
- GET /v1/orders - List orders
- GET /v1/orders/{order_id} - Get order details
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from packages.common.execution_schemas import (
    OrderDetailResponse,
    OrderListMeta,
    OrderListResponse,
    OrderRequest,
    OrderRejectionResponse,
    OrderResponse,
)

router = APIRouter(prefix="/orders", tags=["orders"])

# ============================================================================
# Endpoints
# ============================================================================


@router.post(
    "",
    response_model=OrderResponse,
    responses={
        400: {"model": OrderRejectionResponse, "description": "Order rejected by risk checks"},
    },
    summary="Submit a new order",
    description="""
    Submit a new order for execution.
    
    The order will go through pre-trade risk checks:
    - Kill switch check
    - Portfolio limits (max positions, capital deployed)
    - Order limits (max notional, price sanity)
    
    If risk checks fail, returns 400 with violation details.
    
    **Idempotency:** If `client_order_id` is provided and an order with that ID
    already exists, the existing order will be returned instead of creating a duplicate.
    """,
)
async def submit_order(request: OrderRequest) -> OrderResponse:
    """Submit a new order."""
    raise HTTPException(
        status_code=501,
        detail="Order submission is not wired yet (mock order store removed)",
    )


@router.get(
    "",
    response_model=OrderListResponse,
    summary="List orders",
    description="Get list of orders with optional filters.",
)
async def list_orders(
    strategy_id: Optional[str] = Query(None, description="Filter by strategy"),
    status: Optional[str] = Query(None, description="Filter by status"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
) -> OrderListResponse:
    """List orders with optional filters."""
    return OrderListResponse(
        data=[],
        meta=OrderListMeta(
            total_count=0,
            page=page,
            per_page=per_page,
        ),
    )


@router.get(
    "/{order_id}",
    response_model=OrderDetailResponse,
    summary="Get order details",
    description="Get detailed information for a specific order.",
)
async def get_order(order_id: str) -> OrderDetailResponse:
    """Get order details by ID."""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Order not found: {order_id}",
    )


@router.delete(
    "/{order_id}",
    summary="Cancel order",
    description="Cancel a pending or submitted order.",
)
async def cancel_order(order_id: str) -> dict:
    """Cancel an order."""
    raise HTTPException(
        status_code=501,
        detail="Order cancellation is not wired yet (mock order store removed)",
    )
