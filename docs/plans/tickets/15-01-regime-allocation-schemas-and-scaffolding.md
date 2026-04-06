# Ticket: 15-01-regime-allocation-schemas-and-scaffolding

## Task
Add Sprint 15 service scaffolding + Pydantic schemas for regime + allocation + performance matrix.

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- services/regime/**
- services/allocation/**
- services/api/routers/__init__.py (schemas imports only if needed later; otherwise leave untouched)
- pyproject.toml
- requirements.txt

### Required read-only references
- docs/plans/specs/sprint-15-regime-allocation-spec.md
- packages/common/polymarket_schemas.py (FeatureSnapshot fields)

### Optional read-only references
- services/ml/probability_model/predictor.py (pattern: async loop + optional signal bus + async DB writes)
- services/features/polymarket/store.py (pattern: asyncpg store)

### Agent type (optional)
- backend-agent

## Skill pack (optional, keep small)
- Required: `python-patterns`
- Optional: `fastapi-pro` (only for schema shaping conventions)

## Context + tool budget
- Max file reads: 8
- Max grep/glob operations: 6
- Max total tool calls: 12

## Done criteria
- New packages created: `services/regime/` and `services/allocation/` with `__init__.py`.
- New schema modules exist and match spec shapes:
  - `services/regime/schemas.py`: `RegimeState`, `RegimeQualityReport` (+ any small helper models needed like `ConnectivityMetrics`).
  - `services/allocation/schemas.py`: `PerformanceMatrix`, `AllocationDecision` (+ any helper models like `RegimeAllocation` if needed).
- `requirements.txt` and `pyproject.toml` updated to include `hmmlearn` and `statsmodels` (pin ranges consistent with existing style).
- No behavioral logic yet beyond type definitions (keeps this ticket small).
- `docs/plans/PROGRESS.md` updated with a brief dated completion note referencing Sprint 15 ticket 15-01 completion.

