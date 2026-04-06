# Ticket: 15-03-hmm-regime-classifier-and-trainer

## Task
Implement `HMMRegimeClassifier` (Gaussian HMM via `hmmlearn`) and a minimal `HMMTrainer` scaffold; include synthetic-data training tests for AC-2.

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- services/regime/classifiers/hmm.py
- services/regime/trainer.py
- services/regime/schemas.py
- pyproject.toml
- requirements.txt
- tests/unit/regime/test_hmm_classifier.py
- docs/plans/PROGRESS.md

### Required read-only references
- docs/plans/specs/sprint-15-regime-allocation-spec.md
- packages/common/polymarket_schemas.py (feature names; global vector `G_t` inputs)

### Optional read-only references
- docs/research/regime-allocation.md
- docs/plans/specs/sprint-12-feature-layer-spec.md (feature availability context)

### Agent type (optional)
- backend-agent

## Skill pack (optional, keep small)
- Required: `statsmodels`
- Optional: `scikit-learn` (KMeans init, Ledoit-Wolf familiarity)

## Context + tool budget
- Max file reads: 8
- Max grep/glob operations: 6
- Max total tool calls: 12

## Done criteria
- `HMMRegimeClassifier`:
  - Encodes `G_t` as a fixed-order numeric vector from FeatureSnapshot (document exact column order in-code).
  - Wraps `hmmlearn.hmm.GaussianHMM` with `K=4`, full covariance.
  - Exposes `predict_proba(snapshot | X)` returning posterior probs over 4 hidden states (sum to 1.0).
- `HMMTrainer` scaffold:
  - Provides `fit(X)` and persists (in-memory for now) the fitted model + mapping from hidden state -> semantic regime (`R1`/`R2`/`R3` only; `R4`/`R5` remain threshold-only).
  - Implements **KMeans initialization** for consistent state assignments (per spec).
- Tests (AC-2):
  - Synthetic 30-day data generation (seeded) -> fit succeeds without error.
  - Posterior probabilities sum to 1.0 for each row.
  - KMeans init determinism: identical synthetic input + seed -> same initial assignments.
- `requirements.txt` and `pyproject.toml` include `hmmlearn` + `statsmodels` (if not already done in 15-01).
- `docs/plans/PROGRESS.md` updated with a brief dated completion note referencing ticket 15-03 completion.
