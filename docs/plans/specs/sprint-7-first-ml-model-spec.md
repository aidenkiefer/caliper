# Sprint 7 Spec: First ML Model (End-to-End Loop)

**Sprint goal:** Introduce exactly one real ML model into the system and run it end-to-end with correct training, validation, inference, and execution semantics. This sprint is about correctness, clarity, and learning — not performance or UI polish.

**Source:** `plans/task_plan.md` (Sprint 7).  
**Workflow:** Follow `claude-workflow-opt.md`: specs are read-only context; execute only the ticket you are given.  
**CLAUDE rules:** No review/verification/QA by Claude; no build/compile/test commands. Verification is the user’s job.

---

## 1. Scope

**In scope:**

- One ML model (e.g. logistic regression or small tree) used for signal generation.
- ML problem definition (target, horizon, labels, metrics) documented in `docs/`.
- Offline training script with time-aware train/validation split and leakage prevention.
- Standardized model input/output contract consumable by the execution layer.
- Inference integrated into the live/paper pipeline (strategy or dedicated service) with risk and execution.
- Text-based explainability (features used, confidence, short rationale) stored with predictions; no SHAP required yet.

**Out of scope:**

- Multiple models or ensemble logic.
- SHAP or other advanced explainability (Sprint 8).
- Model registry UI, experiment registry, or MLOps tooling beyond what’s needed for one model.
- Full replacement of API mocks with production DB (can be partial if needed for logging predictions).

---

## 2. Skills to Use for Sprint 7 (Mandatory)

When working on any Sprint 7 ticket, Claude **must** use skills as follows:

1. **First:** Read and follow `agents/skills/skills/using-superpowers/SKILL.md` (or project equivalent) before doing anything else.
2. **Then:** Use as many of the following skills as apply to the ticket. Prefer 5–7 for small tickets and up to 12–15 for large ones.

**ML & experimentation**

1. **ml-pipeline-builder**
2. **feature-engineering**
3. **time-series-ml**
4. **ensemble-modeling** (only if ticket involves ensemble; otherwise skip)
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

Each ticket will list which of these are **mandatory** for that task; use additional skills from this list as needed. If a skill file is missing under `agents/skills/skills/`, treat the skill name as a reminder of the domain (e.g. data leakage, risk control) and apply that thinking; do not block the ticket.

---

## 3. Planning and Pausing for Input

- **Planning:** If a ticket requires new design choices (e.g. target variable definition, where to persist model artifacts, or schema changes), Claude must **write planning documentation in the `docs/` folder** (e.g. `docs/sprint-7-ml-problem-definition.md` or `docs/plans/sprint-7-training-design.md`) and **stop**.
- **Pause for input:** After writing that doc, Claude must **ask for your input** before implementing. Example: “I’ve added `docs/plans/sprint-7-ml-target.md` with proposed target, horizon, and metrics. Please review and confirm or adjust before I implement.”
- **No guessing on product/design:** Do not implement ambiguous or high-impact decisions (e.g. “what is the prediction horizon?” or “where do we store the trained model?”) without a doc and your confirmation.

---

## 4. Design Intent and Constraints

- **One model only:** The first model is a single classifier or regressor (e.g. logistic regression, small decision tree). No ensembles for Sprint 7.
- **Time-aware:** Train/validation splits must respect time (no future data in training). Walk-forward or sliding-window is acceptable; document the choice.
- **Leakage:** Explicit checks or patterns to prevent data leakage (e.g. no forward-looking features, no peeking at validation during training).
- **Contract:** Model output must include at least: prediction (or signal), confidence (0–1), and optional abstain signal. Execution and risk layers consume this; see `packages/common/ml_schemas.py` and `services/ml/confidence/gating.py`.
- **Explainability:** Simple text or structured payload (features used, confidence, short rationale). Stored with each prediction/trade; no SHAP in Sprint 7.
- **Risk:** All orders still go through `RiskManager` and kill switch; model output does not bypass risk checks.

---

## 5. Success Criteria (Sprint 7)

- Exactly one ML model runs end-to-end (training → serialization → load → inference → signal → risk → order path).
- Model behavior is understandable and inspectable (documented target, metrics, and simple explanations).
- No silent failures or hidden assumptions (documented failure modes and assumptions).

---

## 6. Reference Docs (Read-Only for Tickets)

- `docs/architecture.md` — services, data flow, strategy interface.
- `docs/data-contracts.md` — canonical schemas.
- `docs/risk-policy.md` — risk limits and kill switch.
- `deep-review.md` — current ML state and pipeline.
- `plans/task_plan.md` — Sprint 7 actionable implementation list.
- `packages/common/schemas.py` — PriceBar, Signal, Order, Position.
- `packages/common/ml_schemas.py` — ML API and model output schemas.
- `services/ml/confidence/gating.py` — confidence and ABSTAIN semantics.
- `packages/strategies/base.py` — Strategy interface.

---

## 7. Ticket Index (Sprint 7)

| Ticket | Description |
|--------|-------------|
| 07-01-ml-problem-definition-doc.md | Document ML problem (target, horizon, labels, metrics, assumptions, failure modes) in `docs/`. |
| 07-02-training-pipeline-script.md | Implement offline training script with time-aware split and leakage prevention. |
| 07-03-model-interface-contract.md | Define and implement standardized model input/output schema; ensure execution layer can consume it. |
| 07-04-inference-integration.md | Wire model inference into live/paper pipeline; integrate with risk and execution; log predictions. |
| 07-05-text-explainability.md | Add simple explanation payload (features used, confidence, rationale) and store with predictions. |
