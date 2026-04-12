from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from services.api.dependencies import get_db

router = APIRouter()


class LifecycleEventRow(BaseModel):
    event_id: str
    strategy_id: str
    event_type: str
    triggered_at: str
    rule_id: str
    approved: Optional[bool]
    notes: Optional[str]


@router.get(
    "/lifecycle/events",
    response_model=List[LifecycleEventRow],
    summary="Get lifecycle events",
)
async def get_lifecycle_events(
    strategy_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> List[LifecycleEventRow]:
    where = "WHERE strategy_id = :strategy_id" if strategy_id else ""
    params: dict = {"limit": limit}
    if strategy_id:
        params["strategy_id"] = strategy_id

    try:
        rows = db.execute(
            text(
                f"""
                SELECT event_id, strategy_id, event_type, triggered_at, rule_id, approved, notes
                FROM pm.lifecycle_events
                {where}
                ORDER BY triggered_at DESC
                LIMIT :limit
                """
            ),
            params,
        ).mappings().all()
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Lifecycle events unavailable") from exc

    return [
        LifecycleEventRow(
            event_id=str(r["event_id"]),
            strategy_id=str(r["strategy_id"]),
            event_type=str(r["event_type"]),
            triggered_at=str(r["triggered_at"]),
            rule_id=str(r["rule_id"]),
            approved=r.get("approved"),
            notes=str(r["notes"]) if r.get("notes") else None,
        )
        for r in rows
    ]
