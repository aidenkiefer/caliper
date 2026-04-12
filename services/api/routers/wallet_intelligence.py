from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from services.api.dependencies import get_db

router = APIRouter()


class WalletSignalRow(BaseModel):
    market_id: str
    computed_at: str
    smart_money_consensus: float
    smart_money_activity_zscore: float
    signal_confidence: float
    wallet_count: int
    top_wallet_direction: Optional[str]


@router.get(
    "/wallet-intelligence/signals",
    response_model=List[WalletSignalRow],
    summary="Get latest wallet intelligence signals",
)
async def get_wallet_signals(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> List[WalletSignalRow]:
    try:
        rows = db.execute(
            text(
                """
                SELECT DISTINCT ON (market_id) market_id, computed_at, signal
                FROM pm.wallet_signals
                ORDER BY market_id, computed_at DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        ).mappings().all()
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Wallet signals unavailable") from exc

    out: List[WalletSignalRow] = []
    for r in rows:
        s: Dict[str, Any] = r["signal"] or {}
        out.append(
            WalletSignalRow(
                market_id=str(r["market_id"]),
                computed_at=str(r["computed_at"]),
                smart_money_consensus=float(s.get("smart_money_consensus", 0)),
                smart_money_activity_zscore=float(s.get("smart_money_activity_zscore", 0)),
                signal_confidence=float(s.get("signal_confidence", 0)),
                wallet_count=int(s.get("wallet_count", 0)),
                top_wallet_direction=s.get("top_wallet_direction"),
            )
        )
    return out
