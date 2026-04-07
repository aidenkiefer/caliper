from __future__ import annotations

from datetime import datetime, timezone
import json
from decimal import Decimal
from typing import List, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from services.api.dependencies import get_db
from services.ranking.ranker import MarketRanker
from services.ranking.schemas import CandidateMarket


router = APIRouter()


class RankedMarket(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    market_id: str
    market_name: str
    condition_id: str
    side: Literal["YES", "NO"]
    score: float = Field(..., ge=0)
    ev_adj: float
    feasibility: float = Field(..., ge=0, le=1)
    confidence: float = Field(..., ge=0, le=1)
    spread_pct: float = Field(..., ge=0)
    volume_24h_usd: float = Field(..., ge=0)
    time_to_close_seconds: int = Field(..., ge=0)
    selected: bool = False
    cooldown_protected: bool = False


class RankedUniverse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ranked_at: datetime
    total_candidates: int
    selected_markets: List[RankedMarket]
    excluded_markets: List[str]
    ranking_method: str
    cooldown_protected: List[str]
    candidate_markets: List[RankedMarket]


@router.get("/ranking/current", response_model=RankedUniverse, summary="Get current ranked universe")
async def get_current_ranked_universe(db: Session = Depends(get_db)) -> RankedUniverse:
    now = datetime.now(timezone.utc)
    try:
        rows = db.execute(
            text(
                """
                SELECT
                  s.session_id,
                  s.market_condition_id,
                  s.market_slug,
                  s.token_id_yes,
                  s.token_id_no,
                  s.window_end,
                  COALESCE(m.question, s.market_slug) AS question,
                  COALESCE(m.slug, s.market_slug) AS slug,
                  COALESCE(m.total_volume, 0) AS total_volume,
                  COALESCE(m.fees_enabled, s.fees_enabled, TRUE) AS fees_enabled,
                  m.fee_rate_bps AS fee_rate_bps,
                  ob.timestamp AS ob_ts,
                  ob.best_bid AS best_bid,
                  ob.best_ask AS best_ask,
                  ob.midpoint AS midpoint,
                  ob.spread AS spread,
                  ob.bid_depth_1pct AS bid_depth,
                  ob.ask_depth_1pct AS ask_depth
                FROM pm.sessions s
                LEFT JOIN pm.market_metadata m
                  ON m.condition_id = s.market_condition_id
                LEFT JOIN LATERAL (
                  SELECT *
                  FROM pm.orderbook_snapshots
                  WHERE session_id = s.session_id
                  ORDER BY timestamp DESC
                  LIMIT 1
                ) ob ON TRUE
                WHERE s.status IN ('ACTIVE', 'WIND_DOWN')
                  AND s.window_end > (NOW() - INTERVAL '1 hour')
                ORDER BY s.window_end ASC
                LIMIT 250
                """
            )
        ).mappings().all()
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Ranking not available (DB not configured or migrations not applied)",
        ) from exc

    candidates: List[CandidateMarket] = []
    for r in rows:
        condition_id = str(r.get("market_condition_id") or "")
        token_yes = str(r.get("token_id_yes") or "")
        token_no = str(r.get("token_id_no") or "")
        if not condition_id or not token_yes or not token_no:
            continue

        best_bid = r.get("best_bid")
        best_ask = r.get("best_ask")
        midpoint = r.get("midpoint")
        if midpoint is None and best_bid is not None and best_ask is not None:
            midpoint = (Decimal(str(best_bid)) + Decimal(str(best_ask))) / Decimal("2")
        if midpoint is None:
            continue

        p_yes = Decimal(str(midpoint))
        if p_yes < 0:
            p_yes = Decimal("0")
        if p_yes > 1:
            p_yes = Decimal("1")

        spread = Decimal(str(r.get("spread") or 0))
        spread_pct = (spread / p_yes) if p_yes > 0 else Decimal("0")
        spread_bps = spread_pct * Decimal("10000")

        bid_depth = Decimal(str(r.get("bid_depth") or 0))
        ask_depth = Decimal(str(r.get("ask_depth") or 0))

        window_end = r.get("window_end")
        time_to_close = 0.0
        if isinstance(window_end, datetime):
            dt = window_end if window_end.tzinfo is not None else window_end.replace(tzinfo=timezone.utc)
            time_to_close = max((dt - now).total_seconds(), 0.0)

        staleness_seconds = 0.0
        ob_ts = r.get("ob_ts")
        if isinstance(ob_ts, datetime):
            dt = ob_ts if ob_ts.tzinfo is not None else ob_ts.replace(tzinfo=timezone.utc)
            staleness_seconds = max((now - dt).total_seconds(), 0.0)

        total_volume = Decimal(str(r.get("total_volume") or 0))
        fee_rate_bps = r.get("fee_rate_bps")

        meta = {
            "session_id": str(r.get("session_id")),
            "question": str(r.get("question") or ""),
            "slug": str(r.get("slug") or ""),
        }

        candidates.append(
            CandidateMarket(
                market_id=token_yes,
                condition_id=condition_id,
                token_id=token_yes,
                side="YES",
                slug=str(r.get("slug") or None),
                question=str(r.get("question") or None),
                total_volume_usd=total_volume,
                spread=spread,
                spread_pct=spread_pct,
                spread_bps=spread_bps,
                book_depth_bid_5tick=bid_depth,
                book_depth_ask_5tick=ask_depth,
                time_to_close_seconds=time_to_close,
                p_pm=p_yes,
                fees_enabled=bool(r.get("fees_enabled")),
                fee_rate_bps=Decimal(str(fee_rate_bps)) if fee_rate_bps is not None else None,
                staleness_seconds=staleness_seconds,
                last_updated=ob_ts,
                metadata=meta,
            )
        )
        candidates.append(
            CandidateMarket(
                market_id=token_no,
                condition_id=condition_id,
                token_id=token_no,
                side="NO",
                slug=str(r.get("slug") or None),
                question=str(r.get("question") or None),
                total_volume_usd=total_volume,
                spread=spread,
                spread_pct=spread_pct,
                spread_bps=spread_bps,
                book_depth_bid_5tick=bid_depth,
                book_depth_ask_5tick=ask_depth,
                time_to_close_seconds=time_to_close,
                p_pm=Decimal("1") - p_yes,
                fees_enabled=bool(r.get("fees_enabled")),
                fee_rate_bps=Decimal(str(fee_rate_bps)) if fee_rate_bps is not None else None,
                staleness_seconds=staleness_seconds,
                last_updated=ob_ts,
                metadata=meta,
            )
        )

    if not candidates:
        raise HTTPException(status_code=503, detail="Ranking not available (no eligible candidates found)")

    ranker = MarketRanker()
    ranked = ranker.rank_once(candidates, now=now)

    selected_ids = {entry.candidate.market_id for entry in ranked.selected_markets}
    cooldown_ids = set(ranked.cooldown_protected)

    scored = [ranker.score_candidate(c) for c in candidates]
    candidate_markets: List[RankedMarket] = []
    for entry in scored:
        c = entry.candidate
        candidate_markets.append(
            RankedMarket(
                market_id=c.market_id,
                market_name=str(c.question or c.slug or c.market_id),
                condition_id=c.condition_id,
                side=c.side,  # type: ignore[arg-type]
                score=float(entry.score),
                ev_adj=float(entry.edge.ev_adj),
                feasibility=float(entry.feasibility.feasibility_score),
                confidence=float(entry.confidence),
                spread_pct=float(c.spread_pct),
                volume_24h_usd=float(c.total_volume_usd),
                time_to_close_seconds=int(max(c.time_to_close_seconds, 0.0)),
                selected=c.market_id in selected_ids,
                cooldown_protected=c.market_id in cooldown_ids,
            )
        )

    selected_markets = [m for m in candidate_markets if m.selected]

    response = RankedUniverse(
        ranked_at=ranked.ranked_at,
        total_candidates=len(candidates),
        selected_markets=selected_markets,
        excluded_markets=ranked.excluded_markets,
        ranking_method=ranked.ranking_method,
        cooldown_protected=ranked.cooldown_protected,
        candidate_markets=candidate_markets,
    )

    try:
        db.execute(
            text("INSERT INTO pm.ranked_universe_snapshots (ranked_at, payload) VALUES (:t, :p::jsonb)"),
            {"t": response.ranked_at, "p": json.dumps(response.model_dump(mode="json"), default=str)},
        )
        db.commit()
    except Exception:
        db.rollback()

    return response
