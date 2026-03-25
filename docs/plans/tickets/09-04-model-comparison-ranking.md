# 09-04: Model Comparison & Ranking View

## Task

- Add a **Model Comparison & Ranking** view: side-by-side model comparison page; comparison dimensions (validation metrics, recent performance, drawdown, volatility); sorting/filtering (best performers, most stable, least risky); confidence stability and drift score comparison. Data from existing APIs (metrics, drift, baselines); UI only unless a small comparison endpoint is needed.

## Mandatory skill usage

- Read `agents/skills/skills/using-superpowers/SKILL.md` first; then use as many of the following as apply: **model-evaluation**, **model-observability**, **dashboard-architect**, **experiment-tracking**, **documentation-generator**. Aim for at least 5–7 skills.

## Reference docs (read-only)

- `docs/plans/specs/sprint-9-model-observatory-dashboard-spec.md`
- `docs/dashboard-spec.md`, `docs/design-guidelines.md`
- `docs/api-contracts.md` (metrics, drift, baselines)
- `apps/dashboard/` (existing list and comparison patterns)
- `plans/task_plan.md` (Sprint 9, Model Comparison & Ranking View)

## Allowed files (ONLY these)

- `apps/dashboard/` (new comparison page, e.g. `/models/compare`, components for side-by-side table/cards, sorting/filtering)
- `services/api/routers/` (only if adding a comparison endpoint that aggregates metrics/drift per model)
- `packages/common/api_schemas.py` or `ml_schemas.py` (only if adding comparison response types)

> If the comparison view should live elsewhere or use a different layout, stop and ask to extend the Allowed Files list.

## Hard limits

- Do **not** run build, test, or verification commands.
- **If blocked:** Stop and ask (e.g. “Which dimensions are required for the first release?”).

## Instructions

1. Use skills as above; read the spec and existing list/table patterns.
2. Add a Model Comparison page (e.g. `/models/compare`) or section: side-by-side comparison of models with columns/cards for validation metrics, recent performance, drawdown, volatility, confidence stability, drift score; sorting (e.g. by Sharpe, by drift); filtering (e.g. by status, type). Wire to existing metrics/drift/baseline APIs or use mock data.
3. Ensure users can rank models by multiple criteria (sortable columns or dropdown); document expected API shape if not defined.
4. Link from Model Registry or sidebar to comparison view; match dashboard styling.
5. If comparison dimensions or API are undefined, add a short design note in `docs/` and **pause for user input**.

## Done criteria

- Model comparison & ranking view exists; users can compare models side-by-side and rank by multiple criteria (validation metrics, performance, drawdown, volatility, confidence, drift).
- Only allowed files were modified.
- Summarize changes in ≤5 bullets; add Implementation Summary if needed.
