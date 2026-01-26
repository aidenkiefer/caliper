# Sprint 6 Multi-Agent Workflow: ML Safety & Interpretability Core

**Sprint 6 Focus:** Enable explicit model behavior under uncertainty, build trust through interpretability, and deploy dashboard to Vercel

---

## 🎯 Sprint 6 Overview

**Goal:** Transform the platform from a functional ML trading system into a **trustworthy ML platform** with explicit uncertainty handling, interpretable recommendations, and human oversight capabilities.

**Prerequisites:** Sprint 5 complete (Execution engine, Risk management, Kill switches)

**Sprint Duration:** Days 15-18

**Parallelization:** ✅ High - ML services, frontend, and infrastructure can develop largely in parallel

---

## 📋 Sprint 6 Tasks Breakdown

### Stream A: Model Drift & Decay Detection (ML Agent) - PARALLEL

| Task | Description | Dependencies |
|------|-------------|--------------|
| A1 | Create `services/ml/drift/__init__.py` skeleton | None |
| A2 | Implement feature drift tracking (mean, std, PSI, KL divergence) | A1 |
| A3 | Implement prediction confidence drift monitoring | A2 |
| A4 | Implement error drift tracking (when ground truth available) | A2 |
| A5 | Implement threshold-based drift alerts | A3, A4 |
| A6 | Implement model "health score" derived from drift signals | A5 |
| A7 | Create drift metrics storage and query API | A6 |

### Stream B: Confidence Gating & Abstention (ML Agent) - PARALLEL

| Task | Description | Dependencies |
|------|-------------|--------------|
| B1 | Extend model output schema: BUY / SELL / ABSTAIN | None |
| B2 | Implement configurable confidence thresholds per strategy | B1 |
| B3 | Implement entropy/uncertainty measure calculation | B1 |
| B4 | Implement ensemble disagreement signals | B3 |
| B5 | Update backtest engine to account for abstention trades | B2, B4 |
| B6 | Create confidence gating configuration API | B2 |

### Stream C: Local Explainability - SHAP (ML Agent) - PARALLEL

| Task | Description | Dependencies |
|------|-------------|--------------|
| C1 | Create `services/ml/explainability/__init__.py` skeleton | None |
| C2 | Implement SHAP integration for tree-based models | C1 |
| C3 | Implement permutation importance as fallback | C1 |
| C4 | Define explanation payload schema (features, influence, confidence) | C2 |
| C5 | Store explanations alongside trade records | C4 |
| C6 | Create explanation query API endpoint | C5 |

### Stream D: Human-in-the-Loop Controls (ML Agent) - SEQUENTIAL (after B, C)

| Task | Description | Dependencies |
|------|-------------|--------------|
| D1 | Add approval flag in execution pipeline | B6 |
| D2 | Implement recommendation queue (pending human approval) | D1 |
| D3 | Log human vs model decisions for comparison | D2 |
| D4 | Create HITL management API endpoints | D3 |

### Stream E: Regret & Baseline Comparison (ML Agent) - PARALLEL

| Task | Description | Dependencies |
|------|-------------|--------------|
| E1 | Implement baseline strategy: hold cash | None |
| E2 | Implement baseline strategy: buy & hold | None |
| E3 | Implement baseline strategy: random (risk-controlled) | None |
| E4 | Implement regret metrics calculation vs baselines | E1, E2, E3 |
| E5 | Track regret over time | E4 |
| E6 | Create regret metrics API endpoint | E5 |

### Stream F: Frontend - Help & Tooltips (Frontend Agent) - PARALLEL

| Task | Description | Dependencies |
|------|-------------|--------------|
| F1 | Create `glossary.ts` data file with term definitions | None |
| F2 | Create reusable `Tooltip` wrapper component | None |
| F3 | Add tooltips to StatsCard component (Overview page) | F1, F2 |
| F4 | Add tooltips to table headers (Strategies, Runs, Positions) | F1, F2 |
| F5 | Build `/help` page with searchable glossary | F1 |
| F6 | Add `?` icon to sidebar navigation linking to Help | F5 |

### Stream G: Frontend - Explainability UI (Frontend Agent) - SEQUENTIAL (after C6)

| Task | Description | Dependencies |
|------|-------------|--------------|
| G1 | Create trade explanation component | C6 |
| G2 | Add explanation view to strategy detail page | G1 |
| G3 | Create feature importance visualization (bar chart) | G1 |
| G4 | Add confidence indicator to recommendations | B6, G1 |

### Stream H: Frontend - HITL & Baselines UI (Frontend Agent) - SEQUENTIAL (after D4, E6)

| Task | Description | Dependencies |
|------|-------------|--------------|
| H1 | Create recommendation approval queue UI | D4 |
| H2 | Create manual override controls | H1 |
| H3 | Create regret/baseline comparison dashboard widget | E6 |
| H4 | Add "vs baseline" toggle to performance charts | H3 |

### Stream I: Vercel Deployment (DevOps Agent) - PARALLEL

| Task | Description | Dependencies |
|------|-------------|--------------|
| I1 | Create `vercel.json` with build and routing configuration | None |
| I2 | Configure environment variables for Vercel | I1 |
| I3 | Set up API rewrites to proxy `/api/*` to FastAPI backend | I1 |
| I4 | Configure production and preview environments | I2 |
| I5 | Document deployment runbook | I4 |

### Stream J: Architecture Review (Architect Agent) - PARALLEL

| Task | Description | Dependencies |
|------|-------------|--------------|
| J1 | Review ML drift detection architecture | A7 |
| J2 | Review explainability integration | C6 |
| J3 | Review HITL control flow | D4 |
| J4 | Update `docs/architecture.md` with ML safety sections | J1, J2, J3 |
| J5 | Create ADR-0008 for ML explainability decisions | J4 |
| J6 | Create ADR-0009 for drift detection decisions | J4 |

### Stream K: Testing (QA Agent) - SEQUENTIAL (after ML services)

| Task | Description | Dependencies |
|------|-------------|--------------|
| K1 | Write unit tests for drift detection | A7 |
| K2 | Write unit tests for confidence gating | B6 |
| K3 | Write unit tests for SHAP explanations | C6 |
| K4 | Write unit tests for baseline strategies | E6 |
| K5 | Write integration tests for HITL workflow | D4 |
| K6 | Write E2E tests for help page | F6 |
| K7 | Create ML safety verification runbook | K1-K6 |

### Stream L: Integration & Documentation (Integrator Agent) - FINAL

| Task | Description | Dependencies |
|------|-------------|--------------|
| L1 | Verify all agent deliverables are complete | A-K complete |
| L2 | Run all tests and verify acceptance criteria | L1 |
| L3 | Write `plans/SPRINT6_SUMMARY.md` with tasks, files, skills per agent | L2 |
| L4 | Update `plans/task_plan.md` - mark Sprint 6 complete | L3 |
| L5 | Update `plans/progress.md` - update current phase and status | L3 |
| L6 | Update `plans/milestones.md` - mark Sprint 6 deliverables complete | L3 |
| L7 | Update `README.md` - reflect Sprint 6 completion | L3 |
| L8 | Update `docs/FEATURES.md` - add ML safety features | L3 |
| L9 | Final verification that all docs reflect current project state | L4-L8 |

---

## 📊 Dependency Graph

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       SPRINT 6 EXECUTION PLAN                                │
└─────────────────────────────────────────────────────────────────────────────┘

                    START
                      │
    ┌─────────────────┼─────────────────┬────────────────────────┐
    │                 │                 │                        │
    ▼                 ▼                 ▼                        ▼
┌──────────────────────────────────────────┐    ┌──────────┐   ┌─────────────┐
│           ML AGENT (Streams A-E)          │    │ DevOps   │   │  Architect  │
│                                          │    │(Stream I)│   │ (Stream J)  │
│  ┌───────┐  ┌───────┐  ┌───────┐        │    │ Vercel   │   │  Reviews    │
│  │Stream │  │Stream │  │Stream │        │    │ Deploy   │   │  as work    │
│  │   A   │  │   B   │  │   C   │        │    └────┬─────┘   │  completes  │
│  │ Drift │  │ Conf. │  │ SHAP  │        │         │         └──────┬──────┘
│  └───┬───┘  └───┬───┘  └───┬───┘        │         │                │
│      │          │          │            │         │                │
│      │          ▼          ▼            │         │                │
│      │    ┌─────────────────────┐       │         │                │
│      │    │    Stream D         │       │         │                │
│      │    │ Human-in-the-Loop   │       │         │                │
│      │    └──────────┬──────────┘       │         │                │
│      │               │                  │         │                │
│      │               │                  │         │                │
│      │  ┌───────┐    │                  │         │                │
│      │  │Stream │    │                  │         │                │
│      │  │   E   │    │                  │         │                │
│      │  │Regret │    │                  │         │                │
│      │  └───┬───┘    │                  │         │                │
│      │      │        │                  │         │                │
└──────┼──────┼────────┼──────────────────┘         │                │
       │      │        │                            │                │
       ▼      ▼        ▼                            │                │
┌────────────────────────────────────┐              │                │
│     FRONTEND AGENT (Streams F-H)   │              │                │
│                                    │              │                │
│  Stream F (Parallel)               │              │                │
│  ┌───────────────────────────┐     │              │                │
│  │ Tooltips + Help Page      │     │              │                │
│  └───────────────────────────┘     │              │                │
│                                    │◄─────────────┘                │
│  Stream G (After C6)               │                               │
│  ┌───────────────────────────┐     │                               │
│  │ Explainability UI         │     │                               │
│  └───────────────────────────┘     │                               │
│                                    │                               │
│  Stream H (After D4, E6)           │                               │
│  ┌───────────────────────────┐     │                               │
│  │ HITL + Baselines UI       │     │                               │
│  └───────────────────────────┘     │                               │
└────────────────┬───────────────────┘                               │
                 │                                                   │
                 ▼                                                   │
          ┌─────────────┐                                            │
          │  QA Agent   │◄───────────────────────────────────────────┘
          │ (Stream K)  │
          └──────┬──────┘
                 │
                 ▼
          ┌─────────────┐
          │ Integrator  │
          │ (Stream L)  │
          │ Verification│
          │ & Summary   │
          └─────────────┘
```

**Parallelization Strategy:**
- **ML Agent Streams A, B, C, E** start immediately (drift, confidence, SHAP, baselines)
- **ML Agent Stream D** (HITL) starts after B and C complete
- **DevOps Agent Stream I** starts immediately (Vercel deployment)
- **Frontend Agent Stream F** starts immediately (tooltips, help page)
- **Frontend Agent Stream G** starts after C6 (explanation API ready)
- **Frontend Agent Stream H** starts after D4 and E6 (HITL and baselines APIs ready)
- **Architect Agent** reviews as ML services complete
- **QA Agent** starts after ML services are testable
- **Integrator** runs final verification and documentation

---

## 👥 Agent Assignment

### ML Agent (Backend)
**Owns:** Tasks A1-A7, B1-B6, C1-C6, D1-D4, E1-E6 (ML Services)

**Files:**
- `services/ml/drift/**/*.py`
- `services/ml/explainability/**/*.py`
- `services/ml/baselines/**/*.py`
- `services/ml/hitl/**/*.py`
- `services/ml/README.md`
- `services/ml/pyproject.toml`
- `packages/common/ml_schemas.py` (new)
- `services/api/routers/drift.py` (new)
- `services/api/routers/explanations.py` (new)
- `services/api/routers/recommendations.py` (new)
- `services/backtest/abstention.py` (new)

**Cannot Touch:**
- `apps/dashboard/**` (Frontend Agent)
- `vercel.json` (DevOps Agent)
- `tests/**` (QA Agent)
- `docs/architecture.md` (Architect Agent)

### Frontend Agent
**Owns:** Tasks F1-F6, G1-G4, H1-H4 (Dashboard UX)

**Files:**
- `apps/dashboard/lib/glossary.ts` (new)
- `apps/dashboard/components/ui/tooltip-wrapper.tsx` (new)
- `apps/dashboard/components/stats-card.tsx` (update - add tooltips)
- `apps/dashboard/app/(dashboard)/help/page.tsx` (new)
- `apps/dashboard/components/explanation-card.tsx` (new)
- `apps/dashboard/components/feature-importance-chart.tsx` (new)
- `apps/dashboard/components/approval-queue.tsx` (new)
- `apps/dashboard/components/baseline-comparison.tsx` (new)

**Cannot Touch:**
- `services/**/*.py` (ML/Backend Agent)
- `tests/**/*.py` (QA Agent)
- `docs/architecture.md` (Architect Agent)

### Architect Agent
**Owns:** Tasks J1-J6 (Design Review)

**Files:**
- `docs/architecture.md` (update ML safety sections)
- `adr/0008-ml-explainability.md` (new)
- `adr/0009-drift-detection.md` (new)

**Cannot Touch:**
- `services/**/*.py` (ML/Backend Agent)
- `apps/dashboard/**` (Frontend Agent)
- `tests/**` (QA Agent)

### QA Agent
**Owns:** Tasks K1-K7 (Testing)

**Files:**
- `tests/unit/test_drift_detection.py`
- `tests/unit/test_confidence_gating.py`
- `tests/unit/test_explainability.py`
- `tests/unit/test_baselines.py`
- `tests/integration/test_hitl_workflow.py`
- `tests/e2e/test_help_page.py`
- `tests/fixtures/ml_data.py`
- `docs/runbooks/ml-safety-verification.md`

**Cannot Touch:**
- `services/**/*.py` (ML/Backend Agent)
- `apps/dashboard/**` (Frontend Agent)
- `vercel.json` (DevOps Agent)

### DevOps Agent
**Owns:** Tasks I1-I5 (Vercel Deployment)

**Files:**
- `apps/dashboard/vercel.json`
- `apps/dashboard/.env.example` (update)
- `docs/runbooks/vercel-deployment.md`

**Cannot Touch:**
- `services/**/*.py` (ML/Backend Agent)
- `apps/dashboard/components/**` (Frontend Agent)
- `tests/**` (QA Agent)

---

## 🛠️ Required Skills per Agent

### ML Agent
| Skill | Purpose | Checklist |
|-------|---------|-----------|
| `@using-superpowers` | Skill invocation protocol | ☐ Read before ANY work |
| `@python-patterns` | Async patterns, type hints, Pydantic | ☐ All ML modules |
| `@api-patterns` | REST endpoints for drift/explanations | ☐ API routes |
| `@clean-code` | Maintainable ML code | ☐ Small functions, docstrings |

### Frontend Agent
| Skill | Purpose | Checklist |
|-------|---------|-----------|
| `@using-superpowers` | Skill invocation protocol | ☐ Read before ANY work |
| `@nextjs-best-practices` | App Router, Server Components | ☐ Help page |
| `@react-patterns` | Component patterns, hooks | ☐ Tooltip, Explanation components |
| `@tailwind-patterns` | Styling consistency | ☐ All new components |

### Architect Agent
| Skill | Purpose | Checklist |
|-------|---------|-----------|
| `@using-superpowers` | Skill invocation protocol | ☐ Read before ANY work |
| `@api-patterns` | Validate API design | ☐ ML endpoints |
| `@software-architecture` | System design review | ☐ ML safety architecture |

### QA Agent
| Skill | Purpose | Checklist |
|-------|---------|-----------|
| `@using-superpowers` | Skill invocation protocol | ☐ Read before ANY work |
| `@testing-patterns` | TDD, mocking | ☐ ML service tests |
| `@python-patterns` | pytest, fixtures | ☐ All test files |

### DevOps Agent
| Skill | Purpose | Checklist |
|-------|---------|-----------|
| `@using-superpowers` | Skill invocation protocol | ☐ Read before ANY work |
| `@vercel-deployment` | Vercel configuration | ☐ vercel.json, env vars |

---

## 📄 Output Contracts

### ML Agent Deliverables

1. **Drift Detection Service** (`services/ml/drift/`)
   - `__init__.py`, `detector.py`
   - `metrics.py` (PSI, KL divergence, mean/std tracking)
   - `health_score.py` (composite health score)
   - `alerts.py` (threshold-based alerts)

2. **Confidence Gating** (`services/ml/confidence/`)
   - `__init__.py`, `gating.py`
   - `abstention.py` (ABSTAIN decision logic)
   - `uncertainty.py` (entropy, ensemble disagreement)

3. **Explainability Service** (`services/ml/explainability/`)
   - `__init__.py`, `shap_explainer.py`
   - `permutation.py` (fallback explainer)
   - `schemas.py` (explanation payload)

4. **Baseline Strategies** (`services/ml/baselines/`)
   - `hold_cash.py`
   - `buy_and_hold.py`
   - `random_controlled.py`
   - `regret_calculator.py`

5. **HITL Controls** (`services/ml/hitl/`)
   - `__init__.py`, `approval_queue.py`
   - `override.py`
   - `logging.py` (human vs model decisions)

6. **API Routes**
   - `services/api/routers/drift.py` - GET /v1/drift/metrics, GET /v1/drift/health
   - `services/api/routers/explanations.py` - GET /v1/explanations/{trade_id}
   - `services/api/routers/recommendations.py` - GET/POST /v1/recommendations

7. **Schemas**
   - `packages/common/ml_schemas.py` - DriftMetrics, Explanation, Recommendation

### Frontend Agent Deliverables

1. **Glossary & Tooltips**
   - `apps/dashboard/lib/glossary.ts` - Trading term definitions
   - `apps/dashboard/components/ui/tooltip-wrapper.tsx` - Reusable tooltip
   - Updated `StatsCard` with tooltip triggers
   - Updated table headers with tooltips

2. **Help Page**
   - `apps/dashboard/app/(dashboard)/help/page.tsx` - Searchable glossary
   - Category sections (Performance, Risk, Position, Strategy)

3. **Explainability UI**
   - `apps/dashboard/components/explanation-card.tsx` - Trade explanation display
   - `apps/dashboard/components/feature-importance-chart.tsx` - Bar chart

4. **HITL UI**
   - `apps/dashboard/components/approval-queue.tsx` - Pending recommendations
   - `apps/dashboard/components/baseline-comparison.tsx` - vs baseline charts

### QA Agent Deliverables

1. **Unit Tests** (target: 60+ tests)
   - `tests/unit/test_drift_detection.py` (20 tests)
   - `tests/unit/test_confidence_gating.py` (15 tests)
   - `tests/unit/test_explainability.py` (15 tests)
   - `tests/unit/test_baselines.py` (10 tests)

2. **Integration Tests** (target: 15+ tests)
   - `tests/integration/test_hitl_workflow.py` (10 tests)
   - `tests/e2e/test_help_page.py` (5 tests)

3. **Verification Runbook**
   - `docs/runbooks/ml-safety-verification.md`

### Architect Agent Deliverables

1. **Updated Architecture** (`docs/architecture.md`)
   - ML Safety architecture section
   - Drift detection flow diagram
   - SHAP explainability integration
   - HITL control flow
   - Baseline comparison flow

2. **ADRs**
   - `adr/0008-ml-explainability.md` - SHAP decision
   - `adr/0009-drift-detection.md` - Drift metrics decision

### DevOps Agent Deliverables

1. **Vercel Configuration**
   - `apps/dashboard/vercel.json` - Build, routing, rewrites
   - Environment variables documentation
   - Preview and production environment setup

2. **Documentation**
   - `docs/runbooks/vercel-deployment.md` - Deployment guide

### Integrator Agent Deliverables

1. **Sprint Summary** (`plans/SPRINT6_SUMMARY.md`)
   - Tasks completed by each agent
   - Files created/modified per agent
   - Skills used by each agent with evidence
   - Known issues or limitations
   - Test results summary

2. **Documentation Updates**
   - `plans/task_plan.md` - Sprint 6 marked complete
   - `plans/progress.md` - Current phase updated
   - `plans/milestones.md` - Sprint 6 deliverables checked
   - `README.md` - Sprint 6 status and features
   - `docs/FEATURES.md` - ML safety features added

---

## ✅ Acceptance Criteria

### Drift Detection
- [ ] Feature drift calculated (PSI, KL divergence, mean/std shift)
- [ ] Prediction confidence drift monitored
- [ ] Threshold-based alerts trigger when drift exceeds limits
- [ ] Model health score derived from drift signals (0-100)
- [ ] Drift metrics queryable via API per model, per feature

### Confidence Gating
- [ ] Model output includes ABSTAIN option
- [ ] Confidence thresholds configurable per strategy
- [ ] Backtest engine handles abstention trades correctly
- [ ] Strategy abstains when confidence < threshold (verified)

### Explainability
- [ ] SHAP explanations generated for tree-based models
- [ ] Explanation payload includes: features, influence (+/-), confidence
- [ ] Explanations stored alongside trade records
- [ ] Dashboard shows human-readable trade explanations

### Human-in-the-Loop
- [ ] Approval flag can pause execution pending human decision
- [ ] Recommendation queue holds pending approvals
- [ ] Human override logged for comparison
- [ ] Trade requires explicit approval when HITL enabled

### Baselines & Regret
- [ ] Baseline strategies implemented (cash, buy & hold, random)
- [ ] Regret metrics calculated vs baselines
- [ ] Dashboard shows "vs baseline" comparison toggle

### Frontend UX
- [ ] Educational tooltips on StatsCard metrics
- [ ] Tooltips on table column headers
- [ ] Help page with searchable glossary
- [ ] All key trading terms defined (P&L, Sharpe, Max Drawdown, etc.)

### Vercel Deployment
- [ ] `vercel.json` configured correctly
- [ ] Environment variables set (NEXT_PUBLIC_API_URL)
- [ ] API rewrites proxy to FastAPI backend
- [ ] Dashboard deployed to Vercel

---

## 🔐 ML Safety Reference

### Drift Detection Thresholds
| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| PSI | > 0.1 | > 0.25 | Alert, consider retraining |
| KL Divergence | > 0.1 | > 0.2 | Alert, check data |
| Mean Shift | > 2 std | > 3 std | Alert, investigate |
| Confidence Drift | > 10% | > 20% | Alert, reduce allocation |

### Model Health Score Components
| Component | Weight | Description |
|-----------|--------|-------------|
| Feature Drift | 30% | Average PSI across features |
| Prediction Confidence | 30% | Mean confidence of recent predictions |
| Error Drift | 20% | Drift in prediction errors |
| Staleness | 20% | Time since last retraining |

### Confidence Thresholds (Default)
| Decision | Threshold |
|----------|-----------|
| ABSTAIN | Confidence < 0.55 |
| LOW_CONFIDENCE | Confidence < 0.65 |
| NORMAL | Confidence >= 0.65 |
| HIGH_CONFIDENCE | Confidence >= 0.85 |

---

## 📋 Sprint Status

**Status:** 🟡 NOT STARTED  
**Target Duration:** Days 15-18  
**Agents Required:** 5 (ML, Frontend, Architect, QA, DevOps) + Integrator

---

## 🚀 Quick Start

See `docs/workflow/SPRINT6_AGENT_PROMPTS.md` for copy-paste ready prompts for each agent.

**Execution Order:**
1. **Phase 1:** ML (A+B+C+E), DevOps, Frontend (F), Architect start in parallel
2. **Phase 2:** ML Stream D (HITL) after B+C complete
3. **Phase 3:** Frontend Streams G+H after ML APIs ready
4. **Phase 4:** QA Agent (testing)
5. **Phase 5:** Integrator verification and documentation

---

## 📚 Reference Documents

**Must Read:**
- `plans/more-features.md` - Full ML safety feature specifications
- `docs/dashboard-spec.md` - Help page and tooltip requirements
- `docs/architecture.md` - Current architecture
- `docs/risk-policy.md` - Risk context

**Agent Briefs:**
- `agents/briefs/ML.md` (or `BACKEND.md`)
- `agents/briefs/FRONTEND.md`
- `agents/briefs/ARCHITECT.md`
- `agents/briefs/QA.md`
- `agents/briefs/DEVOPS.md`

**Skills:**
- `agents/skills/skills/using-superpowers/SKILL.md` (MANDATORY)
- `agents/skills/skills/python-patterns/SKILL.md`
- `agents/skills/skills/api-patterns/SKILL.md`
- `agents/skills/skills/nextjs-best-practices/SKILL.md`
- `agents/skills/skills/react-patterns/SKILL.md`
- `agents/skills/skills/tailwind-patterns/SKILL.md`
- `agents/skills/skills/testing-patterns/SKILL.md`
- `agents/skills/skills/software-architecture/SKILL.md`
- `agents/skills/skills/vercel-deployment/SKILL.md`
