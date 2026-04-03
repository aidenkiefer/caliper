"""
Unit tests for services/polymarket/adapters/data_api_client.py
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from services.polymarket.adapters.data_api_client import DataAPIClient
from services.polymarket.adapters.gamma_client import APIError, RateLimitError


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_config() -> MagicMock:
    """Return a minimal PolymarketConfig-like mock."""
    cfg = MagicMock()
    cfg.wallet_address = "0xWALLET"
    return cfg


def _make_http_client(response: MagicMock) -> MagicMock:
    """Return an AsyncClient mock whose .get() always returns *response*."""
    client = MagicMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=response)
    return client


def _make_response(body: object, status_code: int = 200) -> MagicMock:
    """Return a mock httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = body
    resp.text = json.dumps(body)
    return resp


def _make_trade(
    *,
    timestamp: int = 1743000000,
    price: str = "0.65",
    size: str = "100",
    side: str = "BUY",
    maker_address: str = "0xMAKER",
    taker_address: str = "0xTAKER",
    fee_rate_bps: int = 100,
) -> dict:
    """Return a dict mimicking a single Data API trade record."""
    return {
        "id": "trade-1",
        "timestamp": timestamp,
        "price": price,
        "size": size,
        "side": side,
        "maker_address": maker_address,
        "taker_address": taker_address,
        "fee_rate_bps": fee_rate_bps,
    }


_START = datetime(2026, 3, 25, 0, 0, 0, tzinfo=timezone.utc)
_END = datetime(2026, 3, 25, 1, 0, 0, tzinfo=timezone.utc)
_TOKEN_ID = "0xTOKEN"
_WALLET = "0xWALLET"


# ---------------------------------------------------------------------------
# test_get_trades_success — single page of results
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_trades_success():
    """DataAPIClient returns parsed trade dicts for a single-page response."""
    trades_raw = [
        _make_trade(price="0.65", size="100", side="BUY"),
        _make_trade(price="0.66", size="50", side="SELL"),
    ]
    body = {"data": trades_raw, "next_cursor": None}
    http_client = _make_http_client(_make_response(body))
    client = DataAPIClient(config=_make_config(), http_client=http_client)

    result = await client.get_trades(_TOKEN_ID, _START, _END)

    assert len(result) == 2
    assert result[0]["price"] == "0.65"
    assert result[0]["side"] == "BUY"
    assert result[0]["maker_address"] == "0xMAKER"
    assert result[0]["taker_address"] == "0xTAKER"
    assert result[1]["price"] == "0.66"
    assert result[1]["side"] == "SELL"


# ---------------------------------------------------------------------------
# test_get_trades_pagination — follows next_cursor across 2+ pages
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_trades_pagination():
    """DataAPIClient follows next_cursor until exhausted."""
    page1_body = {"data": [_make_trade(price="0.60")], "next_cursor": "cursor-abc"}
    page2_body = {"data": [_make_trade(price="0.61")], "next_cursor": "LTE="}

    http_client = MagicMock(spec=httpx.AsyncClient)
    http_client.get = AsyncMock(
        side_effect=[
            _make_response(page1_body),
            _make_response(page2_body),
        ]
    )
    client = DataAPIClient(config=_make_config(), http_client=http_client)

    result = await client.get_trades(_TOKEN_ID, _START, _END)

    assert len(result) == 2
    assert result[0]["price"] == "0.60"
    assert result[1]["price"] == "0.61"
    assert http_client.get.call_count == 2


# ---------------------------------------------------------------------------
# test_get_trades_date_range_filtering — correct unix timestamps in request
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_trades_date_range_filtering():
    """DataAPIClient sends correct Unix timestamps for start_time and end_time."""
    body = {"data": [], "next_cursor": None}
    http_client = _make_http_client(_make_response(body))
    client = DataAPIClient(config=_make_config(), http_client=http_client)

    await client.get_trades(_TOKEN_ID, _START, _END)

    call_kwargs = http_client.get.call_args
    params = call_kwargs.kwargs.get("params") or call_kwargs.args[1]
    assert params["startTime"] == int(_START.timestamp())
    assert params["endTime"] == int(_END.timestamp())
    assert params["token_id"] == _TOKEN_ID


# ---------------------------------------------------------------------------
# test_get_trades_api_error — 500 response raises exception
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_trades_api_error():
    """A persistent 500 response raises APIError after exhausting retries."""
    http_client = MagicMock(spec=httpx.AsyncClient)
    http_client.get = AsyncMock(return_value=_make_response({}, status_code=500))
    client = DataAPIClient(config=_make_config(), http_client=http_client)

    with patch(
        "services.polymarket.adapters.data_api_client.asyncio.sleep",
        new=AsyncMock(),
    ):
        with pytest.raises(APIError):
            await client.get_trades(_TOKEN_ID, _START, _END)

    # 1 initial attempt + 3 retries = 4 total
    assert http_client.get.call_count == 4


# ---------------------------------------------------------------------------
# test_get_activity_success
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_activity_success():
    """get_activity returns a list of activity records."""
    activity_records = [
        {"type": "TRADE", "amount": "100", "timestamp": 1743000000},
        {"type": "DEPOSIT", "amount": "500", "timestamp": 1743001000},
    ]
    body = {"data": activity_records}
    http_client = _make_http_client(_make_response(body))
    client = DataAPIClient(config=_make_config(), http_client=http_client)

    result = await client.get_activity(_WALLET, _START, _END)

    assert len(result) == 2
    assert result[0]["type"] == "TRADE"
    assert result[1]["type"] == "DEPOSIT"


@pytest.mark.asyncio
async def test_get_activity_list_response():
    """get_activity handles a plain-list response (no wrapping dict)."""
    activity_records = [{"type": "TRADE", "amount": "100", "timestamp": 1743000000}]
    http_client = _make_http_client(_make_response(activity_records))
    client = DataAPIClient(config=_make_config(), http_client=http_client)

    result = await client.get_activity(_WALLET, _START, _END)

    assert len(result) == 1
    assert result[0]["type"] == "TRADE"


# ---------------------------------------------------------------------------
# test_get_rebates_success
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_rebates_success():
    """get_rebates returns a rebate dict for a given wallet and date."""
    rebate_body = {
        "user": _WALLET,
        "date": "2026-03-25",
        "rebate_amount": "2.50",
        "volume": "500",
    }
    http_client = _make_http_client(_make_response(rebate_body))
    client = DataAPIClient(config=_make_config(), http_client=http_client)

    result = await client.get_rebates(_WALLET, date(2026, 3, 25))

    assert result["rebate_amount"] == "2.50"
    assert result["date"] == "2026-03-25"

    call_kwargs = http_client.get.call_args
    params = call_kwargs.kwargs.get("params") or call_kwargs.args[1]
    assert params["user"] == _WALLET
    assert params["date"] == "2026-03-25"


@pytest.mark.asyncio
async def test_get_rebates_list_response():
    """get_rebates handles a list-wrapped response, returning the first item."""
    rebate_record = {"user": _WALLET, "date": "2026-03-25", "rebate_amount": "1.00"}
    http_client = _make_http_client(_make_response([rebate_record]))
    client = DataAPIClient(config=_make_config(), http_client=http_client)

    result = await client.get_rebates(_WALLET, date(2026, 3, 25))

    assert result["rebate_amount"] == "1.00"


# ---------------------------------------------------------------------------
# test_rate_limit_retry — 429 triggers retry with backoff
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rate_limit_retry():
    """A 429 response triggers a retry; the subsequent 200 succeeds."""
    trades_raw = [_make_trade(price="0.70")]
    resp_429 = _make_response({}, status_code=429)
    resp_200 = _make_response({"data": trades_raw, "next_cursor": None})

    http_client = MagicMock(spec=httpx.AsyncClient)
    http_client.get = AsyncMock(side_effect=[resp_429, resp_200])
    client = DataAPIClient(config=_make_config(), http_client=http_client)

    with patch(
        "services.polymarket.adapters.data_api_client.asyncio.sleep",
        new=AsyncMock(),
    ) as mock_sleep:
        result = await client.get_trades(_TOKEN_ID, _START, _END)

    assert len(result) == 1
    assert result[0]["price"] == "0.70"
    assert http_client.get.call_count == 2
    mock_sleep.assert_called_once()


@pytest.mark.asyncio
async def test_rate_limit_exhausted_raises():
    """RateLimitError is raised when all retries return 429."""
    http_client = MagicMock(spec=httpx.AsyncClient)
    http_client.get = AsyncMock(return_value=_make_response({}, status_code=429))
    client = DataAPIClient(config=_make_config(), http_client=http_client)

    with patch(
        "services.polymarket.adapters.data_api_client.asyncio.sleep",
        new=AsyncMock(),
    ):
        with pytest.raises(RateLimitError):
            await client.get_trades(_TOKEN_ID, _START, _END)


# ---------------------------------------------------------------------------
# test_naive_datetime_raises — timezone validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_naive_start_time_raises():
    """ValueError is raised when start_time is timezone-naive."""
    naive_start = datetime(2026, 3, 25, 0, 0, 0)  # no tzinfo
    http_client = _make_http_client(_make_response({}))
    client = DataAPIClient(config=_make_config(), http_client=http_client)

    with pytest.raises(ValueError, match="start_time"):
        await client.get_trades(_TOKEN_ID, naive_start, _END)


@pytest.mark.asyncio
async def test_naive_end_time_raises():
    """ValueError is raised when end_time is timezone-naive."""
    naive_end = datetime(2026, 3, 25, 1, 0, 0)  # no tzinfo
    http_client = _make_http_client(_make_response({}))
    client = DataAPIClient(config=_make_config(), http_client=http_client)

    with pytest.raises(ValueError, match="end_time"):
        await client.get_trades(_TOKEN_ID, _START, naive_end)
