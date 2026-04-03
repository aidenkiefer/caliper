"""
Unit tests for services/polymarket/adapters/gamma_client.py
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from services.polymarket.adapters.gamma_client import (
    APIError,
    GammaClient,
    MarketClosedError,
    MarketNotFoundError,
    RateLimitError,
)
from services.polymarket.schemas import MarketInfo


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _make_market(
    *,
    condition_id: str = "0xabc123",
    start_hour_utc: int = 14,
    start_date: str = "2026-03-25",
    closed: bool = False,
    active: bool = True,
    volume: str = "10000.00",
    token_id_yes: str = "0xyes",
    token_id_no: str = "0xno",
    slug: str = "btc-up-14-utc",
    question: str = "Will BTC be higher at 3 PM UTC than at 2 PM UTC on March 25?",
    minimum_tick_size: str = "0.01",
) -> dict:
    """Return a dict mimicking a single Gamma API market entry."""
    return {
        "conditionId": condition_id,
        "question": question,
        "slug": slug,
        "startDate": f"{start_date}T{start_hour_utc:02d}:00:00Z",
        "endDate": (
            datetime.fromisoformat(f"{start_date}T{start_hour_utc:02d}:00:00")
            + timedelta(hours=1)
        ).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "active": active,
        "closed": closed,
        "minimumTickSize": minimum_tick_size,
        "volume": volume,
        "tokens": [
            {"token_id": token_id_yes, "outcome": "Yes"},
            {"token_id": token_id_no, "outcome": "No"},
        ],
    }


def _make_response(markets: list[dict], status_code: int = 200) -> MagicMock:
    """Return a mock httpx Response that returns *markets* as JSON."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = markets
    resp.text = json.dumps(markets)
    return resp


def _make_client_with_response(response: MagicMock) -> httpx.AsyncClient:
    """Return an AsyncClient mock whose .get() always returns *response*."""
    client = MagicMock(spec=httpx.AsyncClient)
    client.get = AsyncMock(return_value=response)
    return client


# ---------------------------------------------------------------------------
# Test: successful market discovery
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_find_market_success():
    """GammaClient returns a correctly-populated MarketInfo for a valid market."""
    market_dict = _make_market(
        condition_id="0xcondition1",
        start_hour_utc=14,
        start_date="2026-03-25",
        volume="50000.00",
        token_id_yes="0xyes1",
        token_id_no="0xno1",
    )
    mock_client = _make_client_with_response(_make_response([market_dict]))
    gamma = GammaClient(httpx_client=mock_client)

    result = await gamma.find_hourly_btc_market(
        target_hour_utc=14, target_date=date(2026, 3, 25)
    )

    assert isinstance(result, MarketInfo)
    assert result.condition_id == "0xcondition1"
    assert result.token_id_yes == "0xyes1"
    assert result.token_id_no == "0xno1"
    assert result.tick_size == Decimal("0.01")
    assert result.total_volume == Decimal("50000.00")
    assert result.window_start == datetime(2026, 3, 25, 14, 0, 0, tzinfo=timezone.utc)
    assert result.window_end == datetime(2026, 3, 25, 15, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Test: market not found
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_find_market_not_found():
    """MarketNotFoundError is raised when the API returns an empty list."""
    mock_client = _make_client_with_response(_make_response([]))
    gamma = GammaClient(httpx_client=mock_client)

    with pytest.raises(MarketNotFoundError, match="No active BTC hourly market"):
        await gamma.find_hourly_btc_market(
            target_hour_utc=14, target_date=date(2026, 3, 25)
        )


@pytest.mark.asyncio
async def test_find_market_not_found_wrong_hour():
    """MarketNotFoundError is raised when no market matches the requested hour."""
    # Market exists for hour 15, not hour 14
    market_dict = _make_market(start_hour_utc=15, start_date="2026-03-25")
    mock_client = _make_client_with_response(_make_response([market_dict]))
    gamma = GammaClient(httpx_client=mock_client)

    with pytest.raises(MarketNotFoundError):
        await gamma.find_hourly_btc_market(
            target_hour_utc=14, target_date=date(2026, 3, 25)
        )


# ---------------------------------------------------------------------------
# Test: multiple markets for same hour — pick highest volume
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_find_market_picks_highest_volume():
    """When multiple markets share the same window, the highest-volume one wins."""
    low_vol = _make_market(
        condition_id="0xlow",
        start_hour_utc=14,
        start_date="2026-03-25",
        volume="100.00",
        token_id_yes="0xyes_low",
        token_id_no="0xno_low",
    )
    high_vol = _make_market(
        condition_id="0xhigh",
        start_hour_utc=14,
        start_date="2026-03-25",
        volume="99999.99",
        token_id_yes="0xyes_high",
        token_id_no="0xno_high",
    )
    mock_client = _make_client_with_response(_make_response([low_vol, high_vol]))
    gamma = GammaClient(httpx_client=mock_client)

    result = await gamma.find_hourly_btc_market(
        target_hour_utc=14, target_date=date(2026, 3, 25)
    )

    assert result.condition_id == "0xhigh"
    assert result.total_volume == Decimal("99999.99")


# ---------------------------------------------------------------------------
# Test: market already closed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_find_market_closed():
    """MarketClosedError is raised when the matching market has closed=True."""
    market_dict = _make_market(
        condition_id="0xclosed",
        start_hour_utc=14,
        start_date="2026-03-25",
        closed=True,
    )
    # The API call filters closed=false, but the parsing layer should also guard
    # against closed markets appearing in the response. We bypass the filter by
    # injecting a pre-built mock that returns a closed market regardless of params.
    mock_client = _make_client_with_response(_make_response([market_dict]))
    gamma = GammaClient(httpx_client=mock_client)

    with pytest.raises(MarketClosedError, match="already closed"):
        await gamma.find_hourly_btc_market(
            target_hour_utc=14, target_date=date(2026, 3, 25)
        )


# ---------------------------------------------------------------------------
# Test: API error handling (HTTP 500)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_error_handling():
    """APIError is raised immediately on non-retryable 4xx errors (e.g. 404)."""
    mock_client = _make_client_with_response(
        _make_response([], status_code=404)
    )
    gamma = GammaClient(httpx_client=mock_client)

    with pytest.raises(APIError, match="404"):
        await gamma.find_hourly_btc_market(
            target_hour_utc=14, target_date=date(2026, 3, 25)
        )


@pytest.mark.asyncio
async def test_api_500_retries_then_raises():
    """After exhausting retries on repeated 500 responses, APIError is raised."""
    resp_500 = _make_response([], status_code=500)
    # Return 500 on every call
    mock_client = MagicMock(spec=httpx.AsyncClient)
    mock_client.get = AsyncMock(return_value=resp_500)

    gamma = GammaClient(httpx_client=mock_client)

    with patch("services.polymarket.adapters.gamma_client.asyncio.sleep", new=AsyncMock()):
        with pytest.raises(APIError):
            await gamma.find_hourly_btc_market(
                target_hour_utc=14, target_date=date(2026, 3, 25)
            )

    # Should have attempted 1 initial + 3 retries = 4 calls
    assert mock_client.get.call_count == 4


# ---------------------------------------------------------------------------
# Test: rate limit retry — 429 then 200 succeeds
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rate_limit_retry():
    """A 429 response triggers a retry; subsequent 200 succeeds."""
    market_dict = _make_market(
        condition_id="0xretried",
        start_hour_utc=14,
        start_date="2026-03-25",
        volume="12345.67",
    )
    resp_429 = _make_response([], status_code=429)
    resp_200 = _make_response([market_dict], status_code=200)

    mock_client = MagicMock(spec=httpx.AsyncClient)
    # First call → 429, second call → 200
    mock_client.get = AsyncMock(side_effect=[resp_429, resp_200])

    gamma = GammaClient(httpx_client=mock_client)

    with patch("services.polymarket.adapters.gamma_client.asyncio.sleep", new=AsyncMock()):
        result = await gamma.find_hourly_btc_market(
            target_hour_utc=14, target_date=date(2026, 3, 25)
        )

    assert result.condition_id == "0xretried"
    assert mock_client.get.call_count == 2


# ---------------------------------------------------------------------------
# Test: get_market_metadata
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_market_metadata_success():
    """get_market_metadata returns the raw dict for a known condition_id."""
    market_dict = _make_market(condition_id="0xmeta1")
    mock_client = _make_client_with_response(_make_response([market_dict]))
    gamma = GammaClient(httpx_client=mock_client)

    result = await gamma.get_market_metadata("0xmeta1")

    assert result["conditionId"] == "0xmeta1"


@pytest.mark.asyncio
async def test_get_market_metadata_not_found():
    """MarketNotFoundError raised when get_market_metadata returns empty list."""
    mock_client = _make_client_with_response(_make_response([]))
    gamma = GammaClient(httpx_client=mock_client)

    with pytest.raises(MarketNotFoundError, match="condition_id"):
        await gamma.get_market_metadata("0xnonexistent")
