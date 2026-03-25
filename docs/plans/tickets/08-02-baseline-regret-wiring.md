# 08-02: Baseline & Regret Metrics Wiring

## Task

- Wire existing baselines (hold cash, buy & hold, random) in `services/ml/baselines/` to the live ML model strategy comparison; compute regret (strategy vs baselines) for the live model; store and expose regret metrics (e.g. via API or dashboard feed). Use existing `RegretCalculator` and baseline strategies; add API or storage only as needed.

## Mandatory skill usage

- Read `agents/skills/skills/using-superpowers/SKILL.md` first; then use as many of the following as apply: **model-evaluation**, **experiment-tracking**, **model-observability**, **backend-service-architect**, **dashboard-architect** (for API shape). Aim for at least 5 skills.

## Reference docs (read-only)

- `docs/plans/specs/sprint-8-observability-safety-spec.md`
- `plans/task_plan.md` (Sprint 8, Baseline & Regret Metrics)
- `services/ml/baselines/` (hold_cash, buy_and_hold, random, regret)
- `packages/common/ml_schemas.py` (BaselineComparisonResponse if present)
- `services/api/routers/baselines.py` (existing baseline comparison endpoint)

## Allowed files (ONLY these)

- `services/ml/baselines/` (wire to live model strategy; extend regret calculator if needed)
- `services/api/routers/baselines.py` (extend to include live model in comparison or add regret feed)
- `packages/common/ml_schemas.py` (response types for regret API)
- `docs/` (short note on regret metrics and API)

> If regret should be computed or stored elsewhere, stop and ask to extend the Allowed Files list.

## Hard limits

- Do **not** implement new baseline strategies in this ticket; use existing hold cash, buy & hold, random.
- Do **not** build dashboard UI in this ticket (Sprint 9); API and data only.
- Do **not** run build, test, or verification commands.
- **If blocked:** Stop and ask (e.g. “Should regret be computed over the same period as performance tracking?”).

## Instructions

1. Use skills as above; read the spec and `services/ml/baselines/`.
2. Wire the live ML model strategy’s performance (from 08-01 or equivalent) into the baseline comparison: compute regret vs hold cash, buy & hold, and random; store or expose via existing or new API (e.g. GET /v1/baselines/comparison with model_id or strategy_id).
3. Ensure model performance is contextualized vs baselines (regret metrics and/or outperforms flags); document the API and semantics in `docs/`.
4. If the comparison period or baseline run method is ambiguous, add a short design note and **pause for user input**.

## Done criteria

- Live model strategy is compared to existing baselines; regret metrics are computed and exposed (e.g. via API).
- Model performance is contextualized vs baselines (regret and/or outperforms).
- Only allowed files were modified.
- Summarize changes in ≤5 bullets; add Implementation Summary if needed.
