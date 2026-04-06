# Sprint 13: Simulation + Evaluation Engine — Ticket Index

**Feature spec:** `docs/plans/specs/sprint-13-simulation-evaluation-spec.md`
**Research sources:** `docs/research/backtesting-simulation.md`
**Version:** v2.3.0  
**Total tickets:** 13  
**Status:** All tickets **Done** (merged to `main`, 2026-04-05).

---

## Ticket dependency graph

```
Layer 1 (no dependencies):
├─ 13-01 Schemas
└─ 13-11 DB migration

Layer 2 (depends on 13-01):
├─ 13-02 Order book + unit tests    (→ 13-01)
├─ 13-03 Fee engine + unit tests    (→ 13-01)
├─ 13-04 Execution simulator        (→ 13-01, 13-02)
└─ 13-05 Adverse selection          (→ 13-01)

Layer 3 (depends on Layer 2):
└─ 13-06 Event loader               (→ 13-01)

Layer 4 (depends on Layer 3):
└─ 13-07 Replay engine + Runner     (→ 13-01, 13-02, 13-03, 13-04, 13-05, 13-06)

Layer 5 (depends on Layer 4):
├─ 13-08 Validation layer           (→ 13-07)
└─ 13-09 Evaluation engine + tests  (→ 13-01, 13-07)

Layer 6 (depends on Layer 5):
├─ 13-10 Baselines                  (→ 13-09)
└─ 13-12 API endpoints              (→ 13-07, 13-09, 13-11)

Layer 7 (testing):
└─ 13-13 Integration test           (→ 13-07, 13-09)
```

---

## Ticket list

| #     | Name                          | Dependencies                              | Status |
|-------|-------------------------------|-------------------------------------------|--------|
| 13-01 | Schemas                       | None                                      | Done   |
| 13-02 | Order book + unit tests       | 13-01                                     | Done   |
| 13-03 | Fee engine + unit tests       | 13-01                                     | Done   |
| 13-04 | Execution simulator           | 13-01, 13-02                              | Done   |
| 13-05 | Adverse selection + tests     | 13-01                                     | Done   |
| 13-06 | Event loader                  | 13-01                                     | Done   |
| 13-07 | Replay engine + SimRunner     | 13-01–13-06                               | Done   |
| 13-08 | Validation layer              | 13-07                                     | Done   |
| 13-09 | Evaluation engine + tests     | 13-01, 13-07                              | Done   |
| 13-10 | Baselines                     | 13-09                                     | Done   |
| 13-11 | DB migration                  | None                                      | Done   |
| 13-12 | API endpoints                 | 13-07, 13-09, 13-11                       | Done   |
| 13-13 | Integration test              | 13-07, 13-09                              | Done   |

---

## Directory layout produced

```
services/simulation/
├── __init__.py
├── schemas.py
├── replay/
│   ├── __init__.py
│   ├── engine.py
│   └── loader.py
├── orderbook/
│   ├── __init__.py
│   ├── book.py
│   └── matching.py
├── execution/
│   ├── __init__.py
│   ├── simulator.py
│   └── fee_engine.py
├── adverse/
│   ├── __init__.py
│   └── selection.py
└── runner.py

services/evaluation/
├── __init__.py
├── metrics.py
├── baselines.py
├── regime_matrix.py
├── report.py
└── schemas.py

services/api/routers/simulation.py

services/data/alembic/versions/004_create_simulation_evaluation_tables.py

tests/unit/simulation/
├── __init__.py
├── test_orderbook.py
├── test_fee_engine.py
└── test_adverse_selection.py

tests/unit/evaluation/
├── __init__.py
└── test_metrics.py

tests/integration/simulation/
├── __init__.py
└── test_simulation_pipeline.py
```

---

## Acceptance criteria cross-reference

| AC   | Ticket(s)        | Description |
|------|------------------|-------------|
| AC-1 | 13-07, 13-13     | Determinism: byte-identical SimResult on same input |
| AC-2 | 13-02            | Order book: taker matching, post-only rejection, partial fills |
| AC-3 | 13-03            | Fee accuracy: both regimes, maker rebate |
| AC-4 | 13-05            | Adverse selection: PnL lower with peak_informed=0.40 near close |
| AC-5 | 13-08            | Validation: fill rate within 10% of actual |
| AC-6 | 13-09            | Evaluation: correct Sharpe/Sortino/Calmar for known PnL series |
| AC-7 | 13-09            | Rolling window: <20 days → confidence=low flag |
| AC-8 | 13-12            | API: all endpoints return valid JSON with correct schemas |
| AC-9 | 13-02, 13-03, 13-09, 13-13 | Tests: unit + integration |

---

## Notes

- **New services:** `services/simulation/` and `services/evaluation/` are brand new — do not touch existing `services/backtest/` (equity backtesting)
- **Fee regime boundary:** FeeEngine keyed on market creation date AND current date (not just current date)
- **Determinism:** SimulationRunner must produce byte-identical output on identical input — no `time.time()`, `random.random()`, or other non-deterministic calls without a seed
- **Decimal precision:** Use `Decimal` for all financial arithmetic (prices, sizes, fees, PnL)
- **Regime slice:** RegimeMetrics uses `FeatureSnapshot` labels from Sprint 12 (`vol_regime`, `toxicity_regime`, `near_close_flag`, `time_bucket`, `spread_regime`)
- **Progress tracking:** Each ticket updates `docs/plans/PROGRESS.md` on completion
