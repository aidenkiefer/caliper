# Caliper Deep Review & Forward Planning

This document is a design review and feature-planning artifact for the Caliper (quant) codebase. It explains how the system works today, what is implemented versus planned, and how the project should evolve next. The audience is a developer with strong software and moderate ML background but minimal trading experience.

> **Status (2026-04):** Sprints **7–10** shipped after much of this narrative was written. For **current** ML and dashboard state, see **[docs/SPRINTS-7-8-9-SUMMARY.md](docs/SPRINTS-7-8-9-SUMMARY.md)** and **[docs/plans/PROGRESS.md](docs/plans/PROGRESS.md)**. For **Polymarket**, see **[docs/plans/summaries/SPRINT-10-POLYMARKET-COMPLETE.md](docs/plans/summaries/SPRINT-10-POLYMARKET-COMPLETE.md)**. Sections below mix **updated** snapshots with **older** paragraphs—use the linked docs as source of truth where they conflict.

---

## 1. Current ML and Model System (Explained for Non-Traders)

### What exists today (post–Sprint 9)

The repo includes a **first ML path** end-to-end: training scripts under **`services/ml/training/`**, a model interface in **`packages/common/ml_schemas.py`**, inference wiring via **`MLDirectionStrategyV1`** (`packages/strategies/ml_direction_v1.py`), confidence gating, text explainability, performance tracking, drift APIs, SHAP/permutation hooks, baselines/regret, and a **Model Observatory** in the dashboard. **Which strategy is active in your deployment** (SMA vs ML vs both) is a **configuration and operations** choice, not fixed in this doc.

The following modules remain the **core safety/interpretability layer** (see Sprint 6–8 docs for detail):

- **Confidence gating** (`services/ml/confidence/`) — ABSTAIN and thresholding on model outputs.
- **Explainability** (`services/ml/explainability/`) — SHAP, permutation, SimpleExplainer.
- **Drift** (`services/ml/drift/`) — PSI, KL, health score, alerts.
- **Baselines and regret** (`services/ml/baselines/`).
- **HITL** (`services/ml/hitl/`) — recommendation queue schemas and flows.

**Rule-based reference:** **SMA Crossover** remains the simple baseline strategy (`packages/strategies/sma_crossover.py`).

### Historical note (pre–Sprint 7 narrative)

Earlier revisions of this file stated that **no** model was trained or invoked. That is **no longer** accurate for the codebase as of Sprints 7–9; keep the **conceptual** explanations below for how signals flow and what to watch for (leakage, drift, abstention), but verify filenames and wiring in the repo.

### Adding another model (e.g. XGBoost / LightGBM)

The **first** sklearn-based direction model path is already sketched in code (training script, `MLDirectionStrategyV1`, schemas). For **additional** models:

- **Inputs:** The feature pipeline (`services/features/`) computes 30+ features from price bars. A model typically consumes a feature vector (or row) per bar; the backtest engine still may not auto-invoke the feature pipeline—confirm wiring for your strategy.
- **Outputs:** The system expects **signal** (BUY/SELL/ABSTAIN) and **confidence** (0–1) at the strategy boundary, with gating and explainability layered as in Sprints 6–8.
- **Training:** Offline training lives under **`services/ml/training/`** (time-aware splits, leakage avoidance—see Sprint 7 docs). The **walk-forward engine** in backtest remains for **strategy parameter** search, not for substituting ML training.
- **Temporal splits:** Use explicit train/validation/test discipline for any new model; reuse Sprint 7 patterns.
- **Safeguards:** Abstention, drift, and explainability APIs exist; ensure new models are wired through the same contracts.

### Summary Table

| Aspect | Current state (verify in deployment) |
|--------|-------------------------------------|
| Models used for signals | **SMA Crossover** (rule) and **ML direction strategy** (trained sklearn path) exist in code; which runs in production is a config/ops choice. |
| Training | **Implemented** for the first model path (`services/ml/training/`); extend for new model families as needed. |
| Validation / testing | Backtest + walk-forward for rules; ML evaluation + observatory for model metrics (Sprints 8–9). |
| Temporal splits | Sprint 7 training uses time-aware splitting; still your responsibility for new datasets/models. |
| Overfitting / leakage | Practices documented in Sprint 7; not automatically enforced for arbitrary new pipelines. |
| Model adaptation | Static artifacts + lifecycle UI; no online learning in core repo. |
| Confidence / abstention | Gating and backtest ABSTAIN handling implemented; wired for ML strategy path. |

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

- **In repo:** **SMA Crossover** (rule-based) and **`MLDirectionStrategyV1`** (ML inference + gating) both implement the `Strategy` interface. Configure which strategy a run uses.
- **Signal shape:** Strategies produce `Signal` objects (BUY/SELL/ABSTAIN). The backtest engine records ABSTAIN and excludes it from order simulation before risk check.

### 4. Signal generation

- **When:** In backtest, `generate_signals(portfolio)` is called after each bar. In live/paper, the same interface would be used when new data is available.
- **Determinism:** SMA Crossover is deterministic given the same bar history. ML inference is deterministic for a fixed artifact and input unless you introduce stochastic models or sampling.

### 5. Risk checks and constraints

- **Order-level:** Risk manager enforces max risk per trade (e.g. 2% of equity), max notional, min price, max price deviation, etc., per `docs/risk-policy.md`.
- **Strategy-level:** Max allocation, daily loss limit, drawdown-based pause.
- **Portfolio-level:** Max daily drawdown (circuit breaker), max total drawdown (kill switch), max capital deployed, max open positions.
- **Kill switch:** Global and per-strategy; when active, orders are blocked. Circuit breaker can auto-trigger on drawdown thresholds.
- **Order of operations:** Kill switch first, then order limits, then strategy limits, then portfolio limits. Failure at any step rejects the order.

### 6. Trade sizing and execution

- **Sizing:** SMA Crossover uses a configurable fraction of equity per position (e.g. 10%). Risk checks can further cap size.
- **Execution:** Orders that pass risk checks go to the OMS. The OMS uses a `BrokerClient` abstraction; the implemented client is Alpaca (paper). Orders move through states (e.g. PENDING → SUBMITTED → FILLED/REJECTED/CANCELLED). Position reconciliation compares local state to broker state and can pause trading on mismatch.

### 7. Observability, logging, and feedback

- **Backtest:** Equity curve, trades, performance metrics, and abstention metadata in reports.
- **API / dashboard:** Health and metrics routers exist; many dashboard list endpoints still use **mock** fixtures until wired to persistent stores—confirm `services/api/dependencies.py` and routers. **Polymarket** analytics: **`pm.*`** + **`GET /v1/polymarket/*`** when DB is wired.

### Where decisions are deterministic vs probabilistic

- **Deterministic:** Strategy logic (SMA), risk checks, order state machine, fill simulation in backtest (slippage/commission are deterministic given config).
- **Probabilistic:** ML models output probabilities or scores that strategies map to BUY/SELL/ABSTAIN via thresholds and gating.

### When confidence is low or safeguards override

- **Low confidence:** Gating maps low confidence to ABSTAIN; ensure your live loop uses the same path as backtest for the ML strategy.
- **Safeguards override:** Risk manager and kill switch reject or block orders; no order is sent to the broker when they fail. Circuit breaker and kill switch are designed to halt new exposure when drawdown limits are hit.

---

## 3. Implemented vs Planned vs Missing

### Fully implemented and production-ready (logic and tests)

- **Backtest engine:** Strategy loop, fill simulation (slippage, commission), position tracking, P&L, performance metrics, abstention tracking, date filtering. Walk-forward is for parameter optimization, not ML training.
- **Strategy framework:** Base interface, SMA Crossover, and ML direction strategy; compatible with backtest and execution paths when configured.
- **Execution:** OMS, broker adapter (Alpaca), order lifecycle, position reconciliation, idempotency via `client_order_id`.
- **Risk:** RiskManager, kill switch, circuit breaker, order/strategy/portfolio limits as per risk policy.
- **Feature pipeline:** Indicators and feature computation from bars; used by ML training/inference paths where wired.
- **ML building blocks:** Drift, confidence gating (ABSTAIN), SHAP/permutation, baselines/regret, HITL—implemented as libraries and API routes, integrated for the ML strategy and observatory (Sprints 6–9).
- **Dashboard and API structure:** Next.js app (incl. Model Observatory), FastAPI routers for health, metrics, strategies, runs, positions, drift, explanations, baselines, recommendations, **Polymarket session reads**. Help/glossary, explanation UI, approval queue, baseline comparison.
- **Polymarket (Sprint 10):** Optional `services/polymarket/` bot, **`pm.*`** schema, **`/v1/polymarket/*`** — parallel to equity OMS; see Sprint 10 summary.

### Implemented but still deployment-dependent

- **API list endpoints:** May still use **mock** data for strategies, runs, positions depending on `dependencies.py` wiring; confirm per environment.
- **Polymarket API:** Read endpoints are defined; live SQL wiring depends on DB configuration.
- **HITL:** Schemas and UI exist; whether execution **requires** approval before submit is a product wiring choice.

### Planned or partial (direction of travel)

- **Full experiment / artifact registry** beyond what the observatory and file-based model artifacts provide today.
- **Dedicated monitoring microservice** (Prometheus/Grafana, paging)—observability is currently API + ML modules + DB, not a separate `services/monitoring` process.
- **Polymarket Phase 2+:** Inventory skew, dynamic spread, directional model, richer dashboard integration (see spec §10).
- **Equity API persistence:** Replace or supplement mocks with durable DB reads/writes for runs and positions where not yet done.

### Gaps to watch (docs vs running system)

- **Mock vs live:** Some API responses may not reflect persisted backtests or live broker state until wired—treat OpenAPI and `dependencies.py` as the judge.
- **Strategy list in UI/API:** Display names may include placeholders that do not map 1:1 to checked-in strategy modules—verify `packages/strategies` and configs.

### Hardening checklist (still worth doing)

1. **Reproducibility:** Tie each reported run to config, data snapshot, and model artifact hashes where possible.
2. **Operational ML:** Scheduled retrain, drift-driven alerts, and clear rollback for bad promotions.
3. **Persistence:** Single source of truth for positions/orders/runs in DB for dashboard at scale.
4. **Polymarket scale-up:** Phase 1 data collection before widening capital; tune from `pm.*` analytics.

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

## 7. Recommendations after Sprints 7–10

Sprints **7–9** delivered the first ML loop, observability, and Model Observatory; **10** added Polymarket V1. Use this list as **iteration** priorities, not greenfield work.

### Near-term

1. **Persistence and mocks:** Replace or narrow API mocks so runs, positions, and strategies reflect DB and broker state where you need truth for demos or ops.
2. **HITL optional enforcement:** If desired, gate order submission on approval queue state for selected strategies.
3. **Polymarket Phase 1 ops:** Run dust sessions, tune from `pm.*` (queue position, adverse selection, toxic flow), then plan Phase 2 quoting improvements per spec.

### Medium-term

4. **Experiment tracking:** Strengthen linkage from dashboard “run” or “model” views to dataset hashes, git SHA, and artifact paths (beyond current UI/API capabilities).
5. **Automation:** Scheduled retrain, drift-based alerts with explicit playbooks, model promotion rules.
6. **Observability service (optional):** If you outgrow API-only metrics, add Prometheus/Grafana or similar **without** blurring the equity vs Polymarket execution boundaries.

### Correctness and safety (ongoing)

- Equity orders: always through **RiskManager** / kill switch / circuit breaker.
- Polymarket: respect **`services/polymarket` safety** and post-only discipline; do not route CLOB orders through equity risk code.
- Stress and failure modes: use **`docs/runbooks/stress-scenarios.md`** and expand as new surfaces go live.

### Refactors for long-term maintainability

- **Feature parity:** Where ML strategies are used, ensure backtest and live share the same feature computation path when feasible.
- **Config:** Keep strategy YAML and env templates the single place for thresholds, model paths, and mode switches.

---

*End of deep review. Use this document to align implementation with your learning-first and correctness-first goals and to decide the order of the next features.*
