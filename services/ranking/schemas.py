from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


RankingSide = Literal["YES", "NO"]


class CandidateMarket(BaseModel):
    """Side-specific candidate market used by the cross-sectional ranker."""

    model_config = ConfigDict(extra="forbid")

    market_id: str = Field(..., description="Unique candidate id, usually token id")
    condition_id: str = Field(..., description="Polymarket condition id shared by YES/NO")
    token_id: str = Field(..., description="Token id for this side")
    side: RankingSide = Field(..., description="YES or NO")

    slug: Optional[str] = None
    question: Optional[str] = None
    market_type: Optional[str] = None

    active: bool = True
    closed: bool = False
    fees_enabled: bool = True
    reward_eligible: bool = False

    total_volume_usd: Decimal = Decimal("0")
    spread: Decimal = Decimal("0")
    spread_pct: Decimal = Decimal("0")
    spread_bps: Decimal = Decimal("0")
    book_depth_bid_5tick: Decimal = Decimal("0")
    book_depth_ask_5tick: Decimal = Decimal("0")
    time_to_close_seconds: float = 0.0

    p_pm: Decimal = Decimal("0.5")
    p_hat: Optional[Decimal] = None
    sigma: Decimal = Decimal("1")
    confidence: Decimal = Decimal("1")

    recent_trade_intensity: Decimal = Decimal("0")
    queue_position_proxy: Decimal = Decimal("0.5")
    fee_rate_bps: Optional[Decimal] = None
    reward_max_spread: Optional[Decimal] = None
    reward_min_size: Optional[Decimal] = None
    staleness_seconds: float = 0.0
    last_updated: Optional[datetime] = None

    metadata: Dict[str, Any] = Field(default_factory=dict)


class EdgeEstimate(BaseModel):
    """Cost-adjusted edge decomposition for one candidate market."""

    model_config = ConfigDict(extra="forbid")

    p_hat: Decimal
    p_pm: Decimal
    ev_raw: Decimal
    ev_adj: Decimal
    half_spread: Decimal
    slippage_estimate: Decimal
    fee_edge: Decimal
    staleness_seconds: float
    decay_factor: float = 1.0
    low_confidence: bool = False


class FeasibilityReport(BaseModel):
    """Executability and fill-probability breakdown for one candidate market."""

    model_config = ConfigDict(extra="forbid")

    liquidity_score: float
    normalized_liquidity: float
    fill_probability: float
    feasibility_score: float
    exclude: bool = False
    exclusion_reason: Optional[str] = None


class MarketScore(BaseModel):
    """Composite ranking result for one candidate market."""

    model_config = ConfigDict(extra="forbid")

    candidate: CandidateMarket
    edge: EdgeEstimate
    feasibility: FeasibilityReport
    sigma: float
    confidence: float
    score: float
    selected: bool = False
    excluded: bool = False
    exclusion_reason: Optional[str] = None
    rank: Optional[int] = None


class RankedUniverse(BaseModel):
    """Ranked cross-sectional market universe produced by the ranker."""

    model_config = ConfigDict(extra="forbid")

    ranked_at: datetime
    total_candidates: int
    selected_markets: List[MarketScore]
    excluded_markets: List[str]
    ranking_method: str
    cooldown_protected: List[str]

