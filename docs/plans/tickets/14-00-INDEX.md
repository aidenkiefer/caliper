# Sprint 14: BTC probability model — task index

**Feature spec:** `docs/plans/specs/sprint-14-probability-model-spec.md`  
**Version:** v2.4.0  
**Summary:** `docs/plans/summaries/SPRINT-14-PROBABILITY-MODEL.md`

**Note:** This index mirrors the agent task list from the Sprint 14 implementation branch. There are no per-task markdown tickets; use this table for status only.

---

## Task list

| ID | Scope | Status |
|----|--------|--------|
| 14-01 | Schemas — `PredictionRecord`, `LagTestResult`, `CalibrationReport` (+ bins, Brier decomposition) | Done |
| 14-02 | Panel dataset builder — walk-forward splits, `Y_h` guards | Done |
| 14-03 | Logistic regression trainer — Platt, ECE/Brier, decomposition | Done |
| 14-04 | GBT model + `ModelRegistry` | Done |
| 14-05 | Lead-lag tests module | Done |
| 14-06 | Fee-aware backtest + simulation persistence hooks | Done |
| 14-07 | `ProbabilityPredictor` async serving | Done |
| 14-08 | `DriftMonitor` | Done |
| 14-09 | DB migration `005` — `pm.probability_predictions`, `pm.lag_test_results`, `pm.calibration_reports` | Done |
| 14-10 | Probability API router + `main.py` registration | Done |
| 14-11 | Unit + integration tests (spec **AC-9**) | **Not started** |

---

## Acceptance criteria

Spec acceptance criteria **AC-1–AC-8** are addressed in library code; **AC-9** (tests) remains open until `14-11` is implemented.
