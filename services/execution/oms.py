"""
Order Management System (OMS) with state machine.

Tracks order lifecycle and provides idempotency via unique client_order_id.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Set
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .broker.base import OrderResult, OrderStatus


class OrderState(str, Enum):
    """
    Order state machine states.

    Transitions:
        PENDING -> SUBMITTED (on submit)
        PENDING -> REJECTED (on reject)
        SUBMITTED -> PARTIALLY_FILLED (on partial fill)
        SUBMITTED -> FILLED (on fill)
        SUBMITTED -> REJECTED (on reject)
        SUBMITTED -> CANCELLED (on cancel)
        PARTIALLY_FILLED -> FILLED (on fill)
        PARTIALLY_FILLED -> CANCELLED (on cancel)
    """

    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


# Valid state transitions
VALID_TRANSITIONS: Dict[OrderState, Set[OrderState]] = {
    OrderState.PENDING: {OrderState.SUBMITTED, OrderState.REJECTED},
    OrderState.SUBMITTED: {
        OrderState.PARTIALLY_FILLED,
        OrderState.FILLED,
        OrderState.REJECTED,
        OrderState.CANCELLED,
    },
    OrderState.PARTIALLY_FILLED: {OrderState.FILLED, OrderState.CANCELLED},
    OrderState.FILLED: set(),  # Terminal state
    OrderState.REJECTED: set(),  # Terminal state
    OrderState.CANCELLED: set(),  # Terminal state
}


class ManagedOrder(BaseModel):
    """
    Order tracked by the OMS.

    Includes all order details plus internal tracking state.
    """

    # Internal tracking
    internal_id: UUID = Field(default_factory=uuid4, description="Internal OMS order ID")
    client_order_id: str = Field(..., description="Unique client order ID for idempotency")

    # Broker tracking
    broker_order_id: Optional[str] = Field(None, description="Broker's order ID")

    # Order details
    strategy_id: str = Field(..., description="Strategy that generated this order")
    symbol: str = Field(..., description="Trading symbol")
    side: str = Field(..., description="BUY or SELL")
    quantity: Decimal = Field(..., gt=0, description="Order quantity")
    order_type: str = Field(..., description="MARKET, LIMIT, STOP, STOP_LIMIT")
    limit_price: Optional[Decimal] = Field(None, description="Limit price")
    stop_price: Optional[Decimal] = Field(None, description="Stop price")
    time_in_force: str = Field("DAY", description="Time in force")

    # State tracking
    state: OrderState = Field(OrderState.PENDING, description="Current order state")
    filled_quantity: Decimal = Field(Decimal(0), ge=0, description="Quantity filled")
    average_fill_price: Optional[Decimal] = Field(None, description="Average fill price")
    fees: Decimal = Field(Decimal(0), ge=0, description="Total fees")

    # Rejection info
    reject_reason: Optional[str] = Field(None, description="Reason if rejected")

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    submitted_at: Optional[datetime] = Field(None)
    filled_at: Optional[datetime] = Field(None)
    cancelled_at: Optional[datetime] = Field(None)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def is_terminal(self) -> bool:
        """Check if order is in a terminal state."""
        return self.state in {OrderState.FILLED, OrderState.REJECTED, OrderState.CANCELLED}

    def is_open(self) -> bool:
        """Check if order is still open (pending or submitted)."""
        return self.state in {OrderState.PENDING, OrderState.SUBMITTED, OrderState.PARTIALLY_FILLED}

    def remaining_quantity(self) -> Decimal:
        """Get unfilled quantity."""
        return self.quantity - self.filled_quantity


class InvalidStateTransitionError(Exception):
    """Raised when attempting an invalid state transition."""

    pass


class DuplicateOrderError(Exception):
    """Raised when client_order_id already exists (idempotency check)."""

    pass


class OrderNotFoundError(Exception):
    """Raised when order is not found in OMS."""

    pass


class OrderManagementSystem:
    """
    Order Management System with state machine and idempotency.

    Features:
    - State machine for order lifecycle
    - Idempotency via unique client_order_id
    - In-memory order storage (mock DB for now)
    - Query orders by various criteria
    """

    def __init__(self):
        """Initialize OMS with empty order store."""
        # Orders indexed by internal ID
        self._orders: Dict[UUID, ManagedOrder] = {}

        # Index by client_order_id for idempotency
        self._client_order_index: Dict[str, UUID] = {}

        # Index by broker_order_id for status updates
        self._broker_order_index: Dict[str, UUID] = {}

        # Index by strategy_id for queries
        self._strategy_order_index: Dict[str, Set[UUID]] = {}

    def create_order(
        self,
        client_order_id: str,
        strategy_id: str,
        symbol: str,
        side: str,
        quantity: Decimal,
        order_type: str,
        limit_price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None,
        time_in_force: str = "DAY",
    ) -> ManagedOrder:
        """
        Create a new order in PENDING state.

        Args:
            client_order_id: Unique client order ID (for idempotency)
            strategy_id: Strategy that generated this order
            symbol: Trading symbol
            side: BUY or SELL
            quantity: Order quantity
            order_type: MARKET, LIMIT, STOP, STOP_LIMIT
            limit_price: Limit price (required for LIMIT orders)
            stop_price: Stop price (required for STOP orders)
            time_in_force: Time in force (DAY, GTC, IOC, FOK)

        Returns:
            ManagedOrder in PENDING state

        Raises:
            DuplicateOrderError: If client_order_id already exists
        """
        # Idempotency check
        if client_order_id in self._client_order_index:
            existing_id = self._client_order_index[client_order_id]
            existing_order = self._orders[existing_id]
            # Return existing order (idempotent behavior)
            return existing_order

        # Create new order
        order = ManagedOrder(
            client_order_id=client_order_id,
            strategy_id=strategy_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            limit_price=limit_price,
            stop_price=stop_price,
            time_in_force=time_in_force,
        )

        # Store and index
        self._orders[order.internal_id] = order
        self._client_order_index[client_order_id] = order.internal_id

        # Index by strategy
        if strategy_id not in self._strategy_order_index:
            self._strategy_order_index[strategy_id] = set()
        self._strategy_order_index[strategy_id].add(order.internal_id)

        return order

    def submit_order(
        self,
        client_order_id: str,
        broker_order_id: str,
    ) -> ManagedOrder:
        """
        Transition order from PENDING to SUBMITTED.

        Args:
            client_order_id: Client order ID
            broker_order_id: Broker's order ID

        Returns:
            Updated ManagedOrder
        """
        order = self.get_order_by_client_id(client_order_id)
        self._transition_state(order, OrderState.SUBMITTED)

        order.broker_order_id = broker_order_id
        order.submitted_at = datetime.now(timezone.utc)
        order.updated_at = datetime.now(timezone.utc)

        # Index by broker ID
        self._broker_order_index[broker_order_id] = order.internal_id

        return order

    def reject_order(
        self,
        client_order_id: str,
        reason: str,
    ) -> ManagedOrder:
        """
        Transition order to REJECTED state.

        Args:
            client_order_id: Client order ID
            reason: Rejection reason

        Returns:
            Updated ManagedOrder
        """
        order = self.get_order_by_client_id(client_order_id)
        self._transition_state(order, OrderState.REJECTED)

        order.reject_reason = reason
        order.updated_at = datetime.now(timezone.utc)

        return order

    def fill_order(
        self,
        broker_order_id: str,
        filled_quantity: Decimal,
        average_fill_price: Decimal,
        fees: Decimal = Decimal(0),
    ) -> ManagedOrder:
        """
        Record a fill (partial or complete).

        Args:
            broker_order_id: Broker's order ID
            filled_quantity: Total filled quantity
            average_fill_price: Average fill price
            fees: Total fees

        Returns:
            Updated ManagedOrder
        """
        order = self.get_order_by_broker_id(broker_order_id)

        # Update fill info
        order.filled_quantity = filled_quantity
        order.average_fill_price = average_fill_price
        order.fees = fees
        order.updated_at = datetime.now(timezone.utc)

        # Determine new state
        if filled_quantity >= order.quantity:
            self._transition_state(order, OrderState.FILLED)
            order.filled_at = datetime.now(timezone.utc)
        elif filled_quantity > 0:
            if order.state == OrderState.SUBMITTED:
                self._transition_state(order, OrderState.PARTIALLY_FILLED)

        return order

    def cancel_order(
        self,
        client_order_id: Optional[str] = None,
        broker_order_id: Optional[str] = None,
    ) -> ManagedOrder:
        """
        Transition order to CANCELLED state.

        Args:
            client_order_id: Client order ID (optional)
            broker_order_id: Broker order ID (optional)

        Returns:
            Updated ManagedOrder

        Raises:
            OrderNotFoundError: If order not found
            ValueError: If neither ID provided
        """
        if client_order_id:
            order = self.get_order_by_client_id(client_order_id)
        elif broker_order_id:
            order = self.get_order_by_broker_id(broker_order_id)
        else:
            raise ValueError("Either client_order_id or broker_order_id required")

        self._transition_state(order, OrderState.CANCELLED)
        order.cancelled_at = datetime.now(timezone.utc)
        order.updated_at = datetime.now(timezone.utc)

        return order

    def update_from_broker(self, broker_result: OrderResult) -> ManagedOrder:
        """
        Update order state from broker status update.

        Args:
            broker_result: OrderResult from broker

        Returns:
            Updated ManagedOrder
        """
        order = self.get_order_by_broker_id(broker_result.broker_order_id)

        # Map broker status to our state
        status_map = {
            OrderStatus.PENDING: OrderState.PENDING,
            OrderStatus.SUBMITTED: OrderState.SUBMITTED,
            OrderStatus.ACCEPTED: OrderState.SUBMITTED,
            OrderStatus.PARTIALLY_FILLED: OrderState.PARTIALLY_FILLED,
            OrderStatus.FILLED: OrderState.FILLED,
            OrderStatus.CANCELLED: OrderState.CANCELLED,
            OrderStatus.REJECTED: OrderState.REJECTED,
            OrderStatus.EXPIRED: OrderState.CANCELLED,
        }

        new_state = status_map.get(broker_result.status)
        if new_state and new_state != order.state:
            try:
                self._transition_state(order, new_state)
            except InvalidStateTransitionError:
                # Log but don't fail - broker may skip states
                pass

        # Update fill info
        if broker_result.filled_quantity:
            order.filled_quantity = broker_result.filled_quantity
        if broker_result.average_fill_price:
            order.average_fill_price = broker_result.average_fill_price
        if broker_result.filled_at:
            order.filled_at = broker_result.filled_at
        if broker_result.reject_reason:
            order.reject_reason = broker_result.reject_reason

        order.updated_at = datetime.now(timezone.utc)

        return order

    def _transition_state(
        self,
        order: ManagedOrder,
        new_state: OrderState,
    ) -> None:
        """
        Validate and perform state transition.

        Args:
            order: Order to transition
            new_state: Target state

        Raises:
            InvalidStateTransitionError: If transition is invalid
        """
        valid_targets = VALID_TRANSITIONS.get(order.state, set())

        if new_state not in valid_targets:
            raise InvalidStateTransitionError(
                f"Cannot transition from {order.state} to {new_state}. "
                f"Valid transitions: {valid_targets}"
            )

        order.state = new_state

    def get_order(self, internal_id: UUID) -> ManagedOrder:
        """Get order by internal ID."""
        if internal_id not in self._orders:
            raise OrderNotFoundError(f"Order not found: {internal_id}")
        return self._orders[internal_id]

    def get_order_by_client_id(self, client_order_id: str) -> ManagedOrder:
        """Get order by client order ID."""
        if client_order_id not in self._client_order_index:
            raise OrderNotFoundError(f"Order not found: {client_order_id}")
        internal_id = self._client_order_index[client_order_id]
        return self._orders[internal_id]

    def get_order_by_broker_id(self, broker_order_id: str) -> ManagedOrder:
        """Get order by broker order ID."""
        if broker_order_id not in self._broker_order_index:
            raise OrderNotFoundError(f"Order not found: {broker_order_id}")
        internal_id = self._broker_order_index[broker_order_id]
        return self._orders[internal_id]

    def get_orders_by_strategy(self, strategy_id: str) -> List[ManagedOrder]:
        """Get all orders for a strategy."""
        if strategy_id not in self._strategy_order_index:
            return []
        order_ids = self._strategy_order_index[strategy_id]
        return [self._orders[oid] for oid in order_ids]

    def get_open_orders(self, strategy_id: Optional[str] = None) -> List[ManagedOrder]:
        """Get all open orders, optionally filtered by strategy."""
        if strategy_id:
            orders = self.get_orders_by_strategy(strategy_id)
        else:
            orders = list(self._orders.values())

        return [o for o in orders if o.is_open()]

    def get_all_orders(self) -> List[ManagedOrder]:
        """Get all orders."""
        return list(self._orders.values())

    def has_order(self, client_order_id: str) -> bool:
        """Check if order exists (idempotency check)."""
        return client_order_id in self._client_order_index

    def cancel_all_open_orders(self, strategy_id: Optional[str] = None) -> List[ManagedOrder]:
        """
        Cancel all open orders.

        Args:
            strategy_id: Optional strategy filter

        Returns:
            List of cancelled orders
        """
        open_orders = self.get_open_orders(strategy_id)
        cancelled = []

        for order in open_orders:
            try:
                self._transition_state(order, OrderState.CANCELLED)
                order.cancelled_at = datetime.now(timezone.utc)
                order.updated_at = datetime.now(timezone.utc)
                cancelled.append(order)
            except InvalidStateTransitionError:
                # Skip orders that can't be cancelled
                pass

        return cancelled

    def generate_client_order_id(self, strategy_id: str, symbol: str) -> str:
        """
        Generate a unique client order ID.

        Format: {strategy_id}_{symbol}_{timestamp}_{uuid}

        Args:
            strategy_id: Strategy identifier
            symbol: Trading symbol

        Returns:
            Unique client order ID
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        unique_id = uuid4().hex[:8]
        return f"{strategy_id}_{symbol}_{timestamp}_{unique_id}"
