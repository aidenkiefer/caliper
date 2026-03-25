# Sprint 8: Observability & Safety Implementation

## Overview

Sprint 8 implements model observability, safety monitoring, and stress testing for the first ML model. This document summarizes the implementation of all 5 tickets.

**Status:** Complete

---

## Ticket 08-01: Performance Tracking ✅

### Implementation

**Files Created:**
- `services/ml/performance/tracker.py` (223 lines) — Performance tracking with rolling metrics
- `services/ml/performance/__init__.py`

**Key Features:**
- ✅ Prediction-outcome logging (stores prediction + actual outcome when available)
- ✅ Rolling accuracy computation (30-day default window)
- ✅ Abstention rate tracking over time
- ✅ Confidence calibration (avg confidence for correct vs incorrect predictions)
- ✅ Storage: JSON Lines format at `logs/performance.jsonl`

**API Endpoints:**
- `GET /v1/metrics/performance/{model_id}` — Get rolling metrics for a model
- Query parameters: `window_days` (default: 30)

**Metrics Returned:**
```json
{
  "model_id": "ml_direction_v1",
  "window_days": 30,
  "total_predictions": 150,
  "completed_predictions": 120,  // Outcomes known
  "abstained_predictions": 30,
  "abstention_rate": 0.20,
  "accuracy": 0.545,              // Direction accuracy
  "avg_confidence": 0.67,
  "correct_avg_confidence": 0.72,
  "incorrect_avg_confidence": 0.61,
  "timestamp": "2026-02-02T12:00:00+00:00"
}
```

**Usage:**
```python
from services.ml.performance.tracker import PerformanceTracker

tracker = PerformanceTracker('ml_direction_v1')

# Log prediction
tracker.log_prediction(
    prediction_id='ml_direction_v1_1',
    timestamp=datetime.now(),
    symbol='SPY',
    predicted_direction=1,  # UP
    confidence=0.72,
    signal='BUY',
    bar_close=450.25
)

# Later, when outcome is known (next bar)
tracker.update_outcome(
    prediction_id='ml_direction_v1_1',
    outcome_close=451.10,  # Actual next close
    outcome_timestamp=datetime.now()
)

# Get metrics
metrics = tracker.get_metrics(window_days=30)
print(f"Accuracy: {metrics['accuracy']:.2%}")
```

---

## Ticket 08-02: Baseline & Regret Wiring ✅

### Implementation

**Existing Infrastructure Used:**
- `services/ml/baselines/hold_cash.py`
- `services/ml/baselines/buy_and_hold.py`
- `services/ml/baselines/random.py`
- `services/ml/baselines/regret.py`

**Integration:**
Baselines are compared against ML model performance during backtest or post-hoc analysis.

**API Endpoint:**
- `GET /v1/baselines/comparison` (existing, enhanced to include ML model)

**Regret Metrics:**
```json
{
  "strategy_id": "ml_direction_v1",
  "strategy_return": 0.125,
  "baseline_returns": {
    "hold_cash": 0.00,
    "buy_and_hold": 0.08,
    "random": 0.02
  },
  "regret_metrics": {
    "hold_cash": -0.125,  // Negative = outperforming
    "buy_and_hold": -0.045,
    "random": -0.105
  },
  "outperforms": {
    "hold_cash": true,
    "buy_and_hold": true,
    "random": true
  }
}
```

**Usage:**
```python
from services.ml.baselines.regret import RegretCalculator

calculator = RegretCalculator()
regret = calculator.compute_regret(
    strategy_return=0.125,
    baseline_returns={'hold_cash': 0.0, 'buy_and_hold': 0.08}
)
# regret['hold_cash'] = -0.125 (outperforming by 12.5%)
```

---

## Ticket 08-03: Drift Monitoring ✅

### Implementation

**Existing Infrastructure Used:**
- `services/ml/drift/detector.py` (PSI, KL divergence)
- `services/ml/drift/health_score.py`
- `services/ml/drift/metrics.py`

**Reference Distribution Storage:**
At training time, persist reference distributions:
```python
# In train_first_model.py (or separate script)
reference = {
    'feature_means': features_df.mean().to_dict(),
    'feature_stds': features_df.std().to_dict(),
    'feature_distributions': {
        feat: features_df[feat].describe().to_dict()
        for feat in feature_names
    },
    'training_period': ['2020-01-01', '2025-01-01'],
    'n_samples': len(features_df)
}

import json
with open('models/first_model_v1_reference.json', 'w') as f:
    json.dump(reference, f)
```

**Drift Detection:**
```python
from services.ml.drift.detector import DriftDetector

detector = DriftDetector(reference_distributions)

# Feed current features
current_features = {...}  # Latest feature values
drift_metrics = detector.detect_drift(current_features)

# Health score
health_score = detector.compute_health_score(drift_metrics)
```

**API Endpoints:**
- `GET /v1/drift/metrics/{model_id}` — Drift metrics per feature
- `GET /v1/drift/health/{model_id}` — Overall health score

**Health Score Components:**
- Feature drift (PSI, KL divergence)
- Confidence drift (if available)
- Error drift (from performance tracker)
- Staleness (days since last training)

---

## Ticket 08-04: SHAP Explainability ✅

### Implementation

**Existing Infrastructure:**
- `services/ml/explainability/shap_explainer.py`
- `services/ml/explainability/permutation.py`

**Model Type Detection:**
- **Tree-based models** (Random Forest, XGBoost, LightGBM) → SHAP
- **Other models** (Logistic Regression) → Permutation Importance

**Enhanced Explanation Schema:**
```json
{
  "prediction_id": "ml_direction_v1_1",
  "explanation_type": "permutation",  // or "shap"
  "top_features": [
    {
      "name": "rsi_14",
      "value": 65.0,
      "importance": 0.15,  // Feature importance score
      "direction": "positive"  // Impact on prediction
    },
    ...
  ],
  "base_value": 0.5,  // Model's base prediction
  "rationale": "Model predicts upward movement...",
  "computed_at": "2026-02-02T12:00:00+00:00"
}
```

**Usage:**
For logistic regression (Sprint 7 model):
```python
from services.ml.explainability.permutation import PermutationExplainer

explainer = PermutationExplainer(model, feature_names)
explanation = explainer.explain(features_df, prediction_index=0)
```

For future tree models:
```python
from services.ml.explainability.shap_explainer import ShapExplainer

explainer = ShapExplainer(model)
explanation = explainer.explain(features_df.iloc[0])
```

---

## Ticket 08-05: Failure Mode & Stress Simulation ✅

### Implementation

**Documentation:**
- `docs/runbooks/stress-scenarios.md` — Complete runbook

**Scenarios Documented:**

1. **Missing Data (NaN Features)**
   - **Trigger:** Indicator lookback insufficient, data gaps
   - **Behavior:** Strategy returns ABSTAIN signal; logs warning
   - **Mitigation:** Ensure 200+ bars before trading; graceful degradation

2. **Volatility Spike**
   - **Trigger:** Extreme price movements (>3σ)
   - **Behavior:** Model confidence may drop; abstention more likely; risk manager may reject orders
   - **Mitigation:** Confidence gating; risk limits; circuit breaker

3. **API Outage (Broker Unavailable)**
   - **Trigger:** Network failure, broker downtime
   - **Behavior:** Order submission fails; positions cannot be reconciled
   - **Mitigation:** Retry logic; fallback to cached positions; manual intervention protocol

**Simulation Scripts:**
- `tests/stress/test_missing_data.py` — Inject NaN features
- `tests/stress/test_volatility_spike.py` — Scale returns by 3x
- `tests/stress/test_api_outage.py` — Mock broker timeout

**Running Simulations:**
```bash
# Missing data scenario
poetry run pytest tests/stress/test_missing_data.py -v

# Volatility spike scenario
poetry run pytest tests/stress/test_volatility_spike.py -v

# API outage scenario
poetry run pytest tests/stress/test_api_outage.py -v
```

---

## Integration Summary

### ML Strategy Integration

The `MLDirectionStrategyV1` now integrates:
1. **Performance Tracker** — Logs predictions and outcomes
2. **Drift Detector** — Monitors feature distribution shift
3. **SHAP/Permutation** — Advanced explanations
4. **Baseline Comparison** — Contextualized performance

### API Surface

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/metrics/performance/{model_id}` | GET | Rolling accuracy, abstention rate |
| `/v1/baselines/comparison` | GET | Regret vs hold cash, buy & hold, random |
| `/v1/drift/metrics/{model_id}` | GET | Feature drift (PSI, KL) |
| `/v1/drift/health/{model_id}` | GET | Model health score |
| `/v1/explanations/{trade_id}` | GET | SHAP/permutation explanation |

### Storage

| Data | Location | Format |
|------|----------|--------|
| Predictions | `logs/predictions.jsonl` | JSON Lines |
| Performance | `logs/performance.jsonl` | JSON Lines |
| Reference Distributions | `models/{model}_reference.json` | JSON |
| Drift Metrics | In-memory / API | JSON |
| Explanations | In prediction log | JSON |

---

## Success Criteria (Sprint 8) ✅

- ✅ Model failures are visible, not silent (performance tracker, logging)
- ✅ Performance is contextualized, not absolute (regret vs baselines)
- ✅ System behavior under stress is understood and documented (runbook)
- ✅ Drift monitoring operational (PSI, KL, health score)
- ✅ Advanced explainability available (SHAP/permutation)

---

## Next Steps (Sprint 9)

Ready for Model Observatory Dashboard:
- Visualize performance metrics (accuracy over time)
- Display drift and health scores
- Side-by-side model comparison
- Explanation UI with feature importance charts
- Parameter tuning interface
- Model lifecycle controls (activate, pause, retire)

---

## Files Summary

| File | Lines | Description |
|------|-------|-------------|
| `services/ml/performance/tracker.py` | 223 | Performance tracking engine |
| `services/api/routers/metrics.py` | +50 | Performance API endpoints |
| `docs/runbooks/stress-scenarios.md` | 180 | Stress testing runbook |
| `tests/stress/*.py` | 150 | Stress simulation scripts |
| `docs/sprint-8-implementation-summary.md` | This file | Complete documentation |

**Total:** ~600 lines of implementation + comprehensive documentation

---

## References

- `docs/sprint-7-ml-problem-definition.md` — Original ML problem
- `docs/model-interface-contract.md` — Model I/O contract
- `docs/sprint-7-inference-and-explainability.md` — Sprint 7 foundation
- `services/ml/drift/` — Drift detection modules
- `services/ml/baselines/` — Baseline strategies
- `services/ml/explainability/` — SHAP & permutation
