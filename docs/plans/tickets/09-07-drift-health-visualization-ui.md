# 09-07: Model Drift & Health Visualization UI

## Task

- Add **drift and health visualization** UI: per-model drift trend charts; feature drift heatmaps; health score timeline; alert badges and threshold indicators; suggested actions (retrain, retire). Consume existing drift/health API (Sprint 8); place on Model Detail page or a dedicated Drift/Health tab. Use existing chart library and dashboard styling.

## Mandatory skill usage

- Read `agents/skills/skills/using-superpowers/SKILL.md` first; then use as many of the following as apply: **model-observability**, **anomaly-detection**, **dashboard-architect**, **explainability-ui**, **documentation-generator**. Aim for at least 5–7 skills.

## Reference docs (read-only)

- `docs/plans/specs/sprint-9-model-observatory-dashboard-spec.md`
- `docs/dashboard-spec.md`, `docs/design-guidelines.md`
- `docs/api-contracts.md` (drift, health endpoints)
- `services/ml/drift/` (health score, metrics)
- `packages/common/ml_schemas.py` (DriftMetricsResponse, HealthScoreResponse)
- `apps/dashboard/` (existing charts)
- `plans/task_plan.md` (Sprint 9, Model Drift & Health Visualization UI)

## Allowed files (ONLY these)

- `apps/dashboard/` (drift trend charts, feature drift heatmap, health score timeline, alert badges, suggested actions on Model Detail or Drift tab)
- `packages/common/api_schemas.py` or `ml_schemas.py` (only if adding types for chart data)
- `services/api/routers/drift.py` (only if extending response for UI, e.g. time-series for charts)

> If visualizations should live on a different page or data shape differs, stop and ask to extend the Allowed Files list.

## Hard limits

- Do **not** run build, test, or verification commands.
- **If blocked:** Stop and ask (e.g. “Should suggested actions trigger API calls or only display?”).

## Instructions

1. Use skills as above; read the spec and drift/health API and schemas.
2. Add UI components: drift trend over time (e.g. line chart per feature or composite); feature drift heatmap (e.g. features × time, color by drift magnitude); health score timeline (e.g. line chart); alert badges and threshold indicators (e.g. WARNING/CRITICAL from API); suggested actions (e.g. “Retrain”, “Retire” as buttons or links). Wire to GET drift/metrics and GET drift/health (or equivalent).
3. Place on Model Detail page or a “Drift & Health” tab; ensure drift aging is visible, not silent.
4. If API response shape for charts is undefined, add a short design note in `docs/` and **pause for user input**.

## Done criteria

- Drift & health visualization UI exists: drift trend charts, feature drift heatmap, health score timeline, alert badges, suggested actions; drift aging is visible.
- Only allowed files were modified.
- Summarize changes in ≤5 bullets; add Implementation Summary if needed.
