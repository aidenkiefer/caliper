"""
Human-in-the-Loop (HITL) recommendation endpoints.

Manages approval queue for model recommendations.
"""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from packages.common.ml_schemas import (
    RecommendationResponse,
    RecommendationApproveRequest,
    RecommendationRejectRequest,
    RecommendationStatsResponse,
)
from services.api.dependencies import get_db

router = APIRouter()


@router.get(
    "/recommendations",
    response_model=List[RecommendationResponse],
    summary="Get pending recommendations",
    description="Returns list of recommendations pending human approval.",
)
async def get_pending_recommendations(
    strategy_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
) -> List[RecommendationResponse]:
    """
    Get all pending recommendations.

    Can be filtered by strategy_id.
    """
    where = ["status = 'PENDING'"]
    params = {}
    if strategy_id:
        where.append("strategy_id = :sid")
        params["sid"] = strategy_id

    where_sql = " AND ".join(where)

    try:
        rows = db.execute(
            text(
                f"""
                SELECT recommendation_id, strategy_id, signal, symbol, confidence, uncertainty, occurred_at, explanation_id
                FROM ml.recommendations
                WHERE {where_sql}
                ORDER BY occurred_at DESC
                LIMIT 200
                """
            ),
            params,
        ).fetchall()
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Recommendations store not available (DB not configured or migrations not applied)",
        ) from exc

    out: List[RecommendationResponse] = []
    for rid, sid, signal, symbol, conf, unc, occurred_at, explanation_id in rows:
        out.append(
            RecommendationResponse(
                recommendation_id=rid,
                strategy_id=sid,
                signal=signal,
                symbol=symbol,
                confidence=float(conf),
                uncertainty=float(unc),
                timestamp=occurred_at.isoformat(),
                explanation_id=explanation_id,
            )
        )
    return out


@router.post(
    "/recommendations/{recommendation_id}/approve",
    summary="Approve a recommendation",
    description="Human approves a model recommendation, allowing it to execute.",
)
async def approve_recommendation(
    recommendation_id: str,
    request: RecommendationApproveRequest,
    db: Session = Depends(get_db),
) -> dict:
    """
    Approve a recommendation.

    Moves recommendation from pending to approved and logs the decision.
    """
    try:
        updated = db.execute(
            text(
                """
                UPDATE ml.recommendations
                SET status = 'APPROVED',
                    decided_at = :now,
                    decided_by = :user_id,
                    decision_note = :note
                WHERE recommendation_id = :rid
                  AND status = 'PENDING'
                RETURNING recommendation_id
                """
            ),
            {
                "rid": recommendation_id,
                "now": datetime.now(timezone.utc),
                "user_id": request.user_id,
                "note": request.rationale,
            },
        ).fetchone()
        if not updated:
            raise HTTPException(status_code=404, detail="Recommendation not found (or already decided)")
        db.commit()
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="Recommendations store not available") from exc

    return {
        "status": "approved",
        "recommendation_id": recommendation_id,
        "message": "Recommendation approved and will be executed",
    }


@router.post(
    "/recommendations/{recommendation_id}/reject",
    summary="Reject a recommendation",
    description="Human rejects a model recommendation.",
)
async def reject_recommendation(
    recommendation_id: str,
    request: RecommendationRejectRequest,
    db: Session = Depends(get_db),
) -> dict:
    """
    Reject a recommendation.

    Moves recommendation from pending to rejected and logs the decision.
    """
    try:
        updated = db.execute(
            text(
                """
                UPDATE ml.recommendations
                SET status = 'REJECTED',
                    decided_at = :now,
                    decided_by = :user_id,
                    decision_note = :note
                WHERE recommendation_id = :rid
                  AND status = 'PENDING'
                RETURNING recommendation_id
                """
            ),
            {
                "rid": recommendation_id,
                "now": datetime.now(timezone.utc),
                "user_id": request.user_id,
                "note": request.reason,
            },
        ).fetchone()
        if not updated:
            raise HTTPException(status_code=404, detail="Recommendation not found (or already decided)")
        db.commit()
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="Recommendations store not available") from exc

    return {
        "status": "rejected",
        "recommendation_id": recommendation_id,
        "message": "Recommendation rejected",
    }


@router.get(
    "/recommendations/stats",
    response_model=RecommendationStatsResponse,
    summary="Get HITL statistics",
    description="Returns statistics on human vs model agreement.",
)
async def get_recommendation_stats(
    strategy_id: str,
    db: Session = Depends(get_db),
) -> RecommendationStatsResponse:
    """
    Get HITL statistics for a strategy.

    Returns agreement rate and approval/rejection counts.
    """
    try:
        rows = db.execute(
            text(
                """
                SELECT status, COUNT(*)::INT
                FROM ml.recommendations
                WHERE strategy_id = :sid
                GROUP BY status
                """
            ),
            {"sid": strategy_id},
        ).fetchall()
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Recommendations store not available") from exc

    counts = {status: int(cnt) for status, cnt in rows}
    approved = counts.get("APPROVED", 0)
    rejected = counts.get("REJECTED", 0)
    pending = counts.get("PENDING", 0)
    total = approved + rejected + pending

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


def enqueue_recommendation_db(
    db: Session,
    *,
    recommendation_id: str,
    strategy_id: str,
    signal: str,
    symbol: str,
    confidence: float,
    uncertainty: float,
    occurred_at: datetime,
    explanation_id: Optional[str] = None,
) -> None:
    """Insert a new PENDING recommendation row (internal helper)."""
    db.execute(
        text(
            """
            INSERT INTO ml.recommendations(
                recommendation_id, strategy_id, signal, symbol, confidence, uncertainty, occurred_at, explanation_id, status
            )
            VALUES (
                :rid, :sid, :signal, :symbol, :conf, :unc, :ts, :explanation_id, 'PENDING'
            )
            ON CONFLICT (recommendation_id) DO NOTHING
            """
        ),
        {
            "rid": recommendation_id,
            "sid": strategy_id,
            "signal": signal,
            "symbol": symbol,
            "conf": confidence,
            "unc": uncertainty,
            "ts": occurred_at,
            "explanation_id": explanation_id,
        },
    )
