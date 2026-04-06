# Ticket 13-10: Baselines

## Task

Implement three baseline strategies for evaluation comparison: hold-cash (PnL=0), buy-and-hold YES (buy at open ask, hold to settlement), and random market-making (quote at mid ± 1 tick, no inventory management). Wire their PnL into the `regret_vs_*` fields in `StrategyMetrics`.

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- Create: `services/evaluation/baselines.py`
- Modify: `services/evaluation/__init__.py` (add baseline exports)
- Modify: `services/evaluation/metrics.py` (populate regret fields, wire in baseline results)
- Modify: `docs/plans/PROGRESS.md` (completion note)

### Required read-only references
- `docs/plans/specs/sprint-13-simulation-evaluation-spec.md` (§ Baseline Strategies)
- `services/evaluation/schemas.py` (StrategyMetrics)
- `services/evaluation/metrics.py` (compute_metrics)
- `services/simulation/schemas.py` (SimFill, SimResult)

## Done criteria

### `services/evaluation/baselines.py`

**`HoldCashBaseline`**:
- `compute(period_hours: int) -> List[Decimal]`: returns `[Decimal(0)] * period_hours`. PnL is always 0.
- `description: str = "Hold cash — PnL = 0 at all times"`

**`BuyAndHoldYesBaseline`**:
- `compute(open_ask: Decimal, settlement_price: Decimal, period_hours: int) -> List[Decimal]`:
  - At hour 0: buy YES at `open_ask`. PnL for all intermediate hours = current mark - open_ask (use settlement_price as final mark).
  - Returns hourly PnL series: `[Decimal(0)] * (period_hours - 1) + [settlement_price - open_ask]`.
  - If settlement_price not yet known: use last available mid_price.
- `description: str = "Buy and hold YES at market open ask"`

**`RandomMMBaseline`**:
- `compute(mid_prices: List[Decimal], tick_size: Decimal = Decimal("0.01"), random_seed: int = 42) -> List[Decimal]`:
  - For each hour: quote bid = mid - tick_size, ask = mid + tick_size with equal probability on each side.
  - Fill probability: assume 50% fill on each side per hour (no inventory management).
  - Hourly PnL = tick_size per filled round-trip (bid fill + ask fill = 2 * tick_size * assumed_size). Use `assumed_size = Decimal("10")` as default.
  - Use `random.Random(random_seed)` for determinism.
  - Returns hourly PnL series.
- `description: str = "Random market-making at mid ± 1 tick"`

**`BaselineEvaluator`**:
```python
class BaselineEvaluator:
    def compute_regrets(
        self,
        strategy_pnl: List[Decimal],
        open_ask: Decimal,
        settlement_price: Decimal,
        mid_prices: List[Decimal],
    ) -> Dict[str, Decimal]:
        # Returns {"hold_cash": ..., "buy_and_hold": ..., "random_mm": ...}
        # regret = strategy_total_pnl - baseline_total_pnl
```

### Modify `services/evaluation/metrics.py`

Update `compute_metrics()` signature to accept optional `baseline_results: Optional[Dict[str, Decimal]] = None`. When provided, populate:
- `regret_vs_hold_cash = total_pnl - baseline_results.get("hold_cash", Decimal(0))`
- `regret_vs_buy_and_hold = total_pnl - baseline_results.get("buy_and_hold", Decimal(0))`
- `regret_vs_random = total_pnl - baseline_results.get("random_mm", Decimal(0))`

This is backwards-compatible (defaults to 0 when baselines not provided).
