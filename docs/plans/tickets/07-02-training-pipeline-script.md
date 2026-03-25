# 07-02: Training & Validation Pipeline Script

## Task

- Implement an offline training script that: (1) loads data and features, (2) performs a time-aware train/validation split (walk-forward or sliding window), (3) prevents data leakage explicitly, (4) trains the first model (e.g. logistic regression or small tree), (5) logs training and validation metrics. Reproducibility (e.g. seed) and logging are required; no UI or API changes.

## Mandatory skill usage

- Read `agents/skills/skills/using-superpowers/SKILL.md` first; then use as many of the following as apply: **ml-pipeline-builder**, **feature-engineering**, **time-series-ml**, **model-evaluation**, **experiment-tracking**, **data-leakage-detector**, **config-management**, **documentation-generator**. Aim for at least 5–7 skills.

## Reference docs (read-only)

- `docs/plans/specs/sprint-7-first-ml-model-spec.md`
- `docs/sprint-7-ml-problem-definition.md` (must exist from 07-01; if missing, stop and ask)
- `plans/task_plan.md` (Sprint 7, Training & Validation Pipeline)
- `services/features/pipeline.py` (feature pipeline)
- `packages/common/schemas.py` (PriceBar, etc.)

## Allowed files (ONLY these)

- `services/ml/` (new or existing modules under this package only: e.g. `training/`, `train_*.py`)
- `packages/common/ml_schemas.py` (only if new schema types are required for training config or logged metrics)
- `configs/` (only if adding a training config file, e.g. `configs/training/first_model.yaml`)
- `docs/` (only to add a short “how to run training” note if needed)

> If the script or config should live elsewhere, stop and ask to extend the Allowed Files list.

## Hard limits

- Do **not** edit `services/api/`, `apps/dashboard/`, `packages/strategies/`, or `services/backtest/engine.py` in this ticket.
- Do **not** run build, test, or verification commands.
- **If blocked:** Stop and ask (e.g. “Where should the trained model artifact be written?”).

## Instructions

1. Use skills as above; read the spec and `docs/sprint-7-ml-problem-definition.md`.
2. Implement a training script (e.g. `services/ml/training/train_first_model.py` or equivalent) that: loads bars/features, builds labels per the problem definition, performs time-aware train/val split, trains the model, logs metrics (e.g. to stdout or a file), and saves the model artifact (path per config or spec).
3. Explicitly prevent data leakage (e.g. no future data in features, split by time).
4. Add minimal config or CLI args (e.g. symbol, date range, split parameters) so the run is reproducible; document in a short doc or docstring how to run it.
5. If the problem definition doc is missing or ambiguous on split or labels, write a short design note in `docs/` and **pause for user input** before implementing.

## Done criteria

- Offline training script exists under `services/ml/` and can be run (e.g. `poetry run python -m services.ml.training.train_first_model ...` or equivalent).
- Time-aware train/validation split is implemented; data leakage is explicitly avoided.
- Training and validation metrics are logged (e.g. accuracy, loss, or metrics from the problem definition).
- Only allowed files were modified.
- Summarize changes in ≤5 bullets; add Implementation Summary if needed.
