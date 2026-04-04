"""
Market-type-aware signal schemas shared across all strategies.

These extend (not replace) the existing packages/common/schemas.py.
Import from here when building new strategies or the portfolio allocator.
"""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class MarketType(str, Enum):
    """Supported market surfaces."""

    EQUITY = "EQUITY"
    PREDICTION = "PREDICTION"
    CRYPTO = "CRYPTO"


class SignalType(str, Enum):
    """Classification of what a signal instructs execution to do."""

    DIRECTIONAL = "DIRECTIONAL"  # take / exit a position
    MARKET_MAKING = "MARKET_MAKING"  # post two-sided quotes
    HYBRID = "HYBRID"  # directional + quote skew combined


class UnifiedSignal(BaseModel):
    """
    Universal signal emitted by any strategy, for any market.

    The portfolio allocator and risk layer consume this; downstream
    execution adapters translate it into market-specific orders.
    """

    signal_id: UUID = Field(default_factory=uuid4)
    strategy_id: str = Field(..., description="ID of the emitting strategy")

    # What and where
    asset_id: str = Field(
        ...,
        description="Symbol (equities) or market condition ID (prediction)",
    )
    market_type: MarketType = Field(..., description="Market surface")
    signal_type: SignalType = Field(..., description="Execution intent")

    # Direction: 'long', 'short', or 'none' (for pure MM signals)
    direction: Literal["long", "short", "none"] = Field(
        ..., description="Directional intent"
    )

    # Confidence 0–1 (used by confidence gating)
    confidence: Decimal = Field(
        ...,
        ge=Decimal("0"),
        le=Decimal("1"),
        description="Model/rule confidence 0–1",
    )

    # How long is this signal valid?
    horizon_seconds: int = Field(
        ..., gt=0, description="Expected signal validity in seconds"
    )

    # Strategy-specific extras (spread params, model outputs, etc.)
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Strategy-specific payload (not interpreted by allocator)",
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
