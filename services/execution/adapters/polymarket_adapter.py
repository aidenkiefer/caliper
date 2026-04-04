"""
PolymarketAdapter — wraps Polymarket CLOB client under ExecutionAdapter.

Translates the unified Order schema into CLOB API calls. Order placement
is post-only by default (as required by Polymarket MM strategy).

Note: Polymarket uses prediction-share sizes (not dollar quantities).
  order.quantity = share count
  order.limit_price = USDC price per share (0.01–0.99)
"""

from decimal import Decimal
from typing import List, Optional

from services.execution.adapter import ExecutionAdapter
from services.execution.broker.base import (
    Account,
    Order,
    OrderResult,
    OrderSide,
    OrderStatus,
    OrderbookLevel,
    OrderbookSnapshot,
    Position,
    TimeInForce,
)
from services.polymarket.adapters.clob_client import CLOBClient
from services.polymarket.data_feed import DataFeed


class PolymarketAdapter(ExecutionAdapter):
    """
    ExecutionAdapter for Polymarket CLOB.

    Inventory and session PnL tracking are done by recorder.py — this adapter
    only handles order placement/cancellation and orderbook queries.
    """

    def __init__(self, clob_client: CLOBClient, data_feed: DataFeed) -> None:
        self._clob = clob_client
        self._feed = data_feed
        self._connected: bool = True

    async def place_order(self, order: Order) -> OrderResult:
        """Submit a post-only limit order to the Polymarket CLOB."""
        if order.limit_price is None:
            raise ValueError(
                "Polymarket requires a limit_price on all orders; market orders are not supported"
            )
        side = "BUY" if order.side == OrderSide.BUY else "SELL"
        order_id = await self._clob.place_order(
            token_id=order.symbol,
            side=side,
            price=order.limit_price,
            size=order.quantity,
            post_only=True,
        )
        return OrderResult(
            broker_order_id=order_id,
            client_order_id=order.client_order_id,
            status=OrderStatus.SUBMITTED,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            time_in_force=TimeInForce.GTC,
        )

    async def cancel_order(self, order_id: str) -> bool:
        return await self._clob.cancel_order(order_id)

    async def get_positions(self) -> List[Position]:
        """Polymarket positions tracked via pm.* DB; not pulled from CLOB."""
        return []

    async def get_account(self) -> Account:
        """Minimal stub; USDC balance is from WalletManager."""
        return Account(
            account_id="polymarket",
            cash=Decimal("0"),
            portfolio_value=Decimal("0"),
            buying_power=Decimal("0"),
            equity=Decimal("0"),
            status="active",
        )

    async def get_order_status(self, order_id: str) -> OrderResult:
        # CLOBClient does not expose a get_order() endpoint; raise until wired.
        raise NotImplementedError(
            "get_order_status is not yet implemented for Polymarket. "
            "Wire to CLOB GET /order/{order_id} when available."
        )

    async def get_orders(
        self, status: Optional[str] = None, limit: int = 100
    ) -> List[OrderResult]:
        return []

    async def get_orderbook(self, asset_id: str) -> OrderbookSnapshot:
        """
        Return a synthetic top-of-book snapshot from the data feed.

        Note: this feed represents a single Polymarket market at a time.
        The `asset_id` parameter is echoed in the snapshot but the data
        always comes from the feed's current market.
        """
        state = self._feed.get_current_state()
        bids, asks = [], []
        if state.midpoint is not None and state.spread is not None:
            half = state.spread / 2
            bids = [OrderbookLevel(price=state.midpoint - half, size=Decimal("100"))]
            asks = [OrderbookLevel(price=state.midpoint + half, size=Decimal("100"))]
        return OrderbookSnapshot(asset_id=asset_id, bids=bids, asks=asks)

    def is_connected(self) -> bool:
        return self._connected

    def is_paper(self) -> bool:
        return False
