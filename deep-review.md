# Caliper Deep Review & Forward Planning

This document is a design review and feature-planning artifact for the Caliper (quant) codebase. It explains how the system works today, what is implemented versus planned, and how the project should evolve next. The audience is a developer with strong software and moderate ML background but minimal trading experience.

---

## 1. Current ML and Model System (Explained for Non-Traders)

### What Exists Today

**No trained ML model is currently used for trading.** The only live strategy is **SMA Crossover**, which is purely rule-based: it buys when a short moving average crosses above a long moving average (golden cross) and sells on the opposite crossover (death cross). All logic is in code; there is no model fitting or inference step.

The codebase does, however, contain **ML-oriented infrastructure** intended for when you add real models:

- **Confidence gating** (`services/ml/confidence/`): Defines a `ModelOutput` with `signal` (BUY/SELL/ABSTAIN), `confidence`, and `uncertainty`. A `ConfidenceGating` class applies configurable thresholds so that low-confidence predictions can be turned into ABSTAIN instead of BUY/SELL. No model is wired to this yet.
- **SHAP explainability** (`services/ml/explainability/`): `ShapExplainer` takes a **tree-based model** (e.g. XGBoost, LightGBM, sklearn tree) and a feature DataFrame, and produces a `TradeExplanation` (feature contributions, direction, confidence). The backtest and execution paths do not call this; it is ready for the day you have a trained tree model and want to attach explanations to trades.
- **Drift detection** (`services/ml/drift/`): Computes PSI, KL divergence, and mean shift between a **reference** (e.g. training) distribution and **current** feature or confidence distributions. It can produce a composite “health score” and alerts. It is not connected to any live data feed or model; you would supply reference and current data when you integrate a model.
- **Baselines and regret** (`services/ml/baselines/`): Implements hold-cash, buy-and-hold, and a risk-controlled random baseline, plus a `RegretCalculator` to compare strategy performance vs those baselines. These are usable with any strategy (including SMA Crossover) for comparison.
- **Human-in-the-loop** (`services/ml/hitl/`): Approval queue and recommendation schemas so that a “recommendation” can be held for human approve/reject before turning into an order. The plumbing exists; it is not yet in the critical path of the execution engine.

So: **inputs and outputs** for a future ML model are largely specified (features, confidence, ABSTAIN, explanations), but **no model is trained, loaded, or invoked** in the current pipeline.

### What a Future Model Would Look Like

If you add an ML model (e.g. XGBoost):

- **Inputs:** The feature pipeline (`services/features/`) already computes 30+ features (SMA, EMA, RSI, MACD, Bollinger, ATR, Stochastic, returns, volatility, etc.) from price bars. A model would receive a feature vector (or DataFrame row) per bar or per symbol-bar.
- **Outputs:** The system expects a **signal** (BUY/SELL/ABSTAIN) and a **confidence** (0–1). Confidence gating would then decide whether to downgrade to ABSTAIN. SHAP would consume the same feature row and the trained model to produce per-trade explanations.
- **Training:** There is **no training pipeline** yet. No offline training job, no walk-forward training, and no model serialization/loading in the strategy layer. The **walk-forward engine** in backtest is for **strategy parameter optimization** (e.g. SMA periods), not for training ML models.
- **Temporal splits:** Backtest supports date-range filtering and the walk-forward engine uses in-sample/out-of-sample windows, but those are for strategy parameters, not for training/validation/test of a model. You would need to add explicit train/validation/test splits and avoid future leakage when you introduce model training.
- **Safeguards:** Abstention is supported in the backtest engine (ABSTAIN signals are recorded and excluded from orders). Confidence gating and drift detection are implemented as modules but not yet wired so that a live model’s outputs flow through them. Data leakage prevention would be your responsibility when you build the training pipeline (e.g. no future data in features, proper time-based splits).

### Summary Table

| Aspect | Current state |
|--------|----------------|
| Models used for signals | None (only rule-based SMA Crossover). |
| Training | Not implemented. |
| Validation / testing | Backtest and walk-forward exist for strategy params only. |
| Temporal splits | Date filtering and walk-forward windows exist; no train/val/test for ML. |
| Overfitting / leakage | No automated safeguards; would be addressed when training is added. |
| Model adaptation | Models are static; no online learning or scheduled retraining. |
| Confidence / abstention | Implemented in code (gating, backtest abstention tracking); not connected to a model. |

---

## 2. End-to-End Trading Decision Pipeline

Here is how the system goes from market data to an order (or to a decision not to trade), step by step.

### 1. Market data ingestion

- **Source:** Alpaca (historical and paper). A data provider layer is abstracted; Alpaca is the implemented provider.
- **Stored:** Price bars (OHLCV) can be stored in Postgres with TimescaleDB. The backtest path can also work with in-memory bar lists (e.g. from tests or from a prior fetch).
- **Live:** Architecture describes event-driven + polling; the execution path expects data to be available (e.g. from a scheduler or live feed) so that strategies can run. The exact trigger (cron, queue, or streaming) is not fully spelled out in the code reviewed.

### 2. Feature generation

- **Service:** `services/features` provides a `FeaturePipeline` that turns price bars into a DataFrame of technical indicators and derived features (30+).
- **Usage:** The **backtest engine does not call the feature pipeline**. The SMA Crossover strategy only needs raw price bars; it keeps a short rolling window and computes its own SMAs. So today, feature generation is **optional** and would become central when an ML strategy is added (e.g. features → model → signal).

### 3. Strategy logic vs ML

- **Current:** The only plugged-in strategy is SMA Crossover. It uses only price history and moving averages; no ML model is involved.
- **Signal shape:** Strategies produce a list of `Signal` objects (symbol, side BUY/SELL, strength, optional price/quantity/reason). The base strategy interface does not mandate ABSTAIN; the backtest engine explicitly handles `side == "ABSTAIN"` (recorded, then filtered out before risk check). So an ML strategy could emit ABSTAIN by convention (e.g. via confidence gating) and the rest of the pipeline already supports it.

### 4. Signal generation

- **When:** In backtest, `generate_signals(portfolio)` is called after each bar. In live/paper, the same interface would be used when new data is available.
- **Determinism:** SMA Crossover is deterministic given the same bar history. A future ML model would add randomness only if the model or sampling is stochastic; the current pipeline does not inject randomness.

### 5. Risk checks and constraints

- **Order-level:** Risk manager enforces max risk per trade (e.g. 2% of equity), max notional, min price, max price deviation, etc., per `docs/risk-policy.md`.
- **Strategy-level:** Max allocation, daily loss limit, drawdown-based pause.
- **Portfolio-level:** Max daily drawdown (circuit breaker), max total drawdown (kill switch), max capital deployed, max open positions.
- **Kill switch:** Global and per-strategy; when active, orders are blocked. Circuit breaker can auto-trigger on drawdown thresholds.
- **Order of operations:** Kill switch first, then order limits, then strategy limits, then portfolio limits. Failure at any step rejects the order.

### 6. Trade sizing and execution

- **Sizing:** SMA Crossover uses a configurable fraction of equity per position (e.g. 10%). Risk checks can further cap size.
- **Execution:** Orders that pass risk checks go to the OMS. The OMS uses a `BrokerClient` abstraction; the implemented client is Alpaca (paper). Orders move through states (e.g. PENDING → SUBMITTED → FILLED/REJECTED/CANCELLED). Position reconciliation compares local state to broker state and can pause trading on mismatch.

### 7. Monitoring, logging, and feedback

- **Backtest:** Equity curve, trades, and performance metrics (Sharpe, max drawdown, win rate, profit factor, etc.) are computed and can be written to JSON/HTML reports. Abstention metrics (count and rate of ABSTAIN) are included in backtest metadata.
- **Live/paper:** Intended to be covered by monitoring and API (metrics, positions, orders, health). API currently serves mock data for strategies, runs, positions; execution and risk code are real.

### Where decisions are deterministic vs probabilistic

- **Deterministic:** Strategy logic (SMA), risk checks, order state machine, fill simulation in backtest (slippage/commission are deterministic given config).
- **Probabilistic:** Would come from an ML model (e.g. probability outputs turned into BUY/SELL/ABSTAIN via thresholds). Not present until a model is added.

### When confidence is low or safeguards override

- **Low confidence:** Confidence gating can map low confidence to ABSTAIN; the backtest engine already ignores ABSTAIN for order generation and only records it. In live execution, you would need to route model output through the gating layer before producing signals.
- **Safeguards override:** Risk manager and kill switch reject or block orders; no order is sent to the broker when they fail. Circuit breaker and kill switch are designed to halt new exposure when drawdown limits are hit.

---

## 3. Implemented vs Planned vs Missing

### Fully implemented and production-ready (logic and tests)

- **Backtest engine:** Strategy loop, fill simulation (slippage, commission), position tracking, P&L, performance metrics, abstention tracking, date filtering. Walk-forward is for parameter optimization, not ML training.
- **Strategy framework:** Base interface and SMA Crossover strategy; works with backtest and is compatible with the execution path.
- **Execution:** OMS, broker adapter (Alpaca), order lifecycle, position reconciliation, idempotency via `client_order_id`.
- **Risk:** RiskManager, kill switch, circuit breaker, order/strategy/portfolio limits as per risk policy.
- **Feature pipeline:** Indicators and feature computation from bars; usable by code or by a future ML strategy.
- **ML building blocks:** Drift (PSI, KL, mean shift, health score), confidence gating (including ABSTAIN), SHAP and permutation explainers, baselines and regret, HITL queue and schemas. These are implemented as libraries/schemas and API routes; they are not yet in the critical path of the single live strategy (SMA Crossover).
- **Dashboard and API structure:** Next.js app, FastAPI routers, documented endpoints for health, metrics, strategies, runs, positions, drift, explanations, baselines, recommendations. Educational tooltips, help/glossary, explanation UI, approval queue UI, baseline comparison.

### Implemented but not wired to real data

- **API:** Uses mock data for strategies, runs, positions, metrics. Database and auth are stubbed (see `dependencies.py`). So “production-ready” here means “code and contracts are in place,” not “serving live DB.”
- **Drift / explanations:** Require reference and current feature data (and, for SHAP, a trained model). No automatic pipeline yet from a live model or data feed to these endpoints.
- **HITL:** Approval queue and schemas exist; execution path does not yet require human approval before sending an order.

### Planned but not implemented

- **Model training:** No training job, no train/val/test split, no model registry or versioning.
- **Model in the loop:** No strategy that loads a trained model and calls it for predictions; no wiring of model output → confidence gating → signals → risk → execution.
- **Feature registry, experiment registry, model registry backend:** Scheduled for Sprint 7 (MLOps).
- **Dynamic capital allocation, failure-mode/stress simulation:** Planned.
- **Model observatory dashboard (Sprint 8):** Model list/detail, ML performance charts, comparison, lifecycle controls, drift visualization UI, model-centric HITL, sandbox/what-if.
- **Monitoring service:** Referenced in architecture; not present as a separate service in the repo.
- **Data service:** Documented (Alpaca, DB); repo layout shows `services/data` in architecture; implementation depth not fully verified here. Backtest and execution assume data is available somehow.

### Gaps between docs and code

- **README/architecture** mention multiple strategies and “XGBoost-based” momentum; the only implemented strategy is SMA Crossover and it is rule-based. Mock strategy data in the API (e.g. “momentum_v1”, “mean_reversion_v1”) does not correspond to real strategy implementations.
- **Dashboard/API** are described as viewing “backtest results”; the API currently returns mock runs/strategies/positions, so real backtest results are not yet persisted and served through this stack in a deployed flow (you can run backtests locally and get reports).

### Critical missing pieces for experimentation, safety, and understanding

1. **Reproducible experiments:** No experiment or model registry; no link from “this backtest run” to “this model version / these features / this config.”
2. **Model iteration:** No training pipeline, so no way to iterate on model type, features, or hyperparameters in a tracked way.
3. **End-to-end wiring of ML safeguards:** Drift and confidence gating are not in the execution path; you cannot yet “run with confidence gating and drift alerts” in front of a real model.
4. **Real data path to API/dashboard:** Replacing mocks with DB (and optional persistence of backtest results) so that the dashboard reflects real strategies, runs, and positions.
5. **Clarity on “one strategy vs many”:** SMA Crossover is one strategy; multi-strategy allocation and risk are designed, but a single clear path (e.g. “one model, one strategy”) for the first ML model would reduce ambiguity.

---

## 4. Model Transparency and User Control Opportunities

These are concrete ways to give an ML-oriented user more visibility and control, aligned with the existing code and docs.

- **Per-model performance:** When you have a model, expose in the API and UI: accuracy/direction correctness, abstention rate, and PnL/Sharpe per model (or per strategy that uses that model). The dashboard already has strategy and run concepts; extend them to “model” once a model registry exists.
- **Parameters and thresholds:** Confidence gating already has config (abstain/low/high thresholds). Expose these in the dashboard (read and, with care, edit) and log changes. Same for risk limits and any model-specific thresholds.
- **Side-by-side comparison:** Use the existing baseline/regret machinery and extend it to “model A vs model B” (e.g. same period, same universe) in the UI. Sprint 8’s “model comparison & ranking” is the natural home.
- **Enable/disable models:** Model registry lifecycle (active/paused/retired) in Sprint 7/8 gives explicit enable/disable. For a single-model first version, a simple “use this model in this strategy” flag plus kill switch already gives a form of disable.
- **Why a prediction:** SHAP and permutation explainers already produce feature contributions. Persist explanations with trades (or recommendations) and show them in the existing explanation UI so the user can see why the model said BUY/SELL/ABSTAIN.
- **When the model abstains or fails:** Backtest already records abstention rate. In live/paper, log every ABSTAIN and every rejection (risk, kill switch, broker). A small “recent abstentions/rejections” panel or filter in the dashboard would make this visible.
- **Predictions vs outcomes:** Once you have a model and store predictions with timestamps, add “prediction vs actual” (direction or return) over time. Sprint 8’s “prediction vs actual plots” and “calibration curves” are the right place; the API could expose aggregated correctness and calibration stats per model.

Prioritizing: (1) explanations attached to trades/recommendations, (2) visible abstention and rejection reasons, (3) per-model performance and thresholds in the UI, (4) then comparison and calibration.

---

## 5. Improving Accuracy Without Finance Expertise

Focus on ML and statistical hygiene rather than market theory.

- **Validation:** Introduce strict time-based train/validation/test splits when you add model training. Use the existing walk-forward idea for **evaluation** (e.g. rolling OOS windows) and report metrics only on OOS data. Avoid training on any data that would not have been available at prediction time.
- **Ensembles:** When you have multiple models, use the existing confidence/uncertainty and gating: e.g. abstain when ensemble disagreement is high, or weight by recent OOS performance. Regret vs baselines already gives a template for “strategy vs reference.”
- **Data quality:** Validate features (no NaNs/Infs where not expected, basic bounds). In the feature pipeline or before model input, add simple sanity checks and log anomalies. Drift (PSI, KL) on features helps detect distribution shift; wire it to reference (training) vs current (inference) once a model is in the loop.
- **Safety:** Keep confidence gating and ABSTAIN; consider a “confidence decay” (e.g. reduce effective confidence over time since last retrain) to avoid overconfidence on stale models. Allow a “model veto” (e.g. human or rule-based override) and log it. Isolate failing models (e.g. pause a single model in an ensemble) without killing the whole system.
- **Feedback:** Store predictions and outcomes (direction or return) and use them for drift (error drift) and for retraining. Avoid reinforcing noise: e.g. use robust targets and avoid training on very short-term flukes. Prefer simple, interpretable feedback (e.g. “right direction” or “within range”) until you have enough data for more nuanced metrics.

Emphasize: reproducibility (seeded splits, logged config), interpretability (explanations, abstention reasons), and testability (unit tests for splits, gating, and drift on synthetic data).

---

## 6. Questions the Project Owner Should Be Asking

- **Architecture:** Do we want the first ML model to live inside the existing Strategy interface (e.g. “MLStrategy” that loads one model and uses the feature pipeline), or as a separate service that the strategy calls? How will we schedule and trigger live/paper inference (cron, queue, or streaming)?
- **ML methodology:** What is the target variable (e.g. next-bar return, binary direction, multi-day horizon)? How will we avoid look-ahead bias in features and labels? What is the minimum OOS period we trust before considering a model “valid”?
- **Experimentation:** How do we version datasets, features, and models so that every backtest and live run can be reproduced? Do we need an experiment registry before or in parallel with the first trained model?
- **UX and learning:** Who is the primary user of the dashboard (you only, or also collaborators)? Do we want a “learning mode” (e.g. show why the model said ABSTAIN, or compare last 10 predictions vs outcomes) before adding more automation?
- **Risk and safety:** For the first ML-driven strategy, do we want every recommendation to go through HITL, or only those below a confidence threshold? How do we define and test “circuit breaker and kill switch still work when the model is wrong”?

These questions should guide the next design steps and sprint choices (e.g. “first integrate one model + gating + explanations” vs “first build experiment registry”).

---

## 7. Recommendations for Next Sprints

### Near-term (next 1–2 sprints)

1. **Integrate one ML model end-to-end (learning path).**  
   Pick a simple model (e.g. logistic regression or a small tree model) and a single symbol/universe. Implement a minimal training script: time-based train/val split, fit, serialize. Add a strategy (or extend the strategy interface) that loads this model, runs the feature pipeline on the same bars, calls the model for signal and confidence, and runs output through confidence gating (so low confidence → ABSTAIN). Wire that strategy into the backtest engine and verify abstention and metrics. No need for full MLOps yet; goal is to see “model → gating → backtest” work and to attach SHAP explanations to a few sample trades.
2. **Replace API mocks with real data where it matters most.**  
   At least: persist and serve real backtest runs (e.g. after each run, write summary and key metrics to DB and expose via existing runs API). Optionally: real strategies and positions from the execution layer. This makes the dashboard useful for real experimentation and demos.
3. **HITL in the execution path (optional but high value).**  
   Add a configuration flag “require_human_approval” for a strategy. When set, recommendations from that strategy go to the existing approval queue and only approved items become orders. Log approvals/rejections and agreement rate. This builds trust before increasing automation.

### Medium-term (Sprint 7–8)

4. **Experiment and model registry (Sprint 7).**  
   Implement experiment registry (dataset version, feature set, model type, hyperparameters, metrics) and a minimal model registry (metadata, lifecycle state, health score link). This enables “which model is live?” and “why this backtest result?” without digging through code.
5. **Drift and health in the loop.**  
   When a model is live, feed current feature (and optionally confidence) distributions into the drift detector against a stored reference. Expose health score and alerts via API and dashboard; consider auto-pausing a model when health drops below a threshold (with clear logging and override).
6. **Model observatory UI (Sprint 8).**  
   Prioritize: model list and detail (config, training summary, health), prediction vs actual and calibration, and drift/health visualization. Then add comparison, lifecycle controls, and sandbox/what-if so the platform supports learning and tuning, not only monitoring.

### Critical for learning and understanding

- First ML model integrated with gating and explanations (above).
- Persisted backtest runs and, when applicable, “run ↔ model/experiment” linkage.
- Dashboard views for “why did we abstain?” and “how did this model perform last N days?”

### Critical for correctness and safety

- Keep risk and kill switch in front of every order.
- Add HITL for the first ML strategy (or for low-confidence recommendations).
- Wire drift/health to at least alerts, and optionally to auto-pause.
- Document and test failure modes (e.g. missing data, broker down, drift spike) using the planned stress-simulation framework.

### Refactors for long-term maintainability

- **Single entry point for “strategy output”:** Unify the shape of strategy output (signal + confidence + optional explanation_id) so that both rule-based and ML strategies can be treated the same by backtest and execution (and so ABSTAIN and explanations are first-class).
- **Feature pipeline in backtest:** Optionally run the feature pipeline inside the backtest loop when the strategy is ML-based, so that the same feature computation is used in backtest and live, and so drift reference can be taken from backtest or training data.
- **Config and secrets:** Centralize strategy and model config (and secrets) so that adding a new model or strategy does not require scattered edits. The existing YAML strategy config is a good start; extend it for “model_id” and “confidence_config” when you add the first ML strategy.

---

*End of deep review. Use this document to align implementation with your learning-first and correctness-first goals and to decide the order of the next features.*
