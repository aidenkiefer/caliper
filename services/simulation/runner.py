from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from services.simulation.schemas import SimEvent, SimFill, SimOrder, SimResult, PnLComponents
from services.simulation.orderbook.book import SimulatedOrderBook
from services.simulation.orderbook.matching import OrderMatcher
from services.simulation.execution.simulator import ExecutionConfig, ExecutionSimulator
from services.simulation.execution.fee_engine import FeeEngine, FeeRegime
from services.simulation.adverse.selection import AdverseSelectionModel
from services.simulation.replay.engine import ReplayEngine


@runtime_checkable
class SimStrategy(Protocol):
    def generate_sim_orders(
        self, event: SimEvent, book: SimulatedOrderBook
    ) -> List[SimOrder]: ...


class SimulationRunner:
    """
    High-level entry point: assembles all components and runs a full simulation.

    AC-1 Determinism: run() called twice on the same instance produces byte-identical SimResult.
    Achieved by: seeded RNG in ExecutionConfig, no wall-clock calls, deterministic fill IDs.
    """

    def __init__(
        self,
        events: List[SimEvent],
        strategy: SimStrategy,
        execution_config: ExecutionConfig,
        fee_regime: FeeRegime,
        adverse_selection: AdverseSelectionModel,
        lr_pool_per_hour: Decimal = Decimal("50"),
        run_id: Optional[str] = None,
    ) -> None:
        self.events = events
        self.strategy = strategy
        self.execution_config = execution_config
        self.fee_regime = fee_regime
        self.adverse_selection = adverse_selection
        self.lr_pool_per_hour = lr_pool_per_hour
        self.run_id = run_id or str(uuid.UUID(int=0))  # deterministic default

    def run(self) -> SimResult:
        """
        Run the full simulation. Deterministic: same inputs + same seed → same output.
        """
        # Fresh components each call for determinism (re-seeded RNG)
        book = SimulatedOrderBook()
        matcher = OrderMatcher()
        fee_engine = FeeEngine(self.fee_regime, self.lr_pool_per_hour)
        execution_sim = ExecutionSimulator(book, matcher, fee_engine, self.execution_config)
        adverse = AdverseSelectionModel(
            baseline_informed=self.adverse_selection.baseline_informed,
            peak_informed=self.adverse_selection.peak_informed,
            ramp_start_minutes=self.adverse_selection.ramp_start_minutes,
            random_seed=self.adverse_selection.random_seed,
        )

        engine = ReplayEngine(
            book=book,
            matcher=matcher,
            execution_simulator=execution_sim,
            adverse_selection=adverse,
            strategy_callback=self.strategy.generate_sim_orders,
        )

        fills = engine.run(self.events)

        # Compute PnL components
        mark_prices = [f.mid_at_fill for f in fills]
        pnl_components = fee_engine.compute_pnl_components(fills, mark_prices)

        # Compute statistics
        fill_count = len(fills)
        submitted = max(engine.submitted_count, 1)
        fill_rate = Decimal(fill_count) / Decimal(submitted)
        maker_fills = sum(1 for f in fills if f.maker_fill)
        maker_fill_rate = Decimal(maker_fills) / Decimal(max(fill_count, 1))

        # Serialize PnL components as Dict[str, Decimal]
        pnl_dict: Dict[str, Decimal] = {
            "spread_capture": pnl_components.spread_capture,
            "inventory_drift": pnl_components.inventory_drift,
            "maker_rebate": pnl_components.maker_rebate,
            "liquidity_reward": pnl_components.liquidity_reward,
            "taker_fee": pnl_components.taker_fee,
            "ops_cost": pnl_components.ops_cost,
        }

        start_time = self.events[0].timestamp if self.events else datetime(2000, 1, 1)
        end_time = self.events[-1].timestamp if self.events else datetime(2000, 1, 1)

        return SimResult(
            run_id=self.run_id,
            strategy_id=getattr(self.strategy, "strategy_id", "unknown"),
            market_id=self.events[0].market_id if self.events else "",
            start_time=start_time,
            end_time=end_time,
            fills=fills,
            pnl_components=pnl_dict,
            total_pnl=pnl_components.total,
            fill_count=fill_count,
            fill_rate=fill_rate,
            maker_fill_rate=maker_fill_rate,
            config={
                "network_delay_ms": self.execution_config.network_delay_ms,
                "delay_distribution": self.execution_config.delay_distribution,
                "max_orders_per_second": self.execution_config.max_orders_per_second,
                "paper_mode": self.execution_config.paper_mode,
                "random_seed": self.execution_config.random_seed,
            },
        )
