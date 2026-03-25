# 09-08: Human-in-the-Loop Review Mode (Model-Centric)

## Task

- Add **model-centric HITL review mode** in the dashboard: model recommendation review queue; explanation display per recommendation; approve/reject at model level; optional rationale input; decision outcome logging. Use existing HITL API (recommendations queue, approve/reject) from Sprint 6; extend UI so the queue and decisions are model-centric (filter by model, show explanation per recommendation). No new backend logic beyond optional filter by model_id if missing.

## Mandatory skill usage

- Read `agents/skills/skills/using-superpowers/SKILL.md` first; then use as many of the following as apply: **abstention-logic**, **risk-control-logic**, **explainability-ui**, **model-observability**, **dashboard-architect**, **documentation-generator**. Aim for at least 5–7 skills.

## Reference docs (read-only)

- `docs/plans/specs/sprint-9-model-observatory-dashboard-spec.md`
- `docs/dashboard-spec.md`, `docs/design-guidelines.md`
- `docs/api-contracts.md` (recommendations, explanations)
- `packages/common/ml_schemas.py` (RecommendationResponse, etc.)
- `services/api/routers/recommendations.py`, `explanations.py`
- `apps/dashboard/` (existing recommendations/approval queue if any)
- `plans/task_plan.md` (Sprint 9, Human-in-the-Loop Review Mode)

## Allowed files (ONLY these)

- `apps/dashboard/` (HITL review page or section: queue list, explanation per recommendation, approve/reject buttons, rationale input, filter by model; decision log view)
- `services/api/routers/recommendations.py` (only if adding filter by model_id or decision log endpoint)
- `packages/common/api_schemas.py` or `ml_schemas.py` (only if adding types for queue or log)

> If HITL should be strategy-centric instead of model-centric, stop and ask to extend the Allowed Files list or clarify scope.

## Hard limits

- Do **not** run build, test, or verification commands.
- **If blocked:** Stop and ask (e.g. “Should rationale be required on reject?”).

## Instructions

1. Use skills as above; read the spec and existing recommendations API and UI.
2. Add or extend UI: recommendation queue (list of pending recommendations, optionally filterable by model); per-row or detail view with explanation (from explanations API or inline); approve/reject actions; optional rationale/reason input (e.g. for reject); decision outcome logging (e.g. table or list of past decisions with outcome). Wire to GET/POST recommendations and GET explanations.
3. Ensure user can review and decide on model recommendations at model level (e.g. queue shows model_id, link to model detail); document any new API shape if added.
4. If API for model-filtered queue or decision log is undefined, add a short design note in `docs/` and **pause for user input**.

## Done criteria

- Model-centric HITL review mode exists: recommendation queue, explanation per recommendation, approve/reject at model level, optional rationale, decision outcome logging; user can review and decide on model recommendations.
- Only allowed files were modified.
- Summarize changes in ≤5 bullets; add Implementation Summary if needed.
