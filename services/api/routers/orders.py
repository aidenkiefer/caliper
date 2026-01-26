"""
Orders API router for order submission and tracking.

Endpoints:
- POST /v1/orders - Submit a new order
- GET /v1/orders - List orders
- GET /v1/orders/{order_id} - Get order details
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, status

from packages.common.execution_schemas import (
    OrderData,
    OrderDetailResponse,
    OrderListMeta,
    OrderListResponse,
    OrderRequest,
    OrderRejectionResponse,
    OrderResponse,
    OrderSide,
    OrderStatus,
    OrderType,
    RiskViolation,
    TimeInForce,
)

router = APIRouter(prefix="/orders", tags=["orders"])


# ============================================================================
# In-memory order store (mock for now - would be backed by database)
# ============================================================================

_orders: dict[str, OrderData] = {}
_client_order_id_index: dict[str, str] = {}  # client_order_id -> order_id

# Risk check state (mock - would integrate with risk service)
_kill_switch_active = False


# ============================================================================
# Helper Functions
# ============================================================================

def generate_order_id() -> str:
    """Generate unique order ID."""
    return str(uuid4())


def generate_client_order_id(strategy_id: str, symbol: str) -> str:
    """Generate unique client order ID."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    unique_id = uuid4().hex[:8]
    return f"{strategy_id}_{symbol}_{timestamp}_{unique_id}"


def mock_risk_check(
    symbol: str,
    side: OrderSide,
    quantity: Decimal,
    price: Decimal,
    strategy_id: str,
) -> tuple[bool, list[RiskViolation]]:
    """
    Mock risk check - in production would call risk service.
    
    Returns:
        Tuple of (approved, list of violations)
    """
    violations = []
    
    # Check kill switch
    if _kill_switch_active:
        violations.append(RiskViolation(
            limit_type="kill_switch_active",
            limit_value="active",
            actual_value="global",
            message="Trading halted - kill switch is active",
        ))
    
    # Mock order limits from risk policy
    order_notional = quantity * price
    
    # Max notional check ($25,000)
    if order_notional > Decimal("25000"):
        violations.append(RiskViolation(
            limit_type="max_notional",
            limit_value="$25,000.00",
            actual_value=f"${order_notional:,.2f}",
            message=f"Order notional ${order_notional:,.2f} exceeds limit of $25,000",
        ))
    
    # Min stock price check ($5.00)
    if price < Decimal("5.00"):
        violations.append(RiskViolation(
            limit_type="min_stock_price",
            limit_value="$5.00",
            actual_value=f"${price}",
            message=f"Stock price ${price} below minimum of $5.00",
        ))
    
    # Max risk per trade (mock - assume 2% of $100k portfolio = $2000)
    max_risk = Decimal("2000")
    # Assume 10% risk on position
    estimated_risk = order_notional * Decimal("0.10")
    if estimated_risk > max_risk:
        violations.append(RiskViolation(
            limit_type="max_risk_per_trade",
            limit_value="2% of equity",
            actual_value=f"${estimated_risk:,.2f} estimated risk",
            message=f"Estimated risk ${estimated_risk:,.2f} exceeds limit",
        ))
    
    return len(violations) == 0, violations


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
    now = datetime.now(timezone.utc)
    
    # Check for idempotency - return existing order if client_order_id exists
    if request.client_order_id and request.client_order_id in _client_order_id_index:
        existing_order_id = _client_order_id_index[request.client_order_id]
        existing_order = _orders[existing_order_id]
        return OrderResponse(
            message="Order already exists (idempotent)",
            data=existing_order,
        )
    
    # Parse quantity and price
    quantity = Decimal(request.quantity)
    
    # Determine price for risk check
    if request.limit_price:
        price = Decimal(request.limit_price)
    elif request.stop_price:
        price = Decimal(request.stop_price)
    else:
        # For market orders, use a mock last price
        # In production, would fetch current market price
        price = Decimal("100.00")
    
    # Perform risk check
    approved, violations = mock_risk_check(
        symbol=request.symbol,
        side=request.side,
        quantity=quantity,
        price=price,
        strategy_id=request.strategy_id,
    )
    
    if not approved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Order rejected by risk checks",
                "violations": [v.model_dump() for v in violations],
            },
        )
    
    # Generate IDs
    order_id = generate_order_id()
    client_order_id = request.client_order_id or generate_client_order_id(
        request.strategy_id, request.symbol
    )
    
    # Create order
    order = OrderData(
        order_id=order_id,
        client_order_id=client_order_id,
        broker_order_id=None,  # Set when submitted to broker
        symbol=request.symbol,
        side=request.side,
        quantity=request.quantity,
        order_type=request.order_type,
        status=OrderStatus.PENDING,
        limit_price=request.limit_price,
        stop_price=request.stop_price,
        time_in_force=request.time_in_force,
        filled_quantity="0",
        average_fill_price=None,
        strategy_id=request.strategy_id,
        reject_reason=None,
        created_at=now,
        submitted_at=None,
        filled_at=None,
    )
    
    # Store order
    _orders[order_id] = order
    _client_order_id_index[client_order_id] = order_id
    
    # Mock: Simulate submission to broker (would be async in production)
    order.status = OrderStatus.SUBMITTED
    order.submitted_at = now
    order.broker_order_id = f"ALPACA_{uuid4().hex[:12].upper()}"
    
    return OrderResponse(
        message="Order submitted successfully",
        data=order,
    )


@router.get(
    "",
    response_model=OrderListResponse,
    summary="List orders",
    description="Get list of orders with optional filters.",
)
async def list_orders(
    strategy_id: Optional[str] = Query(None, description="Filter by strategy"),
    status: Optional[OrderStatus] = Query(None, description="Filter by status"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
) -> OrderListResponse:
    """List orders with optional filters."""
    # Filter orders
    filtered = list(_orders.values())
    
    if strategy_id:
        filtered = [o for o in filtered if o.strategy_id == strategy_id]
    
    if status:
        filtered = [o for o in filtered if o.status == status]
    
    if symbol:
        filtered = [o for o in filtered if o.symbol == symbol]
    
    # Sort by created_at descending
    filtered.sort(key=lambda o: o.created_at, reverse=True)
    
    # Paginate
    total_count = len(filtered)
    start = (page - 1) * per_page
    end = start + per_page
    paginated = filtered[start:end]
    
    return OrderListResponse(
        data=paginated,
        meta=OrderListMeta(
            total_count=total_count,
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
    # Try to find by order_id
    if order_id in _orders:
        return OrderDetailResponse(data=_orders[order_id])
    
    # Try to find by client_order_id
    if order_id in _client_order_id_index:
        actual_id = _client_order_id_index[order_id]
        return OrderDetailResponse(data=_orders[actual_id])
    
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
    # Find order
    if order_id in _orders:
        order = _orders[order_id]
    elif order_id in _client_order_id_index:
        actual_id = _client_order_id_index[order_id]
        order = _orders[actual_id]
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order not found: {order_id}",
        )
    
    # Check if cancellable
    if order.status not in [OrderStatus.PENDING, OrderStatus.SUBMITTED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel order in {order.status} status",
        )
    
    # Cancel
    order.status = OrderStatus.CANCELLED
    
    return {
        "message": "Order cancelled",
        "order_id": order.order_id,
        "status": order.status,
    }
