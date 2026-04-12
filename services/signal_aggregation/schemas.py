# services/signal_aggregation/schemas.py
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Dict, Literal

from pydantic import BaseModel


class AggregatedSignal(BaseModel):
    market_id: str
    aggregated_at: datetime
    final_signal: Decimal         # -1 to +1; positive = bullish
    model_component: Decimal      # z-scored
    wallet_component: Decimal     # z-scored
    microstructure_component: Decimal  # z-scored
    weights: Dict[str, Decimal]
    threshold_met: bool
    signal_strength: Literal["strong", "moderate", "weak", "none"]
