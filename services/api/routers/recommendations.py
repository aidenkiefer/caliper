"""
Human-in-the-Loop (HITL) recommendation endpoints.

Manages approval queue for model recommendations.
"""

from typing import List

from fastapi import APIRouter, HTTPException

from packages.common.ml_schemas import (
    RecommendationResponse,
    RecommendationApproveRequest,
    RecommendationRejectRequest,
    RecommendationStatsResponse,
)

router = APIRouter()

# Mock storage (in production, would use database)
_recommendations_queue: dict[str, dict] = {}
_recommendation_stats: dict[str, dict] = {}


@router.get(
    "/v1/recommendations",
    response_model=List[RecommendationResponse],
    summary="Get pending recommendations",
    description="Returns list of recommendations pending human approval.",
)
async def get_pending_recommendations(
    strategy_id: str | None = None,
) -> List[RecommendationResponse]:
    """
    Get all pending recommendations.

    Can be filtered by strategy_id.
    """
    pending = [
        rec
        for rec in _recommendations_queue.values()
        if rec.get("status") == "pending"
        and (strategy_id is None or rec.get("strategy_id") == strategy_id)
    ]

    return [RecommendationResponse(**rec) for rec in pending]


@router.post(
    "/v1/recommendations/{recommendation_id}/approve",
    summary="Approve a recommendation",
    description="Human approves a model recommendation, allowing it to execute.",
)
async def approve_recommendation(
    recommendation_id: str,
    request: RecommendationApproveRequest,
) -> dict:
    """
    Approve a recommendation.

    Moves recommendation from pending to approved and logs the decision.
    """
    if recommendation_id not in _recommendations_queue:
        raise HTTPException(
            status_code=404,
            detail=f"Recommendation {recommendation_id} not found",
        )

    recommendation = _recommendations_queue[recommendation_id]
    recommendation["status"] = "approved"
    recommendation["approved_by"] = request.user_id
    recommendation["rationale"] = request.rationale

    # Update stats
    strategy_id = recommendation.get("strategy_id")
    if strategy_id:
        if strategy_id not in _recommendation_stats:
            _recommendation_stats[strategy_id] = {
                "total": 0,
                "approved": 0,
                "rejected": 0,
                "pending": 0,
            }
        stats = _recommendation_stats[strategy_id]
        stats["approved"] += 1
        stats["pending"] = max(0, stats["pending"] - 1)

    return {
        "status": "approved",
        "recommendation_id": recommendation_id,
        "message": "Recommendation approved and will be executed",
    }


@router.post(
    "/v1/recommendations/{recommendation_id}/reject",
    summary="Reject a recommendation",
    description="Human rejects a model recommendation.",
)
async def reject_recommendation(
    recommendation_id: str,
    request: RecommendationRejectRequest,
) -> dict:
    """
    Reject a recommendation.

    Moves recommendation from pending to rejected and logs the decision.
    """
    if recommendation_id not in _recommendations_queue:
        raise HTTPException(
            status_code=404,
            detail=f"Recommendation {recommendation_id} not found",
        )

    recommendation = _recommendations_queue[recommendation_id]
    recommendation["status"] = "rejected"
    recommendation["rejected_by"] = request.user_id
    recommendation["rejection_reason"] = request.reason

    # Update stats
    strategy_id = recommendation.get("strategy_id")
    if strategy_id:
        if strategy_id not in _recommendation_stats:
            _recommendation_stats[strategy_id] = {
                "total": 0,
                "approved": 0,
                "rejected": 0,
                "pending": 0,
            }
        stats = _recommendation_stats[strategy_id]
        stats["rejected"] += 1
        stats["pending"] = max(0, stats["pending"] - 1)

    return {
        "status": "rejected",
        "recommendation_id": recommendation_id,
        "message": "Recommendation rejected",
    }


@router.get(
    "/v1/recommendations/stats",
    response_model=RecommendationStatsResponse,
    summary="Get HITL statistics",
    description="Returns statistics on human vs model agreement.",
)
async def get_recommendation_stats(
    strategy_id: str,
) -> RecommendationStatsResponse:
    """
    Get HITL statistics for a strategy.

    Returns agreement rate and approval/rejection counts.
    """
    if strategy_id not in _recommendation_stats:
        raise HTTPException(
            status_code=404,
            detail=f"Statistics not found for strategy {strategy_id}",
        )

    stats = _recommendation_stats[strategy_id]
    total = stats.get("total", 0)
    approved = stats.get("approved", 0)
    rejected = stats.get("rejected", 0)
    pending = stats.get("pending", 0)

    # Agreement rate = approved / (approved + rejected)
    if approved + rejected > 0:
        agreement_rate = approved / (approved + rejected)
    else:
        agreement_rate = 0.0

    return RecommendationStatsResponse(
        strategy_id=strategy_id,
        total_recommendations=total,
        approved=approved,
        rejected=rejected,
        agreement_rate=agreement_rate,
        pending=pending,
    )
