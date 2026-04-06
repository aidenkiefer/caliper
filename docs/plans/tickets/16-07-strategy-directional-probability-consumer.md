# Ticket: 16-07-strategy-directional-probability-consumer

## Task
Implement `poly_directional_v1` which consumes probability predictor output and emits directional taker signals when `|M(t)| > θ(t)` (Strategy 2).

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- packages/strategies/poly_directional_v1.py
- packages/strategies/__init__.py
- packages/strategies/base.py (ONLY if required for shared interfaces)
- tests/unit/strategies/test_poly_directional_v1.py
- docs/plans/PROGRESS.md

### Required read-only references
- docs/plans/specs/sprint-16-cross-sectional-fleet-spec.md
- packages/strategies/ml_direction_v1.py (prior art: M(t) thresholding)

### Optional read-only references
- services/portfolio/allocator.py (CapitalBudget fields)
- services/regime/schemas.py (RegimeState)

## Skill pack (optional, keep small)
- Required: `quant-analyst`
- Optional: `risk-manager`

## Context + tool budget
- Max file reads: 8
- Max grep/glob operations: 6
- Max total tool calls: 12

## Done criteria
- `poly_directional_v1`:
  - emits BUY-YES when `M(t) > θ(t)` and BUY-NO when `M(t) < -θ(t)`
  - skips regimes outside `{R1,R2}`
  - enforces `min_hold_seconds=120` direction cooldown
  - rejects `time_to_close < 120s` in `risk_check()`
- Unit tests cover threshold triggers + cooldown and the `time_to_close` rejection.
- `docs/plans/PROGRESS.md` updated with a dated note referencing ticket 16-07 completion.

