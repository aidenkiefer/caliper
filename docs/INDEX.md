# Docs Index — Caliper (quant)

This is the primary doc map for agent and human navigation in the `quant/` repo.

**Platform overview & onboarding:** root **[README.md](../README.md)** (equities + optional Polymarket, sprint status). **Milestone log:** **[docs/plans/PROGRESS.md](plans/PROGRESS.md)**.

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
| Polymarket quick start | `docs/POLYMARKET-QUICKSTART.md` | Running the Polymarket bot (env, migration, dry-run) |

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
| Plans folder hub | `docs/plans/README.md` | Specs/tickets (7–10), legacy Sprints 1–6 artifacts, file index |
| Workflow progress log | `docs/plans/PROGRESS.md` | Versioned milestones, patches, backlog |
| Planning findings | `docs/plans/findings.md` | Original research / design decisions |
| Early milestones doc | `docs/plans/milestones.md` | Planning-phase milestone checklist |
| ML / observatory concept notes | `docs/plans/more-features.md`, `docs/plans/even-more-features.md` | Pre-spec feature narratives (Sprint 6 & 8–9 themes) |
| Sprint 1–2 skill optimizations | `docs/plans/SPRINT_SKILL_OPTIMIZATIONS.md` | DB/code tweaks from skills review |
| Sprint 7 spec | `docs/plans/specs/sprint-7-first-ml-model-spec.md` | First ML model end-to-end work |
| Sprint 8 spec | `docs/plans/specs/sprint-8-observability-safety-spec.md` | Observability, drift, explainability, baselines |
| Sprint 9 spec | `docs/plans/specs/sprint-9-model-observatory-dashboard-spec.md` | Model dashboard and model-centric UX |
| Sprint 10 spec | `docs/plans/specs/polymarket-btc-trading-spec.md` | Polymarket hourly BTC market-making (architecture, data model, roadmap) |
| Sprint tickets | `docs/plans/tickets/` | One-ticket-at-a-time bounded implementation work |

## Summaries and milestone docs

| Doc | Path | Use when |
|---|---|---|
| Sprints 7-9 summary | `docs/SPRINTS-7-8-9-SUMMARY.md` | Fast summary of recent ML/model-dashboard work |
| Sprint 8 complete | `docs/SPRINT-8-COMPLETE.md` | Reviewing Sprint 8 completion notes |
| Sprint 9 complete | `docs/SPRINT-9-COMPLETE.md` | Reviewing Sprint 9 completion notes |
| Sprint 9 implementation guide | `docs/SPRINT-9-IMPLEMENTATION-GUIDE.md` | Reviewing Sprint 9 implementation framing |
| Sprint 10 complete | `docs/plans/summaries/SPRINT-10-POLYMARKET-COMPLETE.md` | What was built for Polymarket, why, Phase 2/3 roadmap |
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
| Backtest service | `services/backtest/` | Engine, reporting, walk-forward |
| Data service | `services/data/` | Market data ingestion, storage, migrations |
| Execution service | `services/execution/` | OMS, broker adapters, reconciliation |
| Features service | `services/features/` | Indicators and feature pipeline |
| ML service | `services/ml/` | Training, inference, confidence, drift, explainability, HITL, baselines |
| Risk service | `services/risk/` | Risk manager, kill switch, circuit breaker |
| Polymarket service | `services/polymarket/` | Optional CLOB market-making bot; CLI + `pm.*` DB schema; parallel to equity stack |
| Shared schemas | `packages/common/` | Pydantic schemas and shared contracts (includes `polymarket_schemas.py`, `ml_schemas.py`) |
| Strategies | `packages/strategies/` | Strategy ABC and implementations (rule-based + ML direction strategy) |
| Models package | `packages/models/` | Reserved stub for shared model utilities (minimal today) |

## Navigation rule

Start with `docs/INDEX.md`, then load only the specific docs needed for the current task.
