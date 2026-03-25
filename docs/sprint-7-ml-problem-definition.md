# Sprint 7: ML Problem Definition

## Document Purpose

This document defines the machine learning problem for the first model in the Caliper trading platform. It serves as the specification for training pipeline implementation (ticket 07-02), model interface design (ticket 07-03), and inference integration (ticket 07-04).

**Status:** Draft - awaiting confirmation of key choices (see Decision Points section)

---

## 1. ML Problem Statement

### Problem Type
**Binary classification:** Predict whether the price will move up or down over the next prediction horizon.

**Rationale:**
- Simplest problem formulation for first model
- Aligns directly with BUY/SELL signal generation
- Well-understood evaluation metrics (accuracy, precision, recall, F1)
- Clear threshold for confidence gating (probability → confidence → ABSTAIN if below threshold)

### Target Variable
**`direction_next_bar`**: Binary label indicating price direction in the next bar.

- **Value:** 1 (UP) or 0 (DOWN)
- **Definition:**
  - UP (1) if `close[t+1] > close[t]`
  - DOWN (0) if `close[t+1] <= close[t]`

**Alternative consideration:** Could use a minimum return threshold (e.g., UP if return > 0.1%) to filter out noise. See Decision Points below.

---

## 2. Prediction Horizon

**Horizon:** 1 bar (next bar) = 1 trading day for daily bars.

**Rationale:**
- Shortest meaningful horizon for daily trading
- Minimizes uncertainty and model staleness
- Faster feedback loop for model evaluation and drift detection
- Can extend to multi-day horizons (5-day, 10-day) once single-bar prediction is validated

**Temporal alignment:**
- Features computed from bars `[t-lookback, t]`
- Label computed from bar `t+1`
- Prediction made at close of bar `t`, to be acted on at open of bar `t+1` (or next available bar)

---

## 3. Label Construction Logic

### Label Generation Process

1. **Input:** Historical price bars (OHLCV) for a symbol
2. **For each bar at index `t`:**
   - Compute `return = (close[t+1] - close[t]) / close[t]`
   - Assign label:
     - `1` (UP) if `return > 0`
     - `0` (DOWN) if `return <= 0`
3. **Exclude the last bar** (no future data available for label)
4. **Store labels** alongside features in training dataset

### Handling Edge Cases

- **Missing next bar:** Drop the sample (cannot compute label)
- **Gaps (weekends, holidays):** Use actual next available bar; document gap duration if needed for analysis
- **Outliers (extreme moves):** Retain initially; monitor distribution. Can add optional outlier filtering if needed (e.g., cap returns at 3σ) but document as a processing step.

### Data Leakage Prevention

**Critical:** Labels are constructed ONLY from `close[t+1]` (future) and `close[t]` (current). No features from `t+1` or beyond may be used.

- Features use data `[t-lookback, t]` (e.g., SMA over past 20 bars ending at `t`)
- Feature pipeline already computes indicators properly (rolling windows, no future peeking)
- Training script MUST split data by time (train < validation < test) to prevent temporal leakage

---

## 4. Feature Set

### Available Features (from `services/features/pipeline.py`)

**Base:** open, high, low, close, volume (5 features)

**Moving averages:** sma_20, sma_50, sma_200, ema_12, ema_26 (5 features)

**Momentum/volatility:** rsi_14, macd, macd_signal, macd_histogram, bb_upper, bb_middle, bb_lower, bb_width, bb_position, atr_14, stoch_k, stoch_d (12 features)

**Volume:** volume_sma_20, volume_ratio (2 features)

**Derived:** returns, returns_1d, returns_5d, returns_10d, volatility_10d, volatility_20d, price_position, hl_spread, sma_cross_20_50, sma_cross_50_200 (10 features)

**Total:** 34 features

### Initial Feature Selection

**For first model:** Use all 34 features (full feature set from pipeline).

**Rationale:**
- Let the model (tree-based or logistic regression with regularization) handle feature selection
- Baseline performance with all features
- SHAP explainability will identify most important features post-hoc
- Can prune features in future iterations based on importance and drift

### Feature Preprocessing

- **NaN handling:** Drop rows with NaN in features OR labels (initial bars have NaN due to indicator lookback)
- **Scaling:** Not required for tree-based models; apply standardization if using logistic regression
- **Encoding:** Binary crossover features (sma_cross_20_50, sma_cross_50_200) are already 0/1

---

## 5. Evaluation Metrics

### Primary Metrics (Classification)

1. **Accuracy:** Overall correctness (TP + TN) / total
2. **Precision (UP class):** TP / (TP + FP) — when model says UP, how often is it right?
3. **Recall (UP class):** TP / (TP + FN) — of all actual UPs, how many did we catch?
4. **F1 Score (UP class):** Harmonic mean of precision and recall
5. **ROC-AUC:** Area under ROC curve (threshold-independent measure)

### Secondary Metrics (Trading-Aware)

6. **Directional Accuracy:** Accuracy on validation/test set
7. **Abstention Rate:** Percentage of predictions below confidence threshold (tracked, not optimized)
8. **Confidence Calibration:** Correlation between predicted probability and actual correctness (e.g., 70% confidence → 70% accuracy)

### Evaluation Split

- **Training:** 60% of data (earliest)
- **Validation:** 20% of data (middle)
- **Test:** 20% of data (most recent)

**Time-based split:** Data is split by date; no shuffling. Training period < validation period < test period.

### Success Criteria (Minimum Viable Model)

- **Accuracy > 52%** on validation set (better than random for binary)
- **ROC-AUC > 0.55** on validation set
- **No data leakage detected** (validation performance not suspiciously high)
- **Model serializable and loadable** for inference

---

## 6. Model Type (Initial)

**First model:** Logistic Regression with L2 regularization.

**Rationale:**
- Simple, interpretable baseline
- Fast training and inference
- Natural probability output (maps to confidence)
- Permutation importance available for explainability (SHAP requires tree models)

**Alternative:** Small decision tree or Random Forest (3-5 estimators) if logistic regression underperforms. Tree models enable SHAP explainability immediately.

**Hyperparameters (initial):**
- Regularization: `C=1.0` (scikit-learn default)
- Solver: `lbfgs`
- Max iterations: `1000`

Can tune via validation performance in future iterations.

---

## 7. Assumptions

1. **Single symbol:** First model trains on one symbol (e.g., SPY or AAPL). Multi-symbol generalization is out of scope for Sprint 7.
2. **Daily bars:** Model uses daily OHLCV data; intraday (minute bars) is out of scope.
3. **Static features:** Feature set is fixed; no online feature engineering or dynamic selection.
4. **No regime detection:** Model assumes stationary market conditions; no explicit handling of bull/bear/sideways regimes.
5. **No transaction costs in labels:** Labels are based purely on price direction; execution costs (slippage, commission) are handled by backtest/risk layers, not the model.
6. **No options:** Stock price prediction only; options data and Greeks are out of scope.
7. **No ensembles:** Single model; ensemble logic is Sprint 8 or later.

---

## 8. Failure Modes

### Training Failures

| Failure Mode | Detection | Mitigation |
|--------------|-----------|------------|
| Insufficient data | Check training set size < 100 samples | Require minimum 252 bars (1 year daily) |
| All NaN features | Check for empty DataFrame after dropna | Validate raw bars before feature computation |
| Label imbalance (>90% one class) | Check class distribution | Warn user; consider stratified split or class weights |
| Overfitting (train acc >> val acc) | Compare train vs validation accuracy | Add regularization, reduce features, collect more data |
| Model fails to converge | Check scikit-learn warnings | Increase max_iter, scale features |

### Inference Failures

| Failure Mode | Detection | Mitigation |
|--------------|-----------|------------|
| Missing features (NaN at inference) | Check for NaN in feature vector | ABSTAIN signal; log warning |
| Stale model (no recent training) | Track days since last train | Drift detection triggers retrain alert |
| Model file missing/corrupt | Catch deserialization errors | Fallback to last-known-good model or ABSTAIN |
| Prediction outside [0,1] | Validate probability output | Clip to [0,1]; log anomaly |
| Uncertainty spike | Monitor prediction entropy | Confidence gating triggers ABSTAIN |

### Operational Failures

| Failure Mode | Detection | Mitigation |
|--------------|-----------|------------|
| Feature drift (distribution shift) | PSI > 0.2, KL > 0.3 | Drift alert; human review; consider retrain |
| Confidence drift (avg confidence drops) | Track rolling mean confidence | Health score drop; pause model |
| Error drift (accuracy degrades) | Track rolling directional accuracy | Circuit breaker if accuracy < threshold |
| No new data (bars not updating) | Check timestamp of latest bar | ABSTAIN; alert monitoring |

---

## 9. Implementation Notes

### Training Script Responsibilities (ticket 07-02)

- Load historical bars for symbol and date range
- Compute features via `FeaturePipeline.compute_features()`
- Construct labels per section 3
- Split data by time (60/20/20)
- Drop NaN rows
- Train model on training set
- Evaluate on validation set; log metrics
- Serialize model to disk (e.g., `models/first_model_v1.pkl`)
- Log training config, feature names, label logic, split dates, metrics

### Model Interface Responsibilities (ticket 07-03)

- Define `ModelInput` schema (features, symbol, timestamp)
- Define `ModelOutput` schema (prediction, confidence, abstain signal) — extend existing `packages.common.ml_schemas.ModelOutput`
- Document how to map model probability to confidence (e.g., `confidence = max(p, 1-p)` for binary classifier)
- Document ABSTAIN logic (confidence < threshold)

### Inference Integration Responsibilities (ticket 07-04)

- Load trained model at strategy initialization
- At each bar: compute features → call model → apply confidence gating → return Signal (BUY/SELL/ABSTAIN)
- Log predictions with timestamp, symbol, features, confidence, signal
- Store prediction records for drift detection and performance tracking

---

## 10. Decision Points (User Input Required)

Before proceeding to implementation (tickets 07-02, 07-03, 07-04), please confirm or adjust:

### Decision A: Target Variable Threshold

**Current:** `UP if close[t+1] > close[t]` (any positive return)

**Alternative:** `UP if (close[t+1] - close[t]) / close[t] > 0.001` (return > 0.1% to filter noise)

**Question:** Should we use a minimum return threshold, or classify any positive move as UP?

### Decision B: Prediction Horizon

**Current:** 1 bar (next day)

**Alternative:** 5 bars (next week) or 10 bars (2 weeks) for longer-term signals

**Question:** Is 1-day horizon acceptable, or should we target a longer horizon?

### Decision C: Train/Validation/Test Split

**Current:** 60% / 20% / 20% time-based split

**Alternative:** Walk-forward with multiple folds (e.g., 6 months train, 2 months validate, roll forward)

**Question:** Simple 60/20/20 split OK for first model, or prefer walk-forward from the start?

### Decision D: Symbol for First Model

**Current:** Not specified

**Candidates:**
- **SPY** (S&P 500 ETF): Liquid, lower volatility, widely used benchmark
- **AAPL** (Apple): Liquid, large cap, representative stock
- **QQQ** (Nasdaq ETF): Tech-heavy, higher volatility

**Question:** Which symbol should the first model train on?

### Decision E: Date Range for Training

**Current:** Not specified

**Recommendation:** Last 3-5 years of daily data (750-1250 bars)

**Question:** What date range should we use? (e.g., 2020-01-01 to 2025-01-01)

---

## 11. Summary (Implementation Checklist)

Once decisions A-E are confirmed, the following can proceed:

- [ ] **07-02:** Training script loads data for confirmed symbol and date range, constructs labels per confirmed threshold, splits per confirmed method, trains logistic regression, logs validation metrics, saves model.
- [ ] **07-03:** Model interface defines input/output schemas with confirmed features and confidence semantics.
- [ ] **07-04:** Inference integration loads model, generates signals on confirmed symbol, applies confidence gating, logs predictions.
- [ ] **07-05:** Text explainability adds feature contributions (permutation importance initially) to prediction records.

---

**Document version:** 1.0
**Author:** Claude (Sprint 7 planning)
**Last updated:** 2026-02-02
