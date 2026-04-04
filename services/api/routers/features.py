"""
Feature snapshot endpoints (Sprint 12).

Exposes read access to the unified Polymarket feature pipeline data stored
in the ``pm.features`` TimescaleDB hypertable.

Routes:
    GET /v1/features/{market_id}/latest   — Most recent FeatureSnapshot
    GET /v1/features/{market_id}/history  — Time-windowed FeatureSnapshot list
"""

import os
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from packages.common.polymarket_schemas import FeatureSnapshot
from services.features.polymarket.store import FeatureStore, FeatureStoreError

logger = logging.getLogger(__name__)

router = APIRouter()

_MAX_LIMIT = 1000


def _get_feature_store() -> FeatureStore:
    """Return a connected FeatureStore or raise 503 if DB_URL is not set."""
    db_url = os.environ.get("DB_URL")
    if not db_url:
        raise HTTPException(
            status_code=503,
            detail="Feature store not available",
        )
    return FeatureStore(db_url)


# ---------------------------------------------------------------------------
# Latest
# ---------------------------------------------------------------------------


@router.get(
    "/features/{market_id}/latest",
    response_model=FeatureSnapshot,
    summary="Get latest feature snapshot",
    description="Return the most recent FeatureSnapshot for the given market.",
)
async def get_latest_features(
    market_id: str,
) -> FeatureSnapshot:
    """
    Fetch the most recent feature snapshot from pm.features.

    Raises:
        HTTPException: 503 if DB_URL is not configured.
        HTTPException: 404 if no features exist for the market.
        HTTPException: 500 on unexpected store errors.
    """
    store = _get_feature_store()
    try:
        await store.connect()
        try:
            snapshot = await store.read_latest(market_id)
        finally:
            await store.close()
    except FeatureStoreError as exc:
        logger.error("FeatureStore error in get_latest_features: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if snapshot is None:
        raise HTTPException(
            status_code=404,
            detail="No features found for market",
        )
    return snapshot


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------


@router.get(
    "/features/{market_id}/history",
    response_model=List[FeatureSnapshot],
    summary="Get feature snapshot history",
    description="Return a time-windowed list of FeatureSnapshots for the given market.",
)
async def get_features_history(
    market_id: str,
    start: datetime = Query(..., description="Window start (inclusive)"),
    end: datetime = Query(..., description="Window end (inclusive)"),
    limit: int = Query(100, ge=1, le=_MAX_LIMIT, description="Max rows to return (hard cap 1000)"),
) -> List[FeatureSnapshot]:
    """
    Fetch FeatureSnapshot records within [start, end] ordered by captured_at ASC.

    Returns an empty list if no rows match; does not raise 404.

    Raises:
        HTTPException: 503 if DB_URL is not configured.
        HTTPException: 422 if start >= end.
        HTTPException: 500 on unexpected store errors.
    """
    if start >= end:
        raise HTTPException(
            status_code=422,
            detail="Query parameter 'start' must be before 'end'",
        )

    # Cap limit server-side regardless of validated query param
    effective_limit = min(limit, _MAX_LIMIT)

    store = _get_feature_store()
    try:
        await store.connect()
        try:
            snapshots = await store.read_window(
                market_id, start, end, limit=effective_limit
            )
        finally:
            await store.close()
    except FeatureStoreError as exc:
        logger.error("FeatureStore error in get_features_history: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return snapshots
