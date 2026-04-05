from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List

import pytest

from services.simulation.schemas import SimEvent, SimFill, SimOrder, SimResult
from services.simulation.orderbook.book import SimulatedOrderBook
from services.simulation.runner import SimulationRunner, SimStrategy
from services.simulation.execution.simulator import ExecutionConfig
from services.simulation.execution.fee_engine import FeeRegime
from services.simulation.adverse.selection import AdverseSelectionModel
from services.evaluation.metrics import compute_metrics

# ── Fixed base timestamp — NO datetime.now() or datetime.utcnow() ──────────────
BASE_TS = datetime(2026, 4, 1, 9, 0, 0, tzinfo=timezone.utc)
MKT_ID = "test-market-001"
TOK_ID = "test-token-yes"


# ── Synthetic event fixtures ──────────────────────────────────────────────────

def make_snapshot_event(offset_minutes: int) -> SimEvent:
    """Snapshot event with bids at 0.45/0.44/0.43 and asks at 0.55/0.56/0.57."""
    ts = BASE_TS + timedelta(minutes=offset_minutes)
    return SimEvent(
        event_id=f"snap-{offset_minutes}",
        timestamp=ts,
        event_type="snapshot",
        market_id=MKT_ID,
        token_id=TOK_ID,
        payload={
            "bids": [["0.45", "100"], ["0.44", "80"], ["0.43", "60"]],
            "asks": [["0.55", "100"], ["0.56", "80"], ["0.57", "60"]],
        },
    )


def make_trade_event(offset_seconds: int, side: str) -> SimEvent:
    """Trade event at mid-price (0.50), size 10."""
    ts = BASE_TS + timedelta(seconds=offset_seconds)
    return SimEvent(
        event_id=f"trade-{offset_seconds}-{side}",
        timestamp=ts,
        event_type="trade",
        market_id=MKT_ID,
        token_id=TOK_ID,
        payload={"side": side, "price": "0.50", "size": "10"},
    )


def build_synthetic_events() -> List[SimEvent]:
    """
    1 hour of synthetic events:
    - 12 snapshot events (one every 5 minutes)
    - 24 trade events (alternating BUY/SELL, one every 2.5 minutes)
    All timestamps pinned to fixed absolute values.
    """
    events: List[SimEvent] = []
    # Snapshots every 5 minutes
    for i in range(12):
        events.append(make_snapshot_event(offset_minutes=i * 5))
    # Trades every 2.5 minutes = 150 seconds
    for i in range(24):
        side = "BUY" if i % 2 == 0 else "SELL"
        events.append(make_trade_event(offset_seconds=i * 150, side=side))
    # Sort by (timestamp, event_id) — matches EventLoader determinism
    events.sort(key=lambda e: (e.timestamp, e.event_id))
    return events


# ── Simple strategy: on each trade event, submit one taker BUY + one taker SELL ──

class SimpleMMStrategy:
    """Passive market-making: on each trade event, submit taker orders."""
    strategy_id = "simple-mm"
    _order_idx = 0

    def generate_sim_orders(
        self, event: SimEvent, book: SimulatedOrderBook
    ) -> List[SimOrder]:
        if event.event_type != "trade":
            return []
        self.__class__._order_idx += 1
        idx = self.__class__._order_idx
        best_ask = book.best_ask()
        best_bid = book.best_bid()
        orders = []
        if best_ask is not None:
            orders.append(SimOrder(
                order_id=f"buy-{idx}",
                market_id=event.market_id,
                token_id=event.token_id,
                side="BUY",
                order_type="taker",
                price=best_ask,
                size=Decimal("5"),
                submit_time=event.timestamp,
                post_only=False,
            ))
        if best_bid is not None:
            orders.append(SimOrder(
                order_id=f"sell-{idx}",
                market_id=event.market_id,
                token_id=event.token_id,
                side="SELL",
                order_type="taker",
                price=best_bid,
                size=Decimal("5"),
                submit_time=event.timestamp,
                post_only=False,
            ))
        return orders


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def synthetic_events() -> List[SimEvent]:
    return build_synthetic_events()


@pytest.fixture
def execution_config() -> ExecutionConfig:
    return ExecutionConfig(
        network_delay_ms=0.0,
        delay_distribution="fixed",
        max_orders_per_second=100,
        stale_threshold=Decimal("0.10"),
        paper_mode=True,
        random_seed=42,
    )


@pytest.fixture
def fee_regime() -> FeeRegime:
    return FeeRegime.post_mar30_crypto()


@pytest.fixture
def adverse_selection() -> AdverseSelectionModel:
    return AdverseSelectionModel(random_seed=42)


def make_runner(events, config, regime, adverse) -> SimulationRunner:
    strategy = SimpleMMStrategy()
    strategy.__class__._order_idx = 0  # reset for each runner
    return SimulationRunner(
        events=events,
        strategy=strategy,
        execution_config=config,
        fee_regime=regime,
        adverse_selection=adverse,
        run_id="test-run-001",
    )


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_full_simulation_produces_fills(
    synthetic_events, execution_config, fee_regime, adverse_selection
):
    """Running the simulation produces fills and a valid SimResult."""
    runner = make_runner(synthetic_events, execution_config, fee_regime, adverse_selection)
    result = runner.run()

    assert isinstance(result, SimResult)
    assert result.fills is not None
    assert len(result.fills) > 0, "Expected at least one fill from the simple MM strategy"
    assert isinstance(result.total_pnl, Decimal)
    assert result.fill_count == len(result.fills)


def test_determinism_identical_results(
    synthetic_events, execution_config, fee_regime, adverse_selection
):
    """AC-1: Two SimulationRunner instances with identical params produce byte-identical SimResult."""
    # Reset strategy counter before each runner
    SimpleMMStrategy._order_idx = 0
    runner1 = make_runner(synthetic_events, execution_config, fee_regime, adverse_selection)
    SimpleMMStrategy._order_idx = 0
    runner2 = make_runner(synthetic_events, execution_config, fee_regime, adverse_selection)

    result1 = runner1.run()
    result2 = runner2.run()

    json1 = result1.model_dump_json()
    json2 = result2.model_dump_json()

    assert json1 == json2, "SimulationRunner.run() produced different output on identical inputs (AC-1 violated)"


def test_pnl_components_sum_to_total(
    synthetic_events, execution_config, fee_regime, adverse_selection
):
    """PnL components dict values sum to total_pnl (via PnLComponents.total property)."""
    runner = make_runner(synthetic_events, execution_config, fee_regime, adverse_selection)
    result = runner.run()

    pnl = result.pnl_components
    expected = (
        pnl.get("spread_capture", Decimal("0"))
        + pnl.get("inventory_drift", Decimal("0"))
        + pnl.get("maker_rebate", Decimal("0"))
        + pnl.get("liquidity_reward", Decimal("0"))
        - pnl.get("taker_fee", Decimal("0"))
        - pnl.get("ops_cost", Decimal("0"))
    )
    assert abs(result.total_pnl - expected) <= Decimal("0.001"), (
        f"total_pnl {result.total_pnl} does not match components sum {expected}"
    )


def test_evaluation_from_simulation_output(
    synthetic_events, execution_config, fee_regime, adverse_selection
):
    """
    Evaluation engine can process the simulation result.
    With only 1 data point (< 20 daily obs), sharpe_confidence must be 'low' (AC-7).
    """
    runner = make_runner(synthetic_events, execution_config, fee_regime, adverse_selection)
    result = runner.run()

    pnl_series = [result.total_pnl]
    metrics = compute_metrics(
        strategy_id="simple-mm",
        pnl_series=pnl_series,
        fills=result.fills,
        period_start=BASE_TS,
        period_end=BASE_TS + timedelta(hours=1),
    )

    assert metrics.total_pnl == result.total_pnl
    assert metrics.sharpe_confidence == "low", (
        f"Expected sharpe_confidence='low' with 1 data point, got {metrics.sharpe_confidence!r} (AC-7)"
    )
    assert metrics.data_points == 1
