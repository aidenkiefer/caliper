"""
AlpacaAdapter — wraps the existing AlpacaClient under ExecutionAdapter.

The existing AlpacaClient in services/execution/broker/alpaca.py is kept
intact; this adapter re-exposes it through the unified interface and
adds a stub get_orderbook() (to be wired to Alpaca quotes endpoint later).
"""

from typing import List, Optional

from services.execution.adapter import ExecutionAdapter
from services.execution.broker.alpaca import AlpacaClient
from services.execution.broker.base import (
    Account,
    Order,
    OrderResult,
    OrderbookSnapshot,
    Position,
)


class AlpacaAdapter(ExecutionAdapter):
    """ExecutionAdapter backed by the Alpaca paper/live API."""

    def __init__(self, client: AlpacaClient) -> None:
        self._client = client

    async def place_order(self, order: Order) -> OrderResult:
        return await self._client.place_order(order)

    async def cancel_order(self, order_id: str) -> bool:
        return await self._client.cancel_order(order_id)

    async def get_positions(self) -> List[Position]:
        return await self._client.get_positions()

    async def get_account(self) -> Account:
        return await self._client.get_account()

    async def get_order_status(self, order_id: str) -> OrderResult:
        return await self._client.get_order_status(order_id)

    async def get_orders(
        self, status: Optional[str] = None, limit: int = 100
    ) -> List[OrderResult]:
        return await self._client.get_orders(status=status, limit=limit)

    async def get_orderbook(self, asset_id: str) -> OrderbookSnapshot:
        # TODO: wire to Alpaca latest quote endpoint (alpaca-py TradingClient.get_latest_quote)
        return OrderbookSnapshot(asset_id=asset_id, bids=[], asks=[])

    def is_connected(self) -> bool:
        return self._client.is_connected()

    def is_paper(self) -> bool:
        return self._client.is_paper()
