# Ticket: 15-02-threshold-regime-classifier

## Task
Implement the deterministic baseline `ThresholdRegimeClassifier` (AC-1) producing R1–R5 with correct override precedence.

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- services/regime/classifiers/threshold.py
- services/regime/schemas.py
- services/regime/__init__.py
- tests/unit/regime/test_threshold_classifier.py
- docs/plans/PROGRESS.md

### Required read-only references
- docs/plans/specs/sprint-15-regime-allocation-spec.md
- packages/common/polymarket_schemas.py (FeatureSnapshot fields)

### Optional read-only references
- docs/risk-policy.md (for “default reject / fail-safe” mindset)
- services/ml/probability_model/predictor.py (style + type patterns)

### Agent type (optional)
- backend-agent

## Skill pack (optional, keep small)
- Required: `quant-analyst`
- Optional: `risk-manager`

## Context + tool budget
- Max file reads: 8
- Max grep/glob operations: 6
- Max total tool calls: 12

## Done criteria
- `ThresholdRegimeClassifier` implements precedence exactly:
  1) R4 connectivity override (latency >= 2000ms OR heartbeat_miss_count >= 2)
  2) R5 dead market (spread_bps >= 500 OR min(book_depth_bid_5tick, book_depth_ask_5tick) < 10)
  3) R3 near-close toxic (time_to_close_seconds <= 600 OR toxicity_regime == "high" OR vpin_proxy >= 0.65)
  4) R2 choppy (btc_rv_5m >= 0.002 AND btc_sign_persistence_5m < 0.6)
  5) else R1 favorable
- Classifier returns:
  - `primary_regime: Literal["R1","R2","R3","R4","R5"]`
  - `regime_probabilities` as a one-hot dict (baseline output)
  - `source="threshold"`
- Unit tests cover all 5 regime assignments with explicit FeatureSnapshot-like inputs and explicit connectivity inputs (AC-1).
- `docs/plans/PROGRESS.md` updated with a brief dated completion note referencing ticket 15-02 completion.
