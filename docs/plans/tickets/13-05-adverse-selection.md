# Ticket 13-05: Adverse Selection Model + Unit Tests

## Task

Implement `AdverseSelectionModel` — a time-varying model of informed order flow that rises from a baseline fraction near market open to a configurable peak fraction near close. Include unit tests validating the ramp function per AC-4.

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- Create: `services/simulation/adverse/selection.py`
- Create: `tests/unit/simulation/test_adverse_selection.py`
- Modify: `services/simulation/adverse/__init__.py` (exports)
- Modify: `docs/plans/PROGRESS.md` (completion note)

### Required read-only references
- `docs/plans/specs/sprint-13-simulation-evaluation-spec.md` (§ AdverseSelectionModel)
- `services/simulation/schemas.py` (SimOrder)

## Done criteria

### `services/simulation/adverse/selection.py` — `AdverseSelectionModel`

```python
@dataclass
class AdverseSelectionModel:
    baseline_informed: Decimal = Decimal("0.05")
    peak_informed: Decimal = Decimal("0.40")
    ramp_start_minutes: int = 10
    random_seed: Optional[int] = None

    def __post_init__(self):
        self._rng = random.Random(self.random_seed)
```

**`informed_fraction(time_to_close_seconds: float) -> Decimal`**:
- Linear ramp from `baseline_informed` to `peak_informed` over the last `ramp_start_minutes` minutes before close.
- When `time_to_close_seconds >= ramp_start_minutes * 60`: return `baseline_informed`.
- When `time_to_close_seconds <= 0`: return `peak_informed`.
- Between 0 and `ramp_start_minutes * 60`: linear interpolation from `peak_informed` (at 0) to `baseline_informed` (at ramp_start_minutes * 60).
- Formula: `frac = peak + (baseline - peak) * (time_to_close / (ramp_start * 60))`

**`is_informed(time_to_close_seconds: float) -> bool`**:
- Samples a Bernoulli trial using `self._rng.random() < float(self.informed_fraction(time_to_close_seconds))`.

**`directional_bias(expected_settlement: Decimal) -> Literal["BUY", "SELL"]`**:
- `expected_settlement > 0.5` → "BUY" (informed flow bets on YES)
- `expected_settlement <= 0.5` → "SELL"

**`sample_order_direction(time_to_close_seconds: float, expected_settlement: Decimal) -> Literal["BUY", "SELL", "RANDOM"]`**:
- If `is_informed(...)`: return `directional_bias(expected_settlement)`
- Else: return "BUY" or "SELL" with equal probability via `self._rng`

### `tests/unit/simulation/test_adverse_selection.py`

**Ramp function (AC-4):**
- `test_informed_fraction_at_open`: time_to_close = 3600s → returns baseline_informed
- `test_informed_fraction_at_close`: time_to_close = 0 → returns peak_informed
- `test_informed_fraction_monotonically_increasing`: sample 10 points; fraction strictly increases as time_to_close decreases from 600s to 0s
- `test_informed_fraction_before_ramp_start`: time_to_close = 3000s (> 600s) → returns baseline_informed exactly
- `test_informed_fraction_midpoint_of_ramp`: time_to_close = 300s (half of 600s ramp) → returns midpoint between baseline and peak

**AC-4 simulation test:**
- `test_pnl_lower_with_high_peak_informed`: Run 1000 random trades with `peak_informed=0.40` near close (time_to_close=30s) vs `peak_informed=0.0`. With high peak_informed, directional bias produces more informed orders. Verify `informed_fraction(30)` with peak=0.40 > `informed_fraction(30)` with peak=0.0.

**Determinism:**
- `test_is_informed_deterministic_with_seed`: two models with same seed produce identical sequence of is_informed() results

All assertions use `Decimal` for fraction comparisons.
