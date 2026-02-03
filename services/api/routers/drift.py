"""
Drift detection endpoints.

Provides drift metrics and health scores for ML models.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException

from packages.common.ml_schemas import DriftMetricsResponse, HealthScoreResponse
from services.ml.drift import DriftDetector, HealthScore, DriftAlertManager

router = APIRouter()

# Mock storage (in production, would use database)
_drift_metrics_store: dict[str, dict] = {}
_health_scores: dict[str, float] = {}


@router.get(
    "/v1/drift/metrics/{model_id}",
    response_model=DriftMetricsResponse,
    summary="Get drift metrics for a model",
    description="Returns drift metrics (PSI, KL divergence, mean shift) for a model.",
)
async def get_drift_metrics(model_id: str) -> DriftMetricsResponse:
    """
    Get drift metrics for a specific model.

    Returns feature-level drift metrics, confidence drift, and error drift.
    """
    if model_id not in _drift_metrics_store:
        raise HTTPException(
            status_code=404,
            detail=f"Drift metrics not found for model {model_id}",
        )

    metrics = _drift_metrics_store[model_id]

    return DriftMetricsResponse(
        model_id=model_id,
        feature_metrics=metrics.get("feature_metrics", []),
        confidence_metric=metrics.get("confidence_metric"),
        error_metric=metrics.get("error_metric"),
        timestamp=metrics.get("timestamp", datetime.now(timezone.utc).isoformat()),
    )


@router.get(
    "/v1/drift/health/{model_id}",
    response_model=HealthScoreResponse,
    summary="Get model health score",
    description="Returns composite health score (0-100) based on drift metrics.",
)
async def get_health_score(
    model_id: str,
    last_retraining_date: Optional[str] = None,
) -> HealthScoreResponse:
    """
    Get health score for a specific model.

    Health score is calculated from:
    - Feature drift (30%)
    - Confidence drift (30%)
    - Error drift (20%)
    - Staleness (20%)
    """
    if model_id not in _drift_metrics_store:
        raise HTTPException(
            status_code=404,
            detail=f"Drift metrics not found for model {model_id}",
        )

    # Parse last retraining date if provided
    retraining_date = None
    if last_retraining_date:
        try:
            retraining_date = datetime.fromisoformat(last_retraining_date.replace("Z", "+00:00"))
        except ValueError:
            pass

    # Calculate health score (mock - would use actual metrics)
    health_calculator = HealthScore(last_retraining_date=retraining_date)

    # In production, would use actual metrics from store
    # For now, return mock score
    score = _health_scores.get(model_id, 75.0)

    return HealthScoreResponse(
        model_id=model_id,
        health_score=score,
        components={
            "feature_drift": 80.0,
            "confidence_drift": 70.0,
            "error_drift": 75.0,
            "staleness": 80.0,
        },
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
