# Sprint 15: Regime detection + dynamic allocation — summary

**Version:** v2.5.0  
**Status:** Complete (merged to `main`, 2026-04-06)  
**Spec:** [sprint-15-regime-allocation-spec.md](../specs/sprint-15-regime-allocation-spec.md)  
**Tickets:** [15-00-INDEX.md](../tickets/15-00-INDEX.md)

## What shipped

- **`services/regime/`** — **`schemas`** (`RegimeState`, regime labels **R1–R5**); **threshold** rule-based classifier; **HMM** classifier (`classifiers/hmm.py`); **detector** orchestration; **quality** checks; optional **trainer** hooks; **`RegimeStore`** asyncpg reads/writes for persistence.
- **`services/allocation/`** — **`schemas`** (`AllocationDecision`, `PerformanceMatrix`, weights); **performance matrix** builder/updater; allocation **engine** with **risk parity**, **HRP**, and **bounded Kelly** method modules; **regime-specific risk layer**; **`AllocationDecisionStore`** / matrix store for **`pm.*`**.
- **Database** — Alembic **`006_create_regime_allocation_tables.py`**: **`pm.regime_states`**, **`pm.allocation_decisions`**, **`pm.performance_matrices`** (hypertables/indexes per migration).
- **API** — `services/api/routers/regime.py` under **`/v1`**: **`GET /v1/regime/current`**, **`GET /v1/regime/{market_id}/current`**, **`GET /v1/regime/history`**, **`GET /v1/allocation/current`**, **`GET /v1/allocation/history`**, **`GET /v1/allocation/performance-matrix`**. When **`DB_URL`** is set, handlers read **live rows** from the stores; missing “current” rows may yield **404**.

## Boundaries

- **Equity OMS / Alpaca** is unchanged; this sprint targets the **Polymarket research + fleet** stack and shared **`pm.*`** analytics.
- **Sprint 16** consumes regime + allocation outputs in the **paper fleet orchestrator**; wiring from writers (detector/allocation jobs) into DB is separate from the read-only API surface.

## References

- **Milestone / patches:** [PROGRESS.md](../PROGRESS.md) (`v2.5.0` row).
- **API vs Sprint 16:** [api-contracts.md](../../api-contracts.md) — **Sprint 15 vs 16** implementation note.
- **Shapes:** `services/regime/schemas.py`, `services/allocation/schemas.py`.
