from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from services.api.dependencies import get_db

router = APIRouter()


class AggregatedSignalRow(BaseModel):
    market_id: str
    aggregated_at: str
    final_signal: float
    model_component: float
    wallet_component: float
    microstructure_component: float
    threshold_met: bool
    signal_strength: str


@router.get(
    "/signal-aggregation/signals",
    response_model=List[AggregatedSignalRow],
    summary="Get latest aggregated signals",
)
async def get_aggregated_signals(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> List[AggregatedSignalRow]:
    try:
        rows = db.execute(
            text(
                """
                SELECT DISTINCT ON (market_id) market_id, aggregated_at, signal
                FROM pm.aggregated_signals
                ORDER BY market_id, aggregated_at DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        ).mappings().all()
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Aggregated signals unavailable") from exc

    out: List[AggregatedSignalRow] = []
    for r in rows:
        s: Dict[str, Any] = r["signal"] or {}
        out.append(
            AggregatedSignalRow(
                market_id=str(r["market_id"]),
                aggregated_at=str(r["aggregated_at"]),
                final_signal=float(s.get("final_signal", 0)),
                model_component=float(s.get("model_component", 0)),
                wallet_component=float(s.get("wallet_component", 0)),
                microstructure_component=float(s.get("microstructure_component", 0)),
                threshold_met=bool(s.get("threshold_met", False)),
                signal_strength=str(s.get("signal_strength", "none")),
            )
        )
    return out
