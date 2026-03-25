# Caliper (quant) — Progress

Tracks versions, milestones, sprints, and completed work across the project lifespan. Update this doc when completing sprints or shipping releases to maintain a clear record of progress. Completed work should be logged with dates, context, and links to supporting specs or tickets.

---

## Version scheme (optional)

Use this section if your project follows semantic versioning. Define what major/minor/patch versions mean in your context.

| Level | Meaning | Example |
|-------|---------|---------|
| **Major (X.0.0)** | Significant milestones; new product phase or major architectural shift | v2.0.0 = New feature tier complete |
| **Minor (1.X.0)** | Feature or structural work; new surfaces, specs, or integration | v1.3.0 = User dashboard complete |
| **Patch (1.0.X)** | Smaller fixes, polish, adjustments; keep patch numbers usually `<= 15` by grouping related work | v1.2.3 = Bug fixes and UI polish |

---

## Status lifecycle (milestone order)

Milestones progress through this sequence:

1. **Not started** — Item referenced in roadmap; minimal or no documentation yet.
2. **Concept** — Initial design doc or concept file created.
3. **Spec** — Detailed specification written with requirements and scope.
4. **Tickets** — Work broken into tickets or tasks per spec.
5. **In progress** — Implementation or development underway.
6. **Done** — Complete, merged, and shipped or deployed.

---

## Milestones and sprints

Track major work blocks, features, and versions in this table.

| Version | Milestone / sprint | Status | Completed | Remaining | Spec / plan | Summary / notes |
|---------|-------|--------|-----------|-----------|-------|---------|
| **v1.0.0** | **Sprint 1: Infrastructure & Data** | Done | 2026-02-02 | 0 | `plans/task_plan.md` | `plans/SPRINT1_SUMMARY.md` |
| **v1.1.0** | **Sprint 2: Feature Pipeline & Strategy Core** | Done | 2026-02-02 | 0 | `plans/task_plan.md` | `plans/SPRINT2_SUMMARY.md` |
| **v1.2.0** | **Sprint 3: Backtesting & Reporting** | Done | 2026-02-02 | 0 | `plans/task_plan.md` | `plans/SPRINT3_SUMMARY.md` |
| **v1.3.0** | **Sprint 4: Dashboard & API** | Done | 2026-02-02 | 0 | `plans/task_plan.md` | `plans/SPRINT4_SUMMARY.md` |
| **v1.4.0** | **Sprint 5: Execution & Risk** | Done | 2026-02-02 | 0 | `plans/task_plan.md` | `plans/SPRINT5_SUMMARY.md` |
| **v1.5.0** | **Sprint 6: ML Safety & Interpretability** | Done | 2026-02-02 | 0 | `plans/task_plan.md` | `plans/SPRINT6_SUMMARY.md` |
| **v1.6.0** | **Sprint 7: First ML model end-to-end** | Done | 2026-02-02 | 0 | `docs/plans/specs/sprint-7-first-ml-model-spec.md` | `docs/SPRINTS-7-8-9-SUMMARY.md` |
| **v1.7.0** | **Sprint 8: ML observability, safety, and evaluation** | Done | 2026-02-02 | 0 | `docs/plans/specs/sprint-8-observability-safety-spec.md` | `docs/SPRINT-8-COMPLETE.md` |
| **v1.8.0** | **Sprint 9: Model observatory dashboard** | Done | 2026-02-02 | 0 | `docs/plans/specs/sprint-9-model-observatory-dashboard-spec.md` | `docs/SPRINT-9-COMPLETE.md` |

**Status progression:** Not started → Concept → Spec → Tickets → In progress → Done. Keep minor versions `<= 10`; group related patches to keep patch versions usually `<= 15`.

---

## Patch-level completed work (non-sprint)

Log smaller fixes, UI tweaks, docs updates, or tooling improvements here—work below sprint scope.

| Version | Patch work item | Completed | Area | Notes / reference |
|---------|---|-----------|------|---------|
| **v1.8.1** | Install workflow-core suite (docs/workflow + PROGRESS) | 2026-03-25 | Docs / workflow | Adds bounded ticket workflow, execution rules, and progress log |
| **v1.8.2** | Tighten workflow routing to match real repo paths and skills | 2026-03-25 | Docs / workflow | Adds `docs/INDEX.md`, repo-accurate task routing, and stronger skill mapping |

---

## Planned / in-progress (backlog)

Items discussed or spec'd but not yet fully implemented. Track deferred features, future phases, and known gaps here.

| Type | Item | Source / reference | Notes |
|------|------|---------|---------|
| **Future phase** | Iterate on model-centric dashboard and ML evaluation | `plans/progress.md` | Tracker marks Sprints 7-9 complete and points to continued iteration |
| **Fix / patch** | Render API server issue | `docs/render-api-server-issue.md` | Existing issue doc suggests deployment/runtime follow-up work |

---

## How to update this doc

1. **Starting a new milestone/sprint:** Create a row in **Milestones and sprints** with version, name, and "Not started" status. Link to any concept or design docs.

2. **Advancing milestone lifecycle:** Update the **Status** column as work progresses (Not started → Concept → Spec → Tickets → In progress → Done).

3. **Completing a sprint or milestone:** Set Status to **Done**, add the **Completed** date, set **Remaining** to 0 (or note deferred items), and link summary or ticket references.

4. **Logging patch/small work:** Add a row to **Patch-level completed work** with version, date, area, and brief notes. Group related fixes; keep patch versions usually `<= 15`.

5. **Tracking deferred or future work:** Add or update rows in **Planned / in-progress (backlog)**. Remove items once they move to milestone tracking.

6. **Adding specs or summaries:** If defining new milestone scope, update **Milestones and sprints** and link the spec. Add a note in **How to update** if adding new sections.

---

## Index (optional)

If your project maintains linked specs, summaries, or concept docs, index them here to keep PROGRESS.md as a hub.

### Specs (`docs/plans/specs/`)

| Spec | Description |
|------|-----|
| [Sprint 7: First ML model](docs/plans/specs/sprint-7-first-ml-model-spec.md) | First ML model end-to-end loop |
| [Sprint 8: Observability & safety](docs/plans/specs/sprint-8-observability-safety-spec.md) | Drift/health, baselines, explainability wiring |
| [Sprint 9: Model dashboard](docs/plans/specs/sprint-9-model-observatory-dashboard-spec.md) | Model registry + detail views + comparisons |

### Tickets (`docs/plans/tickets/`)

| Ticket set | Scope |
|---------|-------|
| `docs/plans/tickets/07-*` | Sprint 7 ML model tickets |
| `docs/plans/tickets/08-*` | Sprint 8 observability/safety tickets |
| `docs/plans/tickets/09-*` | Sprint 9 model dashboard tickets |

### Summaries (`plans/` and `docs/`)

| Summary | Scope |
|---------|-------|
| `plans/SPRINT1_SUMMARY.md` | Sprint 1 summary |
| `plans/SPRINT2_SUMMARY.md` | Sprint 2 summary |
| `plans/SPRINT3_SUMMARY.md` | Sprint 3 summary |
| `plans/SPRINT4_SUMMARY.md` | Sprint 4 summary |
| `plans/SPRINT5_SUMMARY.md` | Sprint 5 summary |
| `plans/SPRINT6_SUMMARY.md` | Sprint 6 summary |
| `docs/SPRINTS-7-8-9-SUMMARY.md` | Cross-sprint summary for Sprints 7-9 |
| `docs/SPRINT-8-COMPLETE.md` | Sprint 8 completion notes |
| `docs/SPRINT-9-COMPLETE.md` | Sprint 9 completion notes |
