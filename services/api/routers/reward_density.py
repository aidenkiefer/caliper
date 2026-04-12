from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from services.api.dependencies import get_db

router = APIRouter()


class RewardDensityScoreRow(BaseModel):
    market_id: str
    scored_at: str
    reward_density_score: float
    expected_incentives_usd: float
    competition: float
    risk_score: float
    confidence: str


@router.get(
    "/reward-density/scores",
    response_model=List[RewardDensityScoreRow],
    summary="Get latest reward density scores",
)
async def get_reward_density_scores(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> List[RewardDensityScoreRow]:
    try:
        rows = db.execute(
            text(
                """
                SELECT DISTINCT ON (market_id) market_id, scored_at, score
                FROM pm.reward_density_scores
                ORDER BY market_id, scored_at DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        ).mappings().all()
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Reward density scores unavailable") from exc

    out: List[RewardDensityScoreRow] = []
    for r in rows:
        s: Dict[str, Any] = r["score"] or {}
        out.append(
            RewardDensityScoreRow(
                market_id=str(r["market_id"]),
                scored_at=str(r["scored_at"]),
                reward_density_score=float(s.get("reward_density_score", 0)),
                expected_incentives_usd=float(s.get("expected_incentives_usd", 0)),
                competition=float(s.get("competition", 1)),
                risk_score=float(s.get("risk_score", 0)),
                confidence=str(s.get("confidence", "low")),
            )
        )
    return out
