# Ticket: 16-13-dashboard-panels-and-tests

## Task
Add dashboard panels for Market Ranker + Fleet + Regime Timeline and implement Sprint 16 unit/integration tests (AC-1..AC-10).

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- apps/dashboard/src/app/(dashboard)/page.tsx
- apps/dashboard/src/components/** (new or updated)
- apps/dashboard/src/lib/api.ts
- apps/dashboard/src/lib/api/models.ts
- apps/dashboard/src/lib/hooks/** (new or updated)
- apps/dashboard/src/lib/types/** (new or updated)
- tests/unit/ranking/**
- tests/unit/strategies/**
- tests/integration/fleet/**
- docs/plans/PROGRESS.md

### Required read-only references
- docs/plans/specs/sprint-16-cross-sectional-fleet-spec.md

## Skill pack (optional, keep small)
- Required: `frontend-design`
- Optional: `python-testing-patterns`

## Context + tool budget
- Max file reads: 8
- Max grep/glob operations: 6
- Max total tool calls: 12

## Done criteria
- Dashboard panels exist (can be a single page sectioned UI):
  - Market Ranker view (table + staleness)
  - Fleet overview cards (PnL/Sharpe placeholders acceptable if API provides)
  - Per-strategy signal log (last 50)
  - Regime timeline (simple stacked visualization; labels correct)
  - Cross-strategy comparison (table)
- Tests added for:
  - `RankingScore` and selection constraints (AC-1/2/9)
  - each strategy `generate_signals()` semantics (AC-3/4/5)
  - fleet orchestrator 5-tick paper-mode integration (AC-10)
- `docs/plans/PROGRESS.md` updated with a dated note referencing ticket 16-13 completion.

