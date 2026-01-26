"""
Pydantic schemas for execution and risk management API.

These schemas define the request/response contracts for:
- Order submission and tracking
- Controls (kill switch, mode transition)
- Risk limit configuration
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================================
# Order Schemas
# ============================================================================

class OrderSide(str, Enum):
    """Order side."""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    """Order type."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class TimeInForce(str, Enum):
    """Time in force for orders."""
    DAY = "DAY"
    GTC = "GTC"
    IOC = "IOC"
    FOK = "FOK"


class OrderStatus(str, Enum):
    """Order status."""
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    ACCEPTED = "ACCEPTED"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class OrderRequest(BaseModel):
    """Request for POST /v1/orders - submit a new order."""
    symbol: str = Field(..., min_length=1, max_length=10, description="Trading symbol")
    side: OrderSide = Field(..., description="BUY or SELL")
    quantity: str = Field(..., description="Order quantity as string")
    order_type: OrderType = Field(OrderType.MARKET, description="Order type")
    limit_price: Optional[str] = Field(None, description="Limit price for LIMIT orders")
    stop_price: Optional[str] = Field(None, description="Stop price for STOP orders")
    time_in_force: TimeInForce = Field(TimeInForce.DAY, description="Time in force")
    strategy_id: str = Field(..., description="Strategy placing the order")
    client_order_id: Optional[str] = Field(None, description="Client-provided order ID for idempotency")
    
    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "AAPL",
                "side": "BUY",
                "quantity": "100",
                "order_type": "LIMIT",
                "limit_price": "150.00",
                "time_in_force": "DAY",
                "strategy_id": "momentum_v1",
            }
        }


class OrderData(BaseModel):
    """Order data in API responses."""
    order_id: str = Field(..., description="Internal order ID")
    client_order_id: str = Field(..., description="Client order ID")
    broker_order_id: Optional[str] = Field(None, description="Broker's order ID")
    symbol: str = Field(..., description="Trading symbol")
    side: OrderSide = Field(..., description="BUY or SELL")
    quantity: str = Field(..., description="Order quantity")
    order_type: OrderType = Field(..., description="Order type")
    status: OrderStatus = Field(..., description="Current order status")
    limit_price: Optional[str] = Field(None, description="Limit price")
    stop_price: Optional[str] = Field(None, description="Stop price")
    time_in_force: TimeInForce = Field(..., description="Time in force")
    filled_quantity: str = Field("0", description="Filled quantity")
    average_fill_price: Optional[str] = Field(None, description="Average fill price")
    strategy_id: str = Field(..., description="Strategy ID")
    reject_reason: Optional[str] = Field(None, description="Rejection reason if rejected")
    created_at: datetime = Field(..., description="Creation timestamp")
    submitted_at: Optional[datetime] = Field(None, description="Submission timestamp")
    filled_at: Optional[datetime] = Field(None, description="Fill timestamp")


class OrderResponse(BaseModel):
    """Response for POST /v1/orders."""
    message: str = Field(..., description="Result message")
    data: OrderData


class OrderDetailResponse(BaseModel):
    """Response for GET /v1/orders/{order_id}."""
    data: OrderData


class OrderListMeta(BaseModel):
    """Metadata for order list response."""
    total_count: int = Field(..., description="Total orders")
    page: int = Field(..., description="Current page")
    per_page: int = Field(..., description="Items per page")


class OrderListResponse(BaseModel):
    """Response for GET /v1/orders."""
    data: List[OrderData]
    meta: OrderListMeta


# ============================================================================
# Risk Rejection Schema
# ============================================================================

class RiskViolation(BaseModel):
    """Risk limit violation detail."""
    limit_type: str = Field(..., description="Type of limit violated")
    limit_value: str = Field(..., description="Configured limit")
    actual_value: str = Field(..., description="Actual value")
    message: str = Field(..., description="Violation message")


class OrderRejectionResponse(BaseModel):
    """Response when order is rejected by risk checks."""
    message: str = Field("Order rejected by risk checks", description="Rejection message")
    violations: List[RiskViolation] = Field(..., description="List of violations")


# ============================================================================
# Controls Schemas
# ============================================================================

class KillSwitchAction(str, Enum):
    """Kill switch action."""
    ACTIVATE = "activate"
    DEACTIVATE = "deactivate"


class KillSwitchRequest(BaseModel):
    """Request for POST /v1/controls/kill-switch."""
    action: KillSwitchAction = Field(..., description="Activate or deactivate")
    strategy_id: Optional[str] = Field(None, description="Strategy ID (omit for global)")
    reason: str = Field(..., description="Reason for action")
    admin_code: Optional[str] = Field(None, description="Admin code (required for deactivation)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "action": "activate",
                "reason": "Manual intervention due to unusual market volatility",
            }
        }


class KillSwitchData(BaseModel):
    """Kill switch status data."""
    kill_switch_active: bool = Field(..., description="Whether kill switch is active")
    scope: str = Field(..., description="global or strategy")
    affected_strategies: List[str] = Field(default_factory=list, description="Affected strategies")
    reason: Optional[str] = Field(None, description="Reason for current state")
    activated_at: Optional[datetime] = Field(None, description="Activation timestamp")


class KillSwitchResponse(BaseModel):
    """Response for POST /v1/controls/kill-switch."""
    message: str = Field(..., description="Result message")
    data: KillSwitchData


class TradingMode(str, Enum):
    """Trading mode."""
    PAPER = "PAPER"
    LIVE = "LIVE"


class ModeTransitionRequest(BaseModel):
    """Request for POST /v1/controls/mode-transition."""
    strategy_id: str = Field(..., description="Strategy ID")
    from_mode: TradingMode = Field(..., description="Current mode")
    to_mode: TradingMode = Field(..., description="Target mode")
    approval_code: str = Field(..., description="Human approval code")
    
    class Config:
        json_schema_extra = {
            "example": {
                "strategy_id": "momentum_v1",
                "from_mode": "PAPER",
                "to_mode": "LIVE",
                "approval_code": "ABC123",
            }
        }


class ModeTransitionData(BaseModel):
    """Mode transition result data."""
    strategy_id: str = Field(..., description="Strategy ID")
    mode: TradingMode = Field(..., description="Current mode after transition")
    transitioned_at: datetime = Field(..., description="Transition timestamp")


class ModeTransitionResponse(BaseModel):
    """Response for POST /v1/controls/mode-transition."""
    message: str = Field(..., description="Result message")
    data: ModeTransitionData


# ============================================================================
# Health Check Extensions
# ============================================================================

class BrokerHealthStatus(BaseModel):
    """Broker connection health status."""
    status: str = Field(..., description="healthy, degraded, or unhealthy")
    broker: str = Field(..., description="Broker name (e.g., alpaca)")
    mode: str = Field(..., description="Trading mode (PAPER/LIVE)")
    connected: bool = Field(..., description="Whether connected to broker")
    account_status: Optional[str] = Field(None, description="Broker account status")
    last_check: datetime = Field(..., description="Last health check timestamp")


class RiskHealthStatus(BaseModel):
    """Risk manager health status."""
    status: str = Field(..., description="healthy, degraded, or unhealthy")
    kill_switch_active: bool = Field(..., description="Whether kill switch is active")
    circuit_breaker_state: str = Field(..., description="Circuit breaker state")
    daily_drawdown_pct: str = Field(..., description="Current daily drawdown")
    total_drawdown_pct: str = Field(..., description="Current total drawdown")


# ============================================================================
# Position Schemas (Extended)
# ============================================================================

class PositionData(BaseModel):
    """Position data for execution tracking."""
    position_id: str = Field(..., description="Internal position ID")
    symbol: str = Field(..., description="Trading symbol")
    strategy_id: str = Field(..., description="Strategy ID")
    quantity: str = Field(..., description="Position quantity")
    average_entry_price: str = Field(..., description="Average entry price")
    current_price: Optional[str] = Field(None, description="Current market price")
    market_value: Optional[str] = Field(None, description="Current market value")
    unrealized_pnl: Optional[str] = Field(None, description="Unrealized P&L")
    realized_pnl: str = Field("0.00", description="Realized P&L")
    opened_at: datetime = Field(..., description="When position was opened")
    updated_at: datetime = Field(..., description="Last update timestamp")


# ============================================================================
# Account Schemas
# ============================================================================

class AccountData(BaseModel):
    """Broker account information."""
    account_id: str = Field(..., description="Account identifier")
    cash: str = Field(..., description="Available cash")
    portfolio_value: str = Field(..., description="Total portfolio value")
    buying_power: str = Field(..., description="Available buying power")
    equity: str = Field(..., description="Account equity")
    currency: str = Field("USD", description="Account currency")
    status: str = Field(..., description="Account status")
    trading_blocked: bool = Field(False, description="Whether trading is blocked")


class AccountResponse(BaseModel):
    """Response for account information."""
    data: AccountData
