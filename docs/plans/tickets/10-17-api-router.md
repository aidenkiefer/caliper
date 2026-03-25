# Ticket: 10-17-api-router

## Task
Create FastAPI router for Polymarket endpoints (sessions, orders, fills, snapshots, PnL).

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- Create: `services/api/routers/polymarket.py`
- Modify: `services/api/main.py` (include new router)
- Modify: `docs/plans/PROGRESS.md` (completion note)

### Required read-only references
- `docs/plans/specs/polymarket-btc-trading-spec.md` (section 7.1)

### Optional read-only references
- `services/api/routers/strategies.py` (example router pattern)
- `packages/common/polymarket_schemas.py`

## Agent type
backend-agent

## Skill pack
None required (straightforward API router)

## Context + tool budget
- Max file reads: 6
- Max grep/glob operations: 3
- Max total tool calls: 12

## Done criteria
- `polymarket.py` implements FastAPI router with endpoints:
  - `GET /polymarket/sessions` (list sessions, paginated)
  - `GET /polymarket/sessions/{session_id}` (session details)
  - `GET /polymarket/sessions/{session_id}/orders` (orders for session)
  - `GET /polymarket/sessions/{session_id}/fills` (fills for session)
  - `GET /polymarket/sessions/{session_id}/snapshots` (orderbook snapshots, paginated)
  - `GET /polymarket/sessions/{session_id}/pnl` (PnL breakdown)
  - `GET /polymarket/sessions/{session_id}/toxic-flow` (toxic flow by minute)
- All endpoints query `pm.*` tables via asyncpg
- Response models use `polymarket_schemas.py`
- Endpoints include filters: `status`, `date_range`, `regime`
- `main.py` includes router: `app.include_router(polymarket.router, prefix="/api/v1", tags=["polymarket"])`
- `docs/plans/PROGRESS.md` updated
