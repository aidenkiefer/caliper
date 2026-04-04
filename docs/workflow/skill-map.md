# Skill map — Layer 1: Workflow Process Skills

Skills are a **routing layer**, not "load the encyclopedia." The ticket names the exact skill(s) to invoke. Do not load any skills unless the ticket lists them.

**For domain skills and project-specific skills (Layers 2 & 3), see `task-type-reference-map.md`** — the "Skills" column for each task type lists the domain skills to invoke, and the `[PROJECT-SPECIFIC]` section lists project-specific skills and their associated docs.

---

## Layer 1: Core workflow process skills

"How we work" patterns. These are triggered by the **type of workflow event** you're in (planning, debugging, reviewing), not by the code domain.

| When | Skill | Description |
|------|-------|-------------|
| Starting a multi-step feature or sprint | `writing-plans` | Plan before code. Write a spec or implementation plan. |
| Clarifying requirements or design | `brainstorming` | Explore user intent, options, and design before implementation. |
| Executing a written implementation plan | `executing-plans` or `subagent-driven-development` | Follow the plan; checkpoint with review. |
| Implementing a feature or bugfix with tests | `test-driven-development` | Tests before implementation. |
| Any bug or test failure | `systematic-debugging` | Use before proposing any fix. |
| Before claiming work complete or merging | `verification-before-completion` | Verify against ticket criteria and user-requested checks only. |
| Completing a major feature or pre-merge | `requesting-code-review` | Request review; show evidence. |
| Responding to code review feedback | `receiving-code-review` | Verify feedback before implementing; don't blindly apply suggestions. |
| Creating or editing Cursor rules or AGENTS.md | `create-rule` | Follow the rule-writing workflow. |
| Creating or editing agent skills | `writing-skills` | Follow the skill-writing workflow. |

---

## Layer 2: Workflow management skills

These are process-level skills for managing work at the git/branch level. They don't fit into code task types, so they live here rather than in `task-type-reference-map.md`.

| When | Skill |
|------|-------|
| Starting feature work that needs isolation | `using-git-worktrees` |
| Implementation is complete and ready to integrate | `finishing-a-development-branch` |
| Running multiple independent tasks in parallel | `dispatching-parallel-agents` |

---

## Common domain skills for Caliper

These are not auto-loaded. Reference them from tickets or from `task-type-reference-map.md` when the task type calls for them.

| Task area | Recommended skills |
|------|-------|
| FastAPI / Python services / shared contracts | `backend-dev-guidelines` |
| Next.js dashboard implementation | `frontend-design`, `react-best-practices` |
| Dense dashboard UX, charts, operational clarity | `ui-ux-pro-max` |
| Mobile-first monitoring views | `mobile-design` |
| Browser-based dashboard testing | `webapp-testing` |
| Copy / help / glossary / user-facing messaging | `copywriting` |

---

## Domain skills for the Polymarket quant trading system

Skills covering the core technical layers of the bot: probability modeling, backtesting, real-time execution, risk, data pipelines, and on-chain interaction. Load only when the ticket's task type matches the skill area — do not auto-load all of these.

### Quantitative modeling and financial analysis

| Task area | Skill | When to load |
|------|-------|------|
| Financial model design, strategy analysis, portfolio optimization, PnL decomposition | `quant-analyst` | Any ticket involving microstructure models, fee curve analysis, maker-rebate incentive modeling, or Kelly sizing |
| Trading strategy backtests, LOB simulation, walk-forward analysis, avoiding look-ahead bias | `backtesting-frameworks` | All backtest engine work, CLOB simulation design, validation against real fill data |
| Risk-adjusted metrics: VaR, CVaR, Sharpe, Sortino, drawdown; position sizing | `risk-metrics-calculation` | Risk manager implementation, strategy evaluation, regime-conditioned performance matrices |
| Portfolio risk, inventory limits, kill-switch logic, stop-loss design | `risk-manager` | Inventory management in market-making, allocation caps, circuit breaker implementation |

### Statistical and ML modeling

| Task area | Skill | When to load |
|------|-------|------|
| Granger causality, time-series models (AR, HMM, Markov-switching), logistic regression, calibration diagnostics | `statsmodels` | Probability model training, lead-lag tests, regime detection, Brier score / reliability diagrams |
| scikit-learn classification, calibration (Platt/isotonic), walk-forward CV, feature pipelines | `scikit-learn` | Building and evaluating the BTC up/down probability model, calibration layer, feature importance |
| Full ML pipeline design: experiment tracking, model registry, monitoring, drift detection | `mlops-engineer` | Model deployment lifecycle, calibration drift alerts, regime-aware retraining schedules |
| Multi-agent MLOps orchestration, complete pipeline from data → features → training → serving | `machine-learning-ops-ml-pipeline` | End-to-end ML pipeline setup for probability models across fee regimes |

### Real-time systems and execution

| Task area | Skill | When to load |
|------|-------|------|
| asyncio, WebSocket clients, concurrent I/O, non-blocking heartbeat loops, async order management | `async-python-patterns` | CLOB WebSocket subscription, heartbeat loop, async order placement/cancellation, real-time feature updates |
| Modern Python 3.12+, uv, ruff, pydantic, production service patterns | `python-pro` | Any new Python service or package scaffolding, typing, configuration management |
| Profiling, latency reduction, CPU/memory optimization for hot paths | `python-performance-optimization` | Execution engine hot path (quote repricing loop, order matching sim), latency benchmarks |
| FastAPI, Pydantic V2, SQLAlchemy 2.0, async endpoints, WebSocket server patterns | `fastapi-pro` | Bot control API, monitoring endpoints, paper-vs-live status, manual override routes |

### Data infrastructure

| Task area | Skill | When to load |
|------|-------|------|
| Batch + streaming data pipeline architecture, Airflow DAGs, feature stores | `data-engineering-data-pipeline` | Designing the Binance candle ingestion pipeline, Polymarket trade tape replay, intraday feature store |
| Apache Spark, dbt, streaming architectures, data warehouse design | `data-engineer` | High-volume data ingestion (Polymarket CLOB snapshots, Polygon on-chain logs), time-series storage strategy |
| Great Expectations, data contracts, validation rules for pipeline integrity | `data-quality-frameworks` | Critical path data validation (Binance candle timestamps, market condition_id mapping, fee-regime flags) |

### Blockchain and on-chain access

| Task area | Skill | When to load |
|------|-------|------|
| Polygon (Chain ID 137), ERC-1155 tokens, EIP-712 signing, CTF Exchange OrderFilled events | `blockchain-developer` | On-chain maker concentration (HHI) computation from OrderFilled logs, token split/merge/redeem operations, wallet auth |

### Testing

| Task area | Skill | When to load |
|------|-------|------|
| pytest, fixtures, mocking external APIs, async test patterns, integration tests | `python-testing-patterns` | Backtesting validation suite, mocking Polymarket CLOB/WebSocket in unit tests, async execution engine tests |

---

## Usage rules

- **Ticket names the pack(s):** 0–2 core skills per ticket. 0–2 domain skills (from task-type-reference-map). Project-specific only if ticket says so.
- **Small task:** 0–1 skills. **Medium:** 1–3. **Large:** 3–5 max.
- **If no skill fits the situation:** Proceed without invoking any. This map is for optional leverage, not a checklist.
- **Domain and project-specific skills** are in `task-type-reference-map.md` — look there for "which skill to use for this type of code task."
