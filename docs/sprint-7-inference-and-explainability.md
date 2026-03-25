# Sprint 7: Inference Integration & Explainability

## Overview

This document describes the implementation of tickets 07-04 (Inference Integration) and 07-05 (Text-Based Explainability) for the first ML model in the Caliper trading platform.

**Status:** Implemented

---

## Architecture

### Data Flow

```
Price Bars → Strategy.on_market_data()
                ↓
            Price History (buffer)
                ↓
        Strategy.generate_signals()
                ↓
        FeaturePipeline.compute_features()
                ↓
        Feature Dictionary (34 features)
                ↓
        ModelInferenceAdapter.predict_and_convert()
                ↓
        Model Prediction → Confidence Gating → Signal (BUY/SELL/ABSTAIN)
                ↓
        SimpleExplainer.explain()
                ↓
        Prediction Log (JSON Lines)
                ↓
        Risk Check → Orders → Execution
```

---

## Implementation Components

### 1. ML Strategy (Ticket 07-04)

**File:** `packages/strategies/ml_direction_v1.py`

**Class:** `MLDirectionStrategyV1`

**Responsibilities:**
- Load trained model via `ModelInferenceAdapter`
- Maintain price history buffer (200+ bars for features)
- Compute features via `FeaturePipeline` on each bar
- Run model inference with confidence gating
- Convert `ModelInferenceOutput` to `Signal`
- Log predictions with explanations
- Handle inference failures gracefully (return ABSTAIN)

**Configuration:** `configs/strategies/ml_direction_v1.yaml`

**Key Parameters:**
- `model_path`: Path to trained model pickle file (default: `models/first_model_v1.pkl`)
- `position_size_pct`: Position size as fraction of equity (default: 0.1 = 10%)
- `abstain_threshold`: Confidence threshold for ABSTAIN (default: 0.55)
- `prediction_log_path`: Where to log predictions (default: `logs/predictions.jsonl`)

**Strategy Lifecycle:**
1. **Initialize:** Load model, initialize feature pipeline and explainer
2. **on_market_data:** Store bars in history (keep last 250 bars)
3. **generate_signals:** Compute features → run inference → log prediction → return signal
4. **risk_check:** Convert signals to orders (filters ABSTAIN, checks existing positions)

---

### 2. Simple Explainer (Ticket 07-05)

**File:** `services/ml/explainability/simple_explainer.py`

**Class:** `SimpleExplainer`

**Responsibilities:**
- Generate human-readable explanations for predictions
- Extract top features for display
- Produce confidence descriptions ("high", "normal", "low")
- Build rationale text templates

**Explanation Schema:**
```json
{
  "features_used": ["sma_20", "rsi_14", ...],  // All 34 features
  "top_features": [                            // Top 5 by absolute value
    {"name": "rsi_14", "value": 65.0},
    {"name": "macd", "value": 1.2},
    ...
  ],
  "signal": "BUY",
  "confidence": 0.72,
  "confidence_description": "normal",
  "uncertainty": 0.54,
  "rationale": "Model predicts upward movement with 72.0% confidence. Key indicators: rsi_14, macd, sma_20.",
  "model_type": "LogisticRegression",
  "symbol": "SPY",
  "timestamp": "2025-01-15T16:00:00+00:00"
}
```

**Future Enhancements (Sprint 8):**
- SHAP feature importance (tree models only)
- Permutation importance (all models)
- Feature contribution magnitudes (not just values)

---

## Prediction Logging

### Log Format

**File:** `logs/predictions.jsonl` (JSON Lines)

Each line is a complete JSON object with one prediction:

```json
{
  "prediction_id": "ml_direction_v1_1",
  "strategy_id": "ml_direction_v1",
  "timestamp": "2025-01-15T16:00:00+00:00",
  "symbol": "SPY",
  "bar_close": 450.25,
  "signal": "BUY",
  "confidence": 0.72,
  "uncertainty": 0.54,
  "raw_probability": 0.72,
  "explanation": { ... },
  "mode": "BACKTEST",
  "logged_at": "2025-01-15T16:00:01+00:00"
}
```

### Log Fields

| Field | Type | Description |
|-------|------|-------------|
| `prediction_id` | string | Unique identifier (strategy_id + counter) |
| `strategy_id` | string | Strategy that made prediction |
| `timestamp` | string | Bar close time (when prediction was made) |
| `symbol` | string | Trading symbol |
| `bar_close` | float | Close price of the bar |
| `signal` | string | Final signal (BUY/SELL/ABSTAIN) |
| `confidence` | float | Model confidence (0.0 to 1.0) |
| `uncertainty` | float | Prediction uncertainty (entropy) |
| `raw_probability` | float | Raw model probability of UP class |
| `explanation` | object | Full explanation (see schema above) |
| `mode` | string | Trading mode (BACKTEST/PAPER/LIVE) |
| `logged_at` | string | When log entry was written |

### Querying Predictions

**Python:**
```python
import json

predictions = []
with open('logs/predictions.jsonl', 'r') as f:
    for line in f:
        predictions.append(json.loads(line))

# Filter by signal
buy_signals = [p for p in predictions if p['signal'] == 'BUY']

# Filter by confidence
high_conf = [p for p in predictions if p['confidence'] >= 0.85]

# Check abstention rate
abstain_count = len([p for p in predictions if p['signal'] == 'ABSTAIN'])
abstain_rate = abstain_count / len(predictions)
```

**Command line:**
```bash
# Count predictions
wc -l logs/predictions.jsonl

# View latest prediction
tail -n 1 logs/predictions.jsonl | jq .

# Filter BUY signals with high confidence
cat logs/predictions.jsonl | jq 'select(.signal == "BUY" and .confidence > 0.8)'

# Abstention rate
cat logs/predictions.jsonl | jq -s '[.[] | select(.signal == "ABSTAIN")] | length'
```

---

## Integration with Existing Systems

### Backtest Engine

The ML strategy is compatible with the existing backtest engine:

```python
from services.backtest.engine import BacktestEngine
from packages.strategies.ml_direction_v1 import MLDirectionStrategyV1

# Initialize strategy with config
strategy = MLDirectionStrategyV1(
    strategy_id='ml_direction_v1',
    config={
        'model_path': 'models/first_model_v1.pkl',
        'position_size_pct': 0.1,
        'abstain_threshold': 0.55,
    }
)

# Run backtest
engine = BacktestEngine(
    strategy=strategy,
    bars=historical_bars,
    initial_cash=100000,
)

result = engine.run()

# Check prediction log
print(f"Predictions logged to: logs/predictions.jsonl")
```

**ABSTAIN handling:**
- Backtest engine already filters ABSTAIN signals before risk checks
- ABSTAIN signals are recorded in prediction log but do not generate orders
- Abstention rate is tracked in backtest metadata

### Live/Paper Execution

Same interface as backtest:

```python
# In execution loop
for bar in live_bars:
    strategy.on_market_data(bar)
    signals = strategy.generate_signals(portfolio)

    # Filter ABSTAIN (if not already filtered by engine)
    actionable_signals = [s for s in signals if s.side != 'ABSTAIN']

    # Convert to orders
    orders = strategy.risk_check(actionable_signals, portfolio)

    # Submit to risk manager and broker
    for order in orders:
        risk_manager.check_order(order)
        oms.submit_order(order)
```

---

## Failure Modes and Handling

| Failure | Detection | Strategy Behavior |
|---------|-----------|-------------------|
| Model file not found | `FileNotFoundError` during `initialize()` | Strategy init fails; log error and stop |
| NaN in computed features | `ValueError` in adapter | Return ABSTAIN signal; log warning |
| Feature computation fails | Exception in `compute_features()` | Return ABSTAIN signal; log error |
| Model inference crashes | Exception in `predict_and_convert()` | Return ABSTAIN signal with error reason |
| Insufficient bars for features | Check `len(price_history)` | Return empty signal list (no trade) |

**Logging:**
- All failures are logged to prediction log with `signal: "ABSTAIN"` and `explanation.rationale` containing error
- Errors do not crash the strategy or backtest
- Graceful degradation: strategy continues on next bar

---

## Success Criteria (Sprint 7)

- ✅ Model inference runs in backtest pipeline (data → features → model → gating → signals)
- ✅ Predictions flow through confidence gating (ABSTAIN below threshold)
- ✅ Signals integrate with existing risk manager and execution layers
- ✅ Predictions are logged with structured format (JSON Lines)
- ✅ Every prediction has a human-readable explanation
- ✅ Explanation includes features used, confidence, and rationale
- ✅ No SHAP or advanced explainability (deferred to Sprint 8)

---

## Next Steps (Sprint 8)

### Model Observability
- Feed prediction log into drift detector (compare current vs training distributions)
- Track rolling accuracy when ground truth becomes available
- Compute confidence calibration (predicted confidence vs actual correctness)
- Model health score based on drift + accuracy

### Advanced Explainability
- SHAP for tree-based models (feature contributions)
- Permutation importance for all models
- Feature contribution magnitudes in explanation
- Visualization: feature importance charts in dashboard

### Dashboard Integration
- Display predictions in real-time feed
- Show explanations for each trade recommendation
- Abstention log and charts
- Model performance metrics (accuracy, calibration)

---

## Files Modified/Created

| File | Type | Description |
|------|------|-------------|
| `packages/strategies/ml_direction_v1.py` | Created | ML strategy implementation |
| `services/ml/explainability/simple_explainer.py` | Created | Simple text-based explainer |
| `services/ml/inference/adapter.py` | Modified | Added `_build_model_input()` helper |
| `configs/strategies/ml_direction_v1.yaml` | Created | Strategy configuration |
| `docs/sprint-7-inference-and-explainability.md` | Created | This document |

---

## References

- `docs/sprint-7-ml-problem-definition.md` — Problem definition
- `docs/model-interface-contract.md` — Model I/O contract
- `docs/training-first-model.md` — Training guide
- `services/ml/inference/adapter.py` — Inference adapter
- `services/ml/confidence/gating.py` — Confidence gating
- `packages/strategies/base.py` — Strategy interface
