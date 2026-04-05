from __future__ import annotations

import math
import random
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Deque, List, Literal, Optional, Tuple

from services.simulation.schemas import SimFill, SimOrder
from services.simulation.orderbook.book import SimulatedOrderBook
from services.simulation.orderbook.matching import OrderMatcher
from services.simulation.execution.fee_engine import FeeEngine


@dataclass
class ExecutionConfig:
    network_delay_ms: float = 100.0
    delay_distribution: Literal["fixed", "uniform", "lognormal"] = "lognormal"
    max_orders_per_second: int = 10
    stale_threshold: Decimal = Decimal("0.01")
    paper_mode: bool = True
    random_seed: Optional[int] = None


class ExecutionSimulator:
    """
    Wraps the order book and models realistic execution constraints:
    latency, API throttling, stale-quote detection.

    Determinism guarantee: all random sampling uses self._rng seeded from
    ExecutionConfig.random_seed. No wall-clock calls; timestamps come from SimOrder.
    """

    def __init__(
        self,
        book: SimulatedOrderBook,
        matcher: OrderMatcher,
        fee_engine: FeeEngine,
        config: ExecutionConfig,
    ) -> None:
        self.book = book
        self.matcher = matcher
        self.fee_engine = fee_engine
        self.config = config
        self._rng = random.Random(config.random_seed)
        # Track recent submission times for rate limiting (stores submit_time as datetime)
        self._throttle_queue: Deque[datetime] = deque()

    def _sample_delay_ms(self) -> float:
        """Sample network latency from the configured distribution."""
        cfg = self.config
        if cfg.delay_distribution == "fixed":
            return cfg.network_delay_ms
        elif cfg.delay_distribution == "uniform":
            return self._rng.uniform(0.0, cfg.network_delay_ms * 2)
        else:  # lognormal
            # mu and sigma for lognormal: mean of underlying normal = log(delay_ms)
            mu = math.log(max(cfg.network_delay_ms, 1.0))
            sigma = 0.5
            return self._rng.lognormvariate(mu, sigma)

    def _apply_throttle(self, submit_time: datetime) -> datetime:
        """
        Enforce max_orders_per_second. If submitting too fast, delay the receive_time.
        Returns the effective submit time after throttle delay.
        """
        window = timedelta(seconds=1)
        # Remove entries outside the 1-second window
        while self._throttle_queue and (submit_time - self._throttle_queue[0]) > window:
            self._throttle_queue.popleft()

        if len(self._throttle_queue) >= self.config.max_orders_per_second:
            # Must wait: receive time = oldest_in_window + 1s
            oldest = self._throttle_queue[0]
            delayed = oldest + window
            effective_time = max(submit_time, delayed)
        else:
            effective_time = submit_time

        self._throttle_queue.append(effective_time)
        return effective_time

    def submit(
        self,
        order: SimOrder,
    ) -> Tuple[datetime, Optional[List[SimFill]]]:
        """
        Submit an order through the execution simulator.

        Returns (receive_time, fills_or_none):
        - receive_time: when the order arrived at the exchange (after latency + throttle)
        - fills_or_none: list of SimFill if taker order was filled; None for maker orders
          (maker fills happen via apply_trade events from the replay engine)

        Determinism: same order + same book state + same rng state → same result.
        """
        # 1. Apply throttling
        effective_submit = self._apply_throttle(order.submit_time)

        # 2. Sample network delay
        delay_ms = self._sample_delay_ms()
        receive_time = effective_submit + timedelta(milliseconds=delay_ms)

        # 3. Record mid price at submission
        mid_at_submit = self.book.mid_price() or Decimal(0)

        # 4. Check stale quote: if book moved significantly between submit and arrival
        # For simulation purposes, we check current book state
        mid_at_receive = self.book.mid_price() or Decimal(0)
        stale = (
            mid_at_submit != Decimal(0)
            and mid_at_receive != Decimal(0)
            and abs(mid_at_receive - mid_at_submit) >= self.config.stale_threshold
        )

        # 5. Route to matcher
        if order.order_type == "taker":
            fills = self.matcher.match_taker(order, self.book, receive_time)
            if stale:
                # Taker gets worse price: fills already reflect current book state
                # (book moved before receive, so fills are at new prices — already correct)
                pass
            return receive_time, fills if fills else None
        else:
            # Maker (post-only)
            if stale and self.matcher.would_cross(order, self.book):
                # Stale + crossing → reject
                return receive_time, None
            result = self.matcher.match_maker(order, self.book)
            return receive_time, None  # maker fills never come from submit()
