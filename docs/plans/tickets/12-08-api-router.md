# Ticket: 12-08-api-router

## Task
Add a `features` FastAPI router under `services/api/routers/features.py` exposing `GET /v1/features/{market_id}/latest` and `GET /v1/features/{market_id}/history`, then register it in the FastAPI app.

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- Create: `services/api/routers/features.py`
- Modify: `services/api/main.py` (register the features router)
- Modify: `docs/plans/PROGRESS.md` (completion note)

### Required read-only references
- `docs/plans/specs/sprint-12-feature-layer-spec.md` (section: API Endpoint)

### Optional read-only references
- `packages/common/polymarket_schemas.py` (FeatureSnapshot response model — read-only)
- `services/api/routers/` (any existing router for FastAPI + dependency injection patterns)
- `services/api/main.py` (router registration pattern — read before modifying)
- `services/api/dependencies.py` (DB dependency injection patterns)

## Agent type
backend-agent

## Skill pack
None required (FastAPI router, standard pattern)

## Context + tool budget
- Max file reads: 5
- Max grep/glob operations: 3
- Max total tool calls: 10

## Done criteria

**`services/api/routers/features.py`:**
- `GET /v1/features/{market_id}/latest`
  - Response model: `FeatureSnapshot` (from `packages.common.polymarket_schemas`)
  - Queries `FeatureStore.read_latest(market_id)`
  - Returns 404 with `{"detail": "No features found for market"}` if no data
- `GET /v1/features/{market_id}/history`
  - Query params: `start: datetime`, `end: datetime`, `limit: int = 100` (max 1000)
  - Response model: `List[FeatureSnapshot]`
  - Queries `FeatureStore.read_window(market_id, start, end, limit=limit)`
  - Returns empty list (not 404) if no rows in range
  - Validates `start < end`; returns 422 if not
  - `limit` capped at 1000 server-side regardless of query param
- Router prefix: `/v1/features`, tag: `"features"`
- `FeatureStore` provided via FastAPI dependency injection (uses same `DB_URL` env var pattern as existing routers)
- If `DB_URL` not configured: returns 503 with `{"detail": "Feature store not available"}`

**`services/api/main.py`:**
- `app.include_router(features_router)` added in the same style as existing routers

**`docs/plans/PROGRESS.md`** updated
