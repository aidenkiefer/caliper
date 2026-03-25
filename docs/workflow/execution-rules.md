# Execution rules (agent runtime)

**For:** Claude / Cursor agents when working in this repo.
**Goal:** Bounded runs, minimal persistent context, lazy-loaded specs, explicit budgets.

## 1. How to work

### Specs vs tickets

- **Specs** (read-only) live in `docs/plans/specs/`. They describe domain, schema, and sprint scope. Do not re-attach full specs every turn.
- **Tickets** define one concrete change: Scope boundaries (Allowed files, Read-only references), Skill pack, Context + tool budget, and Done criteria. Use `docs/workflow/ticket-template.md`.

### Session strategy (cost-efficient)

1. **Hydrate (once per session):** Read the spec(s) for the next chunk of work once. Produce a Spec Summary (10–20 lines: constraints, invariants). Use it for subsequent tickets. See `docs/workflow/workflow.md` for the full ritual.
2. **Batch 3–8 tickets** with the same spec summary. Do not re-load full specs for each ticket.
3. **Clear at boundaries:** Use /clear (or new thread) between unrelated tasks.
4. **Exploration in subagents:** If the task would require unbounded "investigate X," ask for narrowed scope or use an investigation subagent that returns a summary (exact paths + 3–6 bullets).
5. Work from Spec Summary + ticket + Allowed Files. Re-anchor to spec quotes only when necessary.

---

## 2. Context + tool budget (enforce in tickets)

- Max file reads: **8**. Prefer only Allowed Files and the 1–2 required read-only references.
- Max grep/glob: **6**. Max total tool calls: **12**.
- Before acting: estimate whether you can complete within budgets. If you will exceed, stop and ask for a narrower ticket or expanded budgets.
- Do not scan the whole repo. Prefer targeted retrieval; ask for the path if unclear.
- **Skills:** Ticket names the skill pack (0–2 core, 0–2 domain). Do not load the full skill registry.

---

## 3. Constraints (always in effect)

- **Allowed Files:** Edit only the paths listed in the ticket. If the change requires editing a file not listed, stop and ask.
- **Scope:** Implement only what the task or sprint explicitly requests. Do not add out-of-scope features unless asked.
- **Project-specific constraints:** See Section 3a below.

### 3a. Project-specific constraints

[PROJECT-SPECIFIC]
- Always route order creation through risk controls (`services/risk`) — do not bypass kill switch / circuit breaker checks.
- Paper trading first; do not make changes that imply live trading or real-money execution without explicit instruction.
- Do not introduce new services based only on docs (e.g. don’t assume `services/data` exists) — implement only what exists under `services/` and `packages/` unless the ticket explicitly adds it.
- Never commit real secrets (API keys, broker credentials). Use `configs/environments/.env.example` patterns only.

---

## 4. What not to do

- Do not run build, dev, test, or compile to "verify" or "confirm" changes. Verification is the user's responsibility.
- Do not re-read entire files after editing to "self-review" or "double-check."
- Do not offer to run tests or linters unless the user explicitly asks.
- Do not duplicate constraints that are already in CLAUDE.md or this file inside tickets.
- Do not load philosophy or long explanatory docs at runtime. Human-only: `docs/workflow/philosophy.md`.
- Do not load the full skill registry; use only the skill pack named in the ticket.

---

## 5. Where things are (customize for your repo)

- **Repo map:** `docs/INDEX.md`. **Human docs:** `docs/workflow/philosophy.md`
- **Specs:** `docs/plans/specs/`. Ticket/spec hub: `docs/plans/README.md`
- **Tickets:** `docs/plans/tickets/`. Sprint summaries: `docs/SPRINTS-7-8-9-SUMMARY.md` and `plans/*SUMMARY*.md`
- **Progress log:** `docs/plans/PROGRESS.md` — workflow-era dated completion notes
- **Historical tracker:** `plans/progress.md` — broader sprint completion history
- **Core references:** `docs/architecture.md`, `docs/api-contracts.md`, `docs/data-contracts.md`, `docs/risk-policy.md`, `docs/security.md`, `docs/dashboard-spec.md`, `docs/design-guidelines.md`
- **Runbooks:** `docs/runbooks/`
- **Ticket template:** `docs/workflow/ticket-template.md`. **Skill map:** `docs/workflow/skill-map.md`
- **Task-type reference map:** `docs/workflow/task-type-reference-map.md`
- **Session hydrate:** `docs/workflow/workflow.md` → "Session start ritual"

Read only what the current task needs. Prefer the ticket's read-only references and Allowed Files list.

---

## 6. Sub-agent routing and context priority

When a ticket specifies `Agent type: <type>`, use `docs/workflow/task-type-reference-map.md` to look up:
- The required reference bundle for that agent type
- The domain skills to invoke
- The typical file scope

**Context load order (within a ticket):**
1. Required references — must-read docs in the ticket
2. Small (S) before Large (L) — lower token cost first
3. HIGH-priority before MEDIUM/LOW — primary source of truth first
4. Optional references — only if relevant or within budget

If no agent type is specified, infer from task type using the full table in `task-type-reference-map.md`.

---

## 7. Completion documentation rule

- On completion, append a short dated note to `docs/plans/PROGRESS.md`.
- Keep entries concise (1–3 bullets): what changed, key files/area, and why (if needed).
- Apply to all completed work: tiny bug/UI tweaks through major milestones/sprints.

---

## 8. Anti-patterns (avoid)

- **Kitchen-sink threads:** Use /clear. **Infinite exploration:** narrow prompt or investigation subagent.
- **Overlong CLAUDE.md:** Keep project memory minimal. **Re-attaching large specs every ticket:** read once, summarize once, then ticket.
- **Loading huge skill registries:** ticket-driven activation only. **Planning + implementation + verification in one run:** split phases.
- **Scanning whole repo:** use targeted reads and explicit paths. **Re-reading files after edits:** trust your work.
