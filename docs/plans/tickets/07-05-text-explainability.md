# 07-05: Text-Based Explainability (Initial)

## Task

- Add a simple explanation payload (features used, confidence, short rationale) for each prediction and store it alongside predictions/trades. No SHAP or permutation importance in this ticket; human-readable text or structured fields only. Wire this into the inference path from 07-04 so every prediction has an explanation attached.

## Mandatory skill usage

- Read `agents/skills/skills/using-superpowers/SKILL.md` first; then use as many of the following as apply: **model-evaluation**, **explainability-ui** (for schema only), **model-observability**, **documentation-generator**, **backend-service-architect**. Aim for at least 5 skills.

## Reference docs (read-only)

- `docs/plans/specs/sprint-7-first-ml-model-spec.md`
- `packages/common/ml_schemas.py` (TradeExplanationResponse, FeatureContributionResponse if present)
- `services/ml/explainability/schemas.py`
- Inference path from 07-04 (where predictions are produced and logged)
- `plans/task_plan.md` (Sprint 7, Text-Based Explainability)

## Allowed files (ONLY these)

- `packages/common/ml_schemas.py` (extend or add explanation schema if needed)
- `services/ml/` (e.g. explanation builder that produces features_used, confidence, rationale from model/features)
- Inference/strategy code that produces predictions (only to attach and store explanation)
- `docs/` (short note on explanation format and storage)

> If explanations should be stored in a different service or schema, stop and ask to extend the Allowed Files list.

## Hard limits

- Do **not** implement SHAP or permutation importance in this ticket (Sprint 8).
- Do **not** edit `apps/dashboard/` or API routers in this ticket unless a single response type needs an optional explanation field already defined in api_schemas.
- Do **not** run build, test, or verification commands.
- **If blocked:** Stop and ask (e.g. “Where should explanations be stored: same table as predictions or separate?”).

## Instructions

1. Use skills as above; read the spec and existing explanation schemas.
2. Define a minimal explanation payload (e.g. features_used: list of names, confidence: float, rationale: str) and add or reuse types in `packages/common/ml_schemas.py` or `services/ml/explainability/schemas.py`.
3. In the inference path (from 07-04), after each prediction, build the explanation (e.g. from feature names and model confidence; rationale can be a simple template or one-line summary) and store it with the prediction (same log/DB or linked by id).
4. Document the explanation format and storage location in `docs/` (e.g. `docs/sprint-7-explainability-format.md` or a section in the spec).

## Done criteria

- Every prediction from the first model has a human-readable explanation (features used, confidence, rationale) stored alongside it.
- Explanation schema is defined and used in the inference path; format and storage are documented.
- Only allowed files were modified.
- Summarize changes in ≤5 bullets; add Implementation Summary if needed.
