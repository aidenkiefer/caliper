# 09-09: Model Sandbox / What-If Testing

## Task

- Add **model sandbox / what-if** UI: parameter modification sandbox (no live impact); ability to rerun backtests with modified thresholds (or link to backtest run with modified config); temporarily disable models in sandbox; compare hypothetical allocations; preview effects before applying changes. Safe experimentation only; no live trading or config apply until user explicitly confirms outside sandbox. Backend can support “sandbox” runs (e.g. backtest with overridden config) or UI-only preview with documented limits.

## Mandatory skill usage

- Read `agents/skills/skills/using-superpowers/SKILL.md` first; then use as many of the following as apply: **risk-control-logic**, **config-management**, **model-observability**, **dashboard-architect**, **experiment-tracking**, **documentation-generator**. Aim for at least 5–7 skills.

## Reference docs (read-only)

- `docs/plans/specs/sprint-9-model-observatory-dashboard-spec.md`
- `docs/dashboard-spec.md`, `docs/design-guidelines.md`
- `plans/task_plan.md` (Sprint 9, Model Sandbox / What-If Testing)
- Backtest API (POST runs), config schema (confidence, thresholds)
- `apps/dashboard/` (runs, strategies, tuning UI)

## Allowed files (ONLY these)

- `apps/dashboard/` (sandbox page or section: parameter overrides, “Run backtest with these settings”, disable model in sandbox toggle, hypothetical allocation comparison, preview panel; clear “Sandbox” vs “Live” labeling)
- `services/api/routers/` (only if adding sandbox backtest endpoint or preview endpoint that accepts overridden config and returns metrics without persisting)
- `packages/common/api_schemas.py` or `ml_schemas.py` (only if adding request/response for sandbox run or preview)

> If sandbox should persist runs in a separate “sandbox” namespace or not call backtest at all, stop and ask to extend the Allowed Files list.

## Hard limits

- Do **not** allow sandbox actions to affect live trading or persisted production config without explicit user step outside sandbox (e.g. “Apply to live” with confirmation).
- Do **not** run build, test, or verification commands.
- **If blocked:** Stop and ask (e.g. “Should sandbox backtest runs be stored or ephemeral?”).

## Instructions

1. Use skills as above; read the spec and backtest/config APIs.
2. Add sandbox UI: (a) parameter modification (e.g. same controls as 09-05 but in “Sandbox” mode, values not applied to live); (b) “Rerun backtest with these settings” (e.g. POST backtest with overridden config, show results in sandbox); (c) “Disable model in sandbox” (e.g. toggle to exclude model from hypothetical allocation); (d) compare hypothetical allocations (e.g. side-by-side with current vs sandbox config); (e) preview effects (e.g. “If you apply these changes, abstention rate would change by X”). Clearly label Sandbox vs Live; require explicit “Apply to live” (or equivalent) with confirmation to leave sandbox.
3. Document sandbox behavior and limits in `docs/` (e.g. what is ephemeral, what is stored, how to apply to live).
4. If backtest API does not support overridden config or sandbox namespace, add a short design note in `docs/` and **pause for user input**.

## Done criteria

- Model sandbox / what-if UI exists: parameter sandbox (no live impact), rerun backtests with modified thresholds (or link/preview), disable models in sandbox, compare hypothetical allocations, preview before apply; safe experimentation without affecting live behavior.
- Only allowed files were modified.
- Summarize changes in ≤5 bullets; add Implementation Summary if needed.
