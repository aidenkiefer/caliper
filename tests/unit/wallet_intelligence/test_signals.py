# tests/unit/wallet_intelligence/test_signals.py
import pytest
from decimal import Decimal
from datetime import datetime, timezone

from services.wallet_intelligence.signals import WalletSignalExtractor
from services.reward_density.onchain.polygon_client import OrderFilledEvent


SMART_MONEY = {"0xA", "0xB", "0xC"}


def _fill(maker: str, amount: int, maker_side: bool = True) -> OrderFilledEvent:
    return OrderFilledEvent(
        maker=maker if maker_side else "0xOther",
        taker="0xOther" if maker_side else maker,
        maker_asset_id="YES_TOKEN",
        taker_asset_id="NO_TOKEN",
        maker_amount_filled=amount,
        taker_amount_filled=amount - 5,
        fee=1,
        block_number=1,
        tx_hash="0x" + "aa" * 32,
    )


def test_signal_consensus_bullish_when_net_long() -> None:
    """AC-6: consensus > 0.3 when smart money predominantly net long."""
    extractor = WalletSignalExtractor(smart_money_addresses=SMART_MONEY)
    fills = [_fill("0xA", 1000), _fill("0xB", 800), _fill("0xC", 600)]
    sig = extractor.compute(
        market_id="mkt1",
        recent_fills=fills,
        asset_id_yes="YES_TOKEN",
    )
    assert float(sig.smart_money_consensus) > 0.3


def test_signal_confidence_low_when_few_wallets() -> None:
    """AC-6: signal_confidence is low when fewer than 3 wallets contribute."""
    extractor = WalletSignalExtractor(smart_money_addresses=SMART_MONEY)
    fills = [_fill("0xA", 100)]  # only 1 wallet
    sig = extractor.compute(
        market_id="mkt1",
        recent_fills=fills,
        asset_id_yes="YES_TOKEN",
    )
    assert float(sig.signal_confidence) < 0.5
    assert sig.wallet_count == 1


def test_signal_zero_no_fills() -> None:
    extractor = WalletSignalExtractor(smart_money_addresses=SMART_MONEY)
    sig = extractor.compute(
        market_id="mkt1",
        recent_fills=[],
        asset_id_yes="YES_TOKEN",
    )
    assert float(sig.smart_money_consensus) == 0.0
    assert sig.wallet_count == 0
