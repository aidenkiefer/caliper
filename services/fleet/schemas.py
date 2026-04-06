from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator

from packages.common.market_schemas import MarketType, SignalType
from packages.common.schemas import TradingMode


class StrategyLifecycle(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COOLDOWN = "cooldown"
    ABSTAIN = "abstain"
    ERROR = "error"


class StrategyStatus(BaseModel):
    strategy_id: str
    market_type: MarketType
    status: StrategyLifecycle = StrategyLifecycle.ACTIVE
    current_allocation_weight: Decimal = Decimal("0")
    pnl_24h: Decimal = Decimal("0")
    sharpe_7d: Optional[Decimal] = None
    fill_rate: Optional[Decimal] = None
    active_market_id: Optional[str] = None
    last_signal_at: Optional[datetime] = None
    last_action: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SignalLogEntry(BaseModel):
    recorded_at: datetime
    strategy_id: str
    market_id: str
    signal_type: SignalType
    direction: Literal["long", "short", "none"]
    confidence: Decimal
    action_taken: Literal["executed", "rejected", "abstained"]
    fill_price: Optional[Decimal] = None
    quantity: Optional[Decimal] = None
    regime: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FleetStatus(BaseModel):
    captured_at: datetime
    mode: TradingMode
    status: Literal["running", "paused", "stopped"] = "running"
    strategies: List[StrategyStatus] = Field(default_factory=list)
    active_markets: List[str] = Field(default_factory=list)
    overall_pnl_24h: Decimal = Decimal("0")
    overall_sharpe_7d: Optional[Decimal] = None
    paper_mode: bool = True
    signal_log: List[SignalLogEntry] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PaperTrade(BaseModel):
    trade_id: UUID = Field(default_factory=uuid4)
    executed_at: datetime
    strategy_id: str
    market_id: str
    signal_type: SignalType
    direction: Literal["long", "short", "none"]
    side: Literal["BUY", "SELL", "NONE"]
    price: Decimal
    quantity: Decimal
    notional: Decimal
    confidence: Decimal = Field(..., ge=Decimal("0"), le=Decimal("1"))
    status: Literal["paper_filled", "paper_rejected", "paper_abstained"] = "paper_filled"
    regime: Optional[str] = None
    allocation_weight: Decimal = Decimal("0")
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def ensure_notional(self) -> "PaperTrade":
        if self.notional <= Decimal("0") and self.price > Decimal("0") and self.quantity > Decimal("0"):
            self.notional = self.price * self.quantity
        return self

