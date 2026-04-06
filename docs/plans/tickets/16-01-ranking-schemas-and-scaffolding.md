# Ticket: 16-01-ranking-schemas-and-scaffolding

## Task
Create `services/ranking/` package scaffolding and Pydantic schemas for the cross-sectional market ranker.

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- services/ranking/**
- docs/plans/PROGRESS.md

### Required read-only references
- docs/plans/specs/sprint-16-cross-sectional-fleet-spec.md

### Optional read-only references
- services/polymarket/adapters/gamma_client.py (market metadata shape)

## Skill pack (optional, keep small)
- Required: `quant-analyst`

## Context + tool budget
- Max file reads: 8
- Max grep/glob operations: 6
- Max total tool calls: 12

## Done criteria
- New package exists: `services/ranking/` with `__init__.py`.
- `services/ranking/schemas.py` defines:
  - `CandidateMarket` (minimal fields needed for filters + scoring)
  - `MarketScore` (includes EV components, feasibility, confidence, and final `score`)
  - `RankedUniverse` (matches spec shape including `cooldown_protected`)
- No external side effects or network calls in this ticket (types only).
- `docs/plans/PROGRESS.md` updated with a dated note referencing Sprint 16 ticket 16-01 completion.

