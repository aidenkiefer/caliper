"""
Alpaca broker client implementation.

Supports both paper and live trading via Alpaca API.
"""

import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from .base import (
    Account,
    BrokerClient,
    BrokerError,
    InsufficientFundsError,
    Order,
    OrderNotFoundError,
    OrderResult,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    TimeInForce,
)


# Alpaca SDK imports (conditional to allow testing without dependency)
try:
    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import (
        GetOrdersRequest,
        LimitOrderRequest,
        MarketOrderRequest,
        StopLimitOrderRequest,
        StopOrderRequest,
    )
    from alpaca.trading.enums import (
        OrderSide as AlpacaOrderSide,
        OrderStatus as AlpacaOrderStatus,
        OrderType as AlpacaOrderType,
        TimeInForce as AlpacaTimeInForce,
        QueryOrderStatus,
    )
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False


# Status mapping from Alpaca to our standard format
ALPACA_STATUS_MAP = {
    "new": OrderStatus.SUBMITTED,
    "accepted": OrderStatus.ACCEPTED,
    "pending_new": OrderStatus.PENDING,
    "accepted_for_bidding": OrderStatus.SUBMITTED,
    "stopped": OrderStatus.SUBMITTED,
    "rejected": OrderStatus.REJECTED,
    "suspended": OrderStatus.SUBMITTED,
    "calculated": OrderStatus.SUBMITTED,
    "filled": OrderStatus.FILLED,
    "partially_filled": OrderStatus.PARTIALLY_FILLED,
    "canceled": OrderStatus.CANCELLED,
    "cancelled": OrderStatus.CANCELLED,
    "expired": OrderStatus.EXPIRED,
    "replaced": OrderStatus.CANCELLED,
    "pending_cancel": OrderStatus.SUBMITTED,
    "pending_replace": OrderStatus.SUBMITTED,
    "done_for_day": OrderStatus.SUBMITTED,
}


class AlpacaClient(BrokerClient):
    """
    Alpaca API client for paper and live trading.
    
    Uses alpaca-py SDK for API communication.
    Paper trading endpoint: https://paper-api.alpaca.markets
    Live trading endpoint: https://api.alpaca.markets
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        paper: bool = True,
    ):
        """
        Initialize Alpaca client.
        
        Args:
            api_key: Alpaca API key (or from ALPACA_API_KEY env var)
            secret_key: Alpaca secret key (or from ALPACA_SECRET_KEY env var)
            paper: If True, use paper trading endpoint
        """
        if not ALPACA_AVAILABLE:
            raise ImportError(
                "alpaca-py is not installed. Install with: pip install alpaca-py"
            )
        
        self._api_key = api_key or os.getenv("ALPACA_API_KEY")
        self._secret_key = secret_key or os.getenv("ALPACA_SECRET_KEY")
        self._paper = paper
        
        if not self._api_key or not self._secret_key:
            raise ValueError(
                "Alpaca API credentials required. Set ALPACA_API_KEY and "
                "ALPACA_SECRET_KEY environment variables or pass to constructor."
            )
        
        # Initialize Alpaca trading client
        self._client = TradingClient(
            api_key=self._api_key,
            secret_key=self._secret_key,
            paper=self._paper,
        )
        
        self._connected = False
        self._verify_connection()
    
    def _verify_connection(self) -> None:
        """Verify API connection by fetching account."""
        try:
            self._client.get_account()
            self._connected = True
        except Exception as e:
            self._connected = False
            raise BrokerError(f"Failed to connect to Alpaca: {str(e)}")
    
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._connected
    
    def is_paper(self) -> bool:
        """Check if using paper trading."""
        return self._paper
    
    def _map_order_side(self, side: OrderSide) -> "AlpacaOrderSide":
        """Map our OrderSide to Alpaca's."""
        return AlpacaOrderSide.BUY if side == OrderSide.BUY else AlpacaOrderSide.SELL
    
    def _map_time_in_force(self, tif: TimeInForce) -> "AlpacaTimeInForce":
        """Map our TimeInForce to Alpaca's."""
        mapping = {
            TimeInForce.DAY: AlpacaTimeInForce.DAY,
            TimeInForce.GTC: AlpacaTimeInForce.GTC,
            TimeInForce.IOC: AlpacaTimeInForce.IOC,
            TimeInForce.FOK: AlpacaTimeInForce.FOK,
        }
        return mapping[tif]
    
    def _convert_alpaca_order(self, alpaca_order) -> OrderResult:
        """Convert Alpaca order to our OrderResult."""
        status_str = str(alpaca_order.status.value).lower()
        status = ALPACA_STATUS_MAP.get(status_str, OrderStatus.SUBMITTED)
        
        # Parse side
        side = OrderSide.BUY if str(alpaca_order.side.value).lower() == "buy" else OrderSide.SELL
        
        # Parse time in force
        tif_str = str(alpaca_order.time_in_force.value).lower()
        tif_map = {"day": TimeInForce.DAY, "gtc": TimeInForce.GTC, "ioc": TimeInForce.IOC, "fok": TimeInForce.FOK}
        tif = tif_map.get(tif_str, TimeInForce.DAY)
        
        return OrderResult(
            broker_order_id=str(alpaca_order.id),
            client_order_id=alpaca_order.client_order_id or str(alpaca_order.id),
            status=status,
            symbol=alpaca_order.symbol,
            side=side,
            quantity=Decimal(str(alpaca_order.qty)),
            filled_quantity=Decimal(str(alpaca_order.filled_qty or 0)),
            average_fill_price=Decimal(str(alpaca_order.filled_avg_price)) if alpaca_order.filled_avg_price else None,
            limit_price=Decimal(str(alpaca_order.limit_price)) if alpaca_order.limit_price else None,
            stop_price=Decimal(str(alpaca_order.stop_price)) if alpaca_order.stop_price else None,
            time_in_force=tif,
            submitted_at=alpaca_order.submitted_at,
            filled_at=alpaca_order.filled_at,
            reject_reason=None,  # Alpaca doesn't provide this directly
        )
    
    async def place_order(self, order: Order) -> OrderResult:
        """
        Place an order with Alpaca.
        
        Args:
            order: Order to place
            
        Returns:
            OrderResult with broker order ID
        """
        try:
            # Build order request based on type
            if order.order_type == OrderType.MARKET:
                request = MarketOrderRequest(
                    symbol=order.symbol,
                    qty=float(order.quantity),
                    side=self._map_order_side(order.side),
                    time_in_force=self._map_time_in_force(order.time_in_force),
                    client_order_id=order.client_order_id,
                    extended_hours=order.extended_hours,
                )
            elif order.order_type == OrderType.LIMIT:
                if order.limit_price is None:
                    raise BrokerError("Limit price required for LIMIT orders")
                request = LimitOrderRequest(
                    symbol=order.symbol,
                    qty=float(order.quantity),
                    side=self._map_order_side(order.side),
                    time_in_force=self._map_time_in_force(order.time_in_force),
                    limit_price=float(order.limit_price),
                    client_order_id=order.client_order_id,
                    extended_hours=order.extended_hours,
                )
            elif order.order_type == OrderType.STOP:
                if order.stop_price is None:
                    raise BrokerError("Stop price required for STOP orders")
                request = StopOrderRequest(
                    symbol=order.symbol,
                    qty=float(order.quantity),
                    side=self._map_order_side(order.side),
                    time_in_force=self._map_time_in_force(order.time_in_force),
                    stop_price=float(order.stop_price),
                    client_order_id=order.client_order_id,
                )
            elif order.order_type == OrderType.STOP_LIMIT:
                if order.stop_price is None or order.limit_price is None:
                    raise BrokerError("Stop and limit prices required for STOP_LIMIT orders")
                request = StopLimitOrderRequest(
                    symbol=order.symbol,
                    qty=float(order.quantity),
                    side=self._map_order_side(order.side),
                    time_in_force=self._map_time_in_force(order.time_in_force),
                    stop_price=float(order.stop_price),
                    limit_price=float(order.limit_price),
                    client_order_id=order.client_order_id,
                )
            else:
                raise BrokerError(f"Unsupported order type: {order.order_type}")
            
            # Submit order
            alpaca_order = self._client.submit_order(request)
            return self._convert_alpaca_order(alpaca_order)
            
        except Exception as e:
            error_msg = str(e).lower()
            if "insufficient" in error_msg or "buying power" in error_msg:
                raise InsufficientFundsError(f"Insufficient funds: {str(e)}")
            raise BrokerError(f"Order placement failed: {str(e)}")
    
    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel a pending order.
        
        Args:
            order_id: Broker order ID
            
        Returns:
            True if cancellation successful
        """
        try:
            self._client.cancel_order_by_id(order_id)
            return True
        except Exception as e:
            if "not found" in str(e).lower():
                raise OrderNotFoundError(f"Order not found: {order_id}")
            raise BrokerError(f"Cancel failed: {str(e)}")
    
    async def get_positions(self) -> List[Position]:
        """Get all current positions."""
        try:
            alpaca_positions = self._client.get_all_positions()
            positions = []
            
            for pos in alpaca_positions:
                positions.append(Position(
                    symbol=pos.symbol,
                    quantity=Decimal(str(pos.qty)),
                    average_entry_price=Decimal(str(pos.avg_entry_price)),
                    current_price=Decimal(str(pos.current_price)) if pos.current_price else None,
                    market_value=Decimal(str(pos.market_value)) if pos.market_value else None,
                    unrealized_pnl=Decimal(str(pos.unrealized_pl)) if pos.unrealized_pl else None,
                    unrealized_pnl_pct=Decimal(str(pos.unrealized_plpc)) if pos.unrealized_plpc else None,
                    cost_basis=Decimal(str(pos.cost_basis)) if pos.cost_basis else None,
                    side=str(pos.side).lower() if hasattr(pos, 'side') else "long",
                ))
            
            return positions
            
        except Exception as e:
            raise BrokerError(f"Failed to fetch positions: {str(e)}")
    
    async def get_account(self) -> Account:
        """Get account information."""
        try:
            acct = self._client.get_account()
            
            return Account(
                account_id=str(acct.id),
                cash=Decimal(str(acct.cash)),
                portfolio_value=Decimal(str(acct.portfolio_value)),
                buying_power=Decimal(str(acct.buying_power)),
                equity=Decimal(str(acct.equity)),
                currency=acct.currency or "USD",
                status=str(acct.status),
                pattern_day_trader=acct.pattern_day_trader or False,
                trading_blocked=acct.trading_blocked or False,
                transfers_blocked=acct.transfers_blocked or False,
            )
            
        except Exception as e:
            raise BrokerError(f"Failed to fetch account: {str(e)}")
    
    async def get_order_status(self, order_id: str) -> OrderResult:
        """Get status of a specific order."""
        try:
            alpaca_order = self._client.get_order_by_id(order_id)
            return self._convert_alpaca_order(alpaca_order)
        except Exception as e:
            if "not found" in str(e).lower():
                raise OrderNotFoundError(f"Order not found: {order_id}")
            raise BrokerError(f"Failed to fetch order: {str(e)}")
    
    async def get_orders(
        self,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[OrderResult]:
        """Get list of orders."""
        try:
            # Map status filter
            query_status = None
            if status:
                status_lower = status.lower()
                if status_lower == "open":
                    query_status = QueryOrderStatus.OPEN
                elif status_lower == "closed":
                    query_status = QueryOrderStatus.CLOSED
                else:
                    query_status = QueryOrderStatus.ALL
            
            request = GetOrdersRequest(
                status=query_status,
                limit=limit,
            )
            
            alpaca_orders = self._client.get_orders(request)
            return [self._convert_alpaca_order(order) for order in alpaca_orders]
            
        except Exception as e:
            raise BrokerError(f"Failed to fetch orders: {str(e)}")
