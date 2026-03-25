# 07-04: Inference Integration

## Task

- Wire model inference into the live/paper pipeline: load the trained model (from 07-02), run inference on features (from feature pipeline or strategy), produce model output (per 07-03), pass through confidence gating (existing `services/ml/confidence/`), convert to Signals, and feed into existing risk and execution layers. Log predictions, confidence, and decisions (e.g. to DB or structured logs). No dashboard UI changes in this ticket.

## Mandatory skill usage

- Read `agents/skills/skills/using-superpowers/SKILL.md` first; then use as many of the following as apply: **ml-pipeline-builder**, **feature-engineering**, **risk-control-logic**, **abstention-logic**, **backend-service-architect**, **async-systems**, **config-management**, **model-observability**. Aim for at least 5–7 skills.

## Reference docs (read-only)

- `docs/plans/specs/sprint-7-first-ml-model-spec.md`
- `docs/sprint-7-ml-problem-definition.md`
- `packages/common/ml_schemas.py`, `packages/common/schemas.py`
- `services/ml/confidence/gating.py`
- `packages/strategies/base.py` (Strategy, Signal, risk_check)
- `services/execution/`, `services/risk/` (how orders are validated and sent)
- `plans/task_plan.md` (Sprint 7, Inference Integration)

## Allowed files (ONLY these)

- `packages/strategies/` (e.g. new ML strategy or adapter that calls model + gating and returns Signals)
- `services/ml/` (inference loader, adapter from model output to Signal; logging)
- `services/features/pipeline.py` (only if needed to expose feature computation for inference; prefer minimal change)
- `configs/strategies/` (only if adding a strategy config for the ML strategy)
- `packages/common/ml_schemas.py` or `packages/common/schemas.py` (only if a small extension is required for logging)

> If inference should live in a dedicated service instead of inside a strategy, stop and ask to extend the Allowed Files list.

## Hard limits

- Do **not** edit `services/backtest/engine.py` in this ticket unless strictly required to support an ML strategy (e.g. feature pipeline in loop); if required, minimize scope and stop if blocked.
- Do **not** edit `apps/dashboard/` in this ticket.
- Do **not** run build, test, or verification commands.
- **If blocked:** Stop and ask (e.g. “Should inference run inside Strategy.generate_signals or in a separate service?”).

## Instructions

1. Use skills as above; read the spec, model contract, confidence gating, and execution/risk flow.
2. Implement a path where: (a) trained model is loaded (artifact path from config or env), (b) features are produced (from feature pipeline or strategy-held state), (c) model predicts, (d) output is passed through confidence gating (existing code), (e) result is converted to `Signal`(s) and passed to `risk_check` then execution. Prefer implementing an ML strategy (e.g. under `packages/strategies/`) that uses the feature pipeline and model so backtest and live share the same interface.
3. Log predictions, confidence, and decisions (e.g. to a file, DB table, or structured log) so they can be queried later; schema should support “who predicted what, when, and with what confidence.”
4. If the artifact path or logging destination is undefined, add a short design note in `docs/` and **pause for user input**.

## Done criteria

- Model inference runs in the live/paper pipeline (strategy or dedicated path); model output flows through confidence gating → Signals → risk → execution.
- Predictions, confidence, and decisions are logged (schema and location documented or in config).
- Only allowed files were modified.
- Summarize changes in ≤5 bullets; add Implementation Summary if needed.
