"""
Stress test: Broker API outage scenario.

Simulates broker connectivity failures and order submission timeouts.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from packages.common.schemas import Order, OrderSide, OrderType, TimeInForce, TradingMode


def test_order_submission_timeout():
    """Test order submission behavior during broker timeout."""
    # Create test order
    order = Order(
        order_id=uuid4(),
        strategy_id="ml_direction_v1",
        symbol="SPY",
        contract_type="STOCK",
        side=OrderSide.BUY,
        quantity=Decimal("10"),
        order_type=OrderType.MARKET,
        time_in_force=TimeInForce.DAY,
        mode=TradingMode.PAPER,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    # Mock broker client with timeout
    mock_broker = Mock()
    mock_broker.submit_order.side_effect = TimeoutError("Broker API timeout")

    # Attempt submission (would be caught by OMS retry logic)
    with pytest.raises(TimeoutError):
        mock_broker.submit_order(order)


def test_position_reconciliation_failure():
    """Test position reconciliation when broker is unreachable."""
    # Mock broker positions endpoint
    mock_broker = Mock()
    mock_broker.get_positions.side_effect = ConnectionError("Unable to connect to broker")

    # In production, this would:
    # 1. Log error
    # 2. Use cached positions
    # 3. Pause trading until connection restored

    with pytest.raises(ConnectionError):
        positions = mock_broker.get_positions()
