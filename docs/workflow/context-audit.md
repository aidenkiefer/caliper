# Context Audit Guide

**Purpose:** Systematically verify that reference documents are accurate, consistent, complete, and up-to-date. Run quarterly or after major structural changes.

**For:** Humans and `docs-agent` executing audit tickets.

---

## When to Run an Audit

- **Quarterly:** Every 3 months as ongoing maintenance
- **After major changes:** New architecture, new integrations, renamed files, deprecated patterns
- **Before a major sprint:** Ensure reference docs are reliable before a high-cost sprint
- **When agents cite wrong paths or stale info:** Reactive trigger

---

## Audit Scope

Define the set of core reference documents to audit. Customize this list for your project.

### Standard workflow docs (always audit)

| Doc | Location |
|-----|----------|
| Project memory | `.claude/CLAUDE.md`, `CLAUDE.md` |
| Workflow entrypoint | `docs/workflow/workflow.md` |
| Execution rules | `docs/workflow/execution-rules.md` |
| Ticket template | `docs/workflow/ticket-template.md` |
| Skill map | `docs/workflow/skill-map.md` |
| Task-type reference map | `docs/workflow/task-type-reference-map.md` |
| Context flow | `docs/workflow/context-flow.md` |

### Project-specific reference docs (add your project's docs here)

| Doc | Location |
|---|---|
| Architecture doc | `docs/architecture.md` |
| Dashboard spec | `docs/dashboard-spec.md` |
| Design guide | `docs/design-guidelines.md` |
| API contracts | `docs/api-contracts.md` |
| Data contracts | `docs/data-contracts.md` |
| Risk policy | `docs/risk-policy.md` |
| Security | `docs/security.md` |
| Index / doc map | `docs/INDEX.md` |
| Progress log | `docs/plans/PROGRESS.md` |
| Planning / roadmap | `plans/progress.md` |
| Specs + tickets hub | `docs/plans/README.md` |
| Runbooks | `docs/runbooks/` |

---

## Audit Criteria

For each document, assess on five dimensions:

| Dimension | Questions to ask |
|-----------|-----------------|
| **Accuracy** | Does the content reflect the current state of the codebase? Are file paths, commands, and patterns still correct? |
| **Consistency** | Does this doc agree with other docs? Are there contradictions (e.g., two docs describe the same constraint differently)? |
| **Completeness** | Are there gaps — missing sections, undocumented patterns, or new features not yet covered? |
| **Clarity** | Is the doc understandable to an agent with no prior context? Are examples present where needed? |
| **Relevance** | Is all content still needed? Is anything obsolete, deprecated, or moved elsewhere? |

---

## Audit Process

### Step 1: Define scope

List the documents you will audit in this session. Aim for 10–25 docs. Prioritize docs that are:
- Heavily referenced in tickets
- Recently changed (may have introduced inconsistencies)
- Flagged as outdated in the previous audit

### Step 2: Read and assess each document

For each doc:
1. Read the full document
2. Compare to the actual codebase (spot-check key claims: file paths, commands, patterns)
3. Check for cross-reference consistency: do paths mentioned here match where files actually are?
4. Score each dimension: ✅ Sufficient / ⚠️ Needs Update / ❌ Missing or Broken

### Step 3: Check cross-references

For each document:
- Verify that all linked files exist at the stated paths
- Verify that all referenced commands still work
- Check if any files referenced here have been renamed, moved, or deleted

### Step 4: Identify issues and classify

Classify each issue:

| Issue Type | Description | Action |
|---|---|---|
| **Outdated content** | Doc describes patterns or paths that no longer exist | Update the doc |
| **Missing content** | A common task type or pattern is undocumented | Create or expand the doc |
| **Inconsistency** | Two docs contradict each other | Resolve — pick one authoritative source |
| **Broken link** | Referenced file doesn't exist at stated path | Fix the path or remove the reference |
| **Obsolete doc** | The entire doc is no longer needed | Archive or delete (with approval) |
| **Low clarity** | Doc is hard for an agent to parse or apply | Rewrite or add examples |

### Step 5: Prioritize and ticket

For each issue found, assign priority:
- **High:** Blocking or frequently-hit issue; fix this sprint
- **Medium:** Affects quality but not blocking; fix this quarter
- **Low:** Nice-to-have improvement; fix when convenient

Create tickets for High and Medium issues. Log Low issues in the audit results.

### Step 6: Write audit results

Write results to `docs/workflow/audits/audit-results-[YYYY-MM].md`. Use the template in the "Audit Results Template" section below.

---

## Audit Checklist Template

Use this for each document:

```markdown
### [Document Name]

- **Location:** [path]
- **Last updated:** [date or "unknown"]
- **Status:** ✅ Sufficient / ⚠️ Needs Update / ❌ Missing or Broken

**Accuracy:** [Notes — are file paths, commands, patterns still correct?]
**Consistency:** [Notes — does it agree with other docs?]
**Completeness:** [Notes — any gaps?]
**Clarity:** [Notes — understandable to an agent?]
**Relevance:** [Notes — any obsolete content?]

**Issues found:**
- [Issue 1 — priority: High/Medium/Low]
- [Issue 2]

**Recommended actions:**
- [Action 1]
- [Action 2]
```

---

## Audit Results Template

Save completed audits to `docs/workflow/audits/audit-results-[YYYY-MM].md`:

```markdown
# Context Audit Results — [Month YYYY]

**Date:** [YYYY-MM-DD]
**Auditor:** [Human / agent name]
**Scope:** [N] documents

## Summary

- ✅ Sufficient: [N] docs ([X]%)
- ⚠️ Needs Update: [N] docs ([X]%)
- ❌ Missing or Broken: [N] docs ([X]%)

## High-Priority Actions (complete this sprint)

1. [Action] — [Doc], [Issue description]
2. [Action] — [Doc], [Issue description]

## Medium-Priority Actions (complete this quarter)

1. [Action] — [Doc], [Issue description]

## Low-Priority Actions (ongoing)

1. [Action] — [Doc], [Issue description]

## Detailed Findings

[One section per document audited, using the checklist template above]

## Audit Strengths

[What's working well — good docs, consistent structure, clear constraints]

## Audit Opportunities

[Systemic improvements beyond individual doc fixes]
```

---

## Maintenance Schedule

| Cadence | Trigger | Scope |
|---------|---------|-------|
| **Quarterly** | Calendar (every 3 months) | Full audit of all core reference docs |
| **Post-major-change** | Architecture refactor, new integration, renamed files | Affected docs + cross-references |
| **Pre-sprint** | Before a high-cost sprint | Docs used by that sprint's tickets |
| **Ad hoc** | Agent cites wrong path or stale info | That doc + related docs |

---

## Common Issues and Fixes

### Outdated file paths

**Symptom:** Doc references `apps/store/src/lib/shopify.ts` but file is now at `lib/api/shopify.ts`.

**Fix:** Update the doc path. Run a quick grep to verify the new location.

### Terminology inconsistency

**Symptom:** One doc calls it "store app," another "Next.js app," another "React app."

**Fix:** Pick one canonical term. Do a global find/replace in docs.

### Duplicate content

**Symptom:** Two docs describe the same pattern (e.g., two design guides with overlapping content).

**Fix:** Identify which is authoritative. Update the other to reference it rather than duplicate.

### Missing examples

**Symptom:** Doc describes a pattern but no concrete example (file path, code snippet, ticket).

**Fix:** Add one real example from the codebase.

### Obsolete content

**Symptom:** Doc describes a feature or pattern that was removed (e.g., old auth flow, deprecated component).

**Fix:** Remove or archive the content. Add a one-line note: "Deprecated as of [date] — see [new doc]."

---

## Success Criteria

A successful audit results in:
- [ ] All High-priority issues ticketed and assigned
- [ ] All Medium-priority issues documented for the quarter
- [ ] At least one doc updated or corrected per audit session
- [ ] Audit results saved to `docs/workflow/audits/`
- [ ] `context-flow.md` updated if structural changes were found
- [ ] `docs/INDEX.md` updated if new or removed docs were found
- [ ] `docs/workflow/task-type-reference-map.md` updated if doc paths changed
```
