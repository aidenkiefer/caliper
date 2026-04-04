# Caliper (quant) — Progress

Tracks versions, milestones, sprints, and completed work across the project lifespan. Update this doc when completing sprints or shipping releases to maintain a clear record of progress. Completed work should be logged with dates, context, and links to supporting specs or tickets.

---

## Version scheme (optional)

Use this section if your project follows semantic versioning. Define what major/minor/patch versions mean in your context.


| Level             | Meaning                                                                                         | Example                            |
| ----------------- | ----------------------------------------------------------------------------------------------- | ---------------------------------- |
| **Major (X.0.0)** | Significant milestones; new product phase or major architectural shift                          | v2.0.0 = New feature tier complete |
| **Minor (1.X.0)** | Feature or structural work; new surfaces, specs, or integration                                 | v1.3.0 = User dashboard complete   |
| **Patch (1.0.X)** | Smaller fixes, polish, adjustments; keep patch numbers usually `<= 15` by grouping related work | v1.2.3 = Bug fixes and UI polish   |


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


| Version    | Milestone / sprint                                     | Status | Completed  | Remaining | Spec / plan                                                     | Summary / notes                                |
| ---------- | ------------------------------------------------------ | ------ | ---------- | --------- | --------------------------------------------------------------- | ---------------------------------------------- |
| **v1.0.0** | **Sprint 1: Infrastructure & Data**                    | Done   | 2026-02-02 | 0         | `docs/plans/task_plan.md`                                       | `docs/plans/summaries/SPRINT1_SUMMARY.md`      |
| **v1.1.0** | **Sprint 2: Feature Pipeline & Strategy Core**         | Done   | 2026-02-02 | 0         | `docs/plans/task_plan.md`                                       | `docs/plans/summaries/SPRINT2_SUMMARY.md`      |
| **v1.2.0** | **Sprint 3: Backtesting & Reporting**                  | Done   | 2026-02-02 | 0         | `docs/plans/task_plan.md`                                       | `docs/plans/summaries/SPRINT3_SUMMARY.md`      |
| **v1.3.0** | **Sprint 4: Dashboard & API**                          | Done   | 2026-02-02 | 0         | `docs/plans/task_plan.md`                                       | `docs/plans/summaries/SPRINT4_SUMMARY.md`      |
| **v1.4.0** | **Sprint 5: Execution & Risk**                         | Done   | 2026-02-02 | 0         | `docs/plans/task_plan.md`                                       | `docs/plans/summaries/SPRINT5_SUMMARY.md`      |
| **v1.5.0** | **Sprint 6: ML Safety & Interpretability**             | Done   | 2026-02-02 | 0         | `docs/plans/task_plan.md`                                       | `docs/plans/summaries/SPRINT6_SUMMARY.md`      |
| **v1.6.0** | **Sprint 7: First ML model end-to-end**                | Done   | 2026-02-02 | 0         | `docs/plans/specs/sprint-7-first-ml-model-spec.md`              | `docs/SPRINTS-7-8-9-SUMMARY.md`                |
| **v1.7.0** | **Sprint 8: ML observability, safety, and evaluation** | Done   | 2026-02-02 | 0         | `docs/plans/specs/sprint-8-observability-safety-spec.md`        | `docs/SPRINT-8-COMPLETE.md`                    |
| **v1.8.0** | **Sprint 9: Model observatory dashboard**              | Done   | 2026-02-02 | 0         | `docs/plans/specs/sprint-9-model-observatory-dashboard-spec.md` | `docs/SPRINT-9-COMPLETE.md`                    |
| **v2.0.0** | **Sprint 10: Polymarket BTC market-making**            | Done   | 2026-03-25 | 0         | `docs/plans/specs/polymarket-btc-trading-spec.md`               | `docs/plans/summaries/SPRINT-10-POLYMARKET-COMPLETE.md` (see also `docs/plans/POLYMARKET-TICKETS-1-5-SUMMARY.md`) |


**Status progression:** Not started → Concept → Spec → Tickets → In progress → Done. Keep minor versions `<= 10`; group related patches to keep patch versions usually `<= 15`.

---

## Patch-level completed work (non-sprint)

Log smaller fixes, UI tweaks, docs updates, or tooling improvements here—work below sprint scope.


| Version       | Patch work item                                                                               | Completed  | Area               | Notes / reference                                                                |
| ------------- | --------------------------------------------------------------------------------------------- | ---------- | ------------------ | -------------------------------------------------------------------------------- |
| **v1.8.1**    | Install workflow-core suite (docs/workflow + PROGRESS)                                        | 2026-03-25 | Docs / workflow    | Adds bounded ticket workflow, execution rules, and progress log                  |
| **v1.8.2**    | Tighten workflow routing to match real repo paths and skills                                  | 2026-03-25 | Docs / workflow    | Adds `docs/INDEX.md`, repo-accurate task routing, and stronger skill mapping     |
| **v2.0.0-p1** | Polymarket tickets 1-5: scaffolding, Gamma/CLOB/Binance clients, wallet management            | 2026-03-25 | Polymarket service | `docs/plans/tickets/10-01` through `10-05`; 15 new files, 55+ unit tests         |
| **v2.0.0-p2** | Polymarket tickets 6-10: DB migration, fee model, market discovery, data feed, quoting engine | 2026-03-25 | Polymarket service | `docs/plans/tickets/10-06` through `10-10`; 9 new files, 70+ unit tests          |
| **v2.0.0-p3** | Polymarket tickets 11-15: executor, safety layer, recorder, session orchestrator, CLI         | 2026-03-25 | Polymarket service | `docs/plans/tickets/10-11` through `10-15`; 8 new files, 50+ tests               |
| **v2.0.0-p4** | Polymarket tickets 16-20: shared schemas, API router, data API client, integration test, docs | 2026-03-25 | Polymarket service | `docs/plans/tickets/10-16` through `10-20`; 10 new files, complete documentation |
| **v2.0.0-p5** | Project docs: README, `docs/INDEX.md`, `docs/FEATURES.md`, `docs/plans/README.md` aligned with Sprint 10 | 2026-04-03 | Docs | Cross-links to spec, summary, quickstart, operations runbook |
| **v2.1.0-p1** | Sprint 12 ticket 12-01: `FeatureSnapshot` + `FeatureRecord` schemas; `services/features/polymarket/` scaffold | 2026-04-04 | Features / schemas | Adds 4-family feature snapshot, DB record wrapper, `SourceTimestamps` dataclass |
| **v2.1.0-p2** | Sprint 12 ticket 12-02: `CLOBSource` async data source with WebSocket buffer, REST recovery, reward config, fee rate, heartbeat loop | 2026-04-04 | Features / data sources | `services/features/polymarket/sources/clob.py` + `sources/__init__.py`; `DataUnavailable`, `OrderbookState`, `RewardConfig` |
| **v2.1.0-p3** | Sprint 12 ticket 12-03: `BinanceSource` async data source; polls 1m klines (60-bar rolling buffer) and perpetual futures premium index | 2026-04-04 | Features / data sources | `services/features/polymarket/sources/binance.py` + `sources/__init__.py`; `KlineBar`, `PremiumIndex` exported |
| **v2.1.0-p4** | Sprint 12 ticket 12-05: DB migration for `pm.features` TimescaleDB hypertable | 2026-04-04 | Database / migrations | `services/data/alembic/versions/003_create_pm_features_hypertable.py` with JSONB feature storage and (market_id, captured_at DESC) index |
| **v2.1.0-p5** | Sprint 12 ticket 12-04: `FeatureBuilder` with all 4 feature families (market state, microstructure, probabilistic, regime) | 2026-04-04 | Features / builder | `services/features/polymarket/builder.py`; 5s tick loop, `asyncio.Queue` output, `_trade_tape` deque, minimum-hold regime filter, staleness flag |
| **v2.1.0-p6** | Sprint 12 ticket 12-06: `FeatureStore` asyncpg read/write for `pm.features` hypertable | 2026-04-04 | Features / store | `services/features/polymarket/store.py`; `write`, `read_latest`, `read_window`, `FeatureStoreError`; exported from `services/features/polymarket/__init__.py` |
| **v2.1.0-p7** | Sprint 12 ticket 12-07: Session integration — `FeatureBuilder` wired into `SessionOrchestrator`; `PolymarketMMStrategy.on_market_data` accepts `Union[FeatureSnapshot, Any]` | 2026-04-04 | Features / session | `services/polymarket/session.py` step 4b startup + `_feature_consumer` coroutine + step 8b shutdown; `packages/strategies/polymarket_mm_strategy.py` near_close_flag + liquidity_score suppression gates; optional `FeatureStore` behind `DB_URL` env var |
| **v2.2.0-p2** | Sprint 12 ticket 12-08: features API router | 2026-04-04 | API | `services/api/routers/features.py`; `GET /v1/features/{market_id}/latest` (404 if none) and `GET /v1/features/{market_id}/history` (start/end/limit, 422 on invalid range, 503 if DB_URL unset); registered in `services/api/main.py` |
| **v2.2.0-p3** | Sprint 12 ticket 12-09: unit tests for feature layer | 2026-04-04 | Tests | `tests/unit/features/`: 4 test modules covering all formula families, Pydantic schema validation, FeatureStore asyncpg mock read/write, and regime discretization + minimum-hold filter; 60+ explicit numeric assertions |


---

## Planned / in-progress (backlog)

Items discussed or spec'd but not yet fully implemented. Track deferred features, future phases, and known gaps here.


| Type             | Item                                                 | Source / reference                | Notes                                                                |
| ---------------- | ---------------------------------------------------- | --------------------------------- | -------------------------------------------------------------------- |
| **Future phase** | Iterate on model-centric dashboard and ML evaluation | `docs/plans/DETAILED-SPRINT-PROGRESS.md` | Long-form sprint checklists; see also backlog below |
| **Future phase** | Polymarket Phase 2+ (inventory skew, dynamic spread, hybrid model) | `docs/plans/specs/polymarket-btc-trading-spec.md` §10 | V1 complete; tune from `pm.*` data before funded scale-up |
| **Fix / patch**  | Render API server issue                              | `docs/render-api-server-issue.md` | Existing issue doc suggests deployment/runtime follow-up work        |


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


| Spec                                                                                       | Description                                    |
| ------------------------------------------------------------------------------------------ | ---------------------------------------------- |
| [Sprint 7: First ML model](docs/plans/specs/sprint-7-first-ml-model-spec.md)               | First ML model end-to-end loop                 |
| [Sprint 8: Observability & safety](docs/plans/specs/sprint-8-observability-safety-spec.md) | Drift/health, baselines, explainability wiring |
| [Sprint 9: Model dashboard](docs/plans/specs/sprint-9-model-observatory-dashboard-spec.md) | Model registry + detail views + comparisons    |
| [Sprint 10: Polymarket BTC market-making](docs/plans/specs/polymarket-btc-trading-spec.md) | Hourly BTC binary market-making on Polymarket  |


### Tickets (`docs/plans/tickets/`)


| Ticket set                | Scope                                      |
| ------------------------- | ------------------------------------------ |
| `docs/plans/tickets/07-`* | Sprint 7 ML model tickets                  |
| `docs/plans/tickets/08-*` | Sprint 8 observability/safety tickets      |
| `docs/plans/tickets/09-*` | Sprint 9 model dashboard tickets           |
| `docs/plans/tickets/10-*` | Sprint 10 Polymarket market-making tickets |


### Summaries (`docs/plans/` and `docs/`)


| Summary                                                 | Scope                                         |
| ------------------------------------------------------- | --------------------------------------------- |
| `docs/plans/summaries/SPRINT1_SUMMARY.md`               | Sprint 1 summary                              |
| `docs/plans/summaries/SPRINT2_SUMMARY.md`               | Sprint 2 summary                              |
| `docs/plans/summaries/SPRINT3_SUMMARY.md`               | Sprint 3 summary                              |
| `docs/plans/summaries/SPRINT4_SUMMARY.md`               | Sprint 4 summary                              |
| `docs/plans/summaries/SPRINT5_SUMMARY.md`               | Sprint 5 summary                              |
| `docs/plans/summaries/SPRINT6_SUMMARY.md`               | Sprint 6 summary                              |
| `docs/SPRINTS-7-8-9-SUMMARY.md`                         | Cross-sprint summary for Sprints 7-9          |
| `docs/SPRINT-8-COMPLETE.md`                             | Sprint 8 completion notes                     |
| `docs/SPRINT-9-COMPLETE.md`                             | Sprint 9 completion notes                     |
| `docs/plans/POLYMARKET-TICKETS-1-5-SUMMARY.md`          | Sprint 10 tickets 1-5 completion notes        |
| `docs/plans/summaries/SPRINT-10-POLYMARKET-COMPLETE.md` | Sprint 10 complete (all 20 tickets, runbook) |

### Runbooks (`docs/runbooks/`)

| Runbook                                   | Purpose                                        |
| ----------------------------------------- | ---------------------------------------------- |
| `docs/runbooks/polymarket-operations.md` | Complete operations guide for Polymarket bot |


