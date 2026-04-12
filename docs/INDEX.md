# Docs Index — Caliper (quant)

This is the primary doc map for agent and human navigation in the `quant/` repo.

**Platform overview & onboarding:** root **[README.md](../README.md)** (equities + optional Polymarket, sprint status). **Human setup & daily use:** **[docs/user-guide.md](user-guide.md)**. **Milestone log:** **[docs/plans/PROGRESS.md](plans/PROGRESS.md)**.

## Core system docs

| Doc | Path | Use when |
|---|---|---|
| Architecture | `docs/architecture.md` | Understanding services, boundaries, and data flow |
| API contracts | `docs/api-contracts.md` | Working on FastAPI endpoints, request/response shapes, auth, pagination |
| Data contracts | `docs/data-contracts.md` | Working on shared schemas, market data, positions, orders, model payloads |
| Risk policy | `docs/risk-policy.md` | Touching order validation, kill switch, circuit breaker, limits |
| Security | `docs/security.md` | Touching secrets, auth, credentials, security controls |
| Dashboard spec | `docs/dashboard-spec.md` | Adding or changing dashboard pages, charts, controls, UX flows |
| Design guidelines | `docs/design-guidelines.md` | Dashboard visual system, density, color, layout, contrast |
| Features overview | `docs/FEATURES.md` | Checking what is implemented vs planned across sprints |
| User guide | `docs/user-guide.md` | Install, env (incl. `DB_URL`), run API + dashboard, equities vs Polymarket, troubleshooting |
| Polymarket quick start | `docs/POLYMARKET-QUICKSTART.md` | Running the Polymarket bot (env, migration, dry-run) |
| Recommendations (HITL) design | `docs/system-design/recommendations.md` | Understanding Recommendations intent, current state, and the split between action vs strategy-tuning recs |

## Workflow docs

| Doc | Path | Use when |
|---|---|---|
| Workflow entrypoint | `docs/workflow/workflow.md` | Starting agentic work in this repo |
| Execution rules | `docs/workflow/execution-rules.md` | Runtime rules, budgets, constraints |
| Ticket template | `docs/workflow/ticket-template.md` | Writing one bounded task |
| Skill map | `docs/workflow/skill-map.md` | Choosing workflow/process skills |
| Task-type map | `docs/workflow/task-type-reference-map.md` | Choosing reference bundles, agent types, domain skills |
| Context flow | `docs/workflow/context-flow.md` | Understanding how context should load through sessions |
| Context audit | `docs/workflow/context-audit.md` | Auditing doc accuracy and drift |

## Plans and progress

| Doc | Path | Use when |
|---|---|---|
| Detailed sprint checklists | `docs/plans/DETAILED-SPRINT-PROGRESS.md` | Per-sprint checkbox history (legacy `plans/progress.md`) |
| Original task plan (Sprints 1–6) | `docs/plans/task_plan.md` | Planning-phase decomposition and handoff |
| Plans folder hub | `docs/plans/README.md` | Specs/tickets (7–14), legacy Sprints 1–6 artifacts, file index |
| Workflow progress log | `docs/plans/PROGRESS.md` | Versioned milestones, patches, backlog |
| Planning findings | `docs/plans/findings.md` | Original research / design decisions |
| Early milestones doc | `docs/plans/milestones.md` | Planning-phase milestone checklist |
| ML / observatory concept notes | `docs/plans/more-features.md`, `docs/plans/even-more-features.md` | Pre-spec feature narratives (Sprint 6 & 8–9 themes) |
| Sprint 1–2 skill optimizations | `docs/plans/SPRINT_SKILL_OPTIMIZATIONS.md` | DB/code tweaks from skills review |
| Sprint 7 spec | `docs/plans/specs/sprint-7-first-ml-model-spec.md` | First ML model end-to-end work |
| Sprint 8 spec | `docs/plans/specs/sprint-8-observability-safety-spec.md` | Observability, drift, explainability, baselines |
| Sprint 9 spec | `docs/plans/specs/sprint-9-model-observatory-dashboard-spec.md` | Model dashboard and model-centric UX |
| Sprint 10 spec | `docs/plans/specs/polymarket-btc-trading-spec.md` | Polymarket hourly BTC market-making (architecture, data model, roadmap) |
| Sprint 12 spec | `docs/plans/specs/sprint-12-feature-layer-spec.md` | Unified Polymarket feature layer (`FeatureSnapshot`, sources, store, API) |
| Sprint 13 spec | `docs/plans/specs/sprint-13-simulation-evaluation-spec.md` | CLOB simulation + evaluation engine (replay, metrics, baselines) |
| Sprint 14 spec | `docs/plans/specs/sprint-14-probability-model-spec.md` | BTC hourly probability model, calibration, lead-lag tests, fee-aware backtest |
| Sprint 15 spec | `docs/plans/specs/sprint-15-regime-allocation-spec.md` | Regime detection, performance matrix, dynamic allocation (HRP); **`/v1/regime/*`**, **`/v1/allocation/*`** |
| Sprint 16 spec | `docs/plans/specs/sprint-16-cross-sectional-fleet-spec.md` | Cross-sectional ranker, paper fleet, strategies, **`pm.paper_trades`**; **`/v1/ranking/*`**, **`/v1/fleet/*`** (mock HTTP until wired) |
| Sprint 17 spec | `docs/plans/specs/sprint-17-reward-density-wallet-spec.md` | Reward density (on-chain HHI, incentives, risk scorer), wallet intelligence (profiling, clustering, signals), signal aggregation (z-score + weight learning), lifecycle manager; migration `014`; **`/v1/reward-density/*`**, **`/v1/wallet-intelligence/*`**, **`/v1/signal-aggregation/*`**, **`/v1/lifecycle/*`** |
| Sprint tickets | `docs/plans/tickets/` | Bounded tasks (`10-*`, `12-*`, `13-*`, `14-00-INDEX`, `15-*`, `16-*`, …) |

## Summaries and milestone docs

| Doc | Path | Use when |
|---|---|---|
| Sprints 7-9 summary | `docs/SPRINTS-7-8-9-SUMMARY.md` | Fast summary of recent ML/model-dashboard work |
| Sprint 8 complete | `docs/SPRINT-8-COMPLETE.md` | Reviewing Sprint 8 completion notes |
| Sprint 9 complete | `docs/SPRINT-9-COMPLETE.md` | Reviewing Sprint 9 completion notes |
| Sprint 9 implementation guide | `docs/SPRINT-9-IMPLEMENTATION-GUIDE.md` | Reviewing Sprint 9 implementation framing |
| Sprint 10 complete | `docs/plans/summaries/SPRINT-10-POLYMARKET-COMPLETE.md` | What was built for Polymarket, why, Phase 2/3 roadmap |
| Sprint 13 complete | `docs/plans/summaries/SPRINT-13-SIMULATION-EVALUATION.md` | Simulation + evaluation modules, API stubs, DB migration, boundaries vs `backtest/` |
| Sprint 14 complete | `docs/plans/summaries/SPRINT-14-PROBABILITY-MODEL.md` | Probability model package, migration `005`, `/v1/probability/*`, AC-9 tests deferred |
| Sprint 15 complete | `docs/plans/summaries/SPRINT-15-REGIME-ALLOCATION.md` | Regime + allocation services, migration `006`, live `/v1/regime/*` + `/v1/allocation/*` when `DB_URL` set |
| Sprint 16 complete | `docs/plans/summaries/SPRINT-16-CROSS-SECTIONAL-FLEET.md` | Ranking + fleet, migration `007`, mock `/v1/ranking/*` + `/v1/fleet/*` until wired; dashboard `sprint-16` |
| Sprint 17 complete | `docs/plans/summaries/SPRINT-17-REWARD-DENSITY-WALLET-INTELLIGENCE.md` | Reward density, wallet intelligence, signal aggregation, lifecycle manager; migration `014`; 4 DB-backed API routers; `AggregatedSignal` in fleet strategies; 36 tests |
| Dashboard UI overhaul | `docs/plans/summaries/DASHBOARD-UI-OVERHAUL-2026-04.md` | Phase 1 (`v2.6.0-p2`): `/start`, `/platform`, `/platform/features`, HelpHint, badges. Phase 2 (`v2.6.0-p3`): `/platform/polymarket`, regime-allocation, probability, simulation, ranking-fleet, equities hub. Design: `docs/superpowers/specs/2026-04-06-dashboard-ui-overhaul-design.md` |
| Polymarket tickets 1–5 notes | `docs/plans/POLYMARKET-TICKETS-1-5-SUMMARY.md` | Early Sprint 10 implementation notes (superseded by full summary for overview) |

## Runbooks

| Doc | Path | Use when |
|---|---|---|
| API verification runbook | `docs/runbooks/api-verification.md` | Understanding expected API behavior and checks |
| Backtest verification runbook | `docs/runbooks/backtest-verification.md` | Understanding expected backtest/report behavior |
| Execution verification runbook | `docs/runbooks/execution-verification.md` | Understanding execution/risk behavior |
| ML safety verification runbook | `docs/runbooks/ml-safety-verification.md` | Understanding drift, abstention, explainability, HITL behavior |
| Stress scenarios | `docs/runbooks/stress-scenarios.md` | Failure-mode and resilience scenarios |
| Vercel deployment | `docs/runbooks/vercel-deployment.md` | Dashboard deployment and env configuration |
| Polymarket operations | `docs/runbooks/polymarket-operations.md` | Wallet, env vars, DB migration, sessions, analysis, emergencies |

## Implementation surfaces

| Area | Path | Notes |
|---|---|---|
| Dashboard app | `apps/dashboard/` | Next.js 14 App Router app |
| API service | `services/api/` | FastAPI backend for dashboard and control endpoints |
| Backtest service | `services/backtest/` | Equity backtest engine, reporting, walk-forward |
| Simulation service | `services/simulation/` | Polymarket CLOB replay: order book, fees, execution sim, adverse selection, runner |
| Evaluation service | `services/evaluation/` | Strategy metrics, regime matrix, baselines, evaluation reports |
| Data service | `services/data/` | Market data ingestion, storage, migrations |
| Execution service | `services/execution/` | OMS, broker adapters, reconciliation |
| Portfolio service | `services/portfolio/` | Allocator utilities (unified pipeline; Sprint 11) |
| Regime service | `services/regime/` | Regime state models and detection helpers (Sprint 15); API reads `pm.regime_states` |
| Allocation service | `services/allocation/` | Performance matrix + HRP-style allocation (Sprint 15); API reads `pm.allocation_decisions` |
| Ranking service | `services/ranking/` | Cross-sectional universe, edge, feasibility, scoring, selection (Sprint 16); HTTP layer still mock |
| Fleet service | `services/fleet/` | Paper-mode orchestrator, paper-trade store, `pm.paper_trades` (Sprint 16); HTTP layer still mock; Sprint 17 adds `lifecycle.py` (PAUSE/PROMOTE/DEMOTE/RETIRE rules) |
| Reward density service | `services/reward_density/` | On-chain maker HHI competition, incentive model (post-Mar-30 fee formula), cross-sectional risk scorer, density analyzer (Sprint 17); Polygon RPC client |
| Wallet intelligence service | `services/wallet_intelligence/` | Wallet profiling, KMeans clustering (k=4), smart-money signal extraction (Sprint 17) |
| Signal aggregation service | `services/signal_aggregation/` | Z-scored weighted composite of model + wallet + microstructure signals with weight learning (Sprint 17) |
| Features service | `services/features/` | Indicators, equity + Polymarket feature pipeline (`FeatureSnapshot`, store) |
| ML service | `services/ml/` | Training, inference, confidence, drift, explainability, HITL, baselines; **`probability_model/`** (Sprint 14 BTC forecaster) |
| Risk service | `services/risk/` | Risk manager, kill switch, circuit breaker |
| Polymarket service | `services/polymarket/` | Optional CLOB market-making bot; CLI + `pm.*` DB schema; parallel to equity stack |
| Shared schemas | `packages/common/` | Pydantic schemas and shared contracts (includes `polymarket_schemas.py`, `ml_schemas.py`) |
| Strategies | `packages/strategies/` | Strategy ABC, equity + Polymarket plugins (incl. Sprint 16 `poly_*_v1`, `poly_mm_v2`) |
| Models package | `packages/models/` | Reserved stub for shared model utilities (minimal today) |

## Navigation rule

Start with `docs/INDEX.md`, then load only the specific docs needed for the current task.
