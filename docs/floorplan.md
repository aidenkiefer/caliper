# Quant-ML Trading Bots: Project Floor-Plan (Antigravity ➜ Cursor ➜ Vercel)
**Purpose:** This document is the single source of truth (SSOT) for planning the end-to-end system: data → research → backtesting → paper/live execution → monitoring → dashboard UI.

**Workflow:** Use **Antigravity Agents + Skills/Superpowers** to produce a thorough plan (architecture, infra, systems, tasks, docs). Then move the repo to **Cursor Agents** for implementation using the same plan and artifacts.

> **Important:** Trading involves real financial risk. This project must include safety controls (paper trading, kill switches, max drawdown limits, strict API key handling).

---

## 1) North Star Requirements
### 1.1 Goals
- Build a modular platform to develop **multiple strategies** (stock + options, short-to-medium term holds: 1 day to ~1 week).
- Target “risk level 6–7” (moderate), emphasizing **risk-adjusted returns** and controlled drawdowns.
- Rapid experimentation: spin up new models/strategies quickly, backtest and compare objectively.
- Deploy a **React + Next.js dashboard** on **Vercel** for monitoring, analytics, controls, and reports.
- Support **paper trading first**, then live trading with strict safeguards.

### 1.2 Non-goals (for v1)
- HFT / microsecond latency trading.
- Crypto trading.
- Fully autonomous “set-and-forget” without monitoring and risk controls.
- Unbounded leverage or uncontrolled options selling strategies.

---

## 2) System at a Glance (Floor-Plan)
### 2.1 Core Components
1. **Market Data Layer**
   - Historical + live feeds, normalized into a common schema.
   - Adapters for multiple providers (pluggable).
2. **Feature & Label Pipeline**
   - Technical indicators, volatility features, regime signals, event calendars, etc.
   - Label generation for supervised learning and reward shaping for RL.
3. **Strategy & Model Layer**
   - Multiple strategy “plugins” (momentum, mean reversion, volatility, options spreads).
   - Multiple model families (tree ensembles, linear baselines, LSTM/Transformers, RL).
4. **Backtesting & Simulation Engine**
   - Realistic fills, fees, slippage.
   - Walk-forward evaluation, out-of-sample test sets.
5. **Execution Engine (Paper + Live)**
   - Broker adapters (Alpaca/IB/etc).
   - Order management system (OMS), position tracking.
6. **Risk Management**
   - Position sizing, stop-loss/take-profit, exposure limits, drawdown kill switch.
   - Circuit-breakers and anomaly detection.
7. **Monitoring, Metrics & Alerts**
   - Metrics pipeline (PnL, Sharpe/Sortino, max drawdown, win-rate, turnover).
   - Logs, traces, alerts (Slack/Email).
8. **Dashboard UI (Next.js on Vercel)**
   - Strategy performance, open positions, risk controls, run history.
   - Admin controls: enable/disable strategies, adjust risk caps, view logs.

### 2.2 Deployment Topology (Recommended)
- **Trading Services** (data, backtesting jobs, execution, risk, monitoring): run on a server/VM/container platform (not Vercel).
- **Dashboard UI**: Next.js on **Vercel**.
- **APIs**: a backend service (FastAPI) serving data to the dashboard.
- **Storage**: Postgres for structured data; object storage for artifacts (models, reports).
- **Queue/Scheduler**: simple cron for v1; upgrade to Celery/Redis or Airflow if needed.

---

## 3) Repo Structure (Monorepo Recommended)
```
quant-ml-trading/
  README.md
  docs/
    floorplan.md                # (this doc)
    architecture.md
    data_contracts.md
    risk_policy.md
    runbooks.md
    research_summary.md         # attach deep research as reference
  apps/
    dashboard/                  # Next.js UI (Vercel)
  services/
    api/                        # FastAPI (dashboard backend)
    data/                       # ingestion + normalization
    features/                   # feature pipelines
    research/                   # notebooks/scripts for experiments
    backtest/                   # backtesting service + configs
    execution/                  # paper/live trade executor + broker adapters
    risk/                       # risk rules + kill switches
    monitoring/                 # metrics, alerts, logging integrations
  packages/
    common/                     # shared types, schemas, utilities
    strategies/                 # strategy plugins (python package)
    models/                     # model training/inference utilities
  infra/
    docker/                     # Dockerfiles, compose
    terraform/                  # optional: IaC for cloud
  configs/
    environments/              # dev/stage/prod
    strategies/                # YAML configs per strategy
    secrets.example.env
  tests/
    unit/
    integration/
```

---

## 4) Technology Stack (Suggested Defaults)
### 4.1 Python Services
- **Python 3.11+**
- API: **FastAPI**
- Data: **pandas**, **numpy**
- TA: **ta-lib** or **pandas-ta**
- ML: **scikit-learn**, **xgboost/lightgbm**, **pytorch** (optional)
- RL (optional later): **FinRL** / **stable-baselines3**
- Backtesting: **backtrader** or **vectorbt**
- Storage: **Postgres** (+ SQLAlchemy), optional Redis
- Observability: **structlog/loguru**, OpenTelemetry optional

### 4.2 Frontend (Dashboard)
- **Next.js (App Router) + React**
- Auth: NextAuth or custom JWT
- Charts: lightweight chart library (e.g., TradingView Lightweight Charts / Recharts)
- Deploy: **Vercel**

### 4.3 Infrastructure
- Containers: **Docker** + docker-compose for dev
- CI: GitHub Actions (lint/test/build)
- Secrets: `.env` locally; prod via provider secrets manager

---

## 5) Data Contracts (SSOT Schemas)
Define **canonical schemas** early to keep modules pluggable.

### 5.1 Price Bar Schema (OHLCV)
- `symbol`, `timestamp`, `open`, `high`, `low`, `close`, `volume`, `vwap?`, `source`, `timezone`

### 5.2 Options Quote Schema (v2+)
- `underlying`, `expiration`, `strike`, `right(call/put)`, `bid`, `ask`, `mid`, `iv`, `delta/gamma/theta/vega` (if available)

### 5.3 Trade & Position Schema
- Orders: `order_id`, `strategy_id`, `symbol/contract`, `side`, `qty`, `type`, `limit_price`, `status`, `timestamps`
- Fills: `fill_price`, `fill_qty`, `fees`, `slippage_estimate`
- Positions: `avg_price`, `qty`, `unrealized_pnl`, `realized_pnl`, `exposure`

---

## 6) Strategy Plugin Interface (Critical Design)
Create a stable interface so new strategies are easy to add.

### 6.1 Strategy Lifecycle Methods
- `initialize(config)`
- `on_market_data(bar/quote)`
- `generate_signals(state) -> signals`
- `risk_check(signals, portfolio_state) -> approved_orders`
- `on_fill(fill_event)`
- `daily_close()` / `weekly_rebalance()`

### 6.2 Model Interface
- `fit(train_dataset, params) -> model_artifact`
- `predict(features) -> prediction (probabilities + confidence)`
- `explain(features) -> feature_importances/SHAP (optional)`

### 6.3 Config-Driven Strategies
Each strategy has a YAML config:
- universe selection
- model type + params
- feature set
- signal thresholds
- risk caps
- execution rules

---

## 7) Backtesting Standards (No Shallow Backtests)
### 7.1 Must-Haves
- **Walk-forward / rolling evaluation**
- **Out-of-sample holdout**
- Realistic costs: commissions + **slippage**
- Avoid lookahead bias (signals generated from info available *at the time*)
- Benchmarks: compare vs SPY (or relevant ETF) where appropriate

### 7.2 Metrics to Compute (per strategy + aggregate)
- Total return, CAGR-ish (even for short periods)
- **Sharpe / Sortino**
- Max drawdown
- Win-rate, profit factor
- Turnover, average holding period
- Exposure stats (gross/net)
- Tail risk proxies (VaR/CVaR optional)

### 7.3 Report Outputs
- HTML/PDF report per run
- JSON summary for dashboard ingestion
- “Run card” with git commit hash, config hash, dataset version

---

## 8) Risk Policy (Risk Level 6–7 Guardrails)
Create a written **risk_policy.md** and enforce it in code.

### 8.1 Default Limits (v1 suggestions)
- Max risk per trade: 0.5%–2% of equity (configurable)
- Max capital deployed: 50%–80% (configurable)
- Max concurrent positions: 5–15 (configurable)
- Hard stop daily loss: 1%–3% triggers pause + alert
- Max drawdown kill switch: 5%–12% triggers trading halt + alert

### 8.2 Options-Specific Guardrails
- Prefer **defined-risk spreads** (e.g., debit spreads) over naked short options.
- Avoid low-liquidity contracts (min OI/volume thresholds).
- Cap position delta exposure, cap gamma risk near expiration.

---

## 9) Execution Engine Design (Paper → Live)
### 9.1 Modes
- **Backtest mode**: uses historical fills simulator.
- **Paper mode**: sends orders to paper brokerage; verifies OMS.
- **Live mode**: production trading with strict risk gates.

### 9.2 Broker Adapter Pattern
- `BrokerClient.place_order()`
- `BrokerClient.get_positions()`
- `BrokerClient.get_account()`
- `BrokerClient.stream_quotes()` / polling

### 9.3 Safety Mechanisms
- Pre-trade risk checks (position sizing, exposure, liquidity checks)
- Post-trade reconciliation (ensure fills match expected)
- Idempotent order submission (no duplicate orders)
- “Safe mode” if data feed outages occur

---

## 10) Monitoring + Dashboard Requirements
### 10.1 Monitoring Outputs
- Real-time PnL + risk exposures
- Alerts: kill switch triggered, feed down, unusual slippage, strategy divergence
- Daily summary: performance snapshot, open positions, upcoming expirations

### 10.2 Dashboard Pages (Next.js)
1. **Overview**
   - Equity curve, today’s PnL, exposure, risk status
2. **Strategies**
   - List strategies + status; per-strategy metrics & logs
3. **Positions**
   - Current holdings, entry/exit, stop levels, Greeks (options)
4. **Runs / Backtests**
   - History, compare runs, download reports
5. **Controls**
   - Enable/disable strategy, adjust thresholds, toggle paper/live
6. **System Health**
   - Data feed status, broker connectivity, queue/scheduler status

### 10.3 API Endpoints (FastAPI)
- `/metrics/summary`
- `/strategies`
- `/strategies/{id}/performance`
- `/positions`
- `/runs`
- `/alerts`
- `/controls` (protected)

---

## 11) Antigravity Agent Plan (What to Generate)
Use Agents + Skills/Superpowers to create the planning artifacts below.

### 11.1 Planning Artifacts to Produce
- `docs/architecture.md` (diagrams + interfaces)
- `docs/data_contracts.md` (schemas, versioning)
- `docs/risk_policy.md` (limits, kill switches, auditing)
- `docs/runbooks.md` (how to run locally, recover from failure, rotate keys)
- `docs/implementation_tasks.md` (issue list + milestones)
- `configs/strategies/*.yaml` (starter strategies)
- `infra/docker/docker-compose.yml` (local dev)
- `services/api/` skeleton + OpenAPI spec
- `apps/dashboard/` skeleton + routes + component plan

### 11.2 Suggested Agent Roles
- **Architect Agent**: system boundaries, contracts, interfaces
- **Quant Research Agent**: propose 3–5 starter strategies + feature sets
- **ML Agent**: model families + training/eval protocol
- **Risk Agent**: policy + safeguards + edge cases
- **Infra/DevOps Agent**: docker, envs, CI, deployment topology
- **Frontend Agent**: Next.js dashboard IA, UI components, data flows

---

## 12) Two-Week Build Plan (Milestones)
### Days 1–2: Foundations
- Define data contracts, strategy interface, risk policy
- Skeleton repo + docker-compose
- Implement data ingestion for 1 provider (historical + live)

### Days 3–5: First Strategy End-to-End (Stocks)
- Build baseline features
- Train baseline model (e.g., XGBoost classification on 1–5 day horizon)
- Backtest with realistic costs
- Produce report + store run artifacts

### Days 6–8: Second Strategy (Mean Reversion or Volatility)
- Add strategy plugin
- Compare vs baseline in dashboard

### Days 9–11: Options Strategy (Defined-Risk)
- Implement options data ingestion (or simulate options from underlying)
- Add debit spread strategy (bull call / bear put) with liquidity filters
- Backtest and evaluate risk exposure

### Days 12–14: Execution + Dashboard + Hardening
- Paper trading integration (broker adapter)
- Alerts + kill switch enforcement
- Deploy dashboard to Vercel
- Final “go-live checklist” for limited capital

---

## 13) Security & Compliance Checklist
- Never commit API keys. Use `.env` + secrets manager.
- Separate paper vs live keys; separate accounts if possible.
- Least-privilege API permissions.
- Audit logs for trade decisions + orders.
- Clear disclaimer in README about financial risk.

---

## 14) Deliverables Checklist (Definition of Done for v1)
- [ ] Data ingestion working for at least 1 provider
- [ ] Strategy plugin framework with 2+ strategies
- [ ] Backtesting with walk-forward evaluation + costs
- [ ] Paper trading end-to-end with OMS + risk gate
- [ ] Dashboard deployed on Vercel showing metrics, runs, positions
- [ ] Kill switch + alerts functioning
- [ ] Runbooks + risk policy documented

---

## 15) Attach Research Reference
When ready, add the research PDF/MD into:
- `docs/research_summary.md` (or `docs/research/` folder)
and link it from `README.md`.

---

## 16) Prompt Templates for Antigravity Agents
### Architect Agent Prompt
- “Create system architecture diagrams and define module boundaries, interfaces, and data contracts. Output `docs/architecture.md` and `docs/data_contracts.md`.”

### Quant Research Agent Prompt
- “Propose 3–5 strategies aligned with risk 6–7, short horizon (1–7 days). Provide configs, features, and rationale. Output `configs/strategies/*.yaml` and `docs/research_summary.md`.”

### Risk Agent Prompt
- “Write enforceable risk policy and edge cases. Include kill switch design, loss limits, exposure caps, options-specific rules. Output `docs/risk_policy.md` and risk-check pseudocode.”

### Frontend Agent Prompt
- “Design Next.js dashboard IA, routes, components, and API contracts. Output `apps/dashboard/README.md` + initial routes scaffolding plan.”

---

## 17) Implementation Handoff to Cursor (Rules of Engagement)
- Cursor Agents must implement **one vertical slice at a time**:
  1) ingest data → store → show in dashboard
  2) strategy → backtest → report → show in dashboard
  3) paper execution → risk gates → show status/alerts
- Every slice must include unit tests + logging.
- Keep strategies config-driven; no hardcoded symbols/thresholds.

---

### Final Note
Start with **simple, robust baselines**, then add complexity only when validated by walk-forward testing and realistic costs. The edge comes from:
- data hygiene + realistic simulation,
- strict risk gating,
- systematic experiment tracking,
- fast iteration on multiple strategies.
