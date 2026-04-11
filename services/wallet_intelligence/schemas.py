from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Literal, Optional

from pydantic import BaseModel


class WalletProfile(BaseModel):
    wallet_address: str
    profiled_at: datetime
    total_volume_usd: Decimal
    total_pnl_usd: Decimal
    win_rate: Decimal
    avg_position_size: Decimal
    preferred_markets: List[str]
    role: Literal["maker", "taker", "mixed"]
    activity_hours: List[int]
    last_active_at: datetime
    cluster_id: Optional[int] = None


class WalletCluster(BaseModel):
    cluster_id: int
    label: Literal["informed_directionals", "efficient_makers", "noise_traders", "opportunists"]
    wallet_count: int
    avg_maker_fraction: Decimal
    avg_win_rate: Decimal


class WalletSignal(BaseModel):
    market_id: str
    computed_at: datetime
    net_smart_money_position: Decimal
    smart_money_consensus: Decimal       # -1 to +1
    smart_money_activity_zscore: Decimal
    top_wallet_direction: Optional[Literal["long", "short", "flat"]] = None
    signal_confidence: Decimal
    wallet_count: int
