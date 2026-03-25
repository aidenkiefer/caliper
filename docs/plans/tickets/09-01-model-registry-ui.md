# 09-01: Model Registry UI

## Task

- Add a dedicated **Model Registry** page in the dashboard: list view with sorting/filtering; display name, type, status, trained date, health score, allocation weight; quick actions (activate, pause, view details). Use existing API or extend with a model-list endpoint if needed; consume response in dashboard. No backend model registry implementation beyond what Sprints 7–8 provide; UI and API client only.

## Mandatory skill usage

- Read `agents/skills/skills/using-superpowers/SKILL.md` first; then use as many of the following as apply: **model-observability**, **dashboard-architect**, **explainability-ui**, **config-management**, **documentation-generator**. Aim for at least 5–7 skills.

## Reference docs (read-only)

- `docs/plans/specs/sprint-9-model-observatory-dashboard-spec.md`
- `docs/dashboard-spec.md`, `docs/design-guidelines.md`
- `docs/api-contracts.md` (model/metadata endpoints if defined)
- `apps/dashboard/` (existing layout, sidebar, pages, components)
- `plans/task_plan.md` (Sprint 9, Model Registry UI)

## Allowed files (ONLY these)

- `apps/dashboard/` (new page, components, hooks for model registry)
- `services/api/routers/` (only if adding or extending a model-list endpoint for registry data)
- `packages/common/api_schemas.py` or `ml_schemas.py` (only if adding response types for model list)

> If the registry page or API should live elsewhere, stop and ask to extend the Allowed Files list.

## Hard limits

- Do **not** implement backend model registry CRUD or persistence in this ticket unless a single endpoint is required for the list; prefer mock or existing data shape.
- Do **not** run build, test, or verification commands.
- **If blocked:** Stop and ask (e.g. “What API shape should the model list return?”).

## Instructions

1. Use skills as above; read the spec and dashboard-spec.
2. Add a Model Registry route (e.g. `/models` or `/observatory/models`) and page: list view with columns for name, type, status, trained date, health score, allocation weight; sorting and filtering (e.g. by status, type); quick actions (activate, pause, view details — can be placeholders or wire to API if defined).
3. Add sidebar/nav entry for Model Registry; ensure layout and styling match existing dashboard (Shadcn/UI, Tailwind, dark mode).
4. If API for model list is undefined, add a short design note in `docs/` (e.g. `docs/sprint-9-model-registry-api.md`) and **pause for user input** on API shape before implementing UI against mock data.
5. Document the page and data shape in a short doc or inline comment so future tickets can extend it.

## Done criteria

- Model Registry page exists; list view shows name, type, status, trained date, health score, allocation weight with sorting/filtering and quick actions.
- Only allowed files were modified.
- Summarize changes in ≤5 bullets; add Implementation Summary if needed.
