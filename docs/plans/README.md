# Plans: Specs & Tickets

This folder holds **specs** (read-only context for Claude) and **tickets** (one-at-a-time executable tasks) for Sprints 7, 8, and 9, following `claude-workflow-opt.md`.

## Workflow

- **Specs** (`specs/`) = rules, constraints, design intent. Claude reads them as context but **does not execute** from the spec alone.
- **Tickets** (`tickets/`) = small, bounded tasks. Claude **acts only on the ticket** it is given. Each ticket references one or more specs and lists Allowed Files and Hard Limits.
- **CLAUDE rules:** No review/verification/QA by Claude; no build/compile/test commands. Verification is the user’s job (see root `CLAUDE.md`).
- **Planning:** If a ticket requires design choices, Claude writes documentation in `docs/` and **pauses for your input** before implementing.

## Specs (Sprint 7, 8 & 9)

| Spec | Purpose |
|------|---------|
| [specs/sprint-7-first-ml-model-spec.md](specs/sprint-7-first-ml-model-spec.md) | First ML model end-to-end: problem definition, training, contract, inference, text explainability. |
| [specs/sprint-8-observability-safety-spec.md](specs/sprint-8-observability-safety-spec.md) | ML observability & safety: performance tracking, baselines/regret, drift, SHAP, stress simulation. |
| [specs/sprint-9-model-observatory-dashboard-spec.md](specs/sprint-9-model-observatory-dashboard-spec.md) | Model Observatory Dashboard: registry, detail, ML viz, comparison, tuning, lifecycle, drift UI, HITL review, sandbox. |

All specs include the **Skills to Use for the upcoming Sprints** list (from `plans/task_plan.md`) and require skill usage on every ticket.

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

## How to run

Give Claude **one ticket at a time** (e.g. “Follow the ticket in `docs/plans/tickets/07-01-ml-problem-definition-doc.md`”). Claude should read the referenced spec(s) and reference docs, then execute only the ticket’s Instructions within the Allowed Files and Hard Limits.
