# Sprint 15: Regime detection + dynamic allocation — Ticket Index

**Feature spec:** `docs/plans/specs/sprint-15-regime-allocation-spec.md`  
**Research sources:** `docs/research/regime-allocation.md`  
**Version:** v2.5.0  
**Total tickets:** 13

---

## Ticket dependency graph

```
Layer 1 (foundation — parallel):
├─ 15-01 Schemas + scaffolding
├─ 15-03 HMM deps + classifier + trainer (depends on 15-01 schemas)
└─ 15-11 DB migration (can start immediately)

Layer 2 (regime detection):
├─ 15-02 Threshold classifier (→ 15-01)
├─ 15-04 Regime quality metrics (→ 15-01, 15-03)
└─ 15-05 RegimeDetector + regime store + run loop (→ 15-02, 15-03, 15-04, 15-11)

Layer 3 (performance matrix):
├─ 15-06 Extend evaluation regime matrix for Sprint-15 labels (→ 15-02)
└─ 15-07 PerformanceMatrix builder + store (→ 15-01, 15-06, 15-11)

Layer 4 (allocation):
├─ 15-08 Allocation methods (risk parity, HRP, bounded Kelly) (→ 15-01, 15-07)
├─ 15-09 Allocation risk layer (hard/soft constraints + blending) (→ 15-01, 15-08)
└─ 15-10 AllocationEngine + allocation store + run loop (→ 15-05, 15-07, 15-09, 15-11)

Layer 5 (API + docs + tests):
├─ 15-12 API router + registration + api-contracts update (→ 15-05, 15-07, 15-10)
└─ 15-13 Tests (unit + integration) (→ all logic tickets above)
```

---

## Ticket list

| #     | Name | Dependencies | Est. time | Status |
|-------|------|--------------|-----------|--------|
| 15-01 | Schemas + scaffolding | None | 1.0h | Not started |
| 15-02 | ThresholdRegimeClassifier | 15-01 | 1.5h | Not started |
| 15-03 | HMM classifier + trainer + deps | 15-01 | 3.0h | Not started |
| 15-04 | Regime quality metrics | 15-01, 15-03 | 1.5h | Not started |
| 15-05 | RegimeDetector + store + loop | 15-02, 15-03, 15-04, 15-11 | 3.0h | Not started |
| 15-06 | Eval regime-matrix: add Sprint-15 labels | 15-02 | 1.0h | Not started |
| 15-07 | PerformanceMatrix builder + store | 15-01, 15-06, 15-11 | 3.0h | Not started |
| 15-08 | Allocation methods: risk parity / HRP / bounded Kelly | 15-01, 15-07 | 3.0h | Not started |
| 15-09 | Allocation risk layer: constraints + blending | 15-01, 15-08 | 2.0h | Not started |
| 15-10 | AllocationEngine + store + loop | 15-05, 15-07, 15-09, 15-11 | 2.5h | Not started |
| 15-11 | DB migration: pm.regime_states / allocation_decisions / performance_matrices | None | 1.0h | Not started |
| 15-12 | API router + registration + api-contracts update | 15-05, 15-07, 15-10 | 2.0h | Not started |
| 15-13 | Tests: unit + integration | All | 4.0h | Not started |

**Total estimated time:** ~28.0 hours

---

## Notes

- Sprint 15 is **Polymarket-only** (per spec “Out of Scope”).
- Keep HMM output *soft*; use entropy-based `alpha` blending toward the threshold baseline under uncertainty.
- Hard constraints are enforced in `services/allocation/risk_layer.py` exactly as per spec AC-7.
- DB writes must be non-blocking (fire-and-forget) to protect real-time loops (same pattern as `services/ml/probability_model/predictor.py`).

