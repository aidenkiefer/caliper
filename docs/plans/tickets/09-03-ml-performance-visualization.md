# 09-03: ML Performance Visualization

## Task

- Add **ML performance visualizations** to the dashboard: prediction vs actual plots (directional or regression); rolling accuracy charts; confusion matrix (for classification); calibration curves (confidence vs correctness); error distribution plots; toggle between ML metrics and trading metrics. These can live on the Model Detail page or a dedicated “Performance” tab; use existing chart library (e.g. Recharts, TradingView Lightweight Charts) and API data from Sprints 7–8 (performance metrics, prediction vs outcome).

## Mandatory skill usage

- Read `agents/skills/skills/using-superpowers/SKILL.md` first; then use as many of the following as apply: **model-evaluation**, **model-observability**, **dashboard-architect**, **explainability-ui**, **documentation-generator**. Aim for at least 5–7 skills.

## Reference docs (read-only)

- `docs/plans/specs/sprint-9-model-observatory-dashboard-spec.md`
- `docs/dashboard-spec.md`, `docs/design-guidelines.md`
- `apps/dashboard/` (existing charts, e.g. equity curve, stats cards)
- `plans/task_plan.md` (Sprint 9, ML Performance Visualization)
- API contracts for performance metrics (08-01), prediction vs outcome

## Allowed files (ONLY these)

- `apps/dashboard/` (new components for prediction vs actual, rolling accuracy, confusion matrix, calibration curves, error distribution; tabs or section on model detail)
- `packages/common/api_schemas.py` or `ml_schemas.py` (only if adding response types for chart data)
- `services/api/routers/` (only if adding endpoint for chart-ready performance data)

> If visualizations should live on a different page or use a different chart library, stop and ask to extend the Allowed Files list.

## Hard limits

- Do **not** run build, test, or verification commands.
- **If blocked:** Stop and ask (e.g. “Should calibration use binned confidence or raw values?”).

## Instructions

1. Use skills as above; read the spec and existing chart patterns in the dashboard.
2. Implement components for: prediction vs actual (e.g. scatter or line over time); rolling accuracy (e.g. line chart); confusion matrix (e.g. heatmap or table); calibration curves (confidence vs correctness); error distribution (e.g. histogram). Add a toggle or tab to switch between ML metrics and trading metrics if both are available.
3. Wire to API (performance metrics, prediction vs outcome) from Sprint 8 or use mock data; document expected API shape if not yet defined.
4. Place components on Model Detail page or a dedicated Performance tab; ensure styling matches dashboard.
5. If chart data shape is undefined, add a short design note in `docs/` and **pause for user input**.

## Done criteria

- ML-native visualizations (prediction vs actual, rolling accuracy, confusion matrix, calibration curves, error distribution) exist and render correctly; toggle between ML and trading metrics if applicable.
- Only allowed files were modified.
- Summarize changes in ≤5 bullets; add Implementation Summary if needed.
