# services/wallet_intelligence/profiler.py
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import List

from services.reward_density.onchain.polygon_client import OrderFilledEvent
from services.wallet_intelligence.schemas import WalletProfile


class WalletProfiler:
    """Builds WalletProfile from on-chain maker/taker fills."""

    def build_from_events(
        self,
        wallet_address: str,
        maker_fills: List[OrderFilledEvent],
        taker_fills: List[OrderFilledEvent],
        *,
        pnl_usd: Decimal,
        total_volume_usd: Decimal,
    ) -> WalletProfile:
        total_fills = len(maker_fills) + len(taker_fills)
        maker_fraction = (
            Decimal(str(len(maker_fills))) / Decimal(str(total_fills))
            if total_fills > 0
            else Decimal("0")
        )

        if maker_fraction > Decimal("0.70"):
            role = "maker"
        elif maker_fraction < Decimal("0.30"):
            role = "taker"
        else:
            role = "mixed"

        all_fills = maker_fills + taker_fills
        win_count = sum(1 for f in maker_fills if f.taker_amount_filled >= f.maker_amount_filled)
        win_rate = (
            Decimal(str(win_count)) / Decimal(str(len(maker_fills)))
            if len(maker_fills) > 0
            else Decimal("0")
        )

        all_amounts = [f.maker_amount_filled for f in all_fills]
        avg_size = (
            Decimal(str(sum(all_amounts) // len(all_amounts)))
            if all_amounts
            else Decimal("0")
        )

        condition_ids = list({str(f.maker_asset_id) for f in all_fills})[:5]

        now = datetime.now(timezone.utc)
        return WalletProfile(
            wallet_address=wallet_address,
            profiled_at=now,
            total_volume_usd=total_volume_usd,
            total_pnl_usd=pnl_usd,
            win_rate=win_rate,
            avg_position_size=avg_size,
            preferred_markets=condition_ids,
            role=role,  # type: ignore[arg-type]
            activity_hours=[],
            last_active_at=now,
        )
