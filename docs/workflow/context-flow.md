# Context Flow Through Agent Workflow — Caliper (quant)

**Purpose:** Explain how context documents and guidelines flow through the complete lifecycle of agent work in this project — from startup to ticket execution.

**Note:** This is a project-specific doc. The structure is defined by workflow-core; the content (startup context, sub-agent routing table, reference doc mapping) is specific to this project. Update this file when your project's document structure changes.

---

## 1. Startup Context (What Agents Receive)

When an agent starts a session in this project, it receives:

### Core project files

- **`.claude/CLAUDE.md`** — Minimal project memory:
  - Mission statement
  - How to work (bounded runs, budgets)
  - Hard constraints
  - Project map (stable commands, doc locations)

- **`CLAUDE.md`** (root) — Fuller project context:
  - Monorepo: Python services (`services/`) + shared packages (`packages/`) + Next.js dashboard (`apps/dashboard/`)
  - FastAPI backend in `services/api/` serving the dashboard via REST
  - Backtesting engine in `services/backtest/`; execution + risk in `services/execution/` and `services/risk/`
  - Shared Pydantic contracts in `packages/common/`; strategy interface + implementations in `packages/strategies/`
  - ML safety/observability components in `services/ml/` (wiring to a “first ML model” lives in Sprint 7+ docs)
  - Commands (dev, build, test)
  - Hard constraints
  - Key documentation map

### Workflow documentation (`docs/workflow/`)

- **`workflow.md`** — Entrypoint: specs vs tickets, session ritual, pointers to other docs
- **`execution-rules.md`** — Runtime rules: budgets, constraints, what not to do, where things are
- **`ticket-template.md`** — Bounded job structure for every task
- **`skill-map.md`** — Layer 1 workflow process skills; ticket names the pack
- **`task-type-reference-map.md`** — Domain context: task type → refs, agent type, domain skills

### Stable reference docs loaded on demand

- **`docs/INDEX.md`** — Primary doc map for repo navigation
- **`docs/architecture.md`** — Cross-service architecture and boundaries
- **`docs/api-contracts.md`** — API surface and payload expectations
- **`docs/data-contracts.md`** — Shared schemas and canonical contracts
- **`docs/risk-policy.md`** — Risk guardrails and order constraints
- **`docs/security.md`** — Secrets, auth, and safety boundaries
- **`docs/dashboard-spec.md`** + **`docs/design-guidelines.md`** — Dashboard behavior and visual system

### What is NOT loaded at startup

- **Full specs** — Read only when a ticket explicitly requires them (session hydration)
- **Brand/design guidelines** — Loaded only for copy or UI tasks
- **Architecture docs** — Loaded only for backend/integration tasks
- **Full skill registry** — Only skills named in the ticket are loaded

---

## 2. Session Hydration Pattern

See `docs/workflow/workflow.md` → "Session start ritual" for full steps.

**Summary:** When batching 3–8 related tickets on a sprint:
1. Read the relevant spec(s) **once**
2. Produce a Spec Summary (10–20 lines: constraints, invariants, key quotes)
3. Reuse the summary for all tickets in the batch
4. Do not re-read full specs per ticket; re-anchor to quotes only when necessary

**Benefits:** Minimal context waste, small persistent memory between tickets, faster execution.

---

## 3. Ticket-Driven Context Loading

Each ticket defines exactly what context the agent loads.

### Context priority and size

Load context in this order to minimize token cost:

1. **Required References first** — Must-read docs named in the ticket's "Required read-only references" section
2. **Small (S) before Large (L)** — When multiple docs are required, load smaller ones first
3. **HIGH priority before MEDIUM/LOW** — Each task type has a primary priority doc; load it first
4. **Optional References only if relevant** — Load only when they directly address an open question or are within budget
5. **Large docs (L) on demand** — Load architecture docs, large brand guides, etc. only when the task genuinely needs full system context

**Priority definitions:** HIGH = must-read first (primary source of truth). MEDIUM = supporting doc. LOW = load if budget allows.
**Size definitions:** S < ~150 lines. M = ~150–500 lines. L > ~500 lines.

### Sub-agent routing

When a ticket sets `Agent type: <type>`, use `docs/workflow/task-type-reference-map.md` to look up that agent's reference bundle and skills.

**Project-specific routing table:**

| Agent Type | Load these references | Load these skills |
|---|---|---|
| `api-agent` | `docs/api-contracts.md`, `docs/architecture.md`, `services/api/README.md` | `backend-dev-guidelines` |
| `ml-agent` | sprint 7/8 specs, `docs/data-contracts.md`, `docs/architecture.md` | `backend-dev-guidelines`, `systematic-debugging` |
| `risk-agent` | `docs/risk-policy.md`, `docs/security.md`, `docs/architecture.md` | `backend-dev-guidelines`, `systematic-debugging` |
| `frontend-agent` | `docs/dashboard-spec.md`, `docs/design-guidelines.md`, `apps/dashboard/README.md` | `frontend-design`, `react-best-practices` |
| `dashboard-ux-agent` | `docs/design-guidelines.md`, `docs/dashboard-spec.md` | `frontend-design`, `ui-ux-pro-max`, `mobile-design` |
| `debugging-agent` | `docs/architecture.md`, relevant runbook under `docs/runbooks/`, relevant service README | `systematic-debugging` |
| `docs-agent` | `docs/INDEX.md`, `docs/workflow/workflow.md`, `docs/plans/README.md` | `writing-plans` |

If no agent type is specified, infer from task type using the full table in `task-type-reference-map.md`.

---

## 4. Reference Document Mapping by Task Type

*This section documents how context flows for your project's most common task types. Fill in after initial setup using your actual doc paths. See `task-type-reference-map.md` for the full table.*

### Dashboard / UI change

```
Ticket or spec
  ↓
docs/dashboard-spec.md      [load first — surfaces, components, data needs]
  ↓
docs/design-guidelines.md   [visual system, density, contrast, responsive behavior]
  ↓
apps/dashboard/README.md + existing components
  ↓
Relevant sprint 9 ticket/spec
```

### Backend / API / service change

```
Ticket or spec
  ↓
docs/architecture.md        [load first — data flow, patterns, constraints]
  ↓
docs/api-contracts.md       [if adding/changing API endpoints]
  ↓
service README / runbook    [if touching a specific service]
  ↓
Relevant sprint spec or ticket
```

### Strategy / ML / risk change

```
Ticket or spec
  ↓
docs/architecture.md        [overall system + service boundaries]
  ↓
docs/data-contracts.md      [schemas + canonical data contracts]
  ↓
docs/risk-policy.md         [when orders/risk are involved]
  ↓
sprint 7 or sprint 8 spec   [for ML model and observability work]
```

---

## 5. The 3-Layer Skill System

Skills are **lazy-loaded** — the ticket names which skills to invoke.

### Layer 1: Core workflow process skills (0–2 per ticket)

See `docs/workflow/skill-map.md` for the full Layer 1 table.

| When | Skill |
|------|-------|
| Starting a multi-step feature | `writing-plans` |
| Clarifying requirements or design | `brainstorming` |
| Implementing a feature with tests | `test-driven-development` |
| Any bug or test failure | `systematic-debugging` |
| Before claiming work complete | `verification-before-completion` |
| Pre-merge or major feature complete | `requesting-code-review` |

### Layer 2: Domain skills (0–2 per ticket, from task-type-reference-map)

See `docs/workflow/task-type-reference-map.md` → "Skills" column for each task type.

Examples:
- **Frontend tasks:** `frontend-design`, `react-best-practices`, `ui-ux-pro-max`, `mobile-design`
- **Backend tasks:** `backend-dev-guidelines`
- **Browser testing:** `webapp-testing`
- **Debugging:** `systematic-debugging`

### Layer 3: Project-specific context (from task-type-reference-map [PROJECT-SPECIFIC] section)

See `docs/workflow/task-type-reference-map.md` → `[PROJECT-SPECIFIC]` section at the bottom.

In Caliper, this layer mostly means:
- routing trading/ML/risk/backtest work to the correct service directories
- using sprint 7-9 specs/tickets when the task is model-centric
- pairing dashboard work with both behavior (`docs/dashboard-spec.md`) and visual-system (`docs/design-guidelines.md`) docs

### Usage rule

- Ticket names the pack(s): 0–2 core, 0–2 domain, project-specific only if ticket says so
- Small task: 0–2 skills. Medium: 2–4. Large: 4–6 max.
- Never load the full skill registry.

---

## 6. Context Audit

Run a quarterly context audit using `docs/workflow/context-audit.md` to verify that reference docs are accurate, consistent, and up-to-date.

After each audit, log results to `docs/workflow/audits/audit-results-[YYYY-MM].md`.

---

## 7. Best Practices

### For spec writers

1. List all reference docs explicitly in the spec's "Read-only references" section
2. Explain why each reference is needed (one-line comment)
3. Keep specs focused — one feature or bounded change per spec
4. Include a "Context" section summarizing what agents need to know

### For ticket writers

1. Minimize Allowed Files — only list files that will be edited
2. List all context docs needed in read-only references
3. Name skills explicitly — don't assume agents will infer which skills to use
4. Set realistic budgets: 8 reads, 6 grep/glob, 12 tool calls is the standard

### For agents

1. Read the spec once — create a summary, reuse it for all tickets
2. Respect Allowed Files — stop and ask if you need to edit an unlisted file
3. Stay within budgets — estimate before acting; ask for expansion if needed
4. Load only named skills — don't load the full skill registry

### For humans

1. Keep CLAUDE.md current — update when architecture or constraints change
2. Review context docs quarterly — use `context-audit.md`
3. Add new docs to `docs/INDEX.md` when created
4. Run context audits — verify consistency and remove obsolete info

---

## 8. Summary

Context flows through the agent workflow in a **bounded, lazy-loaded, ticket-driven** manner:

1. **Startup:** Minimal context (CLAUDE.md + workflow docs)
2. **Session hydration:** Read spec once, create summary (see `workflow.md`)
3. **Ticket execution:** Load only what's listed (Allowed Files, Read-only references, named skills)
4. **Task-specific context:** Different task types load different reference docs (see `task-type-reference-map.md`)
5. **Budgets:** Max 8 reads, 6 grep/glob, 12 tool calls per ticket
6. **No waste:** No full-repo scans, no re-reading after edits, no unused skills

This approach keeps context small, execution fast, and costs low while ensuring agents have exactly the information they need to complete each task correctly.
