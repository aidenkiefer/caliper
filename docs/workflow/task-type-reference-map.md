# Task Type → Reference Documents Map

**Purpose:** Map common task categories in `quant/` to the exact reference docs, file areas, agent types, and domain skills that should be loaded for efficient agentic work.

**For:** Agents executing tickets and humans writing tickets/specs.

---

## How to use this map

1. Identify the task type.
2. Load the required references first.
3. Prefer the smallest authoritative doc that answers the question.
4. Add the listed domain skills to the ticket only when directly relevant.
5. Keep Allowed Files narrower than the file scopes shown here.

### Priority and size

- **HIGH:** Primary source of truth for the task.
- **MEDIUM:** Supporting reference that often matters.
- **LOW:** Load only if needed.
- **S:** Short guide or README.
- **M:** Medium-length spec/guide.
- **L:** Large design/contract doc.

---

## Verified domain skills from `~/projects/skills/`

Use only skills that actually exist in the shared skills workspace.

`backend-dev-guidelines` · `frontend-design` · `react-best-practices` · `ui-ux-pro-max` · `mobile-design` · `webapp-testing` · `copywriting` · `web-artifacts-builder`

---

## Sub-agent routing

When a ticket specifies `Agent type: <type>`, load this bundle first.

| Agent type | Load these references | Load these skills |
|---|---|---|
| `api-agent` | `docs/api-contracts.md`, `docs/architecture.md`, `services/api/README.md` | `backend-dev-guidelines` |
| `ml-agent` | `docs/plans/specs/sprint-7-first-ml-model-spec.md`, `docs/plans/specs/sprint-8-observability-safety-spec.md`, `docs/data-contracts.md`, `docs/architecture.md` | `backend-dev-guidelines`, `systematic-debugging` |
| `risk-agent` | `docs/risk-policy.md`, `docs/architecture.md`, `docs/security.md` | `backend-dev-guidelines`, `systematic-debugging` |
| `backtest-agent` | `docs/architecture.md`, `docs/data-contracts.md`, `docs/runbooks/backtest-verification.md` | `backend-dev-guidelines`, `test-driven-development` |
| `data-agent` | `docs/data-contracts.md`, `docs/architecture.md`, `services/data/README.md` | `backend-dev-guidelines`, `test-driven-development` |
| `frontend-agent` | `docs/dashboard-spec.md`, `docs/design-guidelines.md`, `apps/dashboard/README.md` | `frontend-design`, `react-best-practices` |
| `dashboard-ux-agent` | `docs/design-guidelines.md`, `docs/dashboard-spec.md` | `frontend-design`, `ui-ux-pro-max`, `mobile-design` |
| `debugging-agent` | `docs/architecture.md`, relevant runbook under `docs/runbooks/`, relevant service README | `systematic-debugging` |
| `testing-agent` | `docs/runbooks/api-verification.md`, `docs/runbooks/backtest-verification.md`, `docs/runbooks/execution-verification.md`, `docs/runbooks/ml-safety-verification.md` | `test-driven-development`, `webapp-testing` |
| `docs-agent` | `docs/INDEX.md`, `docs/workflow/workflow.md`, `docs/plans/README.md` | `writing-plans` |
| `security-agent` | `docs/security.md`, `docs/architecture.md`, `configs/environments/.env.example` | `systematic-debugging`, `backend-dev-guidelines` |

---

## Task type reference map

| Task type | Examples | Required references | Optional references | File scope | Agent type | Skills | Constraints | Priority | Size |
|---|---|---|---|---|---|---|---|---|---|
| **Dashboard page or route** | New pages under the dashboard route group, page-level refactors, model dashboard work | `docs/dashboard-spec.md`, `docs/design-guidelines.md`, relevant sprint 9 spec | `apps/dashboard/README.md`, `docs/SPRINTS-7-8-9-SUMMARY.md` | `apps/dashboard/src/app/**` | `frontend-agent` | `brainstorming`, `frontend-design`, `react-best-practices` | Keep data sourcing through API hooks/contracts; preserve operational clarity | HIGH | M |
| **Dashboard component / chart** | Cards, tables, charts, model visualizations, responsive layout | `docs/design-guidelines.md`, `docs/dashboard-spec.md` | Existing components under `apps/dashboard/src/components/**` | `apps/dashboard/src/components/**`, `apps/dashboard/src/lib/**` | `dashboard-ux-agent` | `frontend-design`, `ui-ux-pro-max`, `react-best-practices`, `mobile-design` | Dark-mode-first, data-dense, low-noise, accessible | HIGH | M |
| **FastAPI endpoint / router** | Router additions, schema wiring, endpoint fixes | `docs/api-contracts.md`, `docs/architecture.md`, `services/api/README.md` | Relevant sprint spec, `packages/common/api_schemas.py` | `services/api/**`, `packages/common/**` | `api-agent` | `backend-dev-guidelines` | Match REST contracts; use shared schemas; do not log secrets | HIGH | L |
| **Trading / service-layer backend** | Execution, features, broker adapters, orchestration, shared business logic | `docs/architecture.md`, `docs/data-contracts.md` | Relevant service README or sprint spec | `services/**`, `packages/**` | `backend-agent` | `backend-dev-guidelines`, `test-driven-development` | Preserve service boundaries; use shared schemas; no scope creep into UI | HIGH | L |
| **Strategy implementation** | Strategy subclasses, signal generation, inference wiring | `docs/architecture.md`, `docs/data-contracts.md`, sprint 7 spec | `packages/strategies/base.py`, relevant ticket/spec | `packages/strategies/**`, `services/ml/**`, `services/features/**` | `ml-agent` | `backend-dev-guidelines`, `test-driven-development` | Handle `ABSTAIN`; no live trading assumptions; respect risk handoff | HIGH | M |
| **ML training / inference / observability** | Training scripts, adapters, performance tracking, drift, explainability, HITL | sprint 7 spec, sprint 8 spec, `docs/data-contracts.md`, `docs/architecture.md` | `docs/model-interface-contract.md`, `docs/training-first-model.md`, `docs/sprint-7-inference-and-explainability.md` | `services/ml/**`, `packages/common/ml_schemas.py`, `packages/strategies/ml_direction_v1.py` | `ml-agent` | `backend-dev-guidelines`, `systematic-debugging`, `test-driven-development` | Preserve confidence semantics, baseline/regret context, explainability payloads, and HITL safeguards | HIGH | L |
| **Risk management / order controls** | Risk manager, kill switch, circuit breaker, limits, control endpoints | `docs/risk-policy.md`, `docs/architecture.md`, `docs/security.md` | `docs/runbooks/execution-verification.md` | `services/risk/**`, `services/execution/**`, `services/api/routers/controls.py`, `services/api/routers/orders.py` | `risk-agent` | `backend-dev-guidelines`, `systematic-debugging`, `test-driven-development` | Never bypass risk checks; fail safe; protect paper/live separation | HIGH | M |
| **Backtesting and reports** | Engine, P&L, report generation, walk-forward, abstention handling | `docs/architecture.md`, `docs/data-contracts.md`, `docs/runbooks/backtest-verification.md` | Relevant sprint spec, `docs/FEATURES.md` | `services/backtest/**`, `packages/strategies/**` | `backtest-agent` | `backend-dev-guidelines`, `test-driven-development` | No look-ahead bias; reproducible outputs; handle abstentions correctly | HIGH | M |
| **Data ingestion / contracts / migrations** | Market data models, providers, DB schema, shared schemas | `docs/data-contracts.md`, `docs/architecture.md`, `services/data/README.md` | `configs/environments/.env.example` | `services/data/**`, `packages/common/**` | `data-agent` | `backend-dev-guidelines`, `test-driven-development` | Preserve canonical schemas; avoid destructive data ops without approval | HIGH | M |
| **Docs / planning / workflow** | Specs, tickets, workflow docs, architecture/docs updates | `docs/INDEX.md`, `docs/plans/README.md`, `docs/workflow/ticket-template.md`, `docs/workflow/execution-rules.md` | Relevant domain doc being updated | `docs/**`, `plans/**`, `.claude/**`, `AGENTS.md` | `docs-agent` | `writing-plans`, `brainstorming` | Keep docs repo-accurate; prefer specific paths; update doc map when adding docs | HIGH | S |
| **Testing guidance / browser validation** | Dashboard/manual webapp tests, verification runbook updates, test tickets | Relevant runbook under `docs/runbooks/`, `docs/architecture.md` | `apps/dashboard/README.md` | `docs/runbooks/**`, browser test files if added | `testing-agent` | `test-driven-development`, `webapp-testing` | Use repo-specific runbooks; do not invent generic test guidance | MEDIUM | M |
| **Security / secrets / auth** | Secret handling, env var docs, auth boundaries, credential policies | `docs/security.md`, `docs/architecture.md`, `configs/environments/.env.example` | `docs/runbooks/vercel-deployment.md` | `docs/**`, `configs/**`, `services/api/**`, `apps/dashboard/**` | `security-agent` | `backend-dev-guidelines`, `systematic-debugging` | No secrets in code; maintain paper/live separation; fail closed | HIGH | M |
| **Deployment / dashboard ops** | Vercel config, deployment docs, dashboard env vars | `docs/runbooks/vercel-deployment.md`, `docs/security.md`, `apps/dashboard/README.md` | `vercel.json`, `docs/architecture.md` | `vercel.json`, `apps/dashboard/**`, `docs/runbooks/**` | `debugging-agent` | `verification-before-completion`, `react-best-practices` | Keep deployment guidance consistent with repo layout and env setup | MEDIUM | M |
| **Debugging / incident response** | Runtime issues, API failures, data drift, broken UI states | `docs/architecture.md`, relevant runbook, relevant service README | `docs/FEATURES.md`, `plans/progress.md` | task-specific | `debugging-agent` | `systematic-debugging` | Narrow scope first; use repo-accurate context bundle; don’t guess | HIGH | M |

---

## Quick reference: most common task types

1. **Dashboard page/component** → `frontend-agent` or `dashboard-ux-agent`; load `docs/dashboard-spec.md` + `docs/design-guidelines.md`; skills: `frontend-design`, `react-best-practices`, optionally `ui-ux-pro-max` / `mobile-design`
2. **FastAPI endpoint** → `api-agent`; load `docs/api-contracts.md` + `docs/architecture.md`; skill: `backend-dev-guidelines`
3. **ML / strategy / observability** → `ml-agent`; load sprint 7/8 specs + `docs/data-contracts.md`; skills: `backend-dev-guidelines`, `systematic-debugging`
4. **Risk / execution control** → `risk-agent`; load `docs/risk-policy.md` + `docs/security.md`; skills: `backend-dev-guidelines`, `systematic-debugging`
5. **Backtest engine/reporting** → `backtest-agent`; load `docs/runbooks/backtest-verification.md` + `docs/data-contracts.md`; skills: `backend-dev-guidelines`, `test-driven-development`
6. **Docs / spec / ticket work** → `docs-agent`; load `docs/INDEX.md` + workflow docs; skills: `writing-plans`, optionally `brainstorming`

---

## <!-- PRESERVE --> Project-specific notes

- The primary frontend is the Next.js dashboard in `apps/dashboard/`.
- Trading logic lives under `services/` and `packages/`, not under `apps/` except for the dashboard.
- The most valuable domain docs for routine work are `docs/architecture.md`, `docs/data-contracts.md`, `docs/api-contracts.md`, `docs/risk-policy.md`, `docs/security.md`, `docs/dashboard-spec.md`, and `docs/design-guidelines.md`.
- Sprint 7-9 work is organized under `docs/plans/specs/` and `docs/plans/tickets/`; broader historical context remains under `plans/`.
