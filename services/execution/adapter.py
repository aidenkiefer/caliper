"""
Market-agnostic ExecutionAdapter ABC.

Both AlpacaAdapter and PolymarketAdapter implement this interface so the
portfolio layer and risk manager can dispatch orders without knowing the
underlying venue.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from services.execution.broker.base import (
    Account,
    Order,
    OrderResult,
    OrderbookSnapshot,
    Position,
)


class ExecutionAdapter(ABC):
    """
    Unified execution interface for any market.

    Implementations:
    - services/execution/adapters/alpaca_adapter.py  (equities)
    - services/execution/adapters/polymarket_adapter.py  (prediction markets)
    """

    @abstractmethod
    async def place_order(self, order: Order) -> OrderResult:
        """Place an order on the venue."""
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order. Returns True on success."""
        pass

    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """Return all open positions."""
        pass

    @abstractmethod
    async def get_account(self) -> Account:
        """Return account balance and status."""
        pass

    @abstractmethod
    async def get_order_status(self, order_id: str) -> OrderResult:
        """Poll status for a specific order."""
        pass

    @abstractmethod
    async def get_orders(
        self, status: Optional[str] = None, limit: int = 100
    ) -> List[OrderResult]:
        """Return recent orders, optionally filtered by status."""
        pass

    @abstractmethod
    async def get_orderbook(self, asset_id: str) -> OrderbookSnapshot:
        """
        Return a top-of-book snapshot.

        For equity venues this returns bid/ask from the quote feed.
        For Polymarket CLOB this returns the YES-token order book.
        """
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """True if the adapter has an active venue connection."""
        pass

    @abstractmethod
    def is_paper(self) -> bool:
        """True if orders go to a paper/sandbox environment."""
        pass
