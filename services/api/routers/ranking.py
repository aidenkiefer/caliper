from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import List, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

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


def _require_db_url() -> str:
    db_url = os.environ.get("DB_URL")
    if not db_url:
        raise HTTPException(status_code=503, detail="Ranking service not available")
    return db_url


def _mock_ranked_universe() -> RankedUniverse:
    ranked_at = datetime.now(tz=timezone.utc)
    candidates = [
        RankedMarket(
            market_id="btc-hourly-2026-04-06-09",
            market_name="BTC Hourly 09:00 UTC",
            condition_id="cond_btc_0900",
            side="YES",
            score=0.92,
            ev_adj=0.064,
            feasibility=0.88,
            confidence=0.81,
            spread_pct=0.011,
            volume_24h_usd=48250.0,
            time_to_close_seconds=1740,
            selected=True,
        ),
        RankedMarket(
            market_id="btc-hourly-2026-04-06-10",
            market_name="BTC Hourly 10:00 UTC",
            condition_id="cond_btc_1000",
            side="NO",
            score=0.86,
            ev_adj=0.051,
            feasibility=0.84,
            confidence=0.77,
            spread_pct=0.013,
            volume_24h_usd=36120.0,
            time_to_close_seconds=3120,
            selected=True,
        ),
        RankedMarket(
            market_id="btc-hourly-2026-04-06-08",
            market_name="BTC Hourly 08:00 UTC",
            condition_id="cond_btc_0800",
            side="YES",
            score=0.74,
            ev_adj=0.037,
            feasibility=0.79,
            confidence=0.72,
            spread_pct=0.015,
            volume_24h_usd=29510.0,
            time_to_close_seconds=840,
            selected=True,
            cooldown_protected=True,
        ),
        RankedMarket(
            market_id="btc-hourly-2026-04-06-07",
            market_name="BTC Hourly 07:00 UTC",
            condition_id="cond_btc_0700",
            side="YES",
            score=0.31,
            ev_adj=0.011,
            feasibility=0.46,
            confidence=0.55,
            spread_pct=0.021,
            volume_24h_usd=14820.0,
            time_to_close_seconds=3840,
            selected=False,
        ),
        RankedMarket(
            market_id="btc-hourly-2026-04-06-11",
            market_name="BTC Hourly 11:00 UTC",
            condition_id="cond_btc_1100",
            side="NO",
            score=0.18,
            ev_adj=-0.012,
            feasibility=0.19,
            confidence=0.39,
            spread_pct=0.032,
            volume_24h_usd=9800.0,
            time_to_close_seconds=4680,
            selected=False,
        ),
    ]
    selected = [market for market in candidates if market.selected]
    excluded = ["btc-hourly-2026-04-06-11"]
    return RankedUniverse(
        ranked_at=ranked_at,
        total_candidates=len(candidates),
        selected_markets=selected,
        excluded_markets=excluded,
        ranking_method="ev_adj_plus_feasibility_v1",
        cooldown_protected=["btc-hourly-2026-04-06-08"],
        candidate_markets=candidates,
    )


@router.get("/ranking/current", response_model=RankedUniverse, summary="Get current ranked universe")
async def get_current_ranked_universe(_db_url: str = Depends(_require_db_url)) -> RankedUniverse:
    return _mock_ranked_universe()
