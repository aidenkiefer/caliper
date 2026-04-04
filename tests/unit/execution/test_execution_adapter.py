from decimal import Decimal
from unittest.mock import MagicMock
import pytest
from services.execution.adapter import ExecutionAdapter
from services.execution.broker.base import OrderbookSnapshot, OrderbookLevel


def test_orderbook_snapshot_shape():
    snap = OrderbookSnapshot(
        asset_id="AAPL",
        bids=[OrderbookLevel(price=Decimal("149.50"), size=Decimal("100"))],
        asks=[OrderbookLevel(price=Decimal("150.00"), size=Decimal("50"))],
    )
    assert snap.best_bid == Decimal("149.50")
    assert snap.best_ask == Decimal("150.00")
    assert snap.midpoint == Decimal("149.75")
    assert snap.spread == Decimal("0.50")


def test_orderbook_snapshot_empty_side():
    snap = OrderbookSnapshot(asset_id="AAPL", bids=[], asks=[])
    assert snap.best_bid is None
    assert snap.best_ask is None
    assert snap.midpoint is None


class ConcreteAdapter(ExecutionAdapter):
    """Minimal concrete implementation for ABC testing."""

    async def place_order(self, order): return MagicMock()
    async def cancel_order(self, order_id): return True
    async def get_positions(self): return []
    async def get_account(self): return MagicMock()
    async def get_order_status(self, order_id): return MagicMock()
    async def get_orders(self, status=None, limit=100): return []
    async def get_orderbook(self, asset_id): return OrderbookSnapshot(asset_id=asset_id, bids=[], asks=[])
    def is_connected(self): return True
    def is_paper(self): return True


@pytest.mark.asyncio
async def test_concrete_adapter_implements_interface():
    adapter = ConcreteAdapter()
    snap = await adapter.get_orderbook("AAPL")
    assert snap.asset_id == "AAPL"
