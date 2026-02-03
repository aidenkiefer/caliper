"""
Abstract BrokerClient interface for broker adapters.

All broker implementations must inherit from this interface to ensure
consistent behavior across different brokers (Alpaca, IB, etc.).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


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
    """Order status from broker."""

    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    ACCEPTED = "ACCEPTED"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class OrderResult(BaseModel):
    """Result of placing an order with the broker."""

    broker_order_id: str = Field(..., description="Broker's order ID")
    client_order_id: str = Field(..., description="Client's unique order ID")
    status: OrderStatus = Field(..., description="Order status")
    symbol: str = Field(..., description="Trading symbol")
    side: OrderSide = Field(..., description="Buy or sell")
    quantity: Decimal = Field(..., description="Order quantity")
    filled_quantity: Decimal = Field(Decimal(0), description="Filled quantity")
    average_fill_price: Optional[Decimal] = Field(None, description="Average fill price")
    limit_price: Optional[Decimal] = Field(None, description="Limit price")
    stop_price: Optional[Decimal] = Field(None, description="Stop price")
    time_in_force: TimeInForce = Field(..., description="Time in force")
    submitted_at: Optional[datetime] = Field(None, description="Submission time")
    filled_at: Optional[datetime] = Field(None, description="Fill time")
    reject_reason: Optional[str] = Field(None, description="Rejection reason")


class Position(BaseModel):
    """Broker position."""

    symbol: str = Field(..., description="Trading symbol")
    quantity: Decimal = Field(..., description="Position quantity")
    average_entry_price: Decimal = Field(..., description="Average entry price")
    current_price: Optional[Decimal] = Field(None, description="Current market price")
    market_value: Optional[Decimal] = Field(None, description="Current market value")
    unrealized_pnl: Optional[Decimal] = Field(None, description="Unrealized P&L")
    unrealized_pnl_pct: Optional[Decimal] = Field(None, description="Unrealized P&L %")
    cost_basis: Optional[Decimal] = Field(None, description="Cost basis")
    side: str = Field("long", description="Position side (long/short)")


class Account(BaseModel):
    """Broker account information."""

    account_id: str = Field(..., description="Account identifier")
    cash: Decimal = Field(..., description="Available cash")
    portfolio_value: Decimal = Field(..., description="Total portfolio value")
    buying_power: Decimal = Field(..., description="Available buying power")
    equity: Decimal = Field(..., description="Account equity")
    currency: str = Field("USD", description="Account currency")
    status: str = Field(..., description="Account status")
    pattern_day_trader: bool = Field(False, description="PDT flag")
    trading_blocked: bool = Field(False, description="Trading blocked flag")
    transfers_blocked: bool = Field(False, description="Transfers blocked flag")


class Order(BaseModel):
    """Order to submit to broker."""

    client_order_id: str = Field(..., description="Unique client order ID")
    symbol: str = Field(..., description="Trading symbol")
    side: OrderSide = Field(..., description="Buy or sell")
    quantity: Decimal = Field(..., gt=0, description="Order quantity")
    order_type: OrderType = Field(..., description="Order type")
    time_in_force: TimeInForce = Field(TimeInForce.DAY, description="Time in force")
    limit_price: Optional[Decimal] = Field(None, description="Limit price")
    stop_price: Optional[Decimal] = Field(None, description="Stop price")
    extended_hours: bool = Field(False, description="Extended hours trading")


class BrokerClient(ABC):
    """
    Abstract interface for broker API clients.

    All broker implementations (Alpaca, Interactive Brokers, etc.) must
    implement this interface to ensure consistent behavior.
    """

    @abstractmethod
    async def place_order(self, order: Order) -> OrderResult:
        """
        Place an order with the broker.

        Args:
            order: Order to place

        Returns:
            OrderResult with broker order ID and status

        Raises:
            BrokerError: If order placement fails
        """
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel a pending order.

        Args:
            order_id: Broker order ID to cancel

        Returns:
            True if cancellation was successful

        Raises:
            BrokerError: If cancellation fails
        """
        pass

    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """
        Get all current positions.

        Returns:
            List of Position objects

        Raises:
            BrokerError: If position fetch fails
        """
        pass

    @abstractmethod
    async def get_account(self) -> Account:
        """
        Get account information.

        Returns:
            Account object with balance and status

        Raises:
            BrokerError: If account fetch fails
        """
        pass

    @abstractmethod
    async def get_order_status(self, order_id: str) -> OrderResult:
        """
        Get status of a specific order.

        Args:
            order_id: Broker order ID

        Returns:
            OrderResult with current order status

        Raises:
            BrokerError: If order fetch fails
        """
        pass

    @abstractmethod
    async def get_orders(
        self,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[OrderResult]:
        """
        Get list of orders.

        Args:
            status: Filter by status (open, closed, all)
            limit: Maximum number of orders to return

        Returns:
            List of OrderResult objects
        """
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """
        Check if client is connected to broker.

        Returns:
            True if connected
        """
        pass

    @abstractmethod
    def is_paper(self) -> bool:
        """
        Check if client is in paper trading mode.

        Returns:
            True if paper trading
        """
        pass


class BrokerError(Exception):
    """Exception raised for broker API errors."""

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        order_id: Optional[str] = None,
    ):
        super().__init__(message)
        self.code = code
        self.order_id = order_id


class InsufficientFundsError(BrokerError):
    """Raised when account has insufficient funds."""

    pass


class OrderNotFoundError(BrokerError):
    """Raised when order is not found."""

    pass


class PositionNotFoundError(BrokerError):
    """Raised when position is not found."""

    pass
