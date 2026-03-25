# Workflow Philosophy (Humans Only)

**For:** You, when designing sessions or refining the agentic workflow.
**Not for:** Loading into agent context. Keeps runtime docs lean.

---

## Context engineering

Agentic efficiency is **context engineering**: choosing which instructions, files, and history are worth spending tokens on. The dominant failure mode is **persistent context bloat**—global instructions always loaded plus unbounded exploration.

- **Persistent context** must be minimal and stable (e.g. .claude/CLAUDE.md, AGENTS.md).
- **Everything else** is **lazy-loaded** (specs, tickets, path-scoped rules).
- Each run must be **bounded** (explicit Allowed Files, tool/file budgets, done criteria).
- Exploration should happen in **separate contexts** (e.g. subagents) and be summarized back.

---

## Specs vs tickets

- **Specs** = what we're building (domain, schema, architecture, sprint scope). Read once per session; summarize to 10–20 lines + key quotes; then do tickets using the summary, not the full spec.
- **Tickets** = one concrete change, Allowed Files, read-only references, budgets, done criteria. They are the execution boundary.

---

## Session strategy (cost-efficient)

1. **Hydrate (once per session):** Load minimal CLAUDE.md, then read only the spec(s) for the next chunk. Convert to a short Spec Summary + reference quotes. Do not re-attach full specs every turn.
2. **Batch 3–8 tickets** with the *same* spec summary to amortize spec-read cost.
3. **Use /clear** at context boundaries (unrelated tasks).
4. **Exploration in subagents:** If investigation would consume the main context, use a subagent and return a summary (exact file paths + 3–6 bullets).
5. **End-of-session:** Save a short summary of decisions and modified files, and append a brief dated note to `docs/plans/PROGRESS.md` (or equivalent).

---

## Anti-patterns

- **Kitchen-sink threads:** Mixing unrelated tasks; fix with /clear.
- **Infinite exploration:** "Investigate X" without scope; fix with narrow prompts or investigation subagent.
- **Overlong CLAUDE.md:** Prune ruthlessly; move detail to specs, rules, human docs.
- **Loading huge skill registries by default:** Use path- and ticket-driven skill activation; small core + domain packs.
- **Re-attaching large specs every ticket:** Fix with "read once, summarize once, then ticket."
- **Planning + implementation + verification in one massive run:** Split into phases; use the right model/effort.
- **Unbounded indexing scope:** Use .cursorignore and clean repo hygiene so retrieval stays focused.

---

## Skill strategy (3-layer)

- **Core skills (5–12 max):** "How we work" patterns (planning, debugging discipline, doc updates). Always small.
- **Domain packs:** Frontend, backend, data—loaded only when ticket or path is relevant.
- **Project-specific:** Rare, high-ROI; only when ticket touches that subsystem.

Ticket names the exact skill pack(s) allowed. Any other skill = stop and ask.

---

*Execution-rules and ticket-template are the agent-facing artifacts. Keep this doc out of agent context.*
