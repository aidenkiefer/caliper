# Sprint 13: Simulation + evaluation engine — summary

**Version:** v2.3.0  
**Status:** Complete (merged to `main`, 2026-04-05)  
**Spec:** [sprint-13-simulation-evaluation-spec.md](../specs/sprint-13-simulation-evaluation-spec.md)  
**Tickets:** [13-00-INDEX.md](../tickets/13-00-INDEX.md) (`13-01`–`13-13`)

## What shipped

- **`services/simulation/`** — Polymarket CLOB-oriented **replay** stack: Pydantic **`schemas`**, **order book** (matching, post-only, partial fills), **fee engine** (maker/taker regimes), **execution simulator** (latency, throttling, stale quotes), **adverse selection** model, **event loader**, **replay engine** + **`SimulationRunner`**, **validation** layer (sim vs observed fills), unit tests under `tests/unit/simulation/`.
- **`services/evaluation/`** — **Metrics** (Sharpe, Sortino, Calmar, drawdown, rolling-window confidence flags), **regime matrix** (slices using Sprint 12 **`FeatureSnapshot`** labels), **baselines** and **report** assembly, schemas; unit tests under `tests/unit/evaluation/`.
- **Persistence** — Alembic **`004_create_simulation_evaluation_tables.py`**: `pm.simulation_runs`, `pm.evaluation_reports`, `pm.simulation_validation` (and related indexes/constraints per migration).
- **API** — `services/api/routers/simulation.py` mounted under **`/v1`**: `POST /v1/simulation/run`, `GET /v1/simulation/{run_id}/result`, `GET /v1/evaluation/compare`, `GET /v1/evaluation/{strategy_id}/latest`, `GET /v1/evaluation/{strategy_id}/regimes`. **Today:** handlers use **stub** results / in-memory run state so response shapes match Pydantic models; wiring to DB + full **`SimulationRunner`** execution is a follow-up.
- **Integration tests** — `tests/integration/simulation/test_simulation_pipeline.py` (determinism, PnL components, Sharpe confidence, etc., per ticket **13-13**).

## Boundaries

- **Equity backtest** remains **`services/backtest/`**; this sprint does **not** replace it.
- **Polymarket live bot** remains **`services/polymarket/`**; simulation is for **offline replay / research** against stored CLOB-style events.

## References

- **Progress / patches:** [PROGRESS.md](../PROGRESS.md) (v2.3.0 row and `v2.3.0-p*` patch table).
- **API shapes:** `services/simulation/schemas.py`, `services/evaluation/schemas.py`, [api-contracts.md](../../api-contracts.md).
