# 07-01: ML Problem Definition (Documentation)

## Task

- Define and document the ML problem for the first model: target variable, prediction horizon, label construction logic, evaluation metrics, assumptions, and failure modes.
- Produce a single planning document in `docs/` that serves as the source of truth for Sprint 7 implementation. No code changes in this ticket.

## Mandatory skill usage

- Read `agents/skills/skills/using-superpowers/SKILL.md` first; then use as many of the following as apply: **ml-pipeline-builder**, **feature-engineering**, **time-series-ml**, **model-evaluation**, **experiment-tracking**, **data-leakage-detector**, **documentation-generator**. Aim for at least 5 skills.

## Reference docs (read-only)

- `docs/plans/specs/sprint-7-first-ml-model-spec.md`
- `plans/task_plan.md` (Sprint 7 section)
- `deep-review.md` (sections 1 and 5)
- `docs/architecture.md` (strategy and feature pipeline)
- `services/features/pipeline.py` (available features)

## Allowed files (ONLY these)

- `docs/sprint-7-ml-problem-definition.md` (create or overwrite)

> If the problem definition should live elsewhere (e.g. under `docs/plans/`), stop and ask to extend the Allowed Files list.

## Hard limits

- Do **not** edit any Python or TypeScript code in this ticket.
- Do **not** run build, test, or verification commands.
- **If blocked:** Stop and ask for input (e.g. “Should the target be directional or return-based?”).

## Instructions

1. Use skills as above; read the spec and reference docs.
2. Draft the ML problem definition: target variable (e.g. probability of positive return over N bars, or binary direction), prediction horizon, label construction (how labels are built from price/returns), evaluation metrics (classification or regression), assumptions (e.g. single symbol, no options), and failure modes (e.g. no data, stale model).
3. Write the document to `docs/sprint-7-ml-problem-definition.md`. Include clear sections so later tickets can implement against it.
4. If any high-impact choice is ambiguous (e.g. N bars, symbol universe), state options and **pause for user input** in your response rather than guessing.

## Done criteria

- `docs/sprint-7-ml-problem-definition.md` exists and contains: target variable, prediction horizon, label construction, evaluation metrics, assumptions, failure modes.
- Only the allowed file was created or modified.
- If choices were ambiguous, user was asked for input and not guessed.
- Summarize the document in ≤5 bullets in the ticket or in an Implementation Summary.
