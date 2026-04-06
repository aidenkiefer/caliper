# Sprint 12: Feature Layer Unification — Ticket Index

**Feature spec:** `docs/plans/specs/sprint-12-feature-layer-spec.md`
**Research sources:** `docs/research/microstructure-model.md`, `docs/research/probabilities.md`, `docs/research/regime-allocation.md`
**Version:** v2.2.0
**Total tickets:** 10

---

## Ticket dependency graph

```
Layer 1 (no dependencies):
├─ 12-01 Schemas
├─ 12-05 DB migration
└─ (12-02 and 12-03 can start once 12-01 exists)

Layer 2 (depends on Layer 1):
├─ 12-02 CLOB data source      (→ 12-01)
└─ 12-03 Binance data source   (→ 12-01)

Layer 3 (depends on Layer 2):
└─ 12-04 Feature builder       (→ 12-01, 12-02, 12-03)

Layer 4 (depends on Layer 1 + migration):
└─ 12-06 Feature store         (→ 12-01, 12-05)

Layer 5 (depends on Layer 3 + 4):
├─ 12-07 Session integration   (→ 12-04, 12-06)
└─ 12-08 API router            (→ 12-06)

Layer 6 (testing — depends on all logic layers):
├─ 12-09 Unit tests            (→ 12-04)
└─ 12-10 Integration test      (→ 12-04, 12-06, 12-07)
```

---

## Ticket list

| #     | Name                  | Dependencies             | Est. time | Status      |
|-------|-----------------------|--------------------------|-----------|-------------|
| 12-01 | Schemas               | None                     | 30 min    | Not started |
| 12-02 | CLOB data source      | 12-01                    | 1.5 hours | Not started |
| 12-03 | Binance data source   | 12-01                    | 1 hour    | Not started |
| 12-04 | Feature builder       | 12-01, 12-02, 12-03      | 2.5 hours | Not started |
| 12-05 | DB migration          | None                     | 30 min    | Not started |
| 12-06 | Feature store         | 12-01, 12-05             | 1 hour    | Not started |
| 12-07 | Session integration   | 12-04, 12-06             | 1 hour    | Not started |
| 12-08 | API router            | 12-06                    | 45 min    | Not started |
| 12-09 | Unit tests            | 12-04                    | 2 hours   | Not started |
| 12-10 | Integration test      | 12-04, 12-06, 12-07      | 1.5 hours | Not started |

**Total estimated time:** ~12 hours

---

## Recommended build sequence

**Phase 1: Foundation (parallel)**
1. 12-01 (schemas) and 12-05 (migration) — no dependencies

**Phase 2: Data sources (parallel after 12-01)**
2. 12-02 (CLOB source) and 12-03 (Binance source)

**Phase 3: Feature builder (after Phase 2)**
3. 12-04 (feature builder — all 4 families)

**Phase 4: Storage and API (parallel)**
4. 12-06 (feature store, after 12-01 + 12-05) and 12-08 (API router, after 12-06)

**Phase 5: Integration**
5. 12-07 (session integration, after 12-04 + 12-06)

**Phase 6: Tests (parallel)**
6. 12-09 (unit tests) and 12-10 (integration test)

---

## Notes

- **Untouched:** `services/features/pipeline.py` (equity pipeline) must NOT be modified
- **New module:** All Polymarket feature code lives under `services/features/polymarket/`
- **Schema first:** Read `FeatureSnapshot` in `packages/common/polymarket_schemas.py` before implementing builder or store
- **Determinism requirement:** Builder computation path must be identical for online and offline (backtest) modes (AC-5)
- **Regime stability:** Apply minimum-hold filter (3 ticks) before flipping discrete regime labels (per spec risk notes)
- **Progress tracking:** Each ticket updates `docs/plans/PROGRESS.md` on completion
