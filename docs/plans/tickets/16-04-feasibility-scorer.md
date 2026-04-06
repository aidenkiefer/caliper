# Ticket: 16-04-feasibility-scorer

## Task
Implement `FeasibilityScorer` computing bounded `[0,1]` feasibility and the `<0.2` exclusion trigger (spec Part 1).

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- services/ranking/feasibility.py
- services/ranking/schemas.py
- tests/unit/ranking/test_feasibility_scorer.py
- docs/plans/PROGRESS.md

### Required read-only references
- docs/plans/specs/sprint-16-cross-sectional-fleet-spec.md

## Skill pack (optional, keep small)
- Required: `quant-analyst`

## Context + tool budget
- Max file reads: 8
- Max grep/glob operations: 6
- Max total tool calls: 12

## Done criteria
- `FeasibilityScorer.score(...)` outputs:
  - `liquidity_score` consistent with spec formula
  - `fill_probability` as a bounded proxy (deterministic, documented)
  - `feasibility_score` in `[0,1]`
  - `exclude=True` when `feasibility_score < 0.2`
- Unit tests cover:
  - bounding behavior
  - exclusion trigger at <0.2
- `docs/plans/PROGRESS.md` updated with a dated note referencing ticket 16-04 completion.

