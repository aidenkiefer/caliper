# Training the First ML Model

## Overview

This guide explains how to train the first ML model for Sprint 7 using the training pipeline.

**Model:** Logistic regression binary classifier predicting next-bar price direction (UP/DOWN).

**Reference:** See `docs/sprint-7-ml-problem-definition.md` for complete problem specification.

---

## Prerequisites

1. **Price data:** CSV file with historical bars for the target symbol (e.g., SPY)
2. **Python environment:** Poetry with all dependencies installed
3. **Repository root:** Run commands from the repo root directory

---

## Preparing Data

The training script expects a CSV file with price bars in the following format:

```csv
symbol,timestamp,timeframe,open,high,low,close,volume,source
SPY,2020-01-02T00:00:00+00:00,1day,324.87,325.25,324.18,325.00,70000000,alpaca
SPY,2020-01-03T00:00:00+00:00,1day,325.10,325.65,324.50,325.40,68000000,alpaca
...
```

**Required columns:**
- `symbol`: Trading symbol (e.g., "SPY")
- `timestamp`: ISO 8601 datetime with timezone (UTC)
- `timeframe`: Bar timeframe (e.g., "1day")
- `open`, `high`, `low`, `close`: OHLC prices (Decimal or float)
- `volume`: Trading volume (integer)
- `source`: Data provider (e.g., "alpaca", "polygon")

**Obtaining data:**
- Use the data service or Alpaca API to export historical bars
- Recommended: 5 years of daily data (2020-01-01 to 2025-01-01) = ~1250 bars
- Ensure data is clean (no missing bars, valid OHLCV)

---

## Running Training

### Basic Usage

```bash
poetry run python -m services.ml.training.train_first_model \
    --symbol SPY \
    --start-date 2020-01-01 \
    --end-date 2025-01-01 \
    --data-file data/spy_daily_2020_2025.csv \
    --output-path models/first_model_v1.pkl
```

### Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--symbol` | No | SPY | Trading symbol |
| `--start-date` | No | 2020-01-01 | Start date (YYYY-MM-DD) |
| `--end-date` | No | 2025-01-01 | End date (YYYY-MM-DD) |
| `--data-file` | **Yes** | - | Path to price bars CSV |
| `--output-path` | No | models/first_model_v1.pkl | Output path for model |

---

## What Happens During Training

1. **Load data:** Reads bars from CSV and validates format
2. **Compute features:** Runs `FeaturePipeline` to compute 34 technical indicators
3. **Construct labels:** Creates binary labels (UP=1, DOWN=0) based on next bar close
4. **Time-aware split:** Splits data into train (60%), validation (20%), test (20%) by date
5. **Drop NaN rows:** Removes rows with missing features (from indicator lookback)
6. **Train model:** Fits logistic regression on training set
7. **Evaluate:** Computes metrics on train, validation, and test sets
8. **Save model:** Writes model + metadata to disk

**Data leakage prevention:**
- Features use data from `[t-lookback, t]` only
- Labels use `close[t+1]`
- Train/val/test split is strictly temporal (no shuffling)
- Validation and test never influence training

---

## Output Files

After training completes, two files are created:

### 1. Model File (`models/first_model_v1.pkl`)

Pickle file containing:
- Trained scikit-learn `LogisticRegression` model
- Feature names (34 features)
- Training metadata

**Usage:**
```python
import pickle

with open('models/first_model_v1.pkl', 'rb') as f:
    package = pickle.load(f)

model = package['model']
feature_names = package['feature_names']
metadata = package['metadata']
```

### 2. Metadata File (`models/first_model_v1.json`)

JSON file with training info:
- Symbol, date range, number of samples
- Feature names
- Train/val/test metrics
- Success criteria check

**Example:**
```json
{
  "symbol": "SPY",
  "start_date": "2020-01-01",
  "end_date": "2025-01-01",
  "model_type": "LogisticRegression",
  "train_samples": 750,
  "val_samples": 250,
  "test_samples": 250,
  "val_metrics": {
    "accuracy": 0.5440,
    "precision": 0.5520,
    "recall": 0.6100,
    "f1": 0.5800,
    "roc_auc": 0.5780
  },
  ...
}
```

---

## Success Criteria

Per `docs/sprint-7-ml-problem-definition.md`, the model must achieve:

- **Validation accuracy > 52%** (better than random)
- **Validation ROC-AUC > 55%**

The training script checks these criteria and reports success/failure.

---

## Troubleshooting

### Error: "Insufficient training data"

**Cause:** Fewer than 100 samples after dropna and split.

**Fix:** Use more data (longer date range or more frequent bars).

### Warning: "Model did not converge"

**Cause:** Logistic regression hit max_iter before convergence.

**Fix:** Increase `max_iter` or scale features. Typically not a problem if metrics are reasonable.

### Low accuracy (<52%)

**Possible causes:**
- Market is truly unpredictable for this symbol/period
- Features are not informative
- Data quality issues (missing bars, bad OHLCV)

**Next steps:**
- Inspect feature distributions and labels
- Try different symbol or date range
- Consider feature engineering or different model type

---

## Next Steps (Sprint 7)

After training completes:

1. **Ticket 07-03:** Model interface implementation (schemas for input/output)
2. **Ticket 07-04:** Inference integration (load model in strategy, generate signals)
3. **Ticket 07-05:** Explainability (attach feature importance to predictions)

---

## References

- `docs/sprint-7-ml-problem-definition.md` — Problem specification
- `docs/plans/specs/sprint-7-first-ml-model-spec.md` — Sprint 7 spec
- `services/features/pipeline.py` — Feature computation
- `packages/common/schemas.py` — Data schemas
