# 08-01: Model Performance Tracking

## Task

- Log prediction vs outcome (direction or return) when ground truth is available; compute rolling accuracy/error metrics (e.g. over last N days); track abstention rate over time; expose performance metrics via API or DB so the dashboard (or future Sprint 9) can query them per model over time. Use existing API and schemas where possible; add storage and endpoints only as needed.

## Mandatory skill usage

- Read `agents/skills/skills/using-superpowers/SKILL.md` first; then use as many of the following as apply: **model-evaluation**, **experiment-tracking**, **model-observability**, **backend-service-architect**, **database-schema-designer**, **dashboard-architect** (for API shape). Aim for at least 5–7 skills.

## Reference docs (read-only)

- `docs/plans/specs/sprint-8-observability-safety-spec.md`
- `plans/task_plan.md` (Sprint 8, Model Performance Tracking)
- `docs/api-contracts.md` (metrics, summary endpoints)
- `packages/common/api_schemas.py`, `packages/common/ml_schemas.py`
- Inference path and logging from Sprint 7 (predictions, confidence, decisions)

## Allowed files (ONLY these)

- `services/api/routers/` (e.g. metrics or a new performance endpoint)
- `services/ml/` (e.g. performance tracker, aggregation of prediction vs outcome, abstention rate)
- `packages/common/ml_schemas.py` or `packages/common/api_schemas.py` (response types for performance API)
- `docs/` (short note on metrics and API)

> If performance data should be stored in a different service or DB schema, stop and ask to extend the Allowed Files list.

## Hard limits

- Do **not** build dashboard UI in this ticket (Sprint 9); API and data only.
- Do **not** run build, test, or verification commands.
- **If blocked:** Stop and ask (e.g. “Where should prediction-vs-outcome records be stored?”).

## Instructions

1. Use skills as above; read the spec and existing API/schemas.
2. Define how “outcome” is recorded (e.g. realized return or direction after N bars) and when it becomes available; implement or extend logging so prediction + outcome can be joined (e.g. by trade_id or timestamp + symbol).
3. Implement aggregation for rolling accuracy/error and abstention rate (e.g. per model, over configurable window); expose via API (e.g. GET /v1/metrics/performance or extend existing metrics endpoint) with response shape suitable for future dashboard.
4. Document the metrics and API in `docs/` (e.g. `docs/sprint-8-performance-metrics.md` or add to api-contracts).
5. If storage or API shape is ambiguous, add a short design note and **pause for user input**.

## Done criteria

- Prediction vs outcome is logged when ground truth is available; rolling accuracy/error and abstention rate are computable and exposed via API or DB query.
- Performance is queryable per model over time (e.g. by date range, model_id).
- Only allowed files were modified.
- Summarize changes in ≤5 bullets; add Implementation Summary if needed.
