# 08-04: Explainability (Advanced) — SHAP

## Task

- Integrate SHAP (or permutation importance) for the deployed model’s predictions using existing `services/ml/explainability/`; store explanation payload per prediction/recommendation; expose explanation via API (e.g. existing GET /v1/explanations/{trade_id} or equivalent) so each recommendation has an explanation. Prefer SHAP for tree-based models; use permutation as fallback if needed.

## Mandatory skill usage

- Read `agents/skills/skills/using-superpowers/SKILL.md` first; then use as many of the following as apply: **ml-pipeline-builder**, **model-evaluation**, **explainability-ui** (for schema/API), **model-observability**, **backend-service-architect**, **documentation-generator**. Aim for at least 5–7 skills.

## Reference docs (read-only)

- `docs/plans/specs/sprint-8-observability-safety-spec.md`
- `plans/task_plan.md` (Sprint 8, Explainability Advanced)
- `services/ml/explainability/` (shap_explainer, permutation, schemas)
- `packages/common/ml_schemas.py` (TradeExplanationResponse, FeatureContributionResponse)
- `services/api/routers/explanations.py` (existing explanation endpoint)
- Sprint 7 inference path (where predictions and text explanations are produced)

## Allowed files (ONLY these)

- `services/ml/explainability/` (wire SHAP/permutation to deployed model and inference path)
- Inference/strategy path (only to call explainer and store explanation with prediction/trade)
- `services/api/routers/explanations.py` (ensure explanation is available per recommendation/trade)
- `packages/common/ml_schemas.py` (if response types need extension)
- `docs/` (short note on SHAP vs permutation and storage)

> If explanations should be computed in a different service or stored elsewhere, stop and ask to extend the Allowed Files list.

## Hard limits

- Do **not** build dashboard UI in this ticket (Sprint 9); API and storage only.
- Do **not** run build, test, or verification commands.
- **If blocked:** Stop and ask (e.g. “Should we compute SHAP at inference time or in a batch job?”).

## Instructions

1. Use skills as above; read the spec and `services/ml/explainability/`.
2. Wire the deployed model (from Sprint 7) and feature vector into `ShapExplainer` (or permutation explainer) at the point where predictions are produced; generate a structured explanation (e.g. top features, contribution, direction) per prediction.
3. Store the explanation with the prediction/trade (same store as 07-05 or linked by id) and ensure it is retrievable via API (e.g. GET /v1/explanations/{trade_id} or by recommendation_id).
4. Document when SHAP vs permutation is used (e.g. tree model → SHAP; other → permutation) and any performance considerations in `docs/`.
5. If compute cost or storage format is ambiguous, add a short design note and **pause for user input**.

## Done criteria

- SHAP (or permutation) explanation is generated for the deployed model’s predictions and stored per prediction/recommendation.
- Explanation is available for each recommendation (e.g. via API or trade record).
- Only allowed files were modified.
- Summarize changes in ≤5 bullets; add Implementation Summary if needed.
