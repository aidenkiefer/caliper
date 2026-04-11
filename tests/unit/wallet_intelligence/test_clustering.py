from datetime import datetime, timezone
from decimal import Decimal

from services.wallet_intelligence.schemas import WalletProfile, WalletSignal


def test_wallet_profile_fields() -> None:
    p = WalletProfile(
        wallet_address="0xABC",
        profiled_at=datetime.now(timezone.utc),
        total_volume_usd=Decimal("50000"),
        total_pnl_usd=Decimal("1000"),
        win_rate=Decimal("0.55"),
        avg_position_size=Decimal("200"),
        preferred_markets=["cond1", "cond2"],
        role="maker",
        activity_hours=[9, 10, 11],
        last_active_at=datetime.now(timezone.utc),
    )
    assert p.role == "maker"
    assert len(p.preferred_markets) == 2


def test_wallet_signal_consensus_range() -> None:
    sig = WalletSignal(
        market_id="mkt1",
        computed_at=datetime.now(timezone.utc),
        net_smart_money_position=Decimal("500"),
        smart_money_consensus=Decimal("0.4"),
        smart_money_activity_zscore=Decimal("1.8"),
        top_wallet_direction="long",
        signal_confidence=Decimal("0.75"),
        wallet_count=5,
    )
    assert sig.smart_money_consensus == Decimal("0.4")
    assert sig.top_wallet_direction == "long"
