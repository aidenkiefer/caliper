# Sprint 16: Cross-sectional ranking + model fleet — Ticket Index

**Feature spec:** `docs/plans/specs/sprint-16-cross-sectional-fleet-spec.md`  
**Research sources:** `docs/research/cross-sectional.md`, `docs/research/reward-density.md`  
**Version:** v2.6.0  
**Total tickets:** 13

---

## Ticket dependency graph

```
Layer 1 (foundation — parallel):
├─ 16-01 Ranking schemas + scaffolding
├─ 16-06 Strategy 1: Microstructure Maker v2 (depends on base strategy)
├─ 16-07 Strategy 2: Directional probability model consumer (depends on base strategy)
└─ 16-11 DB migration + paper-trade store (can start immediately)

Layer 2 (ranker core):
├─ 16-02 UniverseBuilder (→ 16-01)
├─ 16-03 EdgeEstimator (→ 16-01)
├─ 16-04 FeasibilityScorer (→ 16-01)
└─ 16-05 MarketRanker + selection + cooldown + cadence (→ 16-02/03/04)

Layer 3 (fleet strategies):
├─ 16-08 Strategy 3: Hybrid maker + directional lean (→ 16-06, 16-07)
└─ 16-09 Strategy 4: Regime-aware strategy (→ 16-06, 16-07)

Layer 4 (fleet orchestration):
└─ 16-10 FleetOrchestrator + registry + signal routing (→ 16-05, 16-06..16-09, 16-11)

Layer 5 (API + dashboard + tests):
├─ 16-12 API router + api-contracts update (→ 16-05, 16-10, 16-11)
└─ 16-13 Dashboard panels + tests (→ 16-12; logic unit tests can run in parallel)
```

---

## Ticket list

| #     | Name | Dependencies | Est. time | Status |
|-------|------|--------------|-----------|--------|
| 16-01 | Ranking schemas + scaffolding | None | 1.0h | Not started |
| 16-02 | UniverseBuilder (Gamma discovery + filters) | 16-01 | 2.0h | Not started |
| 16-03 | EdgeEstimator (cost-adjusted EV + staleness decay) | 16-01 | 1.5h | Not started |
| 16-04 | FeasibilityScorer (liquidity + fill probability) | 16-01 | 1.5h | Not started |
| 16-05 | MarketRanker (composite score + selection + cooldown + cadence) | 16-02, 16-03, 16-04 | 3.0h | Not started |
| 16-06 | Strategy 1: `poly_mm_v2` | None | 2.0h | Not started |
| 16-07 | Strategy 2: `poly_directional_v1` | None | 2.0h | Not started |
| 16-08 | Strategy 3: `poly_hybrid_v1` | 16-06, 16-07 | 2.0h | Not started |
| 16-09 | Strategy 4: `poly_regime_v1` | 16-06, 16-07 | 2.0h | Not started |
| 16-10 | FleetOrchestrator + registry | 16-05, 16-06..16-09, 16-11 | 4.0h | Not started |
| 16-11 | DB migration + paper-trade store | None | 1.5h | Not started |
| 16-12 | API router + api-contracts update | 16-05, 16-10, 16-11 | 2.0h | Not started |
| 16-13 | Tests + dashboard panels | 16-12 | 6.0h | Not started |

**Total estimated time:** ~29.0 hours

---

## Notes

- Sprint 16 remains **paper trading only** (explicitly out of scope: live/funded trading).
- Ranker never scores negative-EDGE markets as candidates: `EV_adj < 0 → Score=0`.
- Fleet orchestration must keep Polymarket safety semantics: cancellations on R4 and abstain on R5.
- Avoid import cycles: `services/ranking` and `services/fleet` should depend on stable shared schemas, not each other’s internals.

