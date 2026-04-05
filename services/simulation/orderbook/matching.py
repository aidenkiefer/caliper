from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from services.simulation.schemas import SimFill, SimOrder
from services.simulation.orderbook.book import SimulatedOrderBook


class OrderMatcher:
    """Polymarket matching rules: taker sweeps, post-only maker insertion."""

    def would_cross(self, order: SimOrder, book: SimulatedOrderBook) -> bool:
        """Return True if placing this order as a maker would immediately cross."""
        if order.side == "BUY":
            best_ask = book.best_ask()
            return best_ask is not None and order.price >= best_ask
        else:  # SELL
            best_bid = book.best_bid()
            return best_bid is not None and order.price <= best_bid

    def match_taker(
        self,
        order: SimOrder,
        book: SimulatedOrderBook,
        submit_time: datetime,
    ) -> List[SimFill]:
        """Execute a taker (marketable limit) order. Returns list of fills with slippage."""
        mid_at_submit = book.mid_price() or Decimal(0)
        fills = book.match_market(order)
        # Set slippage and mid_at_fill on each fill
        for fill in fills:
            fill.slippage_vs_mid = fill.fill_price - mid_at_submit
            fill.mid_at_fill = mid_at_submit
            fill.fill_time = submit_time
        return fills

    def match_maker(
        self,
        order: SimOrder,
        book: SimulatedOrderBook,
    ) -> Optional[SimFill]:
        """Post-only maker: place in book if it won't cross; return None (fill on future trade)."""
        if self.would_cross(order, book):
            return None  # Post-only rejection
        book.place_limit(order)
        return None  # Maker fills come from apply_trade events, not here
