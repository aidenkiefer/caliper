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

# In-memory storage (in production, would use database)
_drift_metrics_store: dict[str, dict] = {}


@router.get(
    "/drift/metrics/{model_id}",
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
    "/drift/health/{model_id}",
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

    # Calculate health score from stored drift metrics
    health_calculator = HealthScore(last_retraining_date=retraining_date)

    metrics = _drift_metrics_store[model_id]
    feature_metrics = metrics.get("feature_metrics", []) or []
    confidence_metric = metrics.get("confidence_metric")
    error_metric = metrics.get("error_metric")

    try:
        score = health_calculator.calculate(
            feature_metrics=feature_metrics,
            confidence_metric=confidence_metric,
            error_metric=error_metric,
        )

        feature_score = health_calculator._calculate_feature_score(feature_metrics)  # noqa: SLF001
        confidence_score = health_calculator._calculate_confidence_score(confidence_metric)  # noqa: SLF001
        error_score = health_calculator._calculate_error_score(error_metric)  # noqa: SLF001
        staleness_score = health_calculator._calculate_staleness_score()  # noqa: SLF001
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Health score computation failed (drift metrics store not in expected shape)",
        ) from exc

    return HealthScoreResponse(
        model_id=model_id,
        health_score=score,
        components={
            "feature_drift": feature_score,
            "confidence_drift": confidence_score,
            "error_drift": error_score,
            "staleness": staleness_score,
        },
        alerts=[],
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
