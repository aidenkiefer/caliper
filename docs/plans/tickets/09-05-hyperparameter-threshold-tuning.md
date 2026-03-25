# 09-05: Hyperparameter & Threshold Tuning Interface

## Task

- Add **dashboard controls** for hyperparameter and threshold tuning: confidence thresholds, abstention threshold, ensemble contribution caps, allocation limits; **change confirmation modal** with impact preview; **change logging and rollback** support. No live impact until user confirms; prefer read-and-preview first, then apply with logging. Backend can be stub (e.g. PATCH config endpoint) if not yet implemented.

## Mandatory skill usage

- Read `agents/skills/skills/using-superpowers/SKILL.md` first; then use as many of the following as apply: **risk-control-logic**, **config-management**, **model-observability**, **dashboard-architect**, **documentation-generator**. Aim for at least 5–7 skills.

## Reference docs (read-only)

- `docs/plans/specs/sprint-9-model-observatory-dashboard-spec.md`
- `docs/dashboard-spec.md`, `docs/design-guidelines.md`
- `docs/risk-policy.md` (limits and thresholds)
- `services/ml/confidence/gating.py` (confidence config)
- `packages/common/ml_schemas.py` (ConfidenceConfig, etc.)
- `plans/task_plan.md` (Sprint 9, Hyperparameter & Threshold Tuning Interface)

## Allowed files (ONLY these)

- `apps/dashboard/` (tuning UI: form/controls, confirmation modal, impact preview, rollback UI or link to change log)
- `services/api/routers/` (only if adding or extending PATCH config endpoint and change-log/rollback endpoint)
- `packages/common/api_schemas.py` or `ml_schemas.py` (only if adding request/response types for config update and rollback)

> If tuning should be model-scoped vs global, or if rollback semantics are different, stop and ask to extend the Allowed Files list.

## Hard limits

- Do **not** apply parameter changes to live trading without explicit user confirmation (modal with impact preview).
- Do **not** run build, test, or verification commands.
- **If blocked:** Stop and ask (e.g. “How should rollback be exposed: revert-last or select-version?”).

## Instructions

1. Use skills as above; read the spec, risk policy, and confidence config schemas.
2. Add UI for editing confidence thresholds, abstention threshold, ensemble caps, allocation limits (e.g. on Model Detail or a dedicated Tuning section): form fields with current values, “Preview” and “Apply” actions. On Apply, show confirmation modal with impact preview (e.g. “This will change abstain threshold from 0.55 to 0.6; N recommendations may change outcome”); require explicit confirm before calling API. Log changes (e.g. who, when, old/new values) and expose rollback (e.g. “Revert to previous” or list of changes with revert action).
3. Wire to PATCH config endpoint (or stub); document API contract if new. Ensure parameter changes are reflected in UI after apply (and after rollback if implemented).
4. If impact preview or rollback semantics are undefined, add a short design note in `docs/` and **pause for user input**.

## Done criteria

- Dashboard controls exist for confidence/abstention/ensemble/allocation; change confirmation modal with impact preview; change logging and rollback support (or documented placeholder).
- Only allowed files were modified.
- Summarize changes in ≤5 bullets; add Implementation Summary if needed.
