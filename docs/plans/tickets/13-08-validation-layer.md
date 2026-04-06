# Ticket 13-08: Validation Layer

## Task

Implement the simulation validation layer that compares simulated outcomes to actual historical fills. Computes fill rate comparison, PnL distribution comparison, slippage distribution, and determinism check. Results stored in `pm.simulation_validation`. AC-5.

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- Create: `services/simulation/validation.py`
- Modify: `services/simulation/__init__.py` (add SimulationValidator export)
- Modify: `docs/plans/PROGRESS.md` (completion note)

### Required read-only references
- `docs/plans/specs/sprint-13-simulation-evaluation-spec.md` (§ Validation Layer)
- `services/simulation/schemas.py` (SimResult, SimFill)
- `services/simulation/runner.py` (SimulationRunner — for determinism check)
- `services/features/polymarket/store.py` (asyncpg patterns)

## Done criteria

### `services/simulation/validation.py` — `SimulationValidator`

**`ValidationResult`** (dataclass):
```python
@dataclass
class ValidationResult:
    run_id: str
    validated_at: datetime
    fill_rate_sim: Decimal
    fill_rate_real: Decimal
    fill_rate_within_10pct: bool   # abs(sim - real) / real <= 0.10
    slippage_mean: Decimal
    slippage_std: Decimal
    pnl_correlation: Optional[Decimal]  # Pearson correlation of sim vs real PnL series
    determinism_ok: bool
    notes: List[str]
```

**`SimulationValidator`**:
- `__init__(db_url: Optional[str] = None)`

**`check_determinism(runner: SimulationRunner) -> bool`**:
- Calls `runner.run()` twice. Serializes both `SimResult` objects to JSON. Compares byte-for-byte.
- Returns `True` if identical, `False` otherwise. Logs warning on mismatch.

**`validate_fill_rate(sim_result: SimResult, real_fill_rate: Decimal) -> bool`**:
- Computes `abs(sim_result.fill_rate - real_fill_rate) / max(real_fill_rate, Decimal("0.0001"))`.
- Returns `True` if within 10% (AC-5).

**`compute_slippage_stats(sim_fills: List[SimFill]) -> Tuple[Decimal, Decimal]`**:
- Extracts `slippage_vs_mid` from all taker fills (where `maker_fill=False`).
- Returns `(mean, std)` as Decimals. Returns `(Decimal(0), Decimal(0))` if no taker fills.

**`validate(runner: SimulationRunner, real_fill_rate: Decimal, real_pnl_series: Optional[List[Decimal]] = None) -> ValidationResult`**:
- Runs `runner.run()` to get sim result.
- Calls `check_determinism(runner)`, `validate_fill_rate`, `compute_slippage_stats`.
- If `real_pnl_series` provided: compute Pearson correlation between sim PnL series (hourly buckets) and real PnL series using `statistics.correlation` (Python 3.10+).
- Returns `ValidationResult`.

**`save_to_db(result: ValidationResult, db_url: str) -> None`** (async):
- Inserts into `pm.simulation_validation` table using asyncpg. Maps `ValidationResult` fields to DB columns.

No numpy or scipy — use Python stdlib `statistics` module for mean, stdev, correlation.
