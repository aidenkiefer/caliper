# Ticket 13-09: Evaluation Engine + Metrics Unit Tests

## Task

Implement the evaluation engine: `compute_metrics()` for per-model performance metrics, `RegimeMetrics` partitioning using `FeatureSnapshot` labels from Sprint 12, rolling-window evaluation, `EvaluationReport` builder. Include unit tests for all `StrategyMetrics` fields. AC-6, AC-7.

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- Create: `services/evaluation/metrics.py`
- Create: `services/evaluation/regime_matrix.py`
- Create: `services/evaluation/report.py`
- Create: `tests/unit/evaluation/__init__.py`
- Create: `tests/unit/evaluation/test_metrics.py`
- Modify: `services/evaluation/__init__.py` (exports)
- Modify: `docs/plans/PROGRESS.md` (completion note)

### Required read-only references
- `docs/plans/specs/sprint-13-simulation-evaluation-spec.md` (§ Evaluation Engine, § StrategyMetrics, § RegimeMetrics, § EvaluationReport, § Rolling Window, AC-6, AC-7)
- `services/evaluation/schemas.py` (StrategyMetrics, RegimeMetrics, EvaluationReport)
- `packages/common/polymarket_schemas.py` (FeatureSnapshot — for regime label field names)

## Done criteria

### `services/evaluation/metrics.py` — `compute_metrics()`

```python
def compute_metrics(
    strategy_id: str,
    pnl_series: List[Decimal],        # hourly PnL values, chronological
    fills: List[SimFill],
    period_start: datetime,
    period_end: datetime,
    risk_free_rate: Decimal = Decimal("0"),
) -> StrategyMetrics:
```

Computes all `StrategyMetrics` fields:

- **`total_pnl`**: sum of `pnl_series`.
- **`sharpe_ratio`**: annualized Sharpe. Use hourly PnL → daily PnL by summing 24h windows. `sharpe = (mean(daily_pnl) - risk_free_rate) / std(daily_pnl) * sqrt(252)`. If fewer than 20 daily observations: set `sharpe_confidence="low"` and `data_points=n` (AC-7). Use `Decimal` arithmetic or convert to float for sqrt then back.
- **`sortino_ratio`**: same as Sharpe but downside deviation = std of negative daily PnL only. `sortino = mean(daily_pnl) / downside_std * sqrt(252)`.
- **`calmar_ratio`**: `total_pnl / abs(max_drawdown)` if max_drawdown != 0, else `Decimal(0)`.
- **`max_drawdown`**: maximum peak-to-trough decline in cumulative PnL series. Return as positive Decimal.
- **`max_drawdown_duration_hours`**: longest consecutive sequence of hours below the previous peak.
- **`win_rate`**: fraction of hourly PnL > 0.
- **`profit_factor`**: `sum(pnl > 0) / abs(sum(pnl < 0))`. If no losses: return `Decimal("inf")` represented as `Decimal("9999")`.
- **`consistency_score`**: fraction of rolling 7-day windows (168h) with positive total PnL.
- **`stability_score`**: `1 - std(rolling_7d_pnl) / abs(mean(rolling_7d_pnl))`. Clamp to [0, 1].
- **`total_volume_usd`**: sum of `fill.fill_price * fill.fill_size` for all fills.
- **`fill_rate`**: from fills metadata if available, else `Decimal(0)`.
- **`maker_fill_rate`**: fraction of fills where `maker_fill=True`.
- **`regret_vs_hold_cash`**: equals `total_pnl` (hold cash PnL = 0).
- **`regret_vs_buy_and_hold`**, **`regret_vs_random`**: set to `Decimal(0)` (populated by Baselines ticket 13-10).
- **`sharpe_confidence`**: "low" if data_points < 20, "medium" if 20-60, "high" if > 60.
- **`data_points`**: number of daily PnL observations used for Sharpe calculation.

Helper: `_daily_pnl(hourly_pnl: List[Decimal]) -> List[Decimal]` — groups into 24-hour windows and sums.

### `services/evaluation/regime_matrix.py` — `compute_regime_metrics()`

```python
def compute_regime_metrics(
    strategy_id: str,
    pnl_series: List[Decimal],
    fills: List[SimFill],
    snapshots: List[FeatureSnapshot],  # one per hour, aligned with pnl_series
    period_start: datetime,
    period_end: datetime,
) -> List[RegimeMetrics]:
```

- For each supported regime dimension (`vol_regime`, `toxicity_regime`, `near_close_flag`, `time_bucket`, `spread_regime`):
  - Group `pnl_series` hours by regime label value.
  - For each label value (e.g., `vol_regime=high`): filter pnl_series and fills to that regime; call `compute_metrics(...)` on the subset.
  - Produce `RegimeMetrics(strategy_id=..., regime="vol_regime=high", metrics=..., sample_hours=n)`.
- Returns all `RegimeMetrics` objects (one per regime×label combination).
- If `snapshots` is shorter than `pnl_series`, pad with None and skip those hours in regime grouping.

### `services/evaluation/report.py` — `build_report()`

```python
def build_report(
    strategy_results: Dict[str, Tuple[List[Decimal], List[SimFill]]],
    snapshots: Dict[str, List[FeatureSnapshot]],
    period_start: datetime,
    period_end: datetime,
) -> EvaluationReport:
```

- Calls `compute_metrics()` for each strategy → `per_strategy`.
- Calls `compute_regime_metrics()` for each strategy → `regime_breakdown`.
- Ranks strategies by composite score = 0.4×sharpe + 0.3×win_rate + 0.2×consistency + 0.1×profit_factor (normalized to [0,1] per metric).
- Returns `EvaluationReport` with all fields populated.

### `tests/unit/evaluation/test_metrics.py`

Use a fixed synthetic PnL series of 720 hourly values (30 days × 24h) with known mean and std.

**Sharpe:**
- `test_sharpe_positive_pnl_series`: constant positive PnL → Sharpe > 0
- `test_sharpe_zero_pnl_series`: all-zero PnL → Sharpe = 0
- `test_sharpe_mixed_pnl_known_value`: 30d series with mean=1.0, std=2.0 daily → verify formula

**Confidence flag (AC-7):**
- `test_sharpe_confidence_low_under_20_days`: 19 daily obs → `sharpe_confidence == "low"` (AC-7)
- `test_sharpe_confidence_high_over_60_days`: 61 daily obs → `sharpe_confidence == "high"`

**Sortino:**
- `test_sortino_ignores_positive_returns`: series with positive and negative values; sortino > sharpe

**Calmar:**
- `test_calmar_known_drawdown`: series with known max drawdown → verify ratio

**Drawdown:**
- `test_max_drawdown_simple_series`: [10, -5, -3, 0] cumulative → drawdown = 8
- `test_max_drawdown_duration_hours`: verify correct count of hours below peak

**Win rate, profit factor:**
- `test_win_rate_all_positive`: all positive hours → win_rate = 1.0
- `test_profit_factor_no_losses`: returns "9999"

**Regime metrics (AC-6):**
- `test_regime_metrics_partitions_correctly`: 720h series split into high/medium/low vol_regime; verify each partition has correct sample_hours and sum of sample_hours = 720

All numeric assertions allow Decimal tolerance ≤ `Decimal("0.001")`.
