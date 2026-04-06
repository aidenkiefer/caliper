# Ticket 13-07: Replay Engine + SimulationRunner

## Task

Implement `ReplayEngine` (drives the simulation clock, applies events to the order book, routes strategy orders through `ExecutionSimulator`) and `SimulationRunner` (ties all components together into a single end-to-end simulation run). This is the core integration point for the simulation engine. AC-1 determinism is enforced here.

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- Create: `services/simulation/replay/engine.py`
- Create: `services/simulation/runner.py`
- Modify: `services/simulation/replay/__init__.py` (add ReplayEngine export)
- Modify: `services/simulation/__init__.py` (add SimulationRunner export)
- Modify: `docs/plans/PROGRESS.md` (completion note)

### Required read-only references
- `docs/plans/specs/sprint-13-simulation-evaluation-spec.md` (§ ReplayEngine, § SimulationRunner, § Validation Layer — Determinism check)
- `services/simulation/schemas.py` (SimEvent, SimOrder, SimFill, SimResult, PnLComponents)
- `services/simulation/orderbook/book.py` (SimulatedOrderBook)
- `services/simulation/orderbook/matching.py` (OrderMatcher)
- `services/simulation/execution/simulator.py` (ExecutionSimulator, ExecutionConfig)
- `services/simulation/execution/fee_engine.py` (FeeEngine, FeeRegime)
- `services/simulation/adverse/selection.py` (AdverseSelectionModel)
- `services/simulation/replay/loader.py` (EventLoader)

## Done criteria

### `services/simulation/replay/engine.py` — `ReplayEngine`

**Purpose:** Processes a sorted stream of `SimEvent` objects in timestamp order, applying each to the `SimulatedOrderBook`, and calling the strategy callback for each event to generate `SimOrder` objects.

```python
class ReplayEngine:
    def __init__(
        self,
        book: SimulatedOrderBook,
        matcher: OrderMatcher,
        execution_simulator: ExecutionSimulator,
        adverse_selection: AdverseSelectionModel,
        strategy_callback: Callable[[SimEvent, SimulatedOrderBook], List[SimOrder]],
    ): ...
```

**`run(events: List[SimEvent]) -> List[SimFill]`**:
1. For each event in `events` (already sorted):
   a. Route to book: `apply_snapshot`, `apply_trade`, or `apply_cancel` based on `event_type`.
   b. Call `strategy_callback(event, book)` → `List[SimOrder]`.
   c. For each order: call `execution_simulator.submit(order)` → `(receive_time, fills)`. Collect all fills.
2. Return all accumulated fills.

**Gap handling:** If an event's `event_type` is not one of the three known types, log a warning and skip (do not raise). If book state is empty when a non-snapshot event arrives, log a warning (can't apply trade to empty book).

**Determinism:** Engine processes events sequentially. No asyncio, no threads. Identical `events` list + identical `execution_simulator` seed → identical fills list.

### `services/simulation/runner.py` — `SimulationRunner`

**Purpose:** High-level entry point that assembles all components and runs a full simulation.

```python
class SimulationRunner:
    def __init__(
        self,
        events: List[SimEvent],
        strategy: Any,             # has .generate_sim_orders(event, book) -> List[SimOrder]
        execution_config: ExecutionConfig,
        fee_regime: FeeRegime,
        adverse_selection: AdverseSelectionModel,
        lr_pool_per_hour: Decimal = Decimal("50"),
        run_id: Optional[str] = None,
    ): ...
```

**`run() -> SimResult`**:
1. Initialize `SimulatedOrderBook`, `OrderMatcher`, `FeeEngine(fee_regime, lr_pool_per_hour)`, `ExecutionSimulator(book, matcher, fee_engine, execution_config)`.
2. Create `ReplayEngine` with the above components and `strategy.generate_sim_orders` as callback.
3. Call `engine.run(self.events)` → `fills: List[SimFill]`.
4. Compute `PnLComponents` via `fee_engine.compute_pnl_components(fills, mark_prices=[f.mid_at_fill for f in fills])`.
5. Compute statistics: `fill_count`, `fill_rate = len(fills) / max(submitted_orders, 1)`, `maker_fill_rate`.
6. Return `SimResult` with all fields populated. `run_id` defaults to `str(uuid.uuid4())`.

**AC-1 determinism guarantee:**
- `SimulationRunner.run()` called twice on the same instance produces byte-identical `SimResult`.
- This means: fills list is identical, PnL components are identical, all Decimal values are identical.
- Achieved by: using `execution_config.random_seed`, no wall-clock calls, no `uuid.uuid4()` in fill records (use deterministic IDs like `f"{run_id}-fill-{i}"`).

**`SimStrategy` protocol** (define in `runner.py`):
```python
class SimStrategy(Protocol):
    def generate_sim_orders(self, event: SimEvent, book: SimulatedOrderBook) -> List[SimOrder]: ...
```
