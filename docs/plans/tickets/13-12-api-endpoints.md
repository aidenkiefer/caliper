# Ticket 13-12: API Endpoints

## Task

Implement the simulation and evaluation API router (`services/api/routers/simulation.py`) with 5 endpoints. Register the router in `services/api/main.py`. AC-8.

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- Create: `services/api/routers/simulation.py`
- Modify: `services/api/main.py` (register router)
- Modify: `docs/plans/PROGRESS.md` (completion note)

### Required read-only references
- `docs/plans/specs/sprint-13-simulation-evaluation-spec.md` (§ API Endpoints, AC-8)
- `services/api/routers/features.py` (existing router patterns, background task patterns)
- `services/api/main.py` (router registration pattern)
- `services/simulation/schemas.py` (SimResult)
- `services/evaluation/schemas.py` (EvaluationReport, RegimeMetrics)

## Done criteria

### `services/api/routers/simulation.py`

Router prefix: `/v1`

**`POST /v1/simulation/run`**:
- Request body: `SimulationRunRequest(strategy_id: str, market_id: str, token_id: str, start: datetime, end: datetime, config: Optional[Dict] = None)`.
- Response: `SimulationRunResponse(run_id: str, status: str = "queued")`.
- Records the run in an in-memory `Dict[str, Any]` store (keyed by `run_id`) with status "queued". Uses `BackgroundTasks` to simulate async execution — the background task sets status to "running" then "completed" and stores a stub `SimResult`. (Full DB storage is for post-Sprint scope; stub is acceptable here.)
- Returns `run_id` synchronously. Status 202 Accepted.

**`GET /v1/simulation/{run_id}/result`**:
- Returns `SimResult` if status is "completed". Returns 404 if `run_id` unknown. Returns 202 with `{"status": "running"}` if not yet complete.

**`GET /v1/evaluation/{strategy_id}/latest`**:
- Returns latest `EvaluationReport` for the strategy. Since no live data in stub mode: returns a stub `EvaluationReport` with empty `per_strategy` and `regime_breakdown`. Status 200.
- Returns 404 if `strategy_id` is empty string.

**`GET /v1/evaluation/compare`**:
- Query param: `strategy_ids: str` (comma-separated). Parses into list. Returns `EvaluationReport` with stub data for each strategy. Status 200.
- Returns 422 if `strategy_ids` is missing or empty.

**`GET /v1/evaluation/{strategy_id}/regimes`**:
- Returns `List[RegimeMetrics]` for the strategy. Stub returns empty list. Status 200.

All request/response schemas defined inline in the router file using Pydantic `BaseModel`. No external DB calls in stub mode — use the in-memory store. All responses return valid JSON matching the schemas from `services/simulation/schemas.py` and `services/evaluation/schemas.py`.

### Modify `services/api/main.py`

Register the new router:
```python
from services.api.routers import simulation as simulation_router
app.include_router(simulation_router.router)
```

(Follow the exact import and registration pattern used for the `features` router.)
