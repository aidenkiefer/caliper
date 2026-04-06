"""
Regime + allocation endpoints (Sprint 15).

Exposes read access to:
- pm.regime_states
- pm.allocation_decisions
- pm.performance_matrices

AllocationDecision reconstruction is best-effort since the v2.5.0 table spec
stores only weights/method/confidence (+ optional regime_id).
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from services.allocation.schemas import AllocationDecision, CapitalBudgetModel, PerformanceMatrix
from services.allocation.store import AllocationDecisionStore, PerformanceMatrixStore
from services.regime.schemas import RegimeQualityReport, RegimeState
from services.regime.store import RegimeStore, RegimeStoreError

logger = logging.getLogger(__name__)

router = APIRouter()

_MAX_LIMIT = 5000


def _require_db_url() -> str:
    db_url = os.environ.get("DB_URL")
    if not db_url:
        raise HTTPException(status_code=503, detail="DB not configured")
    return db_url


def _get_regime_store() -> RegimeStore:
    return RegimeStore(_require_db_url())


def _get_decision_store() -> AllocationDecisionStore:
    return AllocationDecisionStore(_require_db_url())


def _get_matrix_store() -> PerformanceMatrixStore:
    return PerformanceMatrixStore(_require_db_url())


@router.get("/regime/current", response_model=RegimeState, summary="Get current global regime")
async def get_current_regime(store: RegimeStore = Depends(_get_regime_store)) -> RegimeState:
    try:
        await store.connect()
        try:
            state = await store.read_latest(market_id=None)
        finally:
            await store.close()
    except RegimeStoreError as exc:
        logger.error("RegimeStore error in get_current_regime: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if state is None:
        raise HTTPException(status_code=404, detail="No regime states found")
    return state


@router.get("/regime/{market_id}/current", response_model=RegimeState, summary="Get current per-market regime")
async def get_current_regime_for_market(
    market_id: str,
    store: RegimeStore = Depends(_get_regime_store),
) -> RegimeState:
    try:
        await store.connect()
        try:
            state = await store.read_latest(market_id=market_id)
        finally:
            await store.close()
    except RegimeStoreError as exc:
        logger.error("RegimeStore error in get_current_regime_for_market: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if state is None:
        raise HTTPException(status_code=404, detail="No regime states found for market")
    return state


@router.get("/regime/history", response_model=List[RegimeState], summary="Get regime history")
async def get_regime_history(
    start: datetime = Query(..., description="Window start (inclusive)"),
    end: datetime = Query(..., description="Window end (inclusive)"),
    market_id: Optional[str] = Query(None, description="Optional market_id; omit for global regime"),
    limit: int = Query(1000, ge=1, le=_MAX_LIMIT),
    store: RegimeStore = Depends(_get_regime_store),
) -> List[RegimeState]:
    if start >= end:
        raise HTTPException(status_code=422, detail="Query parameter 'start' must be before 'end'")
    try:
        await store.connect()
        try:
            states = await store.read_window(start, end, market_id=market_id, limit=limit)
        finally:
            await store.close()
    except RegimeStoreError as exc:
        logger.error("RegimeStore error in get_regime_history: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return states


def _stub_budget() -> CapitalBudgetModel:
    # Not persisted in pm.allocation_decisions in v2.5.0 table spec.
    return CapitalBudgetModel(total_equity=Decimal("0"), market_budgets={})


def _stub_regime(ts: datetime) -> RegimeState:
    return RegimeState(
        detected_at=ts,
        market_id=None,
        primary_regime="R1",
        regime_probabilities={"R1": 1.0, "R2": 0.0, "R3": 0.0, "R4": 0.0, "R5": 0.0},
        quality=RegimeQualityReport(
            computed_at=ts,
            posterior_entropy=0.0,
            switch_rate_per_hour=0.0,
            expected_duration_minutes=0.0,
            agreement_with_threshold=1.0,
            quality_score=1.0,
        ),
        source="threshold",
    )


@router.get("/allocation/current", response_model=AllocationDecision, summary="Get current allocation decision")
async def get_current_allocation(
    decision_store: AllocationDecisionStore = Depends(_get_decision_store),
    regime_store: RegimeStore = Depends(_get_regime_store),
) -> AllocationDecision:
    try:
        await decision_store.connect()
        await regime_store.connect()
        try:
            row = await decision_store.read_latest()
            if row is None:
                raise HTTPException(status_code=404, detail="No allocation decisions found")
            decided_at, weights, method, _regime_id, confidence = row
            regime = await regime_store.read_latest(market_id=None) or _stub_regime(decided_at)
            return AllocationDecision(
                decided_at=decided_at,
                regime=regime,
                weights=weights,
                method_used=method,  # type: ignore[arg-type]
                confidence=float(confidence or 0),
                hard_constraints_applied=[],
                capital_budget=_stub_budget(),
            )
        finally:
            await decision_store.close()
            await regime_store.close()
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Unexpected error in get_current_allocation: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error") from exc


@router.get("/allocation/history", response_model=List[AllocationDecision], summary="Get allocation history")
async def get_allocation_history(
    start: datetime = Query(..., description="Window start (inclusive)"),
    end: datetime = Query(..., description="Window end (inclusive)"),
    limit: int = Query(1000, ge=1, le=_MAX_LIMIT),
    decision_store: AllocationDecisionStore = Depends(_get_decision_store),
    regime_store: RegimeStore = Depends(_get_regime_store),
) -> List[AllocationDecision]:
    if start >= end:
        raise HTTPException(status_code=422, detail="Query parameter 'start' must be before 'end'")
    try:
        await decision_store.connect()
        await regime_store.connect()
        try:
            rows = await decision_store.read_window(start, end, limit=limit)
            regime = await regime_store.read_latest(market_id=None) or _stub_regime(start)
            budget = _stub_budget()
            out: List[AllocationDecision] = []
            for decided_at, weights, method, _regime_id, confidence in rows:
                out.append(
                    AllocationDecision(
                        decided_at=decided_at,
                        regime=regime,
                        weights=weights,
                        method_used=method,  # type: ignore[arg-type]
                        confidence=float(confidence or 0),
                        hard_constraints_applied=[],
                        capital_budget=budget,
                    )
                )
            return out
        finally:
            await decision_store.close()
            await regime_store.close()
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Unexpected error in get_allocation_history: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error") from exc


@router.get(
    "/allocation/performance-matrix",
    response_model=PerformanceMatrix,
    summary="Get latest performance matrix",
)
async def get_latest_performance_matrix(
    store: PerformanceMatrixStore = Depends(_get_matrix_store),
) -> PerformanceMatrix:
    try:
        await store.connect()
        try:
            m = await store.read_latest()
        finally:
            await store.close()
    except Exception as exc:
        logger.error("PerformanceMatrixStore error: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error") from exc
    if m is None:
        raise HTTPException(status_code=404, detail="No performance matrices found")
    return m

