# Sprint 14: BTC Probability Model

**Version:** v2.4.0  
**Status:** Done (implementation merged 2026-04-08) — **AC-9** unit + integration tests **deferred**; see `docs/plans/tickets/14-00-INDEX.md` (14-11) and `docs/plans/PROGRESS.md` backlog.  
**Research sources:** `docs/research/probabilities.md`  
**Skills to load:** `scikit-learn`, `statsmodels`, `quant-analyst`, `mlops-engineer`, `python-testing-patterns`

---

## Overview

The core trading edge on Polymarket's hourly BTC "Up/Down" markets comes from estimating the true conditional probability that the BTC/USDT 1-hour candle closes ≥ its open (the "Up" outcome), then acting on the gap between that estimate and Polymarket's implied probability (derived from the order book midpoint).

Sprint 14 builds the **BTC probability model**: a real-time, calibrated probabilistic forecaster that runs within each trading hour. It produces a continuously updated estimate `p_hat(t)` — the probability of the Up outcome given all information available at time `t`. It also runs **lead-lag tests** to quantify how much Polymarket's implied probability lags behind the model's estimate, establishing whether a systematic edge exists.

This model becomes the core signal for:
- The Directional Probability Model in the fleet (Sprint 16).
- The mispricing feature `mispricing` in the feature pipeline (Sprint 12).
- The cross-sectional edge estimator (Sprint 16).

---

## Goals

1. Build and train a calibrated binary classifier estimating P(BTC close ≥ open | features at time t).
2. Serve real-time `p_hat(t)` updates via the feature pipeline from Sprint 12.
3. Conduct lead-lag tests to measure whether `p_hat(t)` systematically leads Polymarket's implied probability.
4. Implement fee-aware backtesting of a simple threshold-based taker strategy using the model's signals.
5. Provide model monitoring hooks: Brier score, calibration drift, AUC tracking.

---

## Precise Modeling Objective

Define an hourly interval `h` with open time `t_0` and close time `t_1 = t_0 + 3600s`.

- **Binance label:** `Y_h = 1` if BTC/USDT close ≥ open for hour `h` (from Binance 1h kline); `Y_h = 0` otherwise.
- **Forecast:** `p_hat(t) = P(Y_h = 1 | I_t)` for `t ∈ [t_0, t_1)`, where `I_t` includes only information up to time `t`.
- **Implied probability:** `p_PM(t) = (best_ask + best_bid) / 2` if `spread ≤ 0.10`, else `last_trade_price`. This is the Polymarket display convention.
- **Mispricing:** `M(t) = p_hat(t) - p_PM(t)`.

---

## Data Pipeline

### Panel Dataset Construction

One row per (hour `h`, timestamp `t`) at a 10-second sampling interval within the hour. Only information available at time `t` is used (no lookahead).

| Column | Source | Description |
|--------|--------|-------------|
| `Y_h` | Binance 1h kline `close >= open` | Label (known only after `t_1`) |
| `t_minus_t0` | Computed | Seconds since hour open |
| `time_to_close` | Computed | Seconds remaining in hour |
| All `FeatureSnapshot` fields | Sprint 12 `FeatureStore` | Full feature vector at time `t` |

The panel is built offline from the `pm.features` table populated by Sprint 12's `FeatureStore`. Missing feature rows (gaps in data collection) are interpolated using the last valid value, then flagged as `imputed = True`.

### Train / Validation / Test Split

Use walk-forward cross-validation with **no data leakage**:

- **Training folds:** weeks 1 to `k`.
- **Validation fold:** week `k + 1`.
- **Roll forward:** add one week at a time.
- **Minimum training period:** 4 weeks before any validation.
- **Hold-out test set:** the final 2 weeks of all available data, never used during development.

Regime-based splits are also computed: train/validate within each `vol_regime` bucket to detect whether the model generalizes across regimes or overfits to one state.

---

## Model Specifications

### Model 1 — Logistic Regression Baseline (Required)

A regularized logistic regression trained on the `FeatureSnapshot` vector. This is the mandatory interpretable baseline against which all other models are compared.

Key interactions to include explicitly:
- `btc_distance_to_open × time_to_close` — how far BTC has moved, relative to how much time remains.
- `order_book_imbalance × time_to_close` — whether buy/sell pressure is building late in the hour.
- `btc_rv_5m × time_to_close` — whether volatility is rising near close (adverse selection risk).

Regularization: L2, with `C` tuned via walk-forward CV. Calibrate with **Platt scaling** (sigmoid calibration) fitted on the validation fold.

### Model 2 — Gradient Boosted Trees (Primary)

XGBoost or LightGBM classifier on the full `FeatureSnapshot` feature vector. Provides nonlinear relationships and feature importance via SHAP.

Hyperparameter tuning via walk-forward CV. Calibrate with **isotonic regression** on the validation fold.

Key constraints:
- Maximum tree depth: 4 (prevents overfitting on small intraday datasets).
- Number of trees: tuned, typically 100–300.
- Feature importance logged per training run.

### Model 3 — Time-Series GLM with Lagged Terms (Optional)

A GLM that includes lagged values of `implied_probability` and `btc_distance_to_open` (e.g., at `t - 30s`, `t - 60s`, `t - 120s`) to explicitly capture inertia and microstructure lag. This model is most relevant for the lead-lag analysis.

### Calibration

All models pass through a calibration layer before serving predictions. Calibration is fitted independently per walk-forward fold. Output is a reliability diagram comparison across models.

Required calibration diagnostics per model per fold:
- Reliability diagram (10 probability bins).
- Expected Calibration Error (ECE).
- Brier score and its decomposition (reliability + resolution + uncertainty).

Recalibration trigger: if ECE on a rolling 7-day window exceeds `0.05`, flag the model for recalibration.

---

## Lead–Lag Testing

### Hypothesis

Positive mispricing `M(t) = p_hat(t) - p_PM(t) > 0` predicts upward future moves in `p_PM(t + τ)` with a measurable delay `τ`. This is formalized as:

```
Δp_PM(t + τ) = α + β * M(t) + γ * Δp_PM(t) + ε_t
```

`β > 0` for some set of horizons `τ ∈ {10s, 30s, 60s, 120s, 300s}` is the lead-lag signal.

### Test Suite

#### Test 1: Cross-correlation

Compute `corr(M(t), Δp_PM(t + τ))` for each horizon `τ`. Report as a bar chart over horizons. A positive peak at short `τ` and decay to zero at long `τ` indicates a predictive lead.

#### Test 2: Granger Causality

Regress `Δp_PM(t)` on lags of itself plus lags of `M(t)`. Test whether the `M(t)` lags add predictive power (F-test). Use VAR framework from `statsmodels`.

#### Test 3: Event Study Near Close

For each hour, compute the average `Δp_PM` response in windows `T - 10m`, `T - 5m`, `T - 2m`, `T - 1m` conditional on a large initial mispricing `|M(t_0)| > θ`. Report average and confidence intervals.

#### Test 4: Mispricing Persistence Curve

Compute `E[|M(t + τ)| / |M(t)|]` across horizons `τ`. The half-life of mispricing (the `τ` at which the ratio falls to 0.5) is the key operational parameter: it tells you how long an edge typically remains exploitable before Polymarket's price catches up.

### Reporting

Results for all four tests are stored in `pm.lag_test_results` and surfaced in the API. The half-life estimate is the primary decision input for Sprint 16's strategy ranking.

---

## Fee-Aware Backtest (Threshold Strategy)

Run a simple taker strategy on historical data using the simulation engine from Sprint 13:

**Decision rule:**

```
if M(t) > θ(t):
    BUY YES at best_ask  (taker)
elif M(t) < -θ(t):
    BUY NO at best_bid  (taker)
else:
    ABSTAIN
```

Where:

```
θ(t) = spread(t) / 2 + slippage_estimate(size) + fee_edge(p, size) + ε_risk_buffer
```

The threshold `θ(t)` varies in real time based on current orderbook state and fee regime. `ε_risk_buffer` is a configurable conservatism parameter (default: 0.005).

Results are compared across:
- Fee regimes (pre / post March 30).
- Volatility regimes (low / medium / high).
- Time-to-close windows (early / mid / late / near-close).
- Model variants (logistic vs GBT).

All results use the walk-forward held-out test set only. Training and validation data are never reported as trading results.

---

## Serving Architecture

### `services/ml/probability_model/`

```
services/ml/probability_model/
├── __init__.py
├── trainer.py          # ModelTrainer: walk-forward training, calibration
├── predictor.py        # ProbabilityPredictor: real-time p_hat(t) serving
├── lag_tests.py        # LagTestRunner: all four tests
├── drift.py            # DriftMonitor: ECE tracking, recalibration trigger
├── schemas.py          # PredictionRecord, LagTestResult, CalibrationReport
└── registry.py         # ModelRegistry: store/load trained models
```

### `ProbabilityPredictor`

Runs as an async service. Subscribes to the `FeatureBuilder`'s output queue (from Sprint 12). On each `FeatureSnapshot`:

1. Apply the trained calibrated model.
2. Produce `p_hat(t)`.
3. Compute `M(t) = p_hat(t) - snapshot.implied_probability`.
4. Write a `PredictionRecord` to `pm.probability_predictions`.
5. Publish `(p_hat, M, threshold_met)` to the signal bus for downstream strategy consumers.

```python
class PredictionRecord(BaseModel):
    record_id: UUID
    market_id: str
    token_id: str
    predicted_at: datetime
    p_hat: Decimal
    implied_probability: Decimal
    mispricing: Decimal
    threshold: Decimal
    threshold_met: bool
    model_version: str
    confidence: Decimal             # from calibration; e.g., p_hat * (1 - p_hat)
    data_staleness_ok: bool
```

### `ModelRegistry`

Stores trained model artifacts (serialized with `joblib`) in the filesystem or object storage, keyed by `(model_type, training_period, calibration_method)`. Integrates with the existing `services/ml/` model registry patterns.

---

## Database Tables

```sql
-- Model predictions (real-time)
CREATE TABLE pm.probability_predictions (
    record_id      UUID DEFAULT gen_random_uuid() NOT NULL,
    market_id      TEXT NOT NULL,
    token_id       TEXT NOT NULL,
    predicted_at   TIMESTAMPTZ NOT NULL,
    p_hat          DECIMAL NOT NULL,
    implied_prob   DECIMAL NOT NULL,
    mispricing     DECIMAL NOT NULL,
    threshold_met  BOOLEAN NOT NULL,
    model_version  TEXT NOT NULL,
    PRIMARY KEY (record_id, predicted_at)
);
SELECT create_hypertable('pm.probability_predictions', 'predicted_at');

-- Lag test results
CREATE TABLE pm.lag_test_results (
    test_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_at         TIMESTAMPTZ NOT NULL,
    test_type      TEXT NOT NULL,   -- 'cross_correlation' | 'granger' | 'event_study' | 'persistence'
    period_start   TIMESTAMPTZ NOT NULL,
    period_end     TIMESTAMPTZ NOT NULL,
    results        JSONB NOT NULL
);

-- Calibration reports
CREATE TABLE pm.calibration_reports (
    report_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    generated_at   TIMESTAMPTZ NOT NULL,
    model_version  TEXT NOT NULL,
    brier_score    DECIMAL NOT NULL,
    ece            DECIMAL NOT NULL,
    auc            DECIMAL,
    reliability    JSONB NOT NULL,    -- (bin_midpoint, observed_freq, predicted_freq) list
    needs_recal    BOOLEAN NOT NULL
);
```

---

## API Endpoints

New router `services/api/routers/probability.py`:

- `GET /v1/probability/{market_id}/latest` — returns latest `PredictionRecord`.
- `GET /v1/probability/{market_id}/history?start=&end=` — returns `List[PredictionRecord]`.
- `GET /v1/probability/calibration?model_version=` — returns latest `CalibrationReport`.
- `GET /v1/probability/lag-tests?type=cross_correlation` — returns latest `LagTestResult`.
- `POST /v1/probability/train` — trigger a training run (background task); returns `run_id`.

---

## Acceptance Criteria

### AC-1: Label construction
- `Y_h` labels are built from Binance 1h klines with correct UTC alignment.
- No future information leaks into any feature row.

### AC-2: Walk-forward correctness
- Training data for fold `k` contains no observations from fold `k + 1` or later.
- Calibration is fitted only on the validation fold (not training fold).

### AC-3: Brier score baseline
- The logistic regression model achieves Brier score < 0.25 on the held-out test set (a model that always predicts 0.5 scores 0.25; any useful model must beat this).
- The GBT model achieves Brier score ≤ logistic regression Brier score.

### AC-4: Calibration quality
- On the held-out test set, both models have ECE < 0.05 (well-calibrated).
- Reliability diagrams are generated and stored in `pm.calibration_reports`.

### AC-5: Lead-lag signal
- Cross-correlation test reports `corr(M(t), Δp_PM(t + τ)) > 0.05` at `τ = 30s` or `τ = 60s`.
- Granger F-test is significant at `p < 0.05` for at least one lag horizon.

### AC-6: Real-time serving
- `ProbabilityPredictor` produces a `PredictionRecord` within 200ms of receiving a `FeatureSnapshot`.
- Latency measured as `predicted_at - snapshot.captured_at`.

### AC-7: Fee-aware backtest
- Threshold strategy PnL is computed correctly for both fee regimes (pre/post March 30).
- Hold-out test backtest results are stored in `pm.simulation_runs` (via Sprint 13 `SimulationRunner`).

### AC-8: Drift detection
- `DriftMonitor` correctly flags `needs_recal = True` when ECE on rolling 7-day window exceeds 0.05.
- Alert is surfaced via the API calibration endpoint.

### AC-9: Tests
- Unit tests for label construction (correct Binance alignment, no lookahead).
- Unit tests for each statistical test (cross-correlation, Granger) with synthetic data.
- Unit tests for `ProbabilityPredictor` latency (mock `FeatureSnapshot` → `PredictionRecord`).
- Integration test: train logistic model on 2 weeks of synthetic panel data, validate Brier score, serve one prediction.

---

## Out of Scope

- Training the regime detector (Sprint 15).
- Full fleet competition and model ranking (Sprint 16).
- SHAP explainability on the probability model (can be added as a patch after Sprint 14).
- Directional bet execution (model produces signals only; execution happens via the fleet orchestrator in Sprint 16).

---

## Implementation Order

1. **Schemas** — `PredictionRecord`, `LagTestResult`, `CalibrationReport`.
2. **Panel dataset builder** — read from `pm.features`, apply walk-forward splits.
3. **Logistic regression baseline** — train, calibrate, evaluate on held-out set.
4. **GBT model** — train, calibrate, evaluate; compare to baseline.
5. **Lead-lag tests** — cross-correlation, Granger, event study, persistence curve.
6. **Fee-aware backtest** — integrate with Sprint 13 `SimulationRunner`.
7. **`ProbabilityPredictor`** — async serving from `FeatureBuilder` queue.
8. **`DriftMonitor`** — ECE rolling window, recalibration trigger.
9. **Database migration** — three new tables.
10. **API endpoints** — probability router.

---

## Recommended Skills

| Task | Skill |
|------|-------|
| Logistic regression, calibration (Platt/isotonic), walk-forward CV | `scikit-learn` |
| Granger causality, cross-correlation, time-series GLM | `statsmodels` |
| PnL attribution, fee-aware edge computation | `quant-analyst` |
| Model registry, calibration drift monitoring | `mlops-engineer` |
| Pytest fixtures, walk-forward test patterns | `python-testing-patterns` |

---

## Risk Notes

- **Lookahead bias:** the single highest-risk error in probability modeling. All features must use data with timestamps strictly before the row's `t`. The panel builder must enforce this with a `max_timestamp = t - Δt` filter on all data sources.
- **Small sample size:** hourly BTC markets produce at most ~24 labeled hours per day. At least 4 weeks (≈ 672 hours) of data are required before training. The model should refuse to serve predictions if fewer than this threshold of labeled hours exist.
- **Calibration instability near t = t_1:** in the final minutes of each hour, `btc_distance_to_open` approaches its terminal value and the model's confidence can become extreme. Apply a time-to-close soft cap: set model confidence to max(`p_hat`, 0.95) / min(`p_hat`, 0.05) for `time_to_close < 120s` to prevent overconfident predictions that create excessive adverse selection exposure.
- **Fee regime boundary:** ensure the fee-aware backtest applies the correct fee parameters based on the market creation date (pre/post March 6) and trade date (pre/post March 30), not just one of these dimensions.
