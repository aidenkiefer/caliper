# Plans: Specs, tickets, and legacy planning

This folder is the **single home** for planning docs (the old repository root `plans/` directory was removed; everything lives here now).

- **Sprints 7–10:** `specs/` and `tickets/` — bounded agent workflow per `docs/workflow/workflow.md`.
- **Sprints 1–6 and planning-phase artifacts:** see **Legacy planning** below.

**Milestone versions, patch notes, and backlog:** **[PROGRESS.md](PROGRESS.md)**. **Repo root overview:** [README.md](../../README.md).

## Legacy planning (Sprints 1–6 + research)

| File | Purpose |
|------|---------|
| [task_plan.md](task_plan.md) | Original multi-sprint task plan and agent handoff (planning phase + Cursor sprints). |
| [DETAILED-SPRINT-PROGRESS.md](DETAILED-SPRINT-PROGRESS.md) | Long-form per-sprint checklists (formerly `plans/progress.md`). |
| [findings.md](findings.md) | Planning research insights and design decisions. |
| [milestones.md](milestones.md) | Early milestone schedule (planning + implementation phases). |
| [more-features.md](more-features.md) | Advanced ML safety / drift / gating feature notes (aligned with Sprint 6 themes). |
| [even-more-features.md](even-more-features.md) | Model observatory / control-plane notes (aligned with Sprints 8–9 themes). |
| [SPRINT_SKILL_OPTIMIZATIONS.md](SPRINT_SKILL_OPTIMIZATIONS.md) | Sprint 1–2 DB/code optimizations from skills review. |
| [summaries/SPRINT1_SUMMARY.md](summaries/SPRINT1_SUMMARY.md) … [summaries/SPRINT6_SUMMARY.md](summaries/SPRINT6_SUMMARY.md) | Per-sprint completion summaries. |

## Workflow (Sprints 7–10)

- **Specs** (`specs/`) = rules, constraints, design intent. Agents read them as context but **do not execute** from the spec alone.
- **Tickets** (`tickets/`) = small, bounded tasks. Agents **act only on the ticket** they are given. Each ticket references one or more specs and lists Allowed Files and tool budgets.
- **CLAUDE rules:** No review/verification/QA by Claude; no build/compile/test commands unless the user asks. Verification is the user’s job (see root `CLAUDE.md`).
- **Planning:** If a ticket requires design choices, write documentation in `docs/` and **pause for human input** before implementing.

## Specs

| Spec | Purpose |
|------|---------|
| [specs/sprint-7-first-ml-model-spec.md](specs/sprint-7-first-ml-model-spec.md) | First ML model end-to-end: problem definition, training, contract, inference, text explainability. |
| [specs/sprint-8-observability-safety-spec.md](specs/sprint-8-observability-safety-spec.md) | ML observability & safety: performance tracking, baselines/regret, drift, SHAP, stress simulation. |
| [specs/sprint-9-model-observatory-dashboard-spec.md](specs/sprint-9-model-observatory-dashboard-spec.md) | Model Observatory Dashboard: registry, detail, ML viz, comparison, tuning, lifecycle, drift UI, HITL review, sandbox. |
| [specs/polymarket-btc-trading-spec.md](specs/polymarket-btc-trading-spec.md) | **Sprint 10:** Polymarket hourly BTC market-making — parallel `services/polymarket/`, `pm.*` schema, V1 MM + Phase 2/3 roadmap. |

Sprints 7–9 specs reference skills from [task_plan.md](task_plan.md) where applicable. Sprint 10 was executed as 20 tickets (`10-01`–`10-20`); see [summaries/SPRINT-10-POLYMARKET-COMPLETE.md](summaries/SPRINT-10-POLYMARKET-COMPLETE.md) for the completion narrative.

## Tickets

**Sprint 7 (First ML Model)**

| Ticket | Description |
|--------|-------------|
| [07-01-ml-problem-definition-doc.md](tickets/07-01-ml-problem-definition-doc.md) | Document ML problem (target, horizon, labels, metrics, assumptions, failure modes) in `docs/`. |
| [07-02-training-pipeline-script.md](tickets/07-02-training-pipeline-script.md) | Offline training script with time-aware split and leakage prevention. |
| [07-03-model-interface-contract.md](tickets/07-03-model-interface-contract.md) | Standardized model input/output schema; execution layer consumable. |
| [07-04-inference-integration.md](tickets/07-04-inference-integration.md) | Wire model inference into live/paper pipeline; risk & execution; log predictions. |
| [07-05-text-explainability.md](tickets/07-05-text-explainability.md) | Simple explanation payload (features, confidence, rationale) stored with predictions. |

**Sprint 8 (Observability & Safety)**

| Ticket | Description |
|--------|-------------|
| [08-01-performance-tracking.md](tickets/08-01-performance-tracking.md) | Log prediction vs outcome; rolling accuracy/abstention; expose via API. |
| [08-02-baseline-regret-wiring.md](tickets/08-02-baseline-regret-wiring.md) | Wire baselines to model comparison; regret metrics exposed. |
| [08-03-drift-monitoring.md](tickets/08-03-drift-monitoring.md) | Feed current data into drift detector; reference storage; health score; API. |
| [08-04-shap-explainability.md](tickets/08-04-shap-explainability.md) | SHAP/permutation for deployed model; store per prediction; expose via API. |
| [08-05-failure-mode-stress-simulation.md](tickets/08-05-failure-mode-stress-simulation.md) | Stress scenarios (missing data, volatility, API outage); runbook or ADR. |

**Sprint 9 (Model Observatory Dashboard)**

| Ticket | Description |
|--------|-------------|
| [09-01-model-registry-ui.md](tickets/09-01-model-registry-ui.md) | Model Registry page: list view, sorting/filtering, quick actions (activate, pause, view details). |
| [09-02-model-detail-page.md](tickets/09-02-model-detail-page.md) | Model Detail page: overview, training/validation summary, live performance, calibration plots. |
| [09-03-ml-performance-visualization.md](tickets/09-03-ml-performance-visualization.md) | ML performance charts: prediction vs actual, rolling accuracy, confusion matrix, calibration curves. |
| [09-04-model-comparison-ranking.md](tickets/09-04-model-comparison-ranking.md) | Model comparison & ranking view: side-by-side, sorting/filtering, drift/confidence comparison. |
| [09-05-hyperparameter-threshold-tuning.md](tickets/09-05-hyperparameter-threshold-tuning.md) | Hyperparameter & threshold tuning UI: confirmation modal, impact preview, logging and rollback. |
| [09-06-model-lifecycle-controls.md](tickets/09-06-model-lifecycle-controls.md) | Model lifecycle controls: activate/deactivate, promote, retire, freeze, clone config. |
| [09-07-drift-health-visualization-ui.md](tickets/09-07-drift-health-visualization-ui.md) | Drift & health visualization UI: drift trend charts, feature heatmaps, health timeline, alerts. |
| [09-08-hitl-review-mode-model-centric.md](tickets/09-08-hitl-review-mode-model-centric.md) | HITL review mode (model-centric): recommendation queue, explanation display, approve/reject. |
| [09-09-model-sandbox-what-if.md](tickets/09-09-model-sandbox-what-if.md) | Model sandbox / what-if: parameter sandbox, rerun backtests, hypothetical allocations, preview. |

**Sprint 10 (Polymarket BTC market-making)** — ✅ complete (2026-03-25)

| Index | Description |
|-------|-------------|
| [tickets/10-00-INDEX.md](tickets/10-00-INDEX.md) | Dependency graph, ticket list, recommended build order |
| [tickets/10-01-polymarket-scaffolding.md](tickets/10-01-polymarket-scaffolding.md) … `10-20-documentation.md` | Twenty bounded tickets (scaffolding → adapters → core → API → tests → docs) |

**Operations (human):** [docs/POLYMARKET-QUICKSTART.md](../POLYMARKET-QUICKSTART.md) · [docs/runbooks/polymarket-operations.md](../runbooks/polymarket-operations.md)

## How to run

Give the agent **one ticket at a time** (e.g. “Follow the ticket in `docs/plans/tickets/07-01-ml-problem-definition-doc.md`”). The agent should read the referenced spec(s) and reference docs, then execute only within the ticket’s Allowed Files and budgets.
