# Ticket: 15-12-api-router-regime-allocation

## Task
Add FastAPI router exposing regime/allocation endpoints and wire into `services/api/main.py`; update `docs/api-contracts.md` accordingly (AC-9).

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- services/api/routers/regime.py (new)
- services/api/routers/__init__.py
- services/api/main.py
- docs/api-contracts.md
- docs/plans/PROGRESS.md

### Required read-only references
- docs/plans/specs/sprint-15-regime-allocation-spec.md
- services/api/routers/features.py (DB_URL + store dependency style)

### Optional read-only references
- services/regime/store.py
- services/allocation/store.py

### Agent type (optional)
- backend-agent

## Skill pack (optional, keep small)
- Required: `fastapi-pro`
- Optional: `api-patterns`

## Context + tool budget
- Max file reads: 8
- Max grep/glob operations: 6
- Max total tool calls: 12

## Done criteria
- New endpoints implemented exactly (paths + response models):
  - `GET /v1/regime/current`
  - `GET /v1/regime/{market_id}/current`
  - `GET /v1/regime/history?start=&end=&market_id?`
  - `GET /v1/allocation/current`
  - `GET /v1/allocation/history?start=&end=`
  - `GET /v1/allocation/performance-matrix`
- Router uses store dependencies that require `DB_URL` (503 when missing).
- `services/api/main.py` includes the new router with tag `["regime"]` (or `["allocation"]` if split; keep the spec’s single-router simplicity).
- `docs/api-contracts.md` updated with the new endpoints and brief shapes.
- `docs/plans/PROGRESS.md` updated with a brief dated completion note referencing ticket 15-12 completion.

