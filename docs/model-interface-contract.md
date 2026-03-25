# Model Interface Contract (Sprint 7)

## Overview

This document specifies the standardized interface for ML models in the Caliper trading platform. All models must adhere to this contract for integration with strategies, risk management, and execution layers.

**Status:** Defined for Sprint 7 (first ML model)

---

## Architecture Flow

```
Market Data → Feature Pipeline → Model Input
                                     ↓
                              Model Inference
                                     ↓
                              Raw Prediction
                                     ↓
                            Confidence Gating
                                     ↓
                            Inference Output (BUY/SELL/ABSTAIN)
                                     ↓
                              Signal Conversion
                                     ↓
                          Strategy Layer (Signal)
                                     ↓
                         Risk Manager → Orders → Execution
```

---

## Data Schemas

All schemas are defined in `packages/common/ml_schemas.py`.

### 1. ModelInput

**Purpose:** Standardized input to model inference.

**Schema:**
```python
class ModelInput(BaseModel):
    symbol: str                    # Trading symbol (e.g., "SPY")
    timestamp: datetime            # Prediction timestamp (bar close time, UTC)
    features: Dict[str, float]     # Feature dictionary {"sma_20": 450.0, ...}
```

**Usage:**
```python
from packages.common.ml_schemas import ModelInput
from datetime import datetime, timezone

model_input = ModelInput(
    symbol="SPY",
    timestamp=datetime.now(timezone.utc),
    features={
        "sma_20": 450.0,
        "rsi_14": 65.0,
        "macd": 1.2,
        # ... all 34 features
    }
)
```

**Contract:**
- Features must include all features expected by the model (34 for first model)
- Feature names must match training feature names exactly
- No NaN values allowed in features
- Timestamp must be timezone-aware (UTC)

---

### 2. ModelPrediction

**Purpose:** Raw output from model before confidence gating.

**Schema:**
```python
class ModelPrediction(BaseModel):
    prediction: int                # 0 (DOWN) or 1 (UP)
    confidence: float              # 0.0 to 1.0 (distance from decision boundary)
    raw_probability: float         # 0.0 to 1.0 (probability of UP class)
    features_used: List[str]       # Feature names used for prediction
```

**Semantics for Binary Classifier:**
- `prediction = 1` → Price expected to go UP → raw signal is BUY
- `prediction = 0` → Price expected to go DOWN → raw signal is SELL
- `confidence = max(p_up, p_down)` where `p_up = raw_probability`, `p_down = 1 - p_up`
- Example: `raw_probability = 0.72` → `confidence = max(0.72, 0.28) = 0.72` → prediction = 1 (UP)

**Usage:**
```python
# Inside model inference adapter
probabilities = model.predict_proba(features)  # [p_down, p_up]
raw_probability = probabilities[0, 1]          # p_up
confidence = max(probabilities[0])             # max(p_down, p_up)
prediction = int(model.predict(features)[0])   # 0 or 1

model_pred = ModelPrediction(
    prediction=prediction,
    confidence=confidence,
    raw_probability=raw_probability,
    features_used=feature_names,
)
```

---

### 3. ModelInferenceOutput

**Purpose:** Complete output after confidence gating, ready for strategy consumption.

**Schema:**
```python
class ModelInferenceOutput(BaseModel):
    signal: Literal["BUY", "SELL", "ABSTAIN"]  # Gated signal
    confidence: float                          # 0.0 to 1.0
    uncertainty: float                         # Entropy (≥ 0.0)
    raw_probability: float                     # 0.0 to 1.0
    features_used: List[str]                   # Feature names
    abstain_reason: Optional[str]              # Reason if ABSTAIN
```

**Signal Semantics:**
- `"BUY"`: Model predicts UP with sufficient confidence → long position or close short
- `"SELL"`: Model predicts DOWN with sufficient confidence → short position or close long
- `"ABSTAIN"`: Confidence below threshold → do not trade

**Confidence Gating Logic:**
```python
if confidence < abstain_threshold:
    signal = "ABSTAIN"
    abstain_reason = f"confidence {confidence} below threshold {abstain_threshold}"
else:
    signal = "BUY" if prediction == 1 else "SELL"
    abstain_reason = None
```

**Default Thresholds** (configurable per strategy):
- `abstain_threshold = 0.55` (confidence below this → ABSTAIN)
- `low_confidence_threshold = 0.65`
- `high_confidence_threshold = 0.85`

**Usage:**
```python
from services.ml.inference.adapter import ModelInferenceAdapter

adapter = ModelInferenceAdapter.from_file('models/first_model_v1.pkl')

inference_output = adapter.predict(model_input)

if inference_output.should_trade():
    # Signal is BUY or SELL
    execute_signal(inference_output.signal)
else:
    # Signal is ABSTAIN
    log_abstention(inference_output.abstain_reason)
```

---

### 4. Signal (Strategy Layer)

**Purpose:** Final trading signal passed to risk manager and execution layer.

**Schema (from `packages.strategies.base`):**
```python
class Signal:
    symbol: str
    side: str                      # "BUY", "SELL", or "ABSTAIN"
    strength: float                # 0.0 to 1.0 (maps to confidence)
    price: Optional[Decimal]       # Limit price (optional)
    quantity: Optional[Decimal]    # Quantity (optional, computed by strategy)
    reason: Optional[str]          # Human-readable reason
    timestamp: datetime            # Signal generation time
```

**Conversion from ModelInferenceOutput:**
```python
signal = Signal(
    symbol="SPY",
    side=inference_output.signal,           # "BUY", "SELL", or "ABSTAIN"
    strength=inference_output.confidence,   # 0.0 to 1.0
    reason=f"ML model prediction (confidence={inference_output.confidence:.3f})",
)
```

**Contract:**
- Signal with `side="ABSTAIN"` is recorded but NOT converted to orders
- Backtest engine and execution engine both handle ABSTAIN (filter out before risk check)
- Risk manager never sees ABSTAIN signals (filtered at strategy layer)

---

## Integration Points

### Loading a Trained Model

**Location:** Strategy initialization (e.g., `MLStrategy.__init__`)

```python
from services.ml.inference.adapter import ModelInferenceAdapter
from services.ml.confidence.gating import ConfidenceConfig

# Load model
adapter = ModelInferenceAdapter.from_file(
    model_path='models/first_model_v1.pkl',
    confidence_config=ConfidenceConfig(
        strategy_id='ml_strategy_v1',
        abstain_threshold=0.55,
        low_confidence_threshold=0.65,
        high_confidence_threshold=0.85,
    ),
)
```

### Running Inference in Strategy

**Location:** Strategy `generate_signals()` method

```python
def generate_signals(self, portfolio: PortfolioState) -> List[Signal]:
    # Compute features from current bar history
    features_df = self.feature_pipeline.compute_features(self.bar_history)
    latest_features = features_df.iloc[-1].to_dict()

    # Remove non-feature columns
    feature_dict = {
        k: float(v) for k, v in latest_features.items()
        if k not in ['timestamp', 'label']
    }

    # Run inference
    signal = self.adapter.predict_and_convert(
        symbol=self.symbol,
        timestamp=self.current_bar.timestamp,
        features=feature_dict,
    )

    return [signal]  # List of signals (one per symbol)
```

### Handling ABSTAIN

**Backtest engine** (already implemented):
```python
# In backtest loop
signals = strategy.generate_signals(portfolio)

# Record all signals including ABSTAIN
for signal in signals:
    record_signal(signal)

# Filter out ABSTAIN before risk check
actionable_signals = [s for s in signals if s.side != "ABSTAIN"]

# Convert signals to orders
orders = strategy.risk_check(actionable_signals, portfolio)
```

**Execution engine** (to be implemented in 07-04):
```python
# Same pattern: record ABSTAIN but do not create orders
signals = strategy.generate_signals(portfolio)
log_signals(signals)

actionable_signals = [s for s in signals if s.side != "ABSTAIN"]
orders = strategy.risk_check(actionable_signals, portfolio)

# Send orders to broker
for order in orders:
    risk_manager.check_order(order)
    oms.submit_order(order)
```

---

## Failure Modes and Mitigations

| Failure | Detection | Behavior |
|---------|-----------|----------|
| Missing model file | `FileNotFoundError` during load | Strategy initialization fails; log error |
| NaN in features | `ValueError` in `prepare_features()` | Return ABSTAIN signal; log warning |
| Wrong feature names | `ValueError` in `prepare_features()` | Strategy initialization fails; log error |
| Model deserialization error | Pickle exception during load | Strategy initialization fails; log error |
| Confidence outside [0, 1] | Schema validation | Raise `ValidationError` |
| Prediction outside {0, 1} | Model output validation | Raise `ValueError` |

---

## Contract Summary (Checklist)

### Model Requirements

- ✅ Model accepts feature array of shape `[1, n_features]`
- ✅ Model returns prediction in {0, 1} (binary classifier)
- ✅ Model provides `predict_proba()` for confidence (scikit-learn interface)
- ✅ Model is serializable (pickle) with metadata

### Schema Requirements

- ✅ `ModelInput`: symbol, timestamp, features (dict)
- ✅ `ModelPrediction`: prediction, confidence, raw_probability, features_used
- ✅ `ModelInferenceOutput`: signal (BUY/SELL/ABSTAIN), confidence, uncertainty, abstain_reason
- ✅ Signal: side (BUY/SELL/ABSTAIN), strength (maps to confidence)

### Adapter Requirements

- ✅ Load model from disk with metadata
- ✅ Prepare features from dictionary (validate completeness, no NaN)
- ✅ Run inference and return raw prediction
- ✅ Apply confidence gating (threshold-based ABSTAIN)
- ✅ Convert to Signal object for strategy layer

### Strategy Requirements

- ✅ Initialize adapter with model path and confidence config
- ✅ Compute features via `FeaturePipeline` (or equivalent)
- ✅ Call adapter to get Signal (BUY/SELL/ABSTAIN)
- ✅ Return list of Signals from `generate_signals()`
- ✅ Execution and backtest layers filter ABSTAIN before risk check

---

## Implementation Files

| File | Purpose |
|------|---------|
| `packages/common/ml_schemas.py` | Data schemas (ModelInput, ModelPrediction, ModelInferenceOutput) |
| `services/ml/inference/adapter.py` | Inference adapter (model loading, gating, signal conversion) |
| `services/ml/confidence/gating.py` | Confidence gating logic (threshold-based ABSTAIN) |
| `services/ml/confidence/uncertainty.py` | Uncertainty computation (entropy) |
| `packages/strategies/base.py` | Signal class definition |

---

## Next Steps (Sprint 7)

- **07-04:** Inference integration (wire adapter into ML strategy)
- **07-05:** Text explainability (attach feature importance to predictions)
- **Sprint 8:** Drift detection integration (feed predictions and outcomes to drift detector)

---

## References

- `docs/sprint-7-ml-problem-definition.md` — Problem definition
- `docs/training-first-model.md` — Training guide
- `services/ml/confidence/gating.py` — Confidence gating implementation
- `packages/strategies/base.py` — Strategy interface
