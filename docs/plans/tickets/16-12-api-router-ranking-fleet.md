# Ticket: 16-12-api-router-ranking-fleet

## Task
Expose ranker + fleet read APIs for the dashboard and update `docs/api-contracts.md` accordingly (AC-8).

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- services/api/routers/ranking.py (new)
- services/api/routers/fleet.py (new)
- services/api/routers/__init__.py
- services/api/main.py
- docs/api-contracts.md
- docs/plans/PROGRESS.md

### Required read-only references
- docs/plans/specs/sprint-16-cross-sectional-fleet-spec.md
- services/api/routers/features.py (dependency patterns)

### Optional read-only references
- services/ranking/schemas.py
- services/fleet/schemas.py

## Skill pack (optional, keep small)
- Required: `fastapi-pro`

## Context + tool budget
- Max file reads: 8
- Max grep/glob operations: 6
- Max total tool calls: 12

## Done criteria
- Add endpoints (paths + response models may be refined, but must cover panel needs):
  - `GET /v1/ranking/current` → `RankedUniverse`
  - `GET /v1/fleet/status` → `FleetStatus`
  - `GET /v1/fleet/signals?limit=` → per-strategy signal log (last N)
  - `GET /v1/fleet/paper-trades?start=&end=&strategy_id?&market_id?` → fills
- Router uses DB URL dependency pattern (503 when missing).
- `docs/api-contracts.md` updated with new endpoints and brief shapes.
- `docs/plans/PROGRESS.md` updated with a dated note referencing ticket 16-12 completion.

