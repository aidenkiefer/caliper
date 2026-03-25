# 08-03: Confidence & Drift Monitoring

## Task

- Feed current feature (and confidence) distributions from the live inference path into the existing drift detector (`services/ml/drift/`); store reference (training) distributions for comparison; compute and store health score from drift signals; expose drift metrics and health via API (e.g. per model, per feature). Use existing PSI, KL, health score; add storage and API only as needed.

## Mandatory skill usage

- Read `agents/skills/skills/using-superpowers/SKILL.md` first; then use as many of the following as apply: **ml-pipeline-builder**, **feature-engineering**, **model-observability**, **anomaly-detection**, **backend-service-architect**, **database-schema-designer**, **caching-strategy**. Aim for at least 5–7 skills.

## Reference docs (read-only)

- `docs/plans/specs/sprint-8-observability-safety-spec.md`
- `plans/task_plan.md` (Sprint 8, Confidence & Drift Monitoring)
- `services/ml/drift/` (detector, metrics, health_score, alerts)
- `packages/common/ml_schemas.py` (DriftMetricsResponse, HealthScoreResponse)
- `services/api/routers/drift.py` (existing drift endpoints)
- Training path from Sprint 7 (where to obtain reference distributions)

## Allowed files (ONLY these)

- `services/ml/drift/` (wire to live data; store reference; compute health score)
- `services/api/routers/drift.py` (extend so drift/health are queryable per model)
- Inference/strategy path (only to feed current feature/confidence samples into drift)
- `packages/common/ml_schemas.py` (if response types need extension)
- `docs/` (short note on reference storage and API)

> If reference or current data should be stored or computed elsewhere, stop and ask to extend the Allowed Files list.

## Hard limits

- Do **not** build dashboard UI in this ticket (Sprint 9); API and data only.
- Do **not** run build, test, or verification commands.
- **If blocked:** Stop and ask (e.g. “Where should reference distributions be stored: at training time or in a separate job?”).

## Instructions

1. Use skills as above; read the spec and `services/ml/drift/`.
2. At training time (or via a one-off job), persist reference feature (and optionally confidence) distributions for the first model; document where they are stored (e.g. file, DB, config).
3. From the live inference path, feed current feature (and confidence) samples into the existing drift detector; compute drift metrics and health score; store results (e.g. per model, per feature, timestamped).
4. Expose drift metrics and health via API (e.g. extend GET /v1/drift/metrics/{model_id}, GET /v1/drift/health/{model_id}) so they are queryable per model.
5. If reference storage or sampling frequency is ambiguous, add a short design note and **pause for user input**.

## Done criteria

- Current feature/confidence distributions are fed into the drift detector; reference distributions are stored and used for comparison.
- Health score is computed from drift signals and stored; drift metrics and health are exposed via API per model.
- Only allowed files were modified.
- Summarize changes in ≤5 bullets; add Implementation Summary if needed.
