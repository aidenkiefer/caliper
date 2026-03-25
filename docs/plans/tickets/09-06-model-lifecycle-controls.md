# 09-06: Model Lifecycle Controls

## Task

- Add **model lifecycle controls** in the dashboard: activate / deactivate model; promote candidate → active workflow; retire model action; freeze parameters toggle; clone model config for new experiment. Wire to API (e.g. PATCH model status, POST clone) or stub; ensure UI reflects state (active, paused, retired, candidate) and actions are gated appropriately (e.g. cannot retire if active without confirm).

## Mandatory skill usage

- Read `agents/skills/skills/using-superpowers/SKILL.md` first; then use as many of the following as apply: **risk-control-logic**, **config-management**, **model-observability**, **dashboard-architect**, **documentation-generator**. Aim for at least 5–7 skills.

## Reference docs (read-only)

- `docs/plans/specs/sprint-9-model-observatory-dashboard-spec.md`
- `docs/dashboard-spec.md`, `docs/design-guidelines.md`
- `docs/api-contracts.md` (model lifecycle if defined)
- `apps/dashboard/` (Model Registry, Model Detail)
- `plans/task_plan.md` (Sprint 9, Model Lifecycle Controls)

## Allowed files (ONLY these)

- `apps/dashboard/` (lifecycle controls on Model Detail and/or Registry: buttons/menus for activate, pause, retire, promote, freeze, clone)
- `services/api/routers/` (only if adding or extending PATCH model status, POST clone, etc.)
- `packages/common/api_schemas.py` or `ml_schemas.py` (only if adding lifecycle action request/response types)

> If lifecycle states or actions differ from spec, stop and ask to extend the Allowed Files list or clarify semantics.

## Hard limits

- Do **not** run build, test, or verification commands.
- **If blocked:** Stop and ask (e.g. “Should retire require a reason or confirmation?”).

## Instructions

1. Use skills as above; read the spec and existing model UI (Registry, Detail).
2. Add lifecycle actions: Activate, Deactivate (pause), Retire, Promote (candidate → active), Freeze parameters, Clone config. Place on Model Detail page and/or Registry row actions; show confirmation for destructive or high-impact actions (e.g. retire). After action, refresh model state in UI (e.g. status badge, disabled actions).
3. Wire to API (PATCH model, POST clone) or stub; document expected API shape if new. Ensure lifecycle actions update model state correctly in the UI.
4. If lifecycle state machine or API is undefined, add a short design note in `docs/` and **pause for user input**.

## Done criteria

- Model lifecycle controls exist (activate, pause, retire, promote, freeze, clone); UI reflects state; lifecycle actions update model state correctly (or stubbed with doc).
- Only allowed files were modified.
- Summarize changes in ≤5 bullets; add Implementation Summary if needed.
