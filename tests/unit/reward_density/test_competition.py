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


from services.reward_density.competition import CompetitionEstimator


def _make_event(maker: str, fee: int) -> "OrderFilledEvent":
    return OrderFilledEvent(
        maker=maker,
        taker="0x0",
        maker_asset_id="123",
        taker_asset_id="456",
        maker_amount_filled=1000,
        taker_amount_filled=900,
        fee=fee,
        block_number=1,
        tx_hash="0x00",
    )


def test_hhi_single_maker() -> None:
    events = [_make_event("0xA", 100), _make_event("0xA", 200)]
    estimator = CompetitionEstimator()
    metric = estimator.compute("mkt1", events)
    assert float(metric.hhi) == pytest.approx(1.0, abs=1e-9)
    assert float(metric.n_eff) == pytest.approx(1.0, abs=1e-9)
    assert metric.top_maker_address == "0xA"
    assert float(metric.top_maker_share) == pytest.approx(1.0, abs=1e-9)


def test_hhi_equal_distribution() -> None:
    events = [_make_event(f"0x{i:X}", 100) for i in range(4)]
    estimator = CompetitionEstimator()
    metric = estimator.compute("mkt1", events)
    # 4 equal makers → HHI = 4 * (0.25)^2 = 0.25, N_eff = 4
    assert float(metric.hhi) == pytest.approx(0.25, abs=1e-9)
    assert float(metric.n_eff) == pytest.approx(4.0, abs=1e-9)


def test_hhi_no_events_fallback() -> None:
    estimator = CompetitionEstimator()
    metric = estimator.compute("mkt1", [])
    assert metric.is_estimate is True
    assert metric.data_source == "rewards_api_proxy"
