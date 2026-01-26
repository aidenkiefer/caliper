"""
Execution Engine Service.

This service handles order execution for paper and live trading:
- BrokerClient interface with Alpaca adapter
- Order Management System (OMS) with state machine
- Position tracking and reconciliation
- Order idempotency via unique client_order_id
"""

from .broker.base import BrokerClient
from .broker.alpaca import AlpacaClient
from .oms import OrderManagementSystem, OrderState
from .reconciliation import PositionTracker, ReconciliationResult

__all__ = [
    "BrokerClient",
    "AlpacaClient",
    "OrderManagementSystem",
    "OrderState",
    "PositionTracker",
    "ReconciliationResult",
]
