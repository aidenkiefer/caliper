# Sprint 16: Cross-sectional ranking + model fleet — summary

**Version:** v2.6.0  
**Status:** Complete (merged to `main`, 2026-04-06). **HTTP layer for ranking/fleet is mock-backed** until handlers call **`MarketRanker`**, **`PaperTradeStore`**, and orchestrator state — see backlog in [PROGRESS.md](../PROGRESS.md) and [api-contracts.md](../../api-contracts.md).  
**Spec:** [sprint-16-cross-sectional-fleet-spec.md](../specs/sprint-16-cross-sectional-fleet-spec.md)  
**Tickets:** [16-00-INDEX.md](../tickets/16-00-INDEX.md) (`16-01`–`16-13`)

## What shipped

- **`services/ranking/`** — **`UniverseBuilder`** (Gamma-oriented filters), **`EdgeEstimator`** (EV-adjusted edge), **`FeasibilityScorer`**, composite **`RankingScore`**, **`MarketRanker`** (selection + cooldown), Pydantic **`schemas`** (`CandidateMarket`, `RankedUniverse`, etc.); unit tests under `tests/unit/ranking/`.
- **`services/fleet/`** — **`FleetOrchestrator`** (paper-mode event loop), **`registry`** (loads Sprint 16 strategies by id), **`PaperTradeStore`** (asyncpg) for **`pm.paper_trades`**, fleet **`schemas`**; integration tests under `tests/integration/fleet/`.
- **`packages/strategies/`** — Fleet strategies: e.g. **`poly_mm_v2`**, **`poly_regime_v1`**, directional probability consumer, hybrid maker — per spec/tickets (`poly_*_v1` family).
- **Database** — Alembic **`007_create_pm_paper_trades_table.py`**: **`pm.paper_trades`** for non-blocking orchestrator writes.
- **API** — `services/api/routers/ranking.py`, `services/api/routers/fleet.py`: **`GET /v1/ranking/current`**, **`GET /v1/fleet/status`**, **`GET /v1/fleet/signals`**, **`GET /v1/fleet/paper-trades`**. Routes require **`DB_URL`** (else **503**) but currently return **static mock JSON** matching Pydantic contracts.
- **Dashboard** — Panels under **`apps/dashboard/src/components/sprint-16/`** (ranker, fleet, regime timeline) calling the above endpoints.

## Deferred / follow-up (explicit)

- **Wire REST handlers** to **`MarketRanker.run`**, **`PaperTradeStore`**, and in-memory or live orchestrator snapshots so the dashboard shows real ranker output and paper-trade history.
- Optional: deepen integration with Sprint 14 **`p_hat`** and Sprint 15 regime/allocation streams inside the orchestrator tick (orchestrator code paths exist; HTTP aggregation is the main gap).

## Boundaries

- **Live Polymarket CLOB bot** remains **`services/polymarket/`**; the fleet is **paper-mode** research wiring unless explicitly connected to adapters.
- **Equity** strategies and **`services/backtest/`** are not replaced by the fleet loop.

## References

- **Progress / patches:** [PROGRESS.md](../PROGRESS.md) (`v2.6.0`, `v2.6.0-p1`, backlog row for API wiring).
- **API shapes:** `services/ranking/schemas.py`, `services/fleet/schemas.py`, [api-contracts.md](../../api-contracts.md).
