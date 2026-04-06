# Ticket 13-04: Execution Simulator

## Task

Implement `ExecutionSimulator` which wraps the order book and models realistic execution constraints: configurable network latency (fixed/uniform/lognormal), API throttling, stale-quote detection, and race condition resolution.

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- Create: `services/simulation/execution/simulator.py`
- Modify: `services/simulation/execution/__init__.py` (add ExecutionConfig, ExecutionSimulator exports)
- Modify: `docs/plans/PROGRESS.md` (completion note)

### Required read-only references
- `docs/plans/specs/sprint-13-simulation-evaluation-spec.md` (§ ExecutionSimulator)
- `services/simulation/schemas.py` (SimOrder, SimFill)
- `services/simulation/orderbook/book.py` (SimulatedOrderBook)
- `services/simulation/orderbook/matching.py` (OrderMatcher)
- `services/simulation/execution/fee_engine.py` (FeeEngine)

## Done criteria

### `services/simulation/execution/simulator.py`

**`ExecutionConfig`** (dataclass):
```python
@dataclass
class ExecutionConfig:
    network_delay_ms: float = 100.0
    delay_distribution: Literal["fixed", "uniform", "lognormal"] = "lognormal"
    max_orders_per_second: int = 10
    stale_threshold: Decimal = Decimal("0.01")
    paper_mode: bool = True
    random_seed: Optional[int] = None  # for determinism
```

**`ExecutionSimulator`**:
- `__init__(book: SimulatedOrderBook, matcher: OrderMatcher, fee_engine: FeeEngine, config: ExecutionConfig)`.
- `_rng: random.Random` initialized from `config.random_seed` (or a fixed default seed) — NEVER use `random.random()` directly (breaks determinism).
- `_sample_delay_ms() -> float`: samples from the configured distribution using `self._rng`. For "lognormal": `self._rng.lognormvariate(mu, sigma)` where mu=log(config.network_delay_ms), sigma=0.5.
- `_throttle_queue: deque` — tracks submission timestamps for rate limiting.
- `submit(order: SimOrder) -> Tuple[datetime, Optional[List[SimFill]]]`:
  1. Apply throttling: if submitting faster than `max_orders_per_second`, compute `receive_time` delay.
  2. Sample network delay → compute `receive_time = submit_time + timedelta(milliseconds=delay)`.
  3. Check stale quote: if `abs(book.mid_price() - mid_at_submit) >= stale_threshold`: for taker orders, execute at current (worse) book price; for maker post-only, re-evaluate crossing.
  4. Route to matcher: taker → `matcher.match_taker(order, book, receive_time)`, maker → `matcher.match_maker(order, book)`.
  5. Return `(receive_time, fills_or_none)`.
- Determinism guarantee: `submit()` called twice on identical state with same seed produces identical output.

All delay sampling uses `self._rng` exclusively. No `time.time()`, `datetime.now()`, or `random` module globals.
