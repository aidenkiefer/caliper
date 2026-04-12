"""
Integration test: FeatureSnapshot → WalletSignal → AggregatedSignal.
Tests AC-10: full signal aggregation pipeline from synthetic data.
"""
import pytest
from decimal import Decimal
from datetime import datetime, timezone

from services.wallet_intelligence.signals import WalletSignalExtractor
from services.signal_aggregation.aggregator import SignalAggregator
from services.reward_density.competition import CompetitionEstimator
from services.reward_density.incentives import IncentiveEstimator
from services.reward_density.risk_scorer import RiskScorer
from services.reward_density.analyzer import RewardDensityAnalyzer
from services.reward_density.onchain.polygon_client import OrderFilledEvent


def _fill(maker: str, fee: int) -> OrderFilledEvent:
    return OrderFilledEvent(
        maker=maker,
        taker="0x0",
        maker_asset_id="TOKEN_YES",
        taker_asset_id="TOKEN_NO",
        maker_amount_filled=1000,
        taker_amount_filled=990,
        fee=fee,
        block_number=1,
        tx_hash="0x" + "ff" * 32,
    )


def test_full_reward_density_pipeline() -> None:
    """End-to-end: on-chain events → competition → incentives → density score."""
    events = [
        _fill("0xMaker1", 200),
        _fill("0xMaker1", 300),
        _fill("0xMaker2", 100),
    ]

    competition = CompetitionEstimator().compute("mkt1", events)
    assert float(competition.n_eff) == pytest.approx(1 / float(competition.hhi), rel=1e-6)

    incentive = IncentiveEstimator().estimate(
        market_id="mkt1",
        volume_7d_avg=Decimal("5000"),
        avg_price=Decimal("0.55"),
        n_eff=competition.n_eff,
        historical_fill_rate=None,
        lr_pool_per_day=Decimal("10"),
        lr_max_spread=Decimal("0.05"),
        lr_min_size=Decimal("20"),
        our_spread=Decimal("0.02"),
        our_size=Decimal("50"),
    )
    assert float(incentive.expected_total_usd) > 0

    risk_scores = RiskScorer().compute_cross_sectional(
        [{"market_id": "mkt1", "btc_rv": Decimal("0.015"), "toxicity": Decimal("0.2")}]
    )

    density = RewardDensityAnalyzer().score(
        market_id="mkt1",
        incentive=incentive,
        competition=competition,
        risk_score=risk_scores["mkt1"],
    )
    assert float(density.reward_density_score) >= 0


def test_full_signal_aggregation_pipeline() -> None:
    """End-to-end: WalletSignal + synthetic model/micro signals → AggregatedSignal."""
    smart_money = {"0xSmart1", "0xSmart2"}
    extractor = WalletSignalExtractor(smart_money_addresses=smart_money)

    fills = [
        OrderFilledEvent(
            maker="0xSmart1",
            taker="0xOther",
            maker_asset_id="YES_TOKEN",
            taker_asset_id="NO_TOKEN",
            maker_amount_filled=1000,
            taker_amount_filled=990,
            fee=2,
            block_number=1,
            tx_hash="0x" + "aa" * 32,
        ),
        OrderFilledEvent(
            maker="0xSmart2",
            taker="0xOther",
            maker_asset_id="YES_TOKEN",
            taker_asset_id="NO_TOKEN",
            maker_amount_filled=800,
            taker_amount_filled=795,
            fee=1,
            block_number=2,
            tx_hash="0x" + "bb" * 32,
        ),
    ]

    wallet_sig = extractor.compute("mkt1", fills, asset_id_yes="YES_TOKEN")
    assert wallet_sig.wallet_count == 2

    # Build history for z-scoring (10 past ticks with variance)
    history = [
        {"model": Decimal(str(i * 0.1)), "wallet": Decimal(str(i * 0.05)), "micro": Decimal(str(i * 0.02))}
        for i in range(10)
    ]

    agg = SignalAggregator()
    result = agg.aggregate(
        market_id="mkt1",
        model_signal=Decimal("0.4"),
        wallet_signal=wallet_sig.smart_money_consensus,
        microstructure_signal=Decimal("0.1"),
        history=history,
    )
    assert result.market_id == "mkt1"
    assert isinstance(result.threshold_met, bool)
    assert result.signal_strength in ("strong", "moderate", "weak", "none")
