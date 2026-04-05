from __future__ import annotations

import logging
from typing import Callable, List

from services.simulation.schemas import SimEvent, SimFill, SimOrder
from services.simulation.orderbook.book import SimulatedOrderBook
from services.simulation.orderbook.matching import OrderMatcher
from services.simulation.execution.simulator import ExecutionSimulator
from services.simulation.adverse.selection import AdverseSelectionModel

logger = logging.getLogger(__name__)


class ReplayEngine:
    """
    Processes a sorted stream of SimEvent objects, applies each to the order book,
    and routes strategy orders through the ExecutionSimulator.

    Determinism: processes events sequentially, no asyncio, no threads.
    Identical events + identical simulator seed → identical fills.
    """

    def __init__(
        self,
        book: SimulatedOrderBook,
        matcher: OrderMatcher,
        execution_simulator: ExecutionSimulator,
        adverse_selection: AdverseSelectionModel,
        strategy_callback: Callable[[SimEvent, SimulatedOrderBook], List[SimOrder]],
    ) -> None:
        self.book = book
        self.matcher = matcher
        self.execution_simulator = execution_simulator
        self.adverse_selection = adverse_selection
        self.strategy_callback = strategy_callback
        self._submitted_count = 0

    def run(self, events: List[SimEvent]) -> List[SimFill]:
        """
        Process all events in order. For each event:
        1. Apply to book (snapshot/trade/cancel)
        2. Call strategy_callback → List[SimOrder]
        3. Submit each order through execution_simulator → fills
        Returns all accumulated fills.
        """
        all_fills: List[SimFill] = []

        for event in events:
            # Apply event to book
            if event.event_type == "snapshot":
                self.book.apply_snapshot(event)
            elif event.event_type == "trade":
                self.book.apply_trade(event)
            elif event.event_type == "cancel":
                self.book.apply_cancel(event)
            else:
                logger.warning(
                    "Unknown event_type %r at %s — skipping",
                    event.event_type,
                    event.timestamp,
                )
                continue

            # Check book not empty for non-snapshot events
            if (
                event.event_type != "snapshot"
                and self.book.best_bid() is None
                and self.book.best_ask() is None
            ):
                logger.warning(
                    "Book empty at %s when applying %r event",
                    event.timestamp,
                    event.event_type,
                )

            # Strategy generates orders
            try:
                orders = self.strategy_callback(event, self.book)
            except Exception as exc:
                logger.warning(
                    "Strategy callback error at %s: %s", event.timestamp, exc
                )
                orders = []

            # Submit each order
            for order in orders:
                self._submitted_count += 1
                _receive_time, fills = self.execution_simulator.submit(order)
                if fills:
                    all_fills.extend(fills)

        return all_fills

    @property
    def submitted_count(self) -> int:
        return self._submitted_count
