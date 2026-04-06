# Sprint 13: Simulation + Evaluation Engine

**Version:** v2.3.0  
**Status:** Spec  
**Research sources:** `docs/research/backtesting-simulation.md`  
**Skills to load:** `backtesting-frameworks`, `quant-analyst`, `risk-metrics-calculation`, `python-testing-patterns`

---

## Overview

The existing `BacktestEngine` in `services/backtest/` was built for equity strategies running over daily OHLCV bars. It does not model CLOB order matching, partial fills, latency, fee/incentive accounting, or the Polymarket-specific microstructure that Sprint 12's feature pipeline now captures.

Sprint 13 builds two complementary systems:

1. **High-Fidelity CLOB Simulation Engine** — a deterministic replay engine for Polymarket historical data, with order book simulation, execution modeling (latency, partial fills, post-only semantics), and full fee/incentive accounting. This is the backtesting core for all Polymarket strategies.

2. **Evaluation Engine** — a unified metrics system that computes per-strategy performance across PnL decomposition, risk-adjusted ratios, regime breakdown, and baseline comparison. This extends the existing observability infrastructure and feeds the model fleet's capital allocation logic (Sprint 16).

These two systems are independent: the simulation engine produces fills and PnL records, and the evaluation engine consumes them. Either can be run in isolation.

---

## Goals

1. Build a deterministic CLOB replay engine that reproduces historical Polymarket orderbook evolution from stored event logs.
2. Model taker and maker order execution with configurable latency, partial fills, and post-only rejection.
3. Apply the exact Polymarket fee curve (with pre/post March 30 2026 regime support) and maker rebate/liquidity reward estimation.
4. Model adverse selection (toxic flow near market close) as a configurable parameter.
5. Build a validation layer that compares simulated outcomes to actual historical fills.
6. Build an evaluation engine that computes per-model, per-regime performance metrics and baseline comparisons.
7. Surface results in a structured `EvaluationReport` accessible via API.

---

## Part 1: CLOB Simulation Engine

### Location: `services/simulation/`

```
services/simulation/
├── __init__.py
├── replay/
│   ├── __init__.py
│   ├── engine.py         # ReplayEngine: reads events, drives simulation clock
│   └── loader.py         # EventLoader: reads from pm.* tables or flat files
├── orderbook/
│   ├── __init__.py
│   ├── book.py           # SimulatedOrderBook: full LOB with price-time priority
│   └── matching.py       # OrderMatcher: fill logic for taker/maker orders
├── execution/
│   ├── __init__.py
│   ├── simulator.py      # ExecutionSimulator: applies latency + routes to book
│   └── fee_engine.py     # FeeEngine: computes taker fees, maker rebates, LR credit
├── adverse/
│   ├── __init__.py
│   └── selection.py      # AdverseSelectionModel: time-varying informed flow fraction
├── schemas.py            # SimEvent, SimOrder, SimFill, SimResult Pydantic models
└── runner.py             # SimulationRunner: ties all components together
```

### Core Components

#### `EventLoader`

Reads historical Polymarket event logs into a unified, time-ordered event stream. Supports two backends:

- **Database backend:** reads from `pm.orderbook_snapshots` and `pm.trades` tables (TimescaleDB).
- **File backend:** reads from JSONL log files (for offline research and testing).

```python
class SimEvent(BaseModel):
    event_id: str
    timestamp: datetime
    event_type: Literal["snapshot", "trade", "cancel"]
    market_id: str
    token_id: str
    payload: Dict[str, Any]   # raw event data
```

Events are sorted by `timestamp`, then by a deterministic sequence number. Any missing events in a range are logged as warnings. The loader is deterministic: the same input always produces the same output.

#### `SimulatedOrderBook`

Maintains full limit order book depth for one token (YES or NO). Stores separate `SortedDict` structures for bids (descending by price) and asks (ascending by price).

Supported operations:

- `apply_snapshot(event)` — replace full book state from a snapshot event.
- `apply_trade(event)` — remove matched volume from the appropriate side.
- `apply_cancel(event)` — remove a specific order by ID.
- `place_limit(order)` — insert a new limit order at its price level, behind existing orders (price-time priority).
- `match_market(order)` → `List[SimFill]` — consume opposite-side levels; return partial fills at each level.

Edge cases: ties at same price respect time priority; zero-volume levels are pruned; orders that would cross after a snapshot are handled as re-submissions.

#### `OrderMatcher`

Implements Polymarket matching rules:

- **Taker (marketable limit):** consume opposite-side levels at each price until order is filled or book is exhausted. Records slippage vs mid-price at time of submission.
- **Maker (post-only limit):** inserted into book queue. If the order would immediately cross (price ≥ best ask for bids, price ≤ best bid for asks), it is **rejected** rather than filled, consistent with post-only semantics.
- **Partial fills:** if taker size exceeds a single level, consume successive levels; each level generates a `SimFill` record.
- **Queue position:** each maker order tracks its position in the queue at its price level, used for fill probability estimation.

#### `ExecutionSimulator`

Wraps the order book and models realistic execution constraints:

- **Network latency:** configurable delay `network_delay_ms` (uniform or log-normal distribution). Order is submitted to the book at `receive_time = submit_time + sampled_delay`.
- **API throttling:** if orders are submitted faster than `max_orders_per_second`, excess orders are queued and delayed.
- **Stale quotes:** if the book has moved significantly between submission and arrival (mid-price change ≥ `stale_threshold`), taker orders execute at the new (worse) price; maker orders may be rejected if they now cross.
- **Race conditions:** simultaneous orders are resolved by simulated network order (first submitted wins at same timestamp).

```python
@dataclass
class ExecutionConfig:
    network_delay_ms: float = 100.0
    delay_distribution: Literal["fixed", "uniform", "lognormal"] = "lognormal"
    max_orders_per_second: int = 10
    stale_threshold: Decimal = Decimal("0.01")
    paper_mode: bool = True
```

#### `FeeEngine`

Applies the exact Polymarket fee formula. Supports two fee regimes switchable by date:

```python
# Pre-March 30, 2026
PRE_MAR30_CRYPTO = FeeRegime(fee_rate=Decimal("0.25"), exponent=2, maker_rebate_pct=Decimal("0.20"))

# Post-March 30, 2026
POST_MAR30_CRYPTO = FeeRegime(fee_rate=Decimal("0.072"), exponent=1, maker_rebate_pct=Decimal("0.20"))
```

Fee computation:

```
taker_fee = shares * price * fee_rate * (price * (1 - price)) ** exponent
```

Maker rebate (if the order was a maker fill):

```
fee_equivalent = shares * price * fee_rate * (price * (1 - price)) ** exponent
rebate = (your_fee_equivalent / total_fee_equivalent_in_market) * rebate_pool
```

The `total_fee_equivalent_in_market` is estimated from historical trade volume in the market over the lookback window. This estimate is flagged as approximate in the `SimFill` record.

Liquidity reward credit: modeled as a parameter `lr_pool_per_hour` (USDC) distributed proportionally by quote score. Quote score per tick: `min(bid_size, ask_size) * max(0, 1 - spread / max_spread)`. Configurable `max_spread` and `min_size` per market.

PnL attribution per fill:

```python
@dataclass
class PnLComponents:
    spread_capture: Decimal      # (fill_price - mid_at_fill) * size * side
    inventory_drift: Decimal     # mark-to-market changes between fills
    maker_rebate: Decimal        # estimated daily rebate accrual
    liquidity_reward: Decimal    # estimated LR credit
    taker_fee: Decimal           # negative for taker fills
    ops_cost: Decimal            # estimated cost of cancels, heartbeat misses
```

#### `AdverseSelectionModel`

Models the increasing proportion of informed order flow as the hour approaches close. Implements a time-varying "informed fraction" `π(t)` that rises from a baseline near open to a configurable peak near close.

```python
class AdverseSelectionModel:
    baseline_informed: Decimal = Decimal("0.05")   # fraction at hour open
    peak_informed: Decimal = Decimal("0.40")       # fraction in last 5 min
    ramp_start_minutes: int = 10                   # when ramp-up begins
    
    def informed_fraction(self, time_to_close_seconds: float) -> Decimal:
        # Linear ramp from baseline to peak over ramp_start_minutes
        ...
```

When an informed order arrives (sampled from the Bernoulli distribution with probability `π(t)`), it is directionally biased toward the expected settlement outcome (derived from the `btc_distance_to_open` feature). Uninformed orders are directionally random.

Validation mode: compare PnL with `peak_informed=0` vs configured value to estimate adverse selection cost.

#### `SimulationRunner`

Ties all components together and runs a simulation end-to-end:

```python
result = SimulationRunner(
    events=loader.load(market_id, start, end),
    strategy=my_strategy,
    execution_config=exec_config,
    fee_regime=FeeRegime.post_mar30_crypto(),
    adverse_selection=AdverseSelectionModel(),
    lr_pool_per_hour=Decimal("50"),
).run()
```

Output: `SimResult` containing all `SimFill` records, `PnLComponents` breakdown, fill rate statistics, and regime-conditioned PnL slices.

### Validation Layer

To validate the simulation against actual historical trading:

1. **Fill rate comparison:** for test orders placed in historical data, compare `SimulatedFillRate` vs `ActualFillRate` from `pm.trades`.
2. **PnL distribution comparison:** for a known strategy run with real fills, compare the simulated PnL distribution vs the actual PnL distribution from `pm.positions`.
3. **Slippage distribution:** compute `simulated_fill_price - actual_fill_price` distribution; mean should be ≈ 0, variance should be small.
4. **Determinism check:** running `SimulationRunner.run()` twice on the same input must produce byte-identical output.

Validation results are stored in `pm.simulation_validation` and surfaced in the API.

---

## Part 2: Evaluation Engine

### Location: `services/evaluation/`

```
services/evaluation/
├── __init__.py
├── metrics.py            # compute_metrics(): all per-model metrics
├── baselines.py          # Baseline strategies for comparison
├── regime_matrix.py      # Regime-conditioned performance breakdown
├── report.py             # EvaluationReport builder
└── schemas.py            # StrategyMetrics, RegimeMetrics, EvaluationReport schemas
```

### `StrategyMetrics` Schema

```python
class StrategyMetrics(BaseModel):
    strategy_id: str
    period_start: datetime
    period_end: datetime
    # PnL
    total_pnl: Decimal
    pnl_components: PnLComponents
    # Risk-adjusted
    sharpe_ratio: Decimal          # annualized; uses rolling daily PnL
    sortino_ratio: Decimal         # downside deviation only
    calmar_ratio: Decimal          # return / max drawdown
    # Trading quality
    win_rate: Decimal              # fraction of hours with positive PnL
    profit_factor: Decimal         # gross profit / gross loss
    max_drawdown: Decimal
    max_drawdown_duration_hours: int
    # Consistency
    consistency_score: Decimal     # fraction of rolling 7-day windows positive
    stability_score: Decimal       # 1 - std(rolling_7d_pnl) / mean(rolling_7d_pnl)
    # Volume
    total_volume_usd: Decimal
    fill_rate: Decimal             # filled orders / submitted orders
    maker_fill_rate: Decimal
    # Baseline comparison
    regret_vs_hold_cash: Decimal   # PnL - (cash PnL = 0)
    regret_vs_buy_and_hold: Decimal
    regret_vs_random: Decimal
```

### `RegimeMetrics`

For each strategy, compute `StrategyMetrics` conditioned on each regime label:

```python
class RegimeMetrics(BaseModel):
    strategy_id: str
    regime: str                    # e.g., "vol_regime=high", "near_close=True"
    metrics: StrategyMetrics
    sample_hours: int              # how many hours in this regime
```

Supported regime slices:
- `vol_regime` (low / medium / high)
- `toxicity_regime` (low / medium / high)
- `near_close_flag` (True / False)
- `time_bucket` (early / mid / late)
- `spread_regime` (tight / normal / wide)

### `EvaluationReport`

```python
class EvaluationReport(BaseModel):
    report_id: UUID
    generated_at: datetime
    strategy_ids: List[str]
    period_start: datetime
    period_end: datetime
    per_strategy: Dict[str, StrategyMetrics]
    regime_breakdown: Dict[str, List[RegimeMetrics]]
    rankings: List[StrategyRanking]       # ordered by composite score
    baseline_comparison: Dict[str, Decimal]   # each strategy vs each baseline
```

### Rolling Window Evaluation

To avoid overfitting to specific time periods, all metrics are computed over rolling windows:

- **Primary window:** last 30 days.
- **Short window:** last 7 days (for recency-weighted allocation in Sprint 16).
- **Regime window:** per-regime conditioned on all historical data (full lookback).

Sharpe ratios computed on rolling daily PnL with a minimum of 20 trading days to produce a valid estimate. Estimated Sharpe is flagged with a confidence interval.

### Baseline Strategies

Three comparison baselines (reusing the existing `services/ml/` baselines infrastructure):

1. **Hold cash:** PnL = 0 always. Spread capture regret = total_pnl.
2. **Buy and hold YES:** at market open, buy YES at the ask; hold to settlement. PnL = settlement - ask.
3. **Random market-making:** quote at mid ± 1 tick with equal probability on each side; no inventory management. Measures value added by the real strategy's quoting policy.

---

## Database Tables

New migration adds:

```sql
-- Simulation results
CREATE TABLE pm.simulation_runs (
    run_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id   TEXT NOT NULL,
    market_id     TEXT NOT NULL,
    started_at    TIMESTAMPTZ NOT NULL,
    completed_at  TIMESTAMPTZ,
    config        JSONB NOT NULL,
    result        JSONB
);

-- Evaluation reports
CREATE TABLE pm.evaluation_reports (
    report_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    generated_at  TIMESTAMPTZ NOT NULL,
    period_start  TIMESTAMPTZ NOT NULL,
    period_end    TIMESTAMPTZ NOT NULL,
    report        JSONB NOT NULL
);

-- Simulation validation
CREATE TABLE pm.simulation_validation (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id        UUID REFERENCES pm.simulation_runs(run_id),
    validated_at  TIMESTAMPTZ NOT NULL,
    fill_rate_sim DECIMAL,
    fill_rate_real DECIMAL,
    slippage_mean DECIMAL,
    slippage_std  DECIMAL,
    pnl_correlation DECIMAL,
    determinism_ok BOOLEAN
);
```

---

## API Endpoints

New router `services/api/routers/simulation.py`:

- `POST /v1/simulation/run` — kick off a backtest simulation run; returns `run_id`.
- `GET /v1/simulation/{run_id}/result` — poll result; returns `SimResult` when complete.
- `GET /v1/evaluation/{strategy_id}/latest` — returns latest `EvaluationReport` for a strategy.
- `GET /v1/evaluation/compare?strategy_ids=a,b,c` — returns side-by-side `EvaluationReport`.
- `GET /v1/evaluation/{strategy_id}/regimes` — returns `List[RegimeMetrics]` breakdown.

---

## Acceptance Criteria

### AC-1: Determinism
- Running `SimulationRunner.run()` twice on identical input produces byte-identical `SimResult`.
- Implemented as a determinism-check integration test.

### AC-2: Order book correctness
- `SimulatedOrderBook` correctly applies taker matching across multiple price levels.
- Post-only orders that would cross are rejected (not executed).
- Partial fills sum to the original order size.

### AC-3: Fee accuracy
- `FeeEngine` produces the exact fee for a set of reference trades from official docs examples.
- Pre-March 30 and post-March 30 fee regimes produce distinct results for the same trade.

### AC-4: Adverse selection model
- Simulation PnL with `peak_informed=0.40` near close is lower than with `peak_informed=0.0` (adverse selection cost is measurable).
- `informed_fraction(time_to_close=60)` > `informed_fraction(time_to_close=3000)`.

### AC-5: Validation layer
- For a test market with known real fills, simulated fill rate is within 10% of actual fill rate.
- Determinism check passes.

### AC-6: Evaluation metrics
- `StrategyMetrics` computes correct Sharpe, Sortino, and Calmar for a known synthetic PnL series.
- `RegimeMetrics` correctly partitions the same PnL series into regime slices using `FeatureSnapshot` labels from Sprint 12.

### AC-7: Rolling window
- Sharpe ratio computed over fewer than 20 days is flagged with `confidence=low` in the report.

### AC-8: API
- All simulation and evaluation endpoints return valid JSON with correct schemas.
- `POST /v1/simulation/run` returns `run_id` synchronously; result is available via poll.

### AC-9: Tests
- Unit tests for `SimulatedOrderBook` (matching, post-only rejection, partial fills).
- Unit tests for `FeeEngine` (both regimes, maker rebate computation).
- Unit tests for every metric in `StrategyMetrics`.
- Integration test: run full simulation on 1 hour of synthetic event data; verify PnL decomposition.

---

## Out of Scope

- Live execution using the simulation engine (simulation is offline/research only).
- Training any model from evaluation output (Sprint 14, 15).
- Fleet-level capital allocation based on evaluation scores (Sprint 16).
- Equity strategy simulation (equity backtest remains in the existing `services/backtest/`).

---

## Implementation Order

1. **Schemas** — `SimEvent`, `SimFill`, `SimOrder`, `SimResult`, `PnLComponents`, `StrategyMetrics`, `EvaluationReport`.
2. **Order book** — `SimulatedOrderBook` + `OrderMatcher`; unit-test exhaustively.
3. **Fee engine** — `FeeEngine` with both regimes; validate against docs examples.
4. **Execution simulator** — latency, throttling, stale quote handling.
5. **Adverse selection model** — `AdverseSelectionModel`; unit-test ramp function.
6. **Event loader** — `EventLoader` with database + file backends.
7. **Replay engine** — `ReplayEngine` + `SimulationRunner`; integration test.
8. **Validation layer** — fill rate, slippage, PnL comparison.
9. **Evaluation engine** — `compute_metrics()`, `RegimeMetrics`, `EvaluationReport`.
10. **Baselines** — hold cash, buy-and-hold, random MM.
11. **Database migration** — three new tables.
12. **API endpoints** — simulation + evaluation routers.

---

## Recommended Skills

| Task | Skill |
|------|-------|
| Order book matching logic, CLOB simulation design | `backtesting-frameworks` |
| Sharpe, Sortino, Calmar, drawdown computations | `risk-metrics-calculation` |
| PnL decomposition, fee curve analysis | `quant-analyst` |
| Pytest fixtures, async test patterns, mocking CLOB data | `python-testing-patterns` |
| FastAPI router, background task for async simulation runs | `fastapi-pro` |

---

## Risk Notes

- **Replay fidelity:** historical orderbook snapshots may have gaps (e.g., missed WebSocket messages). The `EventLoader` must flag gaps and the `ReplayEngine` must handle them gracefully (skip or interpolate, not crash).
- **Fee regime boundary:** markets created between March 6 and March 30 2026 have fees but at pre-March-30 rates. The `FeeEngine` must be keyed on both market creation date and current date, not just current date.
- **Sharpe estimation bias:** with only hourly resolution on a per-market basis, many strategies will have short track records. Always surface confidence intervals alongside Sharpe estimates and block allocation decisions (Sprint 16) for strategies with fewer than 20 data points.
