# tests/unit/reward_density/test_competition.py
import pytest
from services.reward_density.onchain.polygon_client import PolygonClient, OrderFilledEvent


def test_order_filled_event_model() -> None:
    evt = OrderFilledEvent(
        maker="0xabc",
        taker="0xdef",
        maker_asset_id="0x" + "00" * 32,
        taker_asset_id="0x" + "01" * 32,
        maker_amount_filled=1_000_000,
        taker_amount_filled=500_000,
        fee=100,
        block_number=12345,
        tx_hash="0x" + "aa" * 32,
    )
    assert evt.maker == "0xabc"
    assert evt.fee == 100


def test_polygon_client_init_no_rpc() -> None:
    """Client initialises without connecting when no RPC URL is set."""
    client = PolygonClient(rpc_url=None)
    assert client.rpc_url is None
