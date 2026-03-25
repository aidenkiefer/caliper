# 09-02: Model Detail Page

## Task

- Add a **Model Detail** page: model overview (architecture, feature set, hyperparams); training & validation summary (period, method, metrics, overfitting indicators); live/paper performance (accuracy over time, abstention rate); confidence calibration plots. Data can come from existing or new API (e.g. GET model by id); use mock data if API is not yet defined. One page per model; linked from Model Registry (09-01).

## Mandatory skill usage

- Read `agents/skills/skills/using-superpowers/SKILL.md` first; then use as many of the following as apply: **model-observability**, **model-evaluation**, **dashboard-architect**, **explainability-ui**, **documentation-generator**. Aim for at least 5–7 skills.

## Reference docs (read-only)

- `docs/plans/specs/sprint-9-model-observatory-dashboard-spec.md`
- `docs/dashboard-spec.md`, `docs/design-guidelines.md`
- `packages/common/ml_schemas.py`, `api_schemas.py`
- `apps/dashboard/` (existing detail pages e.g. runs/[id], strategies/[id])
- `plans/task_plan.md` (Sprint 9, Model Detail Page)

## Allowed files (ONLY these)

- `apps/dashboard/` (new model detail page, e.g. `models/[id]/page.tsx`, components, hooks)
- `services/api/routers/` (only if adding or extending GET model by id / detail endpoint)
- `packages/common/api_schemas.py` or `ml_schemas.py` (only if adding detail response types)

> If the detail page or API should live elsewhere, stop and ask to extend the Allowed Files list.

## Hard limits

- Do **not** implement backend model storage or training pipeline in this ticket; consume existing or mock API.
- Do **not** run build, test, or verification commands.
- **If blocked:** Stop and ask (e.g. “What fields should the model detail API return?”).

## Instructions

1. Use skills as above; read the spec and existing detail page patterns (e.g. run detail, strategy detail).
2. Add Model Detail route (e.g. `/models/[id]`) with sections: overview (architecture, feature set, hyperparams); training & validation summary (period, method, metrics, overfitting indicators); live/paper performance (accuracy over time, abstention rate); confidence calibration (e.g. chart or table). Use placeholders or mock data if API is not defined.
3. Link from Model Registry list (view details) to this page; ensure layout and styling match existing dashboard.
4. If API shape for model detail is undefined, add a short design note in `docs/` and **pause for user input** before implementing charts against mock data.
5. Document the page sections and expected data shape for future tickets.

## Done criteria

- Model Detail page exists with overview, training/validation summary, live performance, and confidence calibration sections; full model context visible on one page.
- Only allowed files were modified.
- Summarize changes in ≤5 bullets; add Implementation Summary if needed.
