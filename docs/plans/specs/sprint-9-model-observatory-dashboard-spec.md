# Sprint 9 Spec: Model Observatory Dashboard

**Sprint goal:** Make models inspectable, configurable, and comparable as first-class entities in the dashboard. Models are first-class; ML-native visualizations (confusion matrix, calibration curves) and model lifecycle controls are available; users can compare and rank models, tune parameters safely with preview and rollback, and use the dashboard for learning and experimentation, not just monitoring.

**Source:** `plans/task_plan.md` (Sprint 9).  
**Workflow:** Follow `claude-workflow-opt.md`: specs are read-only context; execute only the ticket you are given.  
**CLAUDE rules:** No review/verification/QA by Claude; no build/compile/test commands. Verification is the user’s job.

---

## 1. Scope

**In scope:**

- **Model Registry UI:** Dedicated page; list view with sorting/filtering; name, type, status, trained date, health score, allocation weight; quick actions (activate, pause, view details).
- **Model Detail Page:** Overview (architecture, feature set, hyperparams); training & validation summary; live/paper performance (accuracy over time, abstention rate); confidence calibration plots.
- **ML Performance Visualization:** Prediction vs actual plots; rolling accuracy; confusion matrix; calibration curves; error distribution; toggle between ML metrics and trading metrics.
- **Model Comparison & Ranking View:** Side-by-side comparison; validation metrics, recent performance, drawdown, volatility; sorting/filtering; confidence stability and drift score comparison.
- **Hyperparameter & Threshold Tuning Interface:** Dashboard controls for confidence thresholds, abstention threshold, ensemble caps, allocation limits; change confirmation with impact preview; change logging and rollback support.
- **Model Lifecycle Controls:** Activate/deactivate, promote candidate → active, retire, freeze parameters, clone config for new experiment.
- **Model Drift & Health Visualization UI:** Per-model drift trend charts; feature drift heatmaps; health score timeline; alert badges; suggested actions (retrain, retire).
- **Human-in-the-Loop Review Mode (Model-Centric):** Model recommendation review queue; explanation per recommendation; approve/reject at model level; rationale input; decision outcome logging.
- **Model Sandbox / What-If Testing:** Parameter modification sandbox (no live impact); rerun backtests with modified thresholds; temporarily disable models in sandbox; compare hypothetical allocations; preview effects before applying.

**Out of scope:**

- Backend model registry API (assume endpoints exist or are added in Sprints 7–8; extend only if needed for UI).
- New ML model training or inference logic (Sprint 7–8).
- Full experiment registry or feature registry backend (minimal API extension only as needed for UI).

---

## 2. Skills to Use for Sprint 9 (Mandatory)

When working on any Sprint 9 ticket, Claude **must** use skills as follows:

1. **First:** Read and follow `agents/skills/skills/using-superpowers/SKILL.md` (or project equivalent) before doing anything else.
2. **Then:** Use as many of the following skills as apply to the ticket. Prefer 5–7 for small tickets and up to 12–15 for large ones.

**ML & experimentation**

1. **ml-pipeline-builder**
2. **feature-engineering**
3. **time-series-ml**
4. **ensemble-modeling**
5. **model-evaluation**
6. **experiment-tracking**

**Safety, correctness, robustness**

7. **data-leakage-detector**
8. **risk-control-logic**
9. **abstention-logic**
10. **anomaly-detection**

**Backend & infra**

11. **backend-service-architect**
12. **async-systems**
13. **database-schema-designer**
14. **caching-strategy**
15. **config-management**

**Observability & UX**

16. **model-observability**
17. **explainability-ui**
18. **dashboard-architect**

**Dev velocity & quality**

19. **refactor-engine**
20. **documentation-generator**

Each ticket will list which of these are **mandatory** for that task; use additional skills from this list as needed. If a skill file is missing under `agents/skills/skills/`, treat the skill name as a reminder of the domain and apply that thinking; do not block the ticket.

---

## 3. Planning and Pausing for Input

- **Planning:** If a ticket requires new design choices (e.g. page layout, chart library, or API contract for a new endpoint), Claude must **write planning documentation in the `docs/` folder** and **stop**.
- **Pause for input:** After writing that doc, Claude must **ask for your input** before implementing. Example: “I’ve added `docs/plans/sprint-9-model-registry-ui.md` with proposed layout and data shape. Please review and confirm before I implement.”
- **No guessing on product/design:** Do not implement ambiguous or high-impact UI/UX decisions without a doc and your confirmation.

---

## 4. Design Intent and Constraints

- **Dashboard-first:** All work lives in `apps/dashboard/` unless a small API extension is required (e.g. new endpoint for model list or lifecycle action). Prefer existing API contracts and response types from `packages/common/api_schemas.py` and `ml_schemas.py`.
- **Learning and experimentation:** The dashboard is for ML/SWE users with little trading experience; prioritize clarity, interpretability, and safe experimentation (sandbox, preview, rollback) over flashy UI.
- **Consistency:** Use existing design system (Shadcn/UI, Tailwind, dark mode) and data-fetching patterns (SWR, API client). See `docs/dashboard-spec.md` and `docs/design-guidelines.md`.
- **No live impact by default:** Parameter tuning and sandbox actions must not affect live trading unless the user explicitly confirms (e.g. confirmation modal, preview, then apply).
- **Model lifecycle:** Activate, pause, retire, and promote candidate → active must call the appropriate API (or stub) and reflect state in the UI; document expected API shape if not yet defined.

---

## 5. Success Criteria (Sprint 9)

- Models are first-class entities in the dashboard (registry list, detail page, lifecycle).
- ML-native visualizations (confusion matrix, calibration curves, prediction vs actual, drift) are available and render correctly.
- Users can compare and rank models side-by-side (comparison view, sorting/filtering).
- Parameter tuning is safe with preview and rollback (confirmation modal, logging, rollback support).
- Model lifecycle (activate, pause, retire) is manageable from the UI.
- Dashboard supports learning and experimentation, not just monitoring (sandbox, what-if, HITL review mode).

---

## 6. Reference Docs (Read-Only for Tickets)

- `docs/architecture.md` — services, API, data flow.
- `docs/api-contracts.md` — REST endpoints for models, metrics, drift, baselines, explanations, controls.
- `docs/dashboard-spec.md` — dashboard pages, components, data dependencies.
- `docs/design-guidelines.md` — UI/UX and design system.
- `plans/task_plan.md` — Sprint 9 actionable implementation list.
- `packages/common/api_schemas.py`, `packages/common/ml_schemas.py` — response types.
- `apps/dashboard/` — existing pages, components, hooks, layout.

---

## 7. Ticket Index (Sprint 9)

| Ticket | Description |
|--------|-------------|
| 09-01-model-registry-ui.md | Model Registry page: list view, sorting/filtering, quick actions (activate, pause, view details). |
| 09-02-model-detail-page.md | Model Detail page: overview, training/validation summary, live performance, calibration plots. |
| 09-03-ml-performance-visualization.md | ML performance charts: prediction vs actual, rolling accuracy, confusion matrix, calibration curves, error distribution. |
| 09-04-model-comparison-ranking.md | Model comparison & ranking view: side-by-side, sorting/filtering, drift/confidence comparison. |
| 09-05-hyperparameter-threshold-tuning.md | Hyperparameter & threshold tuning UI: confidence/abstention/allocation controls; confirmation modal; logging and rollback. |
| 09-06-model-lifecycle-controls.md | Model lifecycle controls: activate/deactivate, promote candidate, retire, freeze, clone config. |
| 09-07-drift-health-visualization-ui.md | Drift & health visualization UI: drift trend charts, feature heatmaps, health timeline, alerts, suggested actions. |
| 09-08-hitl-review-mode-model-centric.md | HITL review mode (model-centric): recommendation queue, explanation display, approve/reject, rationale, decision logging. |
| 09-09-model-sandbox-what-if.md | Model sandbox / what-if: parameter sandbox, rerun backtests with modified thresholds, compare hypothetical allocations, preview before apply. |
