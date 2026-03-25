# Claude Code Workflow Playbook
*A practical guide for fast, safe, low-token agentic work*

This document defines how we use **Claude Code** (CLI) and **Cursor** together to:
- avoid runaway token usage
- prevent scope creep
- keep agent runtimes short and predictable
- safely work in large or mixed static + React codebases

**Core workflow:** Write **specs** (rules, constraints, background) in `docs/plans/specs/`, then give Claude **one ticket at a time** from `docs/plans/tickets/`. Claude reads specs as context but **only executes the ticket**.

---

## 1. Mental Model (Important)

Claude Code behaves like a **very careful junior engineer**:

- It will read *more files than you expect* unless explicitly constrained.
- Open-ended tasks trigger exploratory behavior.
- Broad verification tasks cause repeated tool calls.
- Tool calls + file reads = time + token burn.

**Conclusion:**  
> Claude must be given *small, bounded tasks with explicit limits*.

---

## 2. What Causes Slow Runs & Token Blowups

Avoid these patterns:

### ❌ “Epic-sized” tasks
Examples:
- “Fix frontend parity”
- “Verify design consistency”
- “Clean up CSS everywhere”

These imply:
- many files
- many checks
- open-ended completion criteria

---

### ❌ Open-ended verification
Phrases like:
- “Visual QA”
- “Cross-browser testing”
- “Verify parity”

Claude cannot *finish* these deterministically, so it keeps probing.

---

### ❌ Large context + writing in the same run
Asking Claude to:
- read many files **and**
- implement many changes

encourages continuous expansion of scope.

---

### ❌ Unbounded tool usage
If you do not set a tool-use budget, Claude will:
- grep
- ls
- re-grep
- open more files “just to be safe”

---

## 3. High-Level Rules (Always Follow)

### Rule 1 — One task, one outcome
Each Claude run should target **1–3 concrete changes max**.

Good:
- “Remove BACK TO SITE nav link”
- “Add mobile submenu to match static header”

Bad:
- “Fix header parity”

---

### Rule 2 — Separate specs from tickets
- **Specs** (`docs/plans/specs/`) = rules, background, constraints, design intent. They are **read-only context** for Claude.
- **Tickets** (`docs/plans/tickets/`) = small, executable tasks. Claude **acts only on the ticket** it is given.

Each ticket should:
- Reference one or more spec docs (and other read-only docs) under **Reference Docs**.
- Stay within the scope and constraints defined in those specs.

---

### Rule 3 — Hard limits must be explicit
Every ticket must define:
- **Allowed Files** — exact paths or globs (e.g. `apps/store/src/app/account/page.tsx`, `apps/store/src/components/Footer/**`). Claude may only edit files in this list.
- **Hard Limits** — e.g. max tool calls (if used), “do not edit static files,” “if the real component lives elsewhere, stop and ask to extend the list.”
- **If blocked** — “Stop and ask me to add a specific file” (or extend Allowed Files) instead of editing outside the list.

Claude respects explicit limits very well. Use an **escape hatch** in Allowed Files when the exact path might vary: *“If X lives elsewhere, stop and ask to extend the list.”*

---

### Rule 4 — Mandate skills when they matter
Tickets should include a **Mandatory skill usage** section:
- Require **using-superpowers** first so Claude loads and follows relevant skills.
- Require **domain skills** by name (e.g. frontend-design, react-best-practices).
- This section should suggest 5 skills by name (depending on the task), and encourage Claude to use as many as will be helpful (ideal skill usage: 5 for small tasks, 7 for medium and up to 12-15 for large complex tasks)

Example: *“Read `.claude/skills/skills/using-superpowers/SKILL.md` before doing anything else; use frontend-design when designing the treatment.”*

---

### Rule 5 — Only one writer at a time
Multiple agents may analyze in parallel, but:
- only one agent edits files
- or use separate git branches

---

### Rule 6 — Prefer Sonnet for implementation
- **Sonnet** → fastest + most token-efficient for coding
- **Opus (thinking)** → only for *small*, curated reasoning inputs

Never use Opus thinking for repo-wide scans.

---

## 4. Example Ticket Template

### Sample ticket format

```markdown
## Task
- <single concrete change, 1–3 related items max>

## Mandatory skill usage
- Read `.claude/skills/skills/using-superpowers/SKILL.md` first; use <domain-skill> as needed for this task.
- (Remember we want to encourage 5-15 skills if possible)

## Reference Docs (read-only)
- docs/plans/specs/<relevant-spec>.md
- docs/frontend/<relevant-doc>.md
- Static reference: html/index.html (do not edit)
- Static CSS: css/n2-production.css (do not edit)

## Allowed Files (ONLY these)
- apps/store/src/app/<path>/**
- apps/store/src/components/<Component>/**

> If the component or file lives elsewhere, stop and ask to extend the Allowed Files list.

## Hard Limits
- Do **not** edit static marketing files: html/**, css/**, js/**
- Do not read or edit files outside Allowed Files (except reference docs for reading)
- **If blocked**: Stop and ask to add a specific file; do not guess paths

## Instructions
1. Use skills as above; then locate <target> in the codebase.
2. <step two: inspect reference or existing code>.
3. <step three: implement change>.
4. Verify <visual/build/behavior> per Done Criteria.

## Done Criteria
- <concrete, verifiable outcome — e.g. “Footer uses eucalyptus background in devtools”>
- Only files in Allowed Files were modified; static files unchanged
- <Optional: project builds / npm run build passes>
- Summarize changes in ≤5 bullets (or add Implementation Summary below)
```

### Ticket naming and placement
- **Naming:** `NN-short-description.md` (e.g. `07-react-announcement-bar-background.md`). Numbers keep order; prefix (e.g. `react-`) helps when mixing domains.
- **Placement:** Flat in `docs/plans/tickets/` or in a subfolder (e.g. `tickets/cart/`) for a focused batch. Each ticket is self-contained but references specs.

---

## 5. How to Use Large Spec Docs Safely

Large docs (architecture, parity specs, design rules) should be handled carefully so they guide work without causing runaways.

### Guidelines

- **Read once, reuse often**: Ask Claude to read large spec docs once at the start of a session, then treat them as background knowledge. Don’t keep reloading them.
- **Treat specs as constraints, not tasks**: Specs define *how* work should be done, not *what* work to do. Tickets define the concrete changes.
- **One ticket, one spec (or a small set)**: Each ticket should reference the spec(s) that apply. Don’t ask Claude to “do everything in the spec”; point to the ticket and say “follow the spec while doing this ticket.”

### How to phrase instructions

- **Do _not_ say:**  
  > “Do everything described in this doc.”

- **Do say:**  
  > “Follow the rules in this doc while completing the ticket below.”


---

## 6. After Completing a Ticket (Implementation Summary)

When Claude finishes a ticket, it should leave a short record so you and future runs know what was done:

- **Add an “Implementation Summary”** at the bottom of the ticket file (or in a follow-up message), including:
  - **Completed:** Ticket ID and short name.
  - **Changes Made:** Numbered list of concrete edits (files, components, CSS).
  - **Key improvement / Result:** One or two sentences on the outcome.
  - **Files Modified:** Exact paths.
  - **Skills Used:** Which skills were applied (if any).
  - **Result:** One-line summary.

This reduces “did we already do this?” and makes handoffs and audits easier.

---

## 7. Tips for Writing Specs and Tickets

### Specs
- **One spec per theme** (e.g. react-design-parity, react-shell-polish, cart-specs). Keep each spec focused so tickets can reference exactly what they need.
- **Include:** Purpose, scope (in/out), design intent, constraints (React-only, brand tokens, performance), and success criteria that tickets can inherit.
- **Don’t** turn a spec into a task list; leave concrete steps to tickets.

### Tickets
- **One ticket per logical change** (or 1–3 tightly related changes). Split “footer + header + products page” into separate tickets.
- **Reference the spec by name** in Reference Docs so constraints and intent are clear.
- **Use stepwise Instructions** (1. Locate X. 2. Inspect Y. 3. Update Z. 4. Verify.) so Claude has a clear path and doesn’t wander.
- **Done Criteria = verifiable:** “In devtools, footer background is …” or “Only these files were modified.” Avoid “looks good” without a concrete check.
- **Mandate skills** for all tasks, be sure to recommend applicable skills and encourage Claude to use as many as he needs to complete the tickets to the highest quality possible. 

