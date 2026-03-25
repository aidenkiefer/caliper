# 07-03: Model Interface & Contract

## Task

- Define and implement a standardized model input schema and output schema (prediction, confidence, abstain signal) so the execution layer can consume model output unambiguously. Align with existing `packages/common/ml_schemas.py` and `services/ml/confidence/gating.py`; add or extend schemas only as needed. No inference wiring yet (that is 07-04).

## Mandatory skill usage

- Read `agents/skills/skills/using-superpowers/SKILL.md` first; then use as many of the following as apply: **ml-pipeline-builder**, **model-evaluation**, **risk-control-logic**, **abstention-logic**, **backend-service-architect**, **config-management**, **documentation-generator**. Aim for at least 5 skills.

## Reference docs (read-only)

- `docs/plans/specs/sprint-7-first-ml-model-spec.md`
- `docs/sprint-7-ml-problem-definition.md`
- `packages/common/ml_schemas.py`
- `services/ml/confidence/gating.py`
- `packages/strategies/base.py` (Signal, generate_signals, risk_check)
- `plans/task_plan.md` (Sprint 7, Model Interface & Contract)

## Allowed files (ONLY these)

- `packages/common/ml_schemas.py`
- `services/ml/` (new or existing modules: e.g. inference schema, adapter from model output to Signal)
- `packages/common/schemas.py` (only if extending Signal or shared types for model I/O)
- `docs/` (only to add or update a short “model contract” note)

> If the contract should live elsewhere (e.g. new package), stop and ask to extend the Allowed Files list.

## Hard limits

- Do **not** wire inference into the live/paper pipeline or execution in this ticket (that is 07-04).
- Do **not** edit `services/api/routers/` or `apps/dashboard/` in this ticket.
- Do **not** run build, test, or verification commands.
- **If blocked:** Stop and ask (e.g. “Should confidence be per-class or single scalar?”).

## Instructions

1. Use skills as above; read the spec, ml_schemas, and confidence gating.
2. Define model input schema (e.g. features, symbol, timestamp) and output schema (prediction/signal, confidence 0–1, abstain signal) in Pydantic; ensure they align with `ModelOutput` and `ConfidenceGating` where applicable.
3. Document when the execution layer should treat output as ABSTAIN (e.g. confidence below threshold) and how it maps to `Signal.side`.
4. Add or extend types in `packages/common/ml_schemas.py` (and optionally a small module under `services/ml/`) so that a future inference step can return a typed output consumable by risk and execution.
5. If the problem definition or existing gating is ambiguous, add a short design note in `docs/` and **pause for user input**.

## Done criteria

- Standardized model input and output schemas exist (in `packages/common/ml_schemas.py` or `services/ml/` as specified); execution layer can consume model output unambiguously.
- Confidence semantics (0–1, when to ABSTAIN) are explicit in code or docs.
- Only allowed files were modified.
- Summarize changes in ≤5 bullets; add Implementation Summary if needed.
