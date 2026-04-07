"""
Alert endpoints.

Provides a lightweight alert feed for the dashboard. This is intentionally
minimal: alerts are DB-backed for durability and to avoid dummy/mock payloads.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, List
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from packages.common.api_schemas import (
    AlertItem,
    AlertListMeta,
    AlertListResponse,
    AlertResponse,
    AlertSeverity,
)
from services.api.dependencies import get_db

router = APIRouter()


def _now() -> datetime:
    return datetime.now(timezone.utc)


@router.get(
    "/alerts",
    response_model=AlertListResponse,
    summary="List alerts",
    description="Returns recent alerts, optionally filtered by severity and acknowledgement status.",
)
async def list_alerts(
    severity: Optional[str] = Query(
        None,
        description="Filter by severity: INFO, WARNING, ERROR, CRITICAL",
        pattern="^(INFO|WARNING|ERROR|CRITICAL)$",
    ),
    acknowledged: Optional[bool] = Query(
        None,
        description="Filter by acknowledgement status",
    ),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
) -> AlertListResponse:
    where = []
    params = {}

    if severity:
        where.append("severity = :severity")
        params["severity"] = severity
    if acknowledged is not None:
        where.append("acknowledged = :ack")
        params["ack"] = acknowledged

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    try:
        total = int(
            db.execute(
                text(f"SELECT COUNT(*) FROM paper.alerts {where_sql}"),
                params,
            ).scalar()
            or 0
        )

        offset = (page - 1) * per_page
        rows = db.execute(
            text(
                f"""
                SELECT alert_id, severity, message, context, acknowledged, created_at
                FROM paper.alerts
                {where_sql}
                ORDER BY
                  CASE severity
                    WHEN 'CRITICAL' THEN 0
                    WHEN 'ERROR' THEN 1
                    WHEN 'WARNING' THEN 2
                    WHEN 'INFO' THEN 3
                    ELSE 4
                  END ASC,
                  created_at DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            {**params, "limit": per_page, "offset": offset},
        ).fetchall()
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Alerts store not available (DB not configured or migrations not applied)",
        ) from exc

    page_items: List[AlertItem] = []
    for alert_id, sev, message, context, ack, created_at in rows:
        page_items.append(
            AlertItem(
                alert_id=alert_id,
                severity=AlertSeverity(sev),
                message=message,
                context=context,
                acknowledged=bool(ack),
                created_at=created_at,
            )
        )

    return AlertListResponse(
        data=page_items,
        meta=AlertListMeta(total_count=total, page=page, per_page=per_page),
    )


# ---------------------------------------------------------------------------
# Internal helper (not exposed as API) to create alerts from other subsystems.
# ---------------------------------------------------------------------------

def emit_alert(
    severity: AlertSeverity,
    message: str,
    *,
    context: Optional[dict] = None,
) -> AlertItem:
    """
    Create an alert entry and return it.

    WARNING: This helper is kept for compatibility, but it is NOT safe to call
    without a DB session. Prefer `emit_alert_db(...)` below.
    """
    raise RuntimeError("emit_alert requires DB wiring; use emit_alert_db(db, ...) instead")


@router.patch(
    "/alerts/{alert_id}/acknowledge",
    response_model=AlertResponse,
    summary="Acknowledge an alert",
    description="Marks an alert as acknowledged.",
)
async def acknowledge_alert_db(alert_id: str, db: Session = Depends(get_db)) -> AlertResponse:
    try:
        updated = db.execute(
            text(
                """
                UPDATE paper.alerts
                SET acknowledged = TRUE
                WHERE alert_id = :aid
                RETURNING alert_id, severity, message, context, acknowledged, created_at
                """
            ),
            {"aid": alert_id},
        ).fetchone()
        if not updated:
            raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found")
        db.commit()
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="Alerts store not available") from exc

    alert_id, sev, message, context, ack, created_at = updated
    return AlertResponse(
        data=AlertItem(
            alert_id=alert_id,
            severity=AlertSeverity(sev),
            message=message,
            context=context,
            acknowledged=bool(ack),
            created_at=created_at,
        )
    )


def emit_alert_db(
    db: Session,
    severity: AlertSeverity,
    message: str,
    *,
    context: Optional[dict] = None,
) -> AlertItem:
    """Insert an alert row and return it."""
    alert_id = f"alert-{uuid4().hex[:10]}"
    created_at = _now()

    db.execute(
        text(
            """
            INSERT INTO paper.alerts(alert_id, severity, message, context, acknowledged, created_at)
            VALUES (:aid, :sev, :msg, :ctx, FALSE, :created_at)
            """
        ),
        {
            "aid": alert_id,
            "sev": severity.value,
            "msg": message,
            "ctx": context,
            "created_at": created_at,
        },
    )

    return AlertItem(
        alert_id=alert_id,
        severity=severity,
        message=message,
        context=context,
        acknowledged=False,
        created_at=created_at,
    )


def emit_alert_db_dedup(
    db: Session,
    severity: AlertSeverity,
    message: str,
    *,
    source: str,
    category: str,
    dedup_key: str,
    context: Optional[dict] = None,
    window_seconds: int = 600,
) -> Optional[AlertItem]:
    """
    Best-effort insert with de-duplication window (prevents spamming on polling endpoints).

    De-dupe is based on `context.dedup_key` among unacknowledged alerts in the last window.
    """
    created_at = _now()

    try:
        exists = db.execute(
            text(
                """
                SELECT 1
                FROM paper.alerts
                WHERE acknowledged = FALSE
                  AND created_at >= (:now - (:window::INT * INTERVAL '1 second'))
                  AND context->>'dedup_key' = :k
                LIMIT 1
                """
            ),
            {"now": created_at, "window": window_seconds, "k": dedup_key},
        ).fetchone()
        if exists:
            return None
    except Exception:
        # If the query fails for any reason, still attempt insert.
        pass

    ctx = dict(context or {})
    ctx.update({"source": source, "category": category, "dedup_key": dedup_key})
    item = emit_alert_db(db, severity, message, context=ctx)
    return item
