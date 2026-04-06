# Sprint 14: BTC probability model — summary

**Version:** v2.4.0  
**Status:** Implementation merged to `main` (2026-04-08). **Spec AC-9 (dedicated unit + integration test suite)** is **not yet implemented** — track under backlog in `docs/plans/PROGRESS.md`.  
**Spec:** [sprint-14-probability-model-spec.md](../specs/sprint-14-probability-model-spec.md)  
**Task index:** [14-00-INDEX.md](../tickets/14-00-INDEX.md)

## What shipped

- **`services/ml/probability_model/`** — Pydantic **`schemas`** (`PredictionRecord`, `LagTestResult`, `CalibrationReport`, `CalibrationBin`, `BrierDecomposition`); **`dataset`** (panel builder, walk-forward splits, `Y_h` labeling guards); **`trainer`** (logistic baseline + Platt scaling + ECE/Brier + Brier decomposition); **`registry`** + **GBT** path (XGBoost + isotonic calibration, importances); **`lag_tests`** (cross-correlation, Granger, event study, persistence); **`backtest`** (fee-aware threshold backtest via Sprint 13 `SimulationRunner`, optional `pm.simulation_runs` persistence); **`predictor`** (async `ProbabilityPredictor`, time-to-close soft cap, DB writes); **`drift`** (`DriftMonitor`, rolling ECE, calibration report load/save).
- **Database** — Alembic **`005_create_probability_model_tables.py`**: `pm.probability_predictions` (hypertable), `pm.lag_test_results`, `pm.calibration_reports`.
- **API** — `services/api/routers/probability.py` mounted under **`/v1`**: `GET /v1/probability/calibration`, `GET /v1/probability/lag-tests`, `GET /v1/probability/{market_id}/latest`, `GET /v1/probability/{market_id}/history`, `POST /v1/probability/train`. **Note:** router responses are **stub/mock** for several routes; full wiring to live `PredictionRecord` / DB reads is follow-up work alongside dashboard consumption.

## Deferred (explicit)

- **AC-9 tests:** No dedicated `tests/unit/ml/probability_model/` or `tests/integration/...` suite landed in this merge; add per spec (label construction, statistical tests, predictor latency, end-to-end train → serve).

## References

- **Milestone / patches:** [PROGRESS.md](../PROGRESS.md) (`v2.4.0` row, `v2.4.0-p*` patch table, backlog row for AC-9).
- **API shapes:** `services/ml/probability_model/schemas.py`, [api-contracts.md](../../api-contracts.md).
