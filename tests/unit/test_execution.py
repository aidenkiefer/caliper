"""
Unit tests for execution service (OMS, BrokerClient).

Tests:
- BrokerClient interface
- Order state transitions
- Order idempotency
- Position tracking

Following @testing-patterns skill:
- Factory pattern for test data
- Behavior-driven testing
- Test state machine transitions
"""

import pytest
from decimal import Decimal
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, Mock, patch

from services.execution.oms import (
    OrderManagementSystem,
    ManagedOrder,
    OrderState,
    InvalidStateTransitionError,
    DuplicateOrderError,
    OrderNotFoundError,
    VALID_TRANSITIONS,
)
from services.execution.broker.base import (
    BrokerClient,
    Order,
    OrderResult,
    OrderSide,
    OrderStatus,
    OrderType,
    TimeInForce,
    Position,
    Account,
    BrokerError,
)

from tests.fixtures.execution_data import get_mock_order, get_mock_portfolio


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def oms() -> OrderManagementSystem:
    """Fresh OMS for each test."""
    return OrderManagementSystem()


@pytest.fixture
def sample_order() -> dict:
    """Sample order parameters."""
    return {
        "client_order_id": f"test_{uuid4().hex[:8]}",
        "strategy_id": "momentum_v1",
        "symbol": "AAPL",
        "side": "BUY",
        "quantity": Decimal("100"),
        "order_type": "LIMIT",
        "limit_price": Decimal("150.00"),
        "time_in_force": "DAY",
    }


# ============================================================================
# BrokerClient Interface Tests
# ============================================================================

class TestBrokerClientInterface:
    """Tests for BrokerClient abstract interface."""
    
    def test_broker_client_is_abstract(self):
        """BrokerClient cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BrokerClient()
    
    def test_broker_client_required_methods(self):
        """BrokerClient requires all abstract methods."""
        required_methods = [
            "place_order",
            "cancel_order",
            "get_positions",
            "get_account",
            "get_order_status",
            "get_orders",
            "is_connected",
            "is_paper",
        ]
        
        for method in required_methods:
            assert hasattr(BrokerClient, method)
    
    def test_order_model_validation(self):
        """Order model validates required fields."""
        order = Order(
            client_order_id="test_123",
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=Decimal("100"),
            order_type=OrderType.MARKET,
            time_in_force=TimeInForce.DAY,
        )
        
        assert order.client_order_id == "test_123"
        assert order.symbol == "AAPL"
        assert order.side == OrderSide.BUY
        assert order.quantity == Decimal("100")
    
    def test_order_result_model(self):
        """OrderResult model holds broker response."""
        result = OrderResult(
            broker_order_id="BROKER_123",
            client_order_id="test_123",
            status=OrderStatus.FILLED,
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=Decimal("100"),
            filled_quantity=Decimal("100"),
            average_fill_price=Decimal("150.00"),
            time_in_force=TimeInForce.DAY,
        )
        
        assert result.broker_order_id == "BROKER_123"
        assert result.status == OrderStatus.FILLED
        assert result.filled_quantity == Decimal("100")
    
    def test_position_model(self):
        """Position model holds position data."""
        position = Position(
            symbol="AAPL",
            quantity=Decimal("100"),
            average_entry_price=Decimal("150.00"),
            current_price=Decimal("155.00"),
            market_value=Decimal("15500"),
            unrealized_pnl=Decimal("500"),
        )
        
        assert position.symbol == "AAPL"
        assert position.unrealized_pnl == Decimal("500")
    
    def test_account_model(self):
        """Account model holds account info."""
        account = Account(
            account_id="ACCT123",
            cash=Decimal("50000"),
            portfolio_value=Decimal("100000"),
            buying_power=Decimal("100000"),
            equity=Decimal("100000"),
            status="ACTIVE",
        )
        
        assert account.account_id == "ACCT123"
        assert account.portfolio_value == Decimal("100000")
    
    def test_broker_error_contains_details(self):
        """BrokerError can contain error code and order ID."""
        error = BrokerError(
            message="Insufficient funds",
            code="INSUFFICIENT_FUNDS",
            order_id="ORDER_123",
        )
        
        assert str(error) == "Insufficient funds"
        assert error.code == "INSUFFICIENT_FUNDS"
        assert error.order_id == "ORDER_123"


# ============================================================================
# Order State Transitions Tests
# ============================================================================

class TestOrderStateTransitions:
    """Tests for order state machine transitions."""
    
    def test_valid_state_transitions_defined(self):
        """All valid state transitions are defined."""
        assert OrderState.PENDING in VALID_TRANSITIONS
        assert OrderState.SUBMITTED in VALID_TRANSITIONS
        assert OrderState.PARTIALLY_FILLED in VALID_TRANSITIONS
        assert OrderState.FILLED in VALID_TRANSITIONS
        assert OrderState.REJECTED in VALID_TRANSITIONS
        assert OrderState.CANCELLED in VALID_TRANSITIONS
    
    def test_pending_can_transition_to_submitted(self, oms: OrderManagementSystem, sample_order: dict):
        """PENDING order can transition to SUBMITTED."""
        order = oms.create_order(**sample_order)
        assert order.state == OrderState.PENDING
        
        order = oms.submit_order(
            client_order_id=sample_order["client_order_id"],
            broker_order_id="BROKER_123",
        )
        
        assert order.state == OrderState.SUBMITTED
        assert order.broker_order_id == "BROKER_123"
        assert order.submitted_at is not None
    
    def test_pending_can_transition_to_rejected(self, oms: OrderManagementSystem, sample_order: dict):
        """PENDING order can transition to REJECTED."""
        order = oms.create_order(**sample_order)
        
        order = oms.reject_order(
            client_order_id=sample_order["client_order_id"],
            reason="Risk check failed",
        )
        
        assert order.state == OrderState.REJECTED
        assert order.reject_reason == "Risk check failed"
    
    def test_submitted_can_transition_to_filled(self, oms: OrderManagementSystem, sample_order: dict):
        """SUBMITTED order can transition to FILLED."""
        order = oms.create_order(**sample_order)
        oms.submit_order(sample_order["client_order_id"], "BROKER_123")
        
        order = oms.fill_order(
            broker_order_id="BROKER_123",
            filled_quantity=sample_order["quantity"],
            average_fill_price=Decimal("150.25"),
            fees=Decimal("1.00"),
        )
        
        assert order.state == OrderState.FILLED
        assert order.filled_quantity == sample_order["quantity"]
        assert order.average_fill_price == Decimal("150.25")
        assert order.filled_at is not None
    
    def test_submitted_can_transition_to_partially_filled(self, oms: OrderManagementSystem, sample_order: dict):
        """SUBMITTED order can transition to PARTIALLY_FILLED."""
        order = oms.create_order(**sample_order)
        oms.submit_order(sample_order["client_order_id"], "BROKER_123")
        
        order = oms.fill_order(
            broker_order_id="BROKER_123",
            filled_quantity=Decimal("50"),  # Half filled
            average_fill_price=Decimal("150.25"),
        )
        
        assert order.state == OrderState.PARTIALLY_FILLED
        assert order.filled_quantity == Decimal("50")
    
    def test_partially_filled_can_transition_to_filled(self, oms: OrderManagementSystem, sample_order: dict):
        """PARTIALLY_FILLED order can transition to FILLED."""
        order = oms.create_order(**sample_order)
        oms.submit_order(sample_order["client_order_id"], "BROKER_123")
        
        # Partial fill
        oms.fill_order("BROKER_123", Decimal("50"), Decimal("150.25"))
        assert order.state == OrderState.PARTIALLY_FILLED
        
        # Complete fill
        order = oms.fill_order("BROKER_123", Decimal("100"), Decimal("150.25"))
        assert order.state == OrderState.FILLED
    
    def test_submitted_can_transition_to_cancelled(self, oms: OrderManagementSystem, sample_order: dict):
        """SUBMITTED order can be cancelled."""
        order = oms.create_order(**sample_order)
        oms.submit_order(sample_order["client_order_id"], "BROKER_123")
        
        order = oms.cancel_order(client_order_id=sample_order["client_order_id"])
        
        assert order.state == OrderState.CANCELLED
        assert order.cancelled_at is not None
    
    def test_filled_is_terminal_state(self, oms: OrderManagementSystem, sample_order: dict):
        """FILLED is a terminal state - cannot transition further."""
        order = oms.create_order(**sample_order)
        oms.submit_order(sample_order["client_order_id"], "BROKER_123")
        oms.fill_order("BROKER_123", sample_order["quantity"], Decimal("150.25"))
        
        assert order.is_terminal() is True
        assert VALID_TRANSITIONS[OrderState.FILLED] == set()
    
    def test_rejected_is_terminal_state(self, oms: OrderManagementSystem, sample_order: dict):
        """REJECTED is a terminal state."""
        order = oms.create_order(**sample_order)
        oms.reject_order(sample_order["client_order_id"], "Test rejection")
        
        assert order.is_terminal() is True
        assert VALID_TRANSITIONS[OrderState.REJECTED] == set()
    
    def test_cancelled_is_terminal_state(self, oms: OrderManagementSystem, sample_order: dict):
        """CANCELLED is a terminal state."""
        order = oms.create_order(**sample_order)
        oms.submit_order(sample_order["client_order_id"], "BROKER_123")
        oms.cancel_order(client_order_id=sample_order["client_order_id"])
        
        assert order.is_terminal() is True
        assert VALID_TRANSITIONS[OrderState.CANCELLED] == set()
    
    def test_invalid_transition_raises_error(self, oms: OrderManagementSystem, sample_order: dict):
        """Invalid state transitions raise InvalidStateTransitionError."""
        order = oms.create_order(**sample_order)
        oms.submit_order(sample_order["client_order_id"], "BROKER_123")
        oms.fill_order("BROKER_123", sample_order["quantity"], Decimal("150.25"))
        
        # Cannot cancel a filled order
        with pytest.raises(InvalidStateTransitionError):
            oms.cancel_order(client_order_id=sample_order["client_order_id"])


# ============================================================================
# Order Idempotency Tests
# ============================================================================

class TestOrderIdempotency:
    """Tests for order idempotency (unique client_order_id)."""
    
    def test_duplicate_client_order_id_returns_existing(self, oms: OrderManagementSystem, sample_order: dict):
        """Creating order with existing client_order_id returns existing order."""
        # Create first order
        order1 = oms.create_order(**sample_order)
        
        # Try to create duplicate
        order2 = oms.create_order(**sample_order)
        
        # Should return the same order (idempotent behavior)
        assert order1.internal_id == order2.internal_id
        assert order1.client_order_id == order2.client_order_id
    
    def test_has_order_checks_idempotency(self, oms: OrderManagementSystem, sample_order: dict):
        """has_order method checks if order exists."""
        assert oms.has_order(sample_order["client_order_id"]) is False
        
        oms.create_order(**sample_order)
        
        assert oms.has_order(sample_order["client_order_id"]) is True
    
    def test_different_client_order_ids_create_separate_orders(self, oms: OrderManagementSystem):
        """Different client_order_ids create separate orders."""
        order1 = oms.create_order(
            client_order_id="order_1",
            strategy_id="test",
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            order_type="MARKET",
        )
        
        order2 = oms.create_order(
            client_order_id="order_2",
            strategy_id="test",
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            order_type="MARKET",
        )
        
        assert order1.internal_id != order2.internal_id
        assert order1.client_order_id != order2.client_order_id
    
    def test_generated_client_order_id_format(self, oms: OrderManagementSystem):
        """Generated client_order_id has expected format."""
        client_id = oms.generate_client_order_id("strategy_v1", "AAPL")
        
        # Format: {strategy_id}_{symbol}_{timestamp}_{uuid}
        parts = client_id.split("_")
        assert parts[0] == "strategy"
        assert "v1" in parts[1]
        assert "AAPL" in client_id
    
    def test_order_retrieved_by_client_id(self, oms: OrderManagementSystem, sample_order: dict):
        """Order can be retrieved by client_order_id."""
        original = oms.create_order(**sample_order)
        
        retrieved = oms.get_order_by_client_id(sample_order["client_order_id"])
        
        assert retrieved.internal_id == original.internal_id
    
    def test_order_not_found_raises_error(self, oms: OrderManagementSystem):
        """OrderNotFoundError raised for non-existent order."""
        with pytest.raises(OrderNotFoundError):
            oms.get_order_by_client_id("nonexistent")


# ============================================================================
# Position Tracking Tests
# ============================================================================

class TestPositionTracking:
    """Tests for position tracking in OMS."""
    
    def test_open_orders_tracked(self, oms: OrderManagementSystem, sample_order: dict):
        """Open orders are tracked correctly."""
        oms.create_order(**sample_order)
        
        open_orders = oms.get_open_orders()
        assert len(open_orders) == 1
        assert open_orders[0].client_order_id == sample_order["client_order_id"]
    
    def test_filled_orders_not_in_open_orders(self, oms: OrderManagementSystem, sample_order: dict):
        """Filled orders are not in open orders list."""
        oms.create_order(**sample_order)
        oms.submit_order(sample_order["client_order_id"], "BROKER_123")
        oms.fill_order("BROKER_123", sample_order["quantity"], Decimal("150.25"))
        
        open_orders = oms.get_open_orders()
        assert len(open_orders) == 0
    
    def test_orders_tracked_by_strategy(self, oms: OrderManagementSystem):
        """Orders can be retrieved by strategy_id."""
        oms.create_order(
            client_order_id="order_1",
            strategy_id="strategy_a",
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            order_type="MARKET",
        )
        
        oms.create_order(
            client_order_id="order_2",
            strategy_id="strategy_b",
            symbol="MSFT",
            side="BUY",
            quantity=Decimal("50"),
            order_type="MARKET",
        )
        
        strategy_a_orders = oms.get_orders_by_strategy("strategy_a")
        assert len(strategy_a_orders) == 1
        assert strategy_a_orders[0].strategy_id == "strategy_a"
    
    def test_remaining_quantity_calculated(self, oms: OrderManagementSystem, sample_order: dict):
        """Remaining quantity is calculated correctly."""
        order = oms.create_order(**sample_order)
        oms.submit_order(sample_order["client_order_id"], "BROKER_123")
        
        # Partial fill
        order = oms.fill_order("BROKER_123", Decimal("30"), Decimal("150.25"))
        
        assert order.remaining_quantity() == Decimal("70")
    
    def test_cancel_all_open_orders(self, oms: OrderManagementSystem):
        """All open orders can be cancelled at once."""
        # Create multiple orders
        for i in range(3):
            oms.create_order(
                client_order_id=f"order_{i}",
                strategy_id="test",
                symbol="AAPL",
                side="BUY",
                quantity=Decimal("100"),
                order_type="MARKET",
            )
            oms.submit_order(f"order_{i}", f"BROKER_{i}")
        
        cancelled = oms.cancel_all_open_orders()
        
        assert len(cancelled) == 3
        assert all(o.state == OrderState.CANCELLED for o in cancelled)
    
    def test_cancel_all_open_orders_by_strategy(self, oms: OrderManagementSystem):
        """Cancel all open orders for specific strategy."""
        # Strategy A orders
        for i in range(2):
            oms.create_order(
                client_order_id=f"a_order_{i}",
                strategy_id="strategy_a",
                symbol="AAPL",
                side="BUY",
                quantity=Decimal("100"),
                order_type="MARKET",
            )
            oms.submit_order(f"a_order_{i}", f"BROKER_A_{i}")
        
        # Strategy B orders
        oms.create_order(
            client_order_id="b_order",
            strategy_id="strategy_b",
            symbol="MSFT",
            side="BUY",
            quantity=Decimal("100"),
            order_type="MARKET",
        )
        oms.submit_order("b_order", "BROKER_B")
        
        # Cancel only strategy A
        cancelled = oms.cancel_all_open_orders(strategy_id="strategy_a")
        
        assert len(cancelled) == 2
        
        # Strategy B order should still be open
        strategy_b_open = oms.get_open_orders(strategy_id="strategy_b")
        assert len(strategy_b_open) == 1


# ============================================================================
# ManagedOrder Model Tests
# ============================================================================

class TestManagedOrderModel:
    """Tests for ManagedOrder model methods."""
    
    def test_is_terminal_for_terminal_states(self, oms: OrderManagementSystem, sample_order: dict):
        """is_terminal returns True for terminal states."""
        order = oms.create_order(**sample_order)
        oms.reject_order(sample_order["client_order_id"], "Test")
        
        assert order.is_terminal() is True
    
    def test_is_terminal_for_non_terminal_states(self, oms: OrderManagementSystem, sample_order: dict):
        """is_terminal returns False for non-terminal states."""
        order = oms.create_order(**sample_order)
        
        assert order.is_terminal() is False
        
        oms.submit_order(sample_order["client_order_id"], "BROKER_123")
        assert order.is_terminal() is False
    
    def test_is_open_for_open_states(self, oms: OrderManagementSystem, sample_order: dict):
        """is_open returns True for PENDING, SUBMITTED, PARTIALLY_FILLED."""
        order = oms.create_order(**sample_order)
        assert order.is_open() is True
        
        oms.submit_order(sample_order["client_order_id"], "BROKER_123")
        assert order.is_open() is True
        
        oms.fill_order("BROKER_123", Decimal("50"), Decimal("150.25"))
        assert order.is_open() is True
    
    def test_is_open_false_for_terminal_states(self, oms: OrderManagementSystem, sample_order: dict):
        """is_open returns False for terminal states."""
        order = oms.create_order(**sample_order)
        oms.submit_order(sample_order["client_order_id"], "BROKER_123")
        oms.fill_order("BROKER_123", sample_order["quantity"], Decimal("150.25"))
        
        assert order.is_open() is False


# ============================================================================
# Update from Broker Tests
# ============================================================================

class TestUpdateFromBroker:
    """Tests for updating order state from broker status."""
    
    def test_update_from_broker_fills_order(self, oms: OrderManagementSystem, sample_order: dict):
        """Order updated from broker fill notification."""
        oms.create_order(**sample_order)
        oms.submit_order(sample_order["client_order_id"], "BROKER_123")
        
        broker_result = OrderResult(
            broker_order_id="BROKER_123",
            client_order_id=sample_order["client_order_id"],
            status=OrderStatus.FILLED,
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=Decimal("100"),
            filled_quantity=Decimal("100"),
            average_fill_price=Decimal("150.50"),
            time_in_force=TimeInForce.DAY,
            filled_at=datetime.now(timezone.utc),
        )
        
        order = oms.update_from_broker(broker_result)
        
        assert order.state == OrderState.FILLED
        assert order.filled_quantity == Decimal("100")
        assert order.average_fill_price == Decimal("150.50")
    
    def test_update_from_broker_partial_fill(self, oms: OrderManagementSystem, sample_order: dict):
        """Order updated from broker partial fill notification."""
        oms.create_order(**sample_order)
        oms.submit_order(sample_order["client_order_id"], "BROKER_123")
        
        broker_result = OrderResult(
            broker_order_id="BROKER_123",
            client_order_id=sample_order["client_order_id"],
            status=OrderStatus.PARTIALLY_FILLED,
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=Decimal("100"),
            filled_quantity=Decimal("50"),
            average_fill_price=Decimal("150.25"),
            time_in_force=TimeInForce.DAY,
        )
        
        order = oms.update_from_broker(broker_result)
        
        assert order.state == OrderState.PARTIALLY_FILLED
        assert order.filled_quantity == Decimal("50")
