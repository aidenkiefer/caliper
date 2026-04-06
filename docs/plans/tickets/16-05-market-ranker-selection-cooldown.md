# Ticket: 16-05-market-ranker-selection-cooldown

## Task
Implement `MarketRanker` that scores candidates, selects top-N with constraints, and emits `RankedUniverse` on a 60s cadence (AC-1/9).

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- services/ranking/ranker.py
- services/ranking/score.py
- services/ranking/schemas.py
- services/ranking/__init__.py
- tests/unit/ranking/test_ranking_score.py
- tests/unit/ranking/test_market_ranker_selection.py
- docs/plans/PROGRESS.md

### Required read-only references
- docs/plans/specs/sprint-16-cross-sectional-fleet-spec.md

### Optional read-only references
- services/ml/probability_model/predictor.py (signal bus patterns, if applicable)

## Skill pack (optional, keep small)
- Required: `async-python-patterns`
- Optional: `risk-manager`

## Context + tool budget
- Max file reads: 8
- Max grep/glob operations: 6
- Max total tool calls: 12

## Done criteria
- Composite scoring implemented:
  - configurable weights with defaults from spec
  - `EV_adj < 0 → score=0`
- Selection logic:
  - never selects both YES and NO of the same condition simultaneously
  - diversification: skip markets with `|time_to_close - other| < 600s`
  - cooldown: market must be below top-N for 3 consecutive cycles before exit
- `MarketRanker.rank_once(...)` executes in-memory without network I/O.
- Unit tests cover AC-1/9 selection constraints + cooldown state transitions.
- `docs/plans/PROGRESS.md` updated with a dated note referencing ticket 16-05 completion.

