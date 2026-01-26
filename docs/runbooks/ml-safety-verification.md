# ML Safety Verification Runbook

This runbook provides step-by-step verification procedures for ML Safety & Interpretability features.

## Prerequisites

- FastAPI backend running on `http://localhost:8000`
- Database and Redis services running
- Test data available (or use mock data)

---

## 1. Drift Detection Verification

### 1.1 Check Drift Metrics Endpoint

```bash
# Get drift metrics for a model
curl http://localhost:8000/v1/drift/metrics/model-1

# Expected response:
# {
#   "model_id": "model-1",
#   "feature_metrics": [...],
#   "confidence_metric": {...},
#   "timestamp": "..."
# }
```

**Verification:**
- [ ] Response returns 200 OK
- [ ] Contains `feature_metrics` array
- [ ] Each feature metric has `psi`, `kl_divergence`, `mean_shift`
- [ ] `confidence_metric` present (if available)

### 1.2 Check Health Score

```bash
# Get health score for a model
curl http://localhost:8000/v1/drift/health/model-1?last_retraining_date=2024-01-01T00:00:00Z

# Expected response:
# {
#   "model_id": "model-1",
#   "health_score": 75.5,
#   "components": {
#     "feature_drift": 80.0,
#     "confidence_drift": 70.0,
#     "error_drift": 75.0,
#     "staleness": 80.0
#   }
# }
```

**Verification:**
- [ ] Health score between 0 and 100
- [ ] All component scores present
- [ ] Staleness score decreases with older retraining date

### 1.3 Trigger Alert (if drift simulation available)

```bash
# Inject drifted data (would be done via API or direct DB insert)
# Then check metrics again
curl http://localhost:8000/v1/drift/metrics/model-1

# Verify PSI > 0.25 triggers critical alert
```

**Verification:**
- [ ] High PSI values (>0.25) generate alerts
- [ ] Alerts include correct severity level
- [ ] Alerts include threshold information

---

## 2. Confidence Gating Verification

### 2.1 Test ABSTAIN Decision

```bash
# Submit prediction with low confidence (< 0.55)
# This would typically be done via model inference endpoint
# For now, verify confidence gating logic in unit tests
```

**Verification:**
- [ ] Confidence < 0.55 triggers ABSTAIN
- [ ] ABSTAIN signals are tracked in backtest
- [ ] Abstention rate calculated correctly

### 2.2 Test Threshold Configuration

```bash
# Get current confidence config
curl http://localhost:8000/v1/confidence/config/strategy-1

# Update confidence threshold
curl -X PUT http://localhost:8000/v1/confidence/config/strategy-1 \
  -H "Content-Type: application/json" \
  -d '{
    "abstain_threshold": 0.60,
    "low_confidence_threshold": 0.70,
    "high_confidence_threshold": 0.90
  }'
```

**Verification:**
- [ ] Config can be retrieved
- [ ] Config can be updated
- [ ] New thresholds take effect

---

## 3. Explainability Verification

### 3.1 Get Trade Explanation

```bash
# Get explanation for a trade
curl http://localhost:8000/v1/explanations/trade-123

# Expected response:
# {
#   "trade_id": "trade-123",
#   "signal": "BUY",
#   "confidence": 0.82,
#   "top_features": [
#     {
#       "feature_name": "RSI_14",
#       "value": 35.2,
#       "contribution": 0.15,
#       "direction": "positive"
#     },
#     ...
#   ],
#   "model_id": "model-1"
# }
```

**Verification:**
- [ ] Explanation returned for valid trade_id
- [ ] Top features sorted by absolute contribution
- [ ] Each feature has direction (positive/negative)
- [ ] Base value present (if SHAP used)

### 3.2 List Explanations

```bash
# List explanations for a strategy
curl "http://localhost:8000/v1/explanations?strategy_id=strategy-1&limit=10"
```

**Verification:**
- [ ] Returns list of explanations
- [ ] Can filter by strategy_id
- [ ] Limit parameter works
- [ ] Results sorted by timestamp (most recent first)

---

## 4. Human-in-the-Loop Verification

### 4.1 Check Pending Queue

```bash
# Get pending recommendations
curl http://localhost:8000/v1/recommendations

# Expected response:
# [
#   {
#     "recommendation_id": "rec-1",
#     "strategy_id": "strategy-1",
#     "signal": "BUY",
#     "symbol": "AAPL",
#     "confidence": 0.78,
#     "timestamp": "..."
#   },
#   ...
# ]
```

**Verification:**
- [ ] Returns list of pending recommendations
- [ ] Each recommendation has required fields
- [ ] Can filter by strategy_id (query param)

### 4.2 Approve Recommendation

```bash
# Approve a recommendation
curl -X POST http://localhost:8000/v1/recommendations/rec-1/approve \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-123",
    "rationale": "High confidence, good entry point"
  }'
```

**Verification:**
- [ ] Recommendation removed from pending queue
- [ ] Approval logged with user_id
- [ ] Rationale stored (if provided)
- [ ] Recommendation can be executed

### 4.3 Reject Recommendation

```bash
# Reject a recommendation
curl -X POST http://localhost:8000/v1/recommendations/rec-1/reject \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-123",
    "reason": "Market conditions unfavorable"
  }'
```

**Verification:**
- [ ] Recommendation removed from pending queue
- [ ] Rejection logged with reason
- [ ] Recommendation not executed

### 4.4 Get Agreement Statistics

```bash
# Get HITL statistics
curl http://localhost:8000/v1/recommendations/stats?strategy_id=strategy-1

# Expected response:
# {
#   "strategy_id": "strategy-1",
#   "total_recommendations": 42,
#   "approved": 35,
#   "rejected": 5,
#   "agreement_rate": 0.875,
#   "pending": 2
# }
```

**Verification:**
- [ ] Agreement rate calculated correctly (approved / (approved + rejected))
- [ ] Total recommendations matches sum of approved + rejected + pending
- [ ] Agreement rate between 0 and 1

---

## 5. Baseline Verification

### 5.1 Get Baseline Comparison

```bash
# Get baseline comparison for a strategy
curl "http://localhost:8000/v1/baselines/comparison?strategy_id=strategy-1"

# Expected response:
# {
#   "strategy_id": "strategy-1",
#   "strategy_return": 0.15,
#   "baseline_returns": {
#     "hold_cash": 0.0,
#     "buy_and_hold": 0.12,
#     "random": 0.05
#   },
#   "regret_metrics": {
#     "regret_vs_cash": 0.15,
#     "regret_vs_buy_hold": 0.03,
#     "regret_vs_random": 0.10
#   },
#   "outperforms": {
#     "cash": true,
#     "buy_and_hold": true,
#     "random": true
#   }
# }
```

**Verification:**
- [ ] Returns strategy return vs all baselines
- [ ] Regret metrics calculated correctly
- [ ] `outperforms` flags correct
- [ ] All baseline types present (cash, buy_and_hold, optionally random)

---

## 6. Backtest Abstention Verification

### 6.1 Run Backtest with Abstentions

```python
# Python script to test abstention tracking
from services.backtest.engine import BacktestEngine
from services.backtest.abstention import AbstentionTracker

# Create strategy that generates ABSTAIN signals
# Run backtest
# Check metadata for abstention_metrics
```

**Verification:**
- [ ] ABSTAIN signals tracked in backtest
- [ ] Abstention rate calculated correctly
- [ ] Metrics exclude abstained periods (if applicable)
- [ ] Abstention metrics in backtest result metadata

---

## 7. Dashboard UI Verification

### 7.1 Help Page

1. Navigate to `/help`
2. Verify:
   - [ ] Search functionality works
   - [ ] Categories display correctly
   - [ ] All terms from glossary visible
   - [ ] Definitions are clear and accurate

### 7.2 Tooltips

1. Navigate to Overview page
2. Hover over StatsCard titles (P&L, Sharpe Ratio, etc.)
3. Verify:
   - [ ] Tooltip appears on hover
   - [ ] Tooltip shows definition
   - [ ] "Learn more" link works
   - [ ] Tooltip matches glossary

### 7.3 Explanation UI

1. Navigate to Strategy Detail → Explanations tab
2. Verify:
   - [ ] Explanation card displays
   - [ ] Top features shown with contributions
   - [ ] Feature importance chart renders
   - [ ] Direction indicators (↑/↓) correct

### 7.4 Approval Queue UI

1. Navigate to `/recommendations`
2. Verify:
   - [ ] Pending recommendations displayed
   - [ ] Approve button works
   - [ ] Reject button works
   - [ ] Statistics card shows agreement rate

### 7.5 Baseline Comparison UI

1. Navigate to Overview page
2. Scroll to Baseline Comparison widget
3. Verify:
   - [ ] Chart renders correctly
   - [ ] Comparison table shows all baselines
   - [ ] Outperforms badges correct
   - [ ] Regret metrics displayed

---

## 8. Integration Test Checklist

### End-to-End Flow

1. **Model generates recommendation with low confidence**
   - [ ] Recommendation added to queue
   - [ ] Status = "pending"

2. **Human reviews recommendation**
   - [ ] Explanation visible in UI
   - [ ] Can approve or reject
   - [ ] Decision logged

3. **Approved recommendation executes**
   - [ ] Order placed via execution engine
   - [ ] Trade recorded with explanation_id

4. **Drift detection monitors model**
   - [ ] Metrics calculated periodically
   - [ ] Alerts generated when thresholds exceeded
   - [ ] Health score updated

5. **Baseline comparison available**
   - [ ] Strategy vs baselines calculated
   - [ ] Regret metrics available
   - [ ] Dashboard shows comparison

---

## Troubleshooting

### Drift Metrics Not Available

- Check if model has reference data stored
- Verify drift detector initialized with reference features
- Check database for stored metrics

### Explanations Missing

- Verify SHAP explainer initialized with model
- Check if trade has associated explanation
- Verify explanation stored in database

### Approval Queue Empty

- Check if HITL enabled for strategy
- Verify recommendations being generated
- Check API endpoint returns data

### Baseline Comparison Fails

- Verify baseline strategies ran successfully
- Check backtest results available
- Verify regret calculator has all required baselines

---

## Success Criteria

All verification steps should pass:
- [ ] Drift detection calculates metrics correctly
- [ ] Health score between 0-100
- [ ] Confidence gating triggers ABSTAIN correctly
- [ ] Explanations generated for trades
- [ ] Approval queue functional
- [ ] Baseline comparison accurate
- [ ] Dashboard UI displays all features correctly
