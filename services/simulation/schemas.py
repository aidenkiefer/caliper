from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Literal
from pydantic import BaseModel


class SimEvent(BaseModel):
    event_id: str
    timestamp: datetime
    event_type: Literal["snapshot", "trade", "cancel"]
    market_id: str
    token_id: str
    payload: Dict[str, Any]


class SimOrder(BaseModel):
    order_id: str
    market_id: str
    token_id: str
    side: Literal["BUY", "SELL"]
    order_type: Literal["taker", "maker"]
    price: Decimal
    size: Decimal
    submit_time: datetime
    post_only: bool = False


class SimFill(BaseModel):
    fill_id: str
    order_id: str
    market_id: str
    token_id: str
    side: Literal["BUY", "SELL"]
    fill_price: Decimal
    fill_size: Decimal
    fill_time: datetime
    maker_fill: bool
    slippage_vs_mid: Decimal
    mid_at_fill: Decimal
    rebate_estimated: bool = False


@dataclass
class PnLComponents:
    spread_capture: Decimal = field(default_factory=lambda: Decimal(0))
    inventory_drift: Decimal = field(default_factory=lambda: Decimal(0))
    maker_rebate: Decimal = field(default_factory=lambda: Decimal(0))
    liquidity_reward: Decimal = field(default_factory=lambda: Decimal(0))
    taker_fee: Decimal = field(default_factory=lambda: Decimal(0))
    ops_cost: Decimal = field(default_factory=lambda: Decimal(0))

    @property
    def total(self) -> Decimal:
        return (self.spread_capture + self.inventory_drift + self.maker_rebate
                + self.liquidity_reward - self.taker_fee - self.ops_cost)


class SimResult(BaseModel):
    run_id: str
    strategy_id: str
    market_id: str
    start_time: datetime
    end_time: datetime
    fills: List[SimFill]
    pnl_components: Dict[str, Decimal]   # serialized PnLComponents
    total_pnl: Decimal
    fill_count: int
    fill_rate: Decimal
    maker_fill_rate: Decimal
    config: Dict[str, Any]
