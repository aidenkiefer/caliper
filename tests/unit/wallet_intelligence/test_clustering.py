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


from decimal import Decimal
from services.wallet_intelligence.profiler import WalletProfiler
from services.wallet_intelligence.ranker import WalletRanker
from services.reward_density.onchain.polygon_client import OrderFilledEvent


def _make_fill_event(maker: str, maker_amount: int, fee: int) -> OrderFilledEvent:
    return OrderFilledEvent(
        maker=maker,
        taker="0x0",
        maker_asset_id="111",
        taker_asset_id="222",
        maker_amount_filled=maker_amount,
        taker_amount_filled=maker_amount - 10,
        fee=fee,
        block_number=100,
        tx_hash="0x" + "bb" * 32,
    )


def test_profiler_role_maker() -> None:
    """AC-4: role='maker' when maker_fraction > 0.70."""
    profiler = WalletProfiler()
    fills = [_make_fill_event("0xA", 1000, 10) for _ in range(8)]  # 8 maker fills
    taker_fills = [
        OrderFilledEvent(
            maker="0xB",
            taker="0xA",
            maker_asset_id="111",
            taker_asset_id="222",
            maker_amount_filled=500,
            taker_amount_filled=490,
            fee=5,
            block_number=101,
            tx_hash="0x" + "cc" * 32,
        )
        for _ in range(2)
    ]
    profile = profiler.build_from_events(
        wallet_address="0xA",
        maker_fills=fills,
        taker_fills=taker_fills,
        pnl_usd=Decimal("200"),
        total_volume_usd=Decimal("10000"),
    )
    assert profile.role == "maker"


def test_ranker_top_wallets() -> None:
    ranker = WalletRanker()
    base = Decimal("100")
    daily_pnls = [base + Decimal(str(i * 10)) for i in range(7)]
    score = ranker.compute_wallet_score(daily_pnls_7d=daily_pnls, active_days_7d=7)
    assert score > Decimal("0")
