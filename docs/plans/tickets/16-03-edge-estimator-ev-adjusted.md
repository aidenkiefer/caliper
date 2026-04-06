# Ticket: 16-03-edge-estimator-ev-adjusted

## Task
Implement `EdgeEstimator` to compute `EV_raw`, `EV_adj`, and staleness decay for each candidate market (spec Part 1).

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- services/ranking/edge.py
- services/ranking/schemas.py
- tests/unit/ranking/test_edge_estimator.py
- docs/plans/PROGRESS.md

### Required read-only references
- docs/plans/specs/sprint-16-cross-sectional-fleet-spec.md

### Optional read-only references
- services/polymarket/fee_model.py (fee conventions, if needed)

## Skill pack (optional, keep small)
- Required: `quant-analyst`

## Context + tool budget
- Max file reads: 8
- Max grep/glob operations: 6
- Max total tool calls: 12

## Done criteria
- `EdgeEstimator.estimate(...)` computes:
  - `EV_raw = p_hat - p_PM`
  - `EV_adj = EV_raw - half_spread - slippage - fee_edge`, then applies staleness decay
  - fallback `p_hat=0.5` with `low_confidence=True` when needed
- Unit tests assert exact numeric outputs for simple inputs, including decay behavior.
- `docs/plans/PROGRESS.md` updated with a dated note referencing ticket 16-03 completion.

