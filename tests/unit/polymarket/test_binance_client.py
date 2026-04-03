"""
Unit tests for services.polymarket.adapters.binance_client.

All HTTP calls are mocked via httpx.AsyncClient injection — no real network I/O.
asyncio.sleep is patched so retry back-off tests run instantly.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from services.polymarket.adapters.binance_client import (
    BinanceAPIError,
    BinanceClient,
    CandleNotAvailableError,
    RateLimitError,
    _parse_candle,
    _to_ms,
)

# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

# A realistic Binance klines response row (index 0 of the outer array)
_SAMPLE_KLINE = [
    1640995200000,      # 0: open_time ms  (2022-01-01 00:00:00 UTC)
    "46421.66000000",   # 1: open
    "47000.00000000",   # 2: high
    "46000.00000000",   # 3: low
    "46800.00000000",   # 4: close
    "1234.56789000",    # 5: volume
    1640998799999,      # 6: close_time ms
    "57890123.45",      # 7: quote asset volume (ignored in output)
    100,                # 8: number of trades (ignored)
    "600.12345",        # 9: taker buy base (ignored)
    "27890123.45",      # 10: taker buy quote (ignored)
    "0",                # 11: ignore
]

_SAMPLE_DATETIME = datetime(2022, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


def _make_response(status_code: int, json_body=None, text: str = "") -> MagicMock:
    """Build a mock httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_body if json_body is not None else []
    resp.text = text
    return resp


def _make_client(responses: list) -> httpx.AsyncClient:
    """Return a mock AsyncClient whose .get() yields *responses* in order."""
    mock_client = MagicMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(side_effect=responses)
    return mock_client


# ---------------------------------------------------------------------------
# _to_ms helper
# ---------------------------------------------------------------------------


def test_to_ms_utc_datetime():
    dt = datetime(2022, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    assert _to_ms(dt) == 1640995200000


def test_to_ms_naive_datetime_raises():
    naive = datetime(2026, 3, 25, 14, 0, 0)  # no tzinfo
    with pytest.raises(ValueError, match="timezone-aware"):
        _to_ms(naive)


# ---------------------------------------------------------------------------
# _parse_candle helper
# ---------------------------------------------------------------------------


def test_parse_candle_types():
    candle = _parse_candle(_SAMPLE_KLINE)
    assert isinstance(candle["open_time"], datetime)
    assert candle["open_time"].tzinfo is not None
    assert isinstance(candle["open"], Decimal)
    assert isinstance(candle["high"], Decimal)
    assert isinstance(candle["low"], Decimal)
    assert isinstance(candle["close"], Decimal)
    assert isinstance(candle["volume"], Decimal)
    assert isinstance(candle["close_time"], datetime)


def test_parse_candle_values():
    candle = _parse_candle(_SAMPLE_KLINE)
    assert candle["open"] == Decimal("46421.66000000")
    assert candle["high"] == Decimal("47000.00000000")
    assert candle["low"] == Decimal("46000.00000000")
    assert candle["close"] == Decimal("46800.00000000")
    assert candle["volume"] == Decimal("1234.56789000")
    assert candle["open_time"] == datetime(2022, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# 1. test_get_1h_candle_success
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_1h_candle_success():
    """Successful fetch returns a dict with correct types and values."""
    mock_client = _make_client([_make_response(200, json_body=[_SAMPLE_KLINE])])
    client = BinanceClient(httpx_client=mock_client)

    candle = await client.get_1h_candle("BTCUSDT", _SAMPLE_DATETIME)

    assert candle["open"] == Decimal("46421.66000000")
    assert candle["close"] == Decimal("46800.00000000")
    assert candle["open_time"] == datetime(2022, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    assert isinstance(candle["volume"], Decimal)

    # Verify the API was called with correct params
    call_kwargs = mock_client.get.call_args
    params = call_kwargs[1]["params"] if "params" in call_kwargs[1] else call_kwargs[0][1]
    assert params["interval"] == "1h"
    assert params["symbol"] == "BTCUSDT"
    assert params["limit"] == 1


# ---------------------------------------------------------------------------
# 2. test_get_1h_candle_not_available
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_1h_candle_not_available():
    """Empty response (candle not yet closed) raises CandleNotAvailableError."""
    mock_client = _make_client([_make_response(200, json_body=[])])
    client = BinanceClient(httpx_client=mock_client)

    with pytest.raises(CandleNotAvailableError):
        await client.get_1h_candle("BTCUSDT", _SAMPLE_DATETIME)


# ---------------------------------------------------------------------------
# 3. test_get_current_price_success
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_current_price_success():
    """get_current_price returns a Decimal close price from the latest 1m candle."""
    mock_client = _make_client([_make_response(200, json_body=[_SAMPLE_KLINE])])
    client = BinanceClient(httpx_client=mock_client)

    price = await client.get_current_price("BTCUSDT")

    assert isinstance(price, Decimal)
    assert price == Decimal("46800.00000000")

    # Verify 1m interval and limit=1
    call_kwargs = mock_client.get.call_args
    params = call_kwargs[1]["params"] if "params" in call_kwargs[1] else call_kwargs[0][1]
    assert params["interval"] == "1m"
    assert params["limit"] == 1


@pytest.mark.asyncio
async def test_get_current_price_no_data_raises():
    """get_current_price raises CandleNotAvailableError when no data is returned."""
    mock_client = _make_client([_make_response(200, json_body=[])])
    client = BinanceClient(httpx_client=mock_client)

    with pytest.raises(CandleNotAvailableError):
        await client.get_current_price("BTCUSDT")


# ---------------------------------------------------------------------------
# 4. test_api_error_handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_error_handling():
    """Non-retryable HTTP 400 raises BinanceAPIError immediately."""
    mock_client = _make_client([_make_response(400, text='{"msg":"Bad Request"}')])
    client = BinanceClient(httpx_client=mock_client)

    with pytest.raises(BinanceAPIError):
        await client.get_current_price("BTCUSDT")

    # Only one attempt — no retries on 400
    assert mock_client.get.call_count == 1


# ---------------------------------------------------------------------------
# 5. test_rate_limit_retry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rate_limit_retry():
    """A single 429 is retried; subsequent 200 returns the candle successfully."""
    responses = [
        _make_response(429, text="rate limited"),
        _make_response(200, json_body=[_SAMPLE_KLINE]),
    ]
    mock_client = _make_client(responses)
    client = BinanceClient(httpx_client=mock_client)

    with patch("services.polymarket.adapters.binance_client.asyncio.sleep", new_callable=AsyncMock):
        candle = await client.get_1h_candle("BTCUSDT", _SAMPLE_DATETIME)

    assert candle["close"] == Decimal("46800.00000000")
    assert mock_client.get.call_count == 2


@pytest.mark.asyncio
async def test_rate_limit_exhausted_raises():
    """All retries returning 429 raises RateLimitError."""
    responses = [_make_response(429)] * 4  # initial + 3 retries
    mock_client = _make_client(responses)
    client = BinanceClient(httpx_client=mock_client)

    with patch("services.polymarket.adapters.binance_client.asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(RateLimitError):
            await client.get_current_price("BTCUSDT")

    assert mock_client.get.call_count == 4


# ---------------------------------------------------------------------------
# 6. test_timestamp_alignment
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_timestamp_alignment():
    """startTime and endTime params are correctly computed from the input datetime."""
    mock_client = _make_client([_make_response(200, json_body=[_SAMPLE_KLINE])])
    client = BinanceClient(httpx_client=mock_client)

    target_dt = datetime(2022, 1, 1, 14, 0, 0, tzinfo=timezone.utc)
    expected_start_ms = int(target_dt.timestamp() * 1000)
    expected_end_ms = expected_start_ms + 3_600_000 - 1  # one hour window, exclusive

    await client.get_1h_candle("BTCUSDT", target_dt)

    call_kwargs = mock_client.get.call_args
    params = call_kwargs[1]["params"] if "params" in call_kwargs[1] else call_kwargs[0][1]
    assert params["startTime"] == expected_start_ms
    assert params["endTime"] == expected_end_ms


# ---------------------------------------------------------------------------
# get_1h_candles_range
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_1h_candles_range_returns_list():
    """get_1h_candles_range returns a list of candle dicts."""
    two_klines = [_SAMPLE_KLINE, _SAMPLE_KLINE]
    mock_client = _make_client([_make_response(200, json_body=two_klines)])
    client = BinanceClient(httpx_client=mock_client)

    start = datetime(2022, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    end = datetime(2022, 1, 1, 1, 0, 0, tzinfo=timezone.utc)

    candles = await client.get_1h_candles_range("BTCUSDT", start, end)

    assert len(candles) == 2
    assert all(isinstance(c["close"], Decimal) for c in candles)


@pytest.mark.asyncio
async def test_get_1h_candles_range_empty():
    """get_1h_candles_range returns empty list when no candles in range."""
    mock_client = _make_client([_make_response(200, json_body=[])])
    client = BinanceClient(httpx_client=mock_client)

    start = datetime(2022, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    end = datetime(2022, 1, 1, 1, 0, 0, tzinfo=timezone.utc)

    candles = await client.get_1h_candles_range("BTCUSDT", start, end)
    assert candles == []


@pytest.mark.asyncio
async def test_get_1h_candles_range_too_large_raises():
    """get_1h_candles_range raises ValueError when range exceeds 1000 hourly candles."""
    mock_client = _make_client([])
    client = BinanceClient(httpx_client=mock_client)

    start = datetime(2022, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    # 1001 hours later — exceeds the 1000-candle Binance limit
    end = datetime(2022, 2, 12, 1, 0, 0, tzinfo=timezone.utc)  # ~1009 hours

    with pytest.raises(ValueError, match="1000 per request"):
        await client.get_1h_candles_range("BTCUSDT", start, end)


# ---------------------------------------------------------------------------
# close / context manager
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_close_calls_aclose_when_owned():
    """BinanceClient.close() calls aclose() on the internally-created client."""
    with patch("services.polymarket.adapters.binance_client.httpx.AsyncClient") as mock_cls:
        mock_instance = AsyncMock()
        mock_cls.return_value = mock_instance
        client = BinanceClient()
        await client.close()
        mock_instance.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_close_does_not_call_aclose_when_injected():
    """BinanceClient.close() does NOT close an injected httpx client."""
    mock_http = AsyncMock(spec=httpx.AsyncClient)
    mock_http.get = AsyncMock(return_value=_make_response(200, json_body=[_SAMPLE_KLINE]))
    client = BinanceClient(httpx_client=mock_http)
    await client.close()
    mock_http.aclose.assert_not_awaited()
