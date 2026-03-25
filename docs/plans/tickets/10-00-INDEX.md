# Polymarket BTC Hourly Market Making — Ticket Index

**Feature spec:** `docs/plans/specs/polymarket-btc-trading-spec.md`

**Total tickets:** 20

---

## Ticket dependency graph

```
Layer 1 (no dependencies):
├─ 10-01 Scaffolding
├─ 10-06 Database schema
└─ 10-07 Fee model

Layer 2 (depends on Layer 1):
├─ 10-02 Gamma client (→ 10-01)
├─ 10-03 CLOB client (→ 10-01)
├─ 10-04 Binance client (→ 10-01)
└─ 10-05 Wallet management (→ 10-01)

Layer 3 (depends on Layer 2):
├─ 10-08 Market discovery (→ 10-02, 10-06)
├─ 10-09 Data feed (→ 10-03, 10-04)
└─ 10-10 Quoting engine (→ 10-01)

Layer 4 (depends on Layer 3):
├─ 10-11 Executor (→ 10-03, 10-05)
├─ 10-12 Safety layer (→ 10-10)
└─ 10-13 Recorder (→ 10-06, 10-07)

Layer 5 (depends on Layer 4):
└─ 10-14 Session orchestrator (→ 10-08, 10-09, 10-10, 10-11, 10-12, 10-13, 10-05)

Layer 6 (depends on Layer 5):
└─ 10-15 CLI entrypoint (→ 10-14)

Layer 7 (API integration, parallel to main flow):
├─ 10-16 Shared schemas (→ 10-06)
├─ 10-17 API router (→ 10-16)
└─ 10-18 Data API client (→ 10-01)

Layer 8 (testing and docs, depends on all):
├─ 10-19 Integration test (→ 10-15)
└─ 10-20 Documentation (→ all)
```

---

## Ticket list

| # | Name | Dependencies | Est. time | Status |
|---|------|--------------|-----------|--------|
| 10-01 | Scaffolding | None | 30 min | ⬜ Not started |
| 10-02 | Gamma client | 10-01 | 1 hour | ⬜ Not started |
| 10-03 | CLOB client | 10-01 | 2 hours | ⬜ Not started |
| 10-04 | Binance client | 10-01 | 45 min | ⬜ Not started |
| 10-05 | Wallet management | 10-01 | 1.5 hours | ⬜ Not started |
| 10-06 | Database schema | None | 1 hour | ⬜ Not started |
| 10-07 | Fee model | None | 45 min | ⬜ Not started |
| 10-08 | Market discovery | 10-02, 10-06 | 1 hour | ⬜ Not started |
| 10-09 | Data feed | 10-03, 10-04 | 2 hours | ⬜ Not started |
| 10-10 | Quoting engine | 10-01 | 1 hour | ⬜ Not started |
| 10-11 | Executor | 10-03, 10-05 | 1.5 hours | ⬜ Not started |
| 10-12 | Safety layer | 10-10 | 1 hour | ⬜ Not started |
| 10-13 | Recorder | 10-06, 10-07 | 2 hours | ⬜ Not started |
| 10-14 | Session orchestrator | 10-08, 10-09, 10-10, 10-11, 10-12, 10-13, 10-05 | 2 hours | ⬜ Not started |
| 10-15 | CLI entrypoint | 10-14 | 30 min | ⬜ Not started |
| 10-16 | Shared schemas | 10-06 | 30 min | ⬜ Not started |
| 10-17 | API router | 10-16 | 1 hour | ⬜ Not started |
| 10-18 | Data API client | 10-01 | 45 min | ⬜ Not started |
| 10-19 | Integration test | 10-15 | 1.5 hours | ⬜ Not started |
| 10-20 | Documentation | all | 1 hour | ⬜ Not started |

**Total estimated time:** ~22 hours

---

## Recommended build sequence

**Phase 1: Foundation (Layer 1-2)**
1. 10-01, 10-06, 10-07 (parallel)
2. 10-02, 10-03, 10-04, 10-05 (parallel after Layer 1)

**Phase 2: Core logic (Layer 3-4)**
3. 10-08, 10-09, 10-10 (parallel)
4. 10-11, 10-12, 10-13 (parallel after Layer 3)

**Phase 3: Orchestration (Layer 5-6)**
5. 10-14
6. 10-15

**Phase 4: API and testing (Layer 7-8)**
7. 10-16, 10-18 (parallel)
8. 10-17
9. 10-19
10. 10-20

---

## Notes

- **TDD:** All tickets with logic (02-05, 07-14, 18) require tests first
- **Database:** Run migration (10-06) before any DB-dependent tickets
- **Mocking:** Integration test (10-19) uses mocked APIs, not live Polymarket
- **Dry-run:** CLI supports `--dry-run` flag for testing without real orders
- **Progress tracking:** Each ticket updates `docs/plans/PROGRESS.md` on completion
