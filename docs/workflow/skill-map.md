# Skill map — Layer 1: Workflow Process Skills

Skills are a **routing layer**, not "load the encyclopedia." The ticket names the exact skill(s) to invoke. Do not load any skills unless the ticket lists them.

**For domain skills and project-specific skills (Layers 2 & 3), see `task-type-reference-map.md`** — the "Skills" column for each task type lists the domain skills to invoke, and the `[PROJECT-SPECIFIC]` section lists project-specific skills and their associated docs.

---

## Layer 1: Core workflow process skills

"How we work" patterns. These are triggered by the **type of workflow event** you're in (planning, debugging, reviewing), not by the code domain.

| When | Skill | Description |
|------|-------|-------------|
| Starting a multi-step feature or sprint | `writing-plans` | Plan before code. Write a spec or implementation plan. |
| Clarifying requirements or design | `brainstorming` | Explore user intent, options, and design before implementation. |
| Executing a written implementation plan | `executing-plans` or `subagent-driven-development` | Follow the plan; checkpoint with review. |
| Implementing a feature or bugfix with tests | `test-driven-development` | Tests before implementation. |
| Any bug or test failure | `systematic-debugging` | Use before proposing any fix. |
| Before claiming work complete or merging | `verification-before-completion` | Verify against ticket criteria and user-requested checks only. |
| Completing a major feature or pre-merge | `requesting-code-review` | Request review; show evidence. |
| Responding to code review feedback | `receiving-code-review` | Verify feedback before implementing; don't blindly apply suggestions. |
| Creating or editing Cursor rules or AGENTS.md | `create-rule` | Follow the rule-writing workflow. |
| Creating or editing agent skills | `writing-skills` | Follow the skill-writing workflow. |

---

## Layer 2: Workflow management skills

These are process-level skills for managing work at the git/branch level. They don't fit into code task types, so they live here rather than in `task-type-reference-map.md`.

| When | Skill |
|------|-------|
| Starting feature work that needs isolation | `using-git-worktrees` |
| Implementation is complete and ready to integrate | `finishing-a-development-branch` |
| Running multiple independent tasks in parallel | `dispatching-parallel-agents` |

---

## Common domain skills for Caliper

These are not auto-loaded. Reference them from tickets or from `task-type-reference-map.md` when the task type calls for them.

| Task area | Recommended skills |
|------|-------|
| FastAPI / Python services / shared contracts | `backend-dev-guidelines` |
| Next.js dashboard implementation | `frontend-design`, `react-best-practices` |
| Dense dashboard UX, charts, operational clarity | `ui-ux-pro-max` |
| Mobile-first monitoring views | `mobile-design` |
| Browser-based dashboard testing | `webapp-testing` |
| Copy / help / glossary / user-facing messaging | `copywriting` |

---

## Usage rules

- **Ticket names the pack(s):** 0–2 core skills per ticket. 0–2 domain skills (from task-type-reference-map). Project-specific only if ticket says so.
- **Small task:** 0–1 skills. **Medium:** 1–3. **Large:** 3–5 max.
- **If no skill fits the situation:** Proceed without invoking any. This map is for optional leverage, not a checklist.
- **Domain and project-specific skills** are in `task-type-reference-map.md` — look there for "which skill to use for this type of code task."
