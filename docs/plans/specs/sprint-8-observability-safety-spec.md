# Sprint 8 Spec: ML Observability, Safety & Evaluation

**Sprint goal:** Make the first ML model observable, debuggable, and safe before scaling to multiple models. Model failures are visible (not silent), performance is contextualized (vs baselines), and system behavior under stress is understood and documented.

**Source:** `plans/task_plan.md` (Sprint 8).  
**Workflow:** Follow `claude-workflow-opt.md`: specs are read-only context; execute only the ticket you are given.  
**CLAUDE rules:** No review/verification/QA by Claude; no build/compile/test commands. Verification is the user’s job.

---

## 1. Scope

**In scope:**

- Prediction vs outcome logging and rolling accuracy/error metrics; abstention rate tracking; performance queryable per model over time.
- Wiring existing baselines (hold cash, buy & hold, random) to model strategy comparison; regret metrics stored and exposed (e.g. API or dashboard feed).
- Feeding current feature and confidence distributions into existing drift detector; storing reference (training) distributions; health score; drift metrics and health exposed via API.
- SHAP (or permutation importance) for the deployed model’s predictions; explanation stored per prediction/recommendation.
- Failure-mode and stress simulation (missing data, volatility spike, API outage); documented system behavior (runbook or ADR).

**Out of scope:**

- Model Observatory Dashboard UI (Sprint 9).
- Multiple models or dynamic capital allocation.
- Full experiment registry or feature registry (can be minimal if needed for drift reference).

---

## 2. Skills to Use for Sprint 8 (Mandatory)

When working on any Sprint 8 ticket, Claude **must** use skills as follows:

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

- **Planning:** If a ticket requires new design choices (e.g. where to store prediction-vs-outcome records, or how to trigger stress simulations), Claude must **write planning documentation in the `docs/` folder** and **stop**.
- **Pause for input:** After writing that doc, Claude must **ask for your input** before implementing. Example: “I’ve added `docs/plans/sprint-8-stress-scenarios.md` with proposed scenarios and runbook outline. Please review and confirm before I implement.”
- **No guessing on product/design:** Do not implement ambiguous or high-impact decisions without a doc and your confirmation.

---

## 4. Design Intent and Constraints

- **Observability:** All model outputs (predictions, confidence, abstentions) and outcomes (when known) should be loggable and queryable over time. Prefer existing APIs and schemas (`services/ml/`, `packages/common/ml_schemas.py`).
- **Baselines:** Use existing baseline strategies and regret calculator in `services/ml/baselines/`; wire them to the live model strategy comparison and expose regret via API or feed for dashboard.
- **Drift:** Use existing `services/ml/drift/` (PSI, KL, health score). Store reference distributions from training; feed current distributions from inference; expose drift and health via API.
- **Explainability:** Use existing SHAP/permutation explainers in `services/ml/explainability/`; store explanation per prediction/recommendation and expose via existing explanations API where applicable.
- **Stress:** Simulations are scripts or documented procedures (missing data, volatility spike, API outage). Document behavior (no trade, abstain, fallback, etc.) in `docs/` (runbook or ADR); no requirement to automate all scenarios in code.

---

## 5. Success Criteria (Sprint 8)

- Model failures are visible, not silent (logging and queryable metrics).
- Performance is contextualized, not absolute (vs baselines; regret exposed).
- System behavior under stress is understood and documented (runbook or ADR).

---

## 6. Reference Docs (Read-Only for Tickets)

- `docs/architecture.md` — services, data flow.
- `docs/api-contracts.md` — API endpoints for metrics, drift, baselines, explanations.
- `docs/risk-policy.md` — risk limits.
- `deep-review.md` — current ML and pipeline state.
- `plans/task_plan.md` — Sprint 8 actionable implementation list.
- `packages/common/ml_schemas.py` — ML API schemas.
- `services/ml/drift/` — drift detector, health score.
- `services/ml/baselines/` — baselines and regret.
- `services/ml/explainability/` — SHAP and permutation.

---

## 7. Ticket Index (Sprint 8)

| Ticket | Description |
|--------|-------------|
| 08-01-performance-tracking.md | Log prediction vs outcome; rolling accuracy/error; abstention rate; expose via API/DB. |
| 08-02-baseline-regret-wiring.md | Wire baselines to model comparison; compute and expose regret metrics. |
| 08-03-drift-monitoring.md | Feed current data into drift detector; store reference; health score; expose drift/health via API. |
| 08-04-shap-explainability.md | Integrate SHAP/permutation for deployed model; store explanation per prediction; expose via API. |
| 08-05-failure-mode-stress-simulation.md | Implement/script stress scenarios; document system behavior in runbook or ADR. |
