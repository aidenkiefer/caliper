from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Set

from services.reward_density.onchain.polygon_client import OrderFilledEvent
from services.wallet_intelligence.schemas import WalletSignal


class WalletSignalExtractor:
    """Extracts smart-money consensus signals from recent OrderFilled events."""

    def __init__(self, smart_money_addresses: Set[str]) -> None:
        self.smart_money_addresses = {addr.lower() for addr in smart_money_addresses}

    def compute(
        self,
        market_id: str,
        recent_fills: List[OrderFilledEvent],
        asset_id_yes: str,
    ) -> WalletSignal:
        now = datetime.now(timezone.utc)

        # Filter to fills involving smart money
        sm_fills = [
            f for f in recent_fills
            if f.maker.lower() in self.smart_money_addresses
            or f.taker.lower() in self.smart_money_addresses
        ]

        if not sm_fills:
            return WalletSignal(
                market_id=market_id,
                computed_at=now,
                net_smart_money_position=Decimal("0"),
                smart_money_consensus=Decimal("0"),
                smart_money_activity_zscore=Decimal("0"),
                top_wallet_direction=None,
                signal_confidence=Decimal("0"),
                wallet_count=0,
            )

        # Compute net position per smart money wallet
        net_by_wallet: dict[str, int] = defaultdict(int)
        for f in sm_fills:
            maker_lower = f.maker.lower()
            taker_lower = f.taker.lower()
            if maker_lower in self.smart_money_addresses:
                sign = 1 if str(f.maker_asset_id) == asset_id_yes else -1
                net_by_wallet[maker_lower] += sign * f.maker_amount_filled
            if taker_lower in self.smart_money_addresses:
                sign = -1 if str(f.taker_asset_id) == asset_id_yes else 1
                net_by_wallet[taker_lower] += sign * f.taker_amount_filled

        wallet_count = len(net_by_wallet)
        net_total = sum(net_by_wallet.values())

        # Normalize to [-1, +1]
        max_abs = max(abs(v) for v in net_by_wallet.values()) if net_by_wallet else 1
        consensus = Decimal(str(net_total)) / Decimal(str(max_abs)) if max_abs > 0 else Decimal("0")
        consensus = max(Decimal("-1"), min(Decimal("1"), consensus))

        # Confidence scales with wallet count
        if wallet_count == 0:
            confidence = Decimal("0")
        elif wallet_count < 3:
            confidence = Decimal("0.3")
        elif wallet_count < 5:
            confidence = Decimal("0.6")
        else:
            confidence = Decimal("0.9")

        if consensus > Decimal("0.1"):
            direction = "long"
        elif consensus < Decimal("-0.1"):
            direction = "short"
        else:
            direction = "flat"

        return WalletSignal(
            market_id=market_id,
            computed_at=now,
            net_smart_money_position=Decimal(str(net_total)),
            smart_money_consensus=consensus,
            smart_money_activity_zscore=Decimal("0"),
            top_wallet_direction=direction,  # type: ignore[arg-type]
            signal_confidence=confidence,
            wallet_count=wallet_count,
        )
