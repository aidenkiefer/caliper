# Ticket 13-13: Integration Test

## Task

Write an integration test that runs a full simulation on 1 hour of synthetic event data, verifies PnL decomposition, and confirms AC-1 determinism. Also tests the evaluation engine on the resulting PnL series. AC-1, AC-9.

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- Create: `tests/integration/simulation/__init__.py`
- Create: `tests/integration/simulation/test_simulation_pipeline.py`
- Modify: `docs/plans/PROGRESS.md` (completion note)

### Required read-only references
- `docs/plans/specs/sprint-13-simulation-evaluation-spec.md` (AC-1, AC-9)
- `services/simulation/runner.py` (SimulationRunner, SimStrategy)
- `services/simulation/schemas.py` (SimEvent, SimResult)
- `services/evaluation/metrics.py` (compute_metrics)
- `tests/integration/features/test_feature_pipeline_integration.py` (integration test patterns, fixture patterns)

## Done criteria

### `tests/integration/simulation/test_simulation_pipeline.py`

**Fixture: `synthetic_events()`**:
- Generates a list of `SimEvent` objects representing 1 hour of Polymarket activity:
  - 12 snapshot events (one every 5 minutes): bids at `[0.45, 0.44, 0.43]` and asks at `[0.55, 0.56, 0.57]` with sizes `[100, 80, 60]`.
  - 24 trade events (one every 2.5 minutes): alternating BUY/SELL at mid-price (0.50), size 10.
  - All timestamps pinned to fixed absolute values (e.g., `datetime(2026, 4, 1, 9, 0, 0)` + offset). NO `datetime.now()` or `datetime.utcnow()`.
- Returns `List[SimEvent]` sorted by timestamp.

**Fixture: `simple_strategy()`**:
- Implements `SimStrategy` protocol. On each trade event: submits one taker BUY order of size 5 at best ask, and one taker SELL order of size 5 at best bid (simple passive market-making). On snapshot/cancel events: no-op.

**Test: `test_full_simulation_produces_fills`**:
- Creates `SimulationRunner` with `synthetic_events`, `simple_strategy`, `ExecutionConfig(random_seed=42, paper_mode=True, delay_distribution="fixed", network_delay_ms=0)`, `FeeRegime.post_mar30_crypto()`.
- Calls `runner.run()`.
- Asserts `result.fills` is not empty.
- Asserts `result.total_pnl` is a `Decimal` (may be negative — that's fine).
- Asserts `result.fill_count == len(result.fills)`.

**Test: `test_determinism_identical_results` (AC-1)**:
- Creates two `SimulationRunner` instances with identical parameters (same events, same seed).
- Calls `.run()` on both.
- Serializes both `SimResult` objects to JSON using `result.model_dump_json()`.
- Asserts both JSON strings are byte-identical.

**Test: `test_pnl_components_sum_to_total`**:
- Runs simulation. Gets `result.pnl_components` (as dict from `SimResult`).
- Asserts `sum(result.pnl_components.values())` ≈ `result.total_pnl` (tolerance `Decimal("0.001")`).

**Test: `test_evaluation_from_simulation_output`**:
- Runs simulation. Converts fills to hourly PnL series (24 buckets of 0 since 1 hour = 1 bucket).
- Calls `compute_metrics(strategy_id="test", pnl_series=[result.total_pnl], fills=result.fills, period_start=..., period_end=...)`.
- Asserts `metrics.sharpe_confidence == "low"` (only 1 data point, < 20 required for valid Sharpe — AC-7).
- Asserts `metrics.total_pnl == result.total_pnl`.

All tests: no network, no DB. All timestamps fixed. Test isolation: each test creates its own runner instance.
