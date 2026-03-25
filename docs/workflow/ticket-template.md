# Ticket template (bounded agentic runs)

Tickets act as **budgeted jobs**. Use this structure so runs stay bounded and context stays small. Copy into a task description or Cursor/Claude chat.

---

## Template

```markdown
# Ticket: NN-short-name

## Task
One sentence describing the change.

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- exact file paths or globs

If the relevant code lives elsewhere: STOP and ask to expand Allowed Files.

### Required read-only references
- Must-read docs for this task (load first; 1–2 max)
- Example: docs/plans/specs/feature-spec.md

### Optional read-only references
- Read only if relevant or within budget
- Example: docs/DESIGN_GUIDELINES.md (if doing UI work)

### Example files (read-only, optional)
- Reference implementations or patterns to use as examples
- Example: apps/store/src/components/ProductCard.tsx (read-only pattern)

## Agent type (optional)
- One of: frontend-agent, backend-agent, copywriting-agent, debugging-agent, docs-agent, security-agent
- Or a project-specific type from task-type-reference-map.md
- If omitted: infer from task type

## Skill pack (optional, keep small)
- Required: 0–2 core skills (from skill-map.md Layer 1)
- Optional: 0–2 domain skills (from task-type-reference-map.md "Skills" column)
- Do not load any other skills.

## Context + tool budget
- Max file reads: 8
- Max grep/glob operations: 6
- Max total tool calls: 12
If you will exceed a budget, stop and ask.

## Done criteria
- What must be true in the code after the change (verifiable statements).
- List of files modified (exact paths).
- docs/plans/PROGRESS.md updated with a brief dated completion note.
```

---

## Notes

- **Shorter ticket = cheaper run.** Omit guardrails already in CLAUDE.md or execution-rules.md.
- **Required vs optional references:** Required = load first, always. Optional = load only if directly relevant or within budget. Keep required to 1–2 docs max.
- **Example files:** Useful for pattern-matching (e.g., "implement this the same way as X"). Always read-only.
- **Agent type:** Triggers a pre-defined reference bundle from `task-type-reference-map.md`. Saves token cost vs listing all refs manually for known task types.
- **Skill pack:** Ticket names the exact skills allowed. Use `skill-map.md` Layer 1 for workflow process skills; use `task-type-reference-map.md` "Skills" column for domain skills.
- **Budgets:** Before acting, estimate whether you can complete within budgets. If not, stop and ask for a narrower ticket or expanded budgets.
- **Sprint history:** Do not embed full sprint history in tickets. Current sprint pointer lives in CLAUDE.md; historical summaries in `docs/plans/summaries/` when needed.
- **Completion logging:** Keep progress entries concise (1–3 bullets) and include small fixes, not just major milestones.
