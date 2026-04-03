"""
Unit tests for services/polymarket/adapters/clob_client.py

Tests cover:
- place_order success
- cancel_order success
- cancel_all success
- send_heartbeat success
- get_orderbook success
- HTTP 425 retry success (order placed on 3rd attempt)
- HTTP 425 exhausted raises CLOBEngineError
- WebSocket message parsing (_parse_ws_message helper)

Real EIP-712 signing is exercised using the standard Hardhat/Foundry test key
(not a real wallet).
"""

from __future__ import annotations

import json
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import pytest_asyncio

from services.polymarket.adapters.clob_client import (
    CLOBClient,
    CLOBEngineError,
    OrderRejectedError,
    RateLimitError,
    _parse_ws_message,
)

# ---------------------------------------------------------------------------
# Standard Hardhat/Foundry test key — not a real wallet
# ---------------------------------------------------------------------------

TEST_PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
TEST_ADDRESS = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_response(status_code: int, json_data: dict | None = None, text: str = "") -> MagicMock:
    """Create a mock httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.text = text or json.dumps(json_data or {})
    resp.json.return_value = json_data or {}
    return resp


def _make_client(responses: list) -> CLOBClient:
    """Build a CLOBClient whose HTTP client returns the given list of responses."""
    http_mock = AsyncMock(spec=httpx.AsyncClient)
    http_mock.request = AsyncMock(side_effect=responses)
    return CLOBClient(
        private_key=TEST_PRIVATE_KEY,
        wallet_address=TEST_ADDRESS,
        httpx_client=http_mock,
    )


# ---------------------------------------------------------------------------
# Tests — order placement
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_place_order_success():
    """POST /order returns {"orderID": "abc123"} → place_order returns "abc123"."""
    client = _make_client([_make_response(200, {"orderID": "abc123"})])

    order_id = await client.place_order(
        token_id="999",
        side="BUY",
        price=Decimal("0.48"),
        size=Decimal("50"),
    )

    assert order_id == "abc123"


@pytest.mark.asyncio
async def test_place_order_sell_success():
    """SELL side order placement returns the order ID."""
    client = _make_client([_make_response(200, {"orderID": "sell123"})])

    order_id = await client.place_order(
        token_id="999",
        side="SELL",
        price=Decimal("0.52"),
        size=Decimal("25"),
    )

    assert order_id == "sell123"


@pytest.mark.asyncio
async def test_place_order_rejected_no_id():
    """A 200 response with no orderID raises OrderRejectedError."""
    client = _make_client([_make_response(200, {"error": "rejected"})])

    with pytest.raises(OrderRejectedError):
        await client.place_order(
            token_id="999",
            side="BUY",
            price=Decimal("0.48"),
            size=Decimal("50"),
        )


# ---------------------------------------------------------------------------
# Tests — cancel order
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cancel_order_success():
    """DELETE /order with 200 response → cancel_order returns True."""
    client = _make_client([_make_response(200, {"status": "ok"})])

    result = await client.cancel_order("order-xyz")

    assert result is True


# ---------------------------------------------------------------------------
# Tests — cancel all
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cancel_all_success():
    """DELETE /cancel-all returning {"count": 3} → cancel_all returns 3."""
    client = _make_client([_make_response(200, {"count": 3})])

    count = await client.cancel_all()

    assert count == 3


@pytest.mark.asyncio
async def test_cancel_all_zero_count():
    """cancel_all returns 0 when the response has no count field."""
    client = _make_client([_make_response(200, {})])

    count = await client.cancel_all()

    assert count == 0


# ---------------------------------------------------------------------------
# Tests — heartbeat
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_heartbeat_success():
    """POST /heartbeat returning {"heartbeatID": "hb1"} → heartbeatID in result."""
    client = _make_client([_make_response(200, {"heartbeatID": "hb1"})])

    result = await client.send_heartbeat()

    assert result.get("heartbeatID") == "hb1"


# ---------------------------------------------------------------------------
# Tests — orderbook
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_orderbook_success():
    """GET /book returns bids, asks, and timestamp."""
    book_data = {
        "bids": [{"price": "0.48", "size": "100"}],
        "asks": [{"price": "0.52", "size": "80"}],
        "timestamp": "1711324800",
    }
    client = _make_client([_make_response(200, book_data)])

    result = await client.get_orderbook("999")

    assert result["bids"] == book_data["bids"]
    assert result["asks"] == book_data["asks"]
    assert result["timestamp"] == "1711324800"


@pytest.mark.asyncio
async def test_get_orderbook_empty():
    """GET /book with empty response returns empty bids/asks."""
    client = _make_client([_make_response(200, {})])

    result = await client.get_orderbook("999")

    assert result["bids"] == []
    assert result["asks"] == []


# ---------------------------------------------------------------------------
# Tests — 425 retry logic
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_425_retry_success():
    """POST /order returning 425 twice then 200 → order placed on 3rd try."""
    responses = [
        _make_response(425),
        _make_response(425),
        _make_response(200, {"orderID": "retry-ok"}),
    ]
    client = _make_client(responses)

    with patch("services.polymarket.adapters.clob_client.asyncio.sleep", new_callable=AsyncMock):
        order_id = await client.place_order(
            token_id="999",
            side="BUY",
            price=Decimal("0.48"),
            size=Decimal("50"),
        )

    assert order_id == "retry-ok"


@pytest.mark.asyncio
async def test_425_exhausted_raises():
    """POST /order returning 425 four times → CLOBEngineError raised."""
    responses = [_make_response(425)] * 4
    client = _make_client(responses)

    with patch("services.polymarket.adapters.clob_client.asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(CLOBEngineError):
            await client.place_order(
                token_id="999",
                side="BUY",
                price=Decimal("0.48"),
                size=Decimal("50"),
            )


@pytest.mark.asyncio
async def test_429_exhausted_raises():
    """POST /order returning 429 four times → RateLimitError raised."""
    responses = [_make_response(429)] * 4
    client = _make_client(responses)

    with patch("services.polymarket.adapters.clob_client.asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(RateLimitError):
            await client.place_order(
                token_id="999",
                side="BUY",
                price=Decimal("0.48"),
                size=Decimal("50"),
            )


# ---------------------------------------------------------------------------
# Tests — WebSocket message parsing
# ---------------------------------------------------------------------------


def test_websocket_message_parsing_book():
    """A 'book' message is parsed into a dict and returned."""
    msg = json.dumps({
        "event_type": "book",
        "asset_id": "999",
        "bids": [{"price": "0.48", "size": "100"}],
        "asks": [{"price": "0.52", "size": "80"}],
        "timestamp": "1711324800",
    })

    result = _parse_ws_message(msg)

    assert result is not None
    assert result["event_type"] == "book"
    assert result["bids"][0]["price"] == "0.48"


def test_websocket_message_parsing_price_change():
    """A 'price_change' message is parsed correctly."""
    msg = json.dumps({
        "event_type": "price_change",
        "asset_id": "999",
        "price": "0.49",
    })

    result = _parse_ws_message(msg)

    assert result is not None
    assert result["event_type"] == "price_change"
    assert result["price"] == "0.49"


def test_websocket_message_parsing_bytes():
    """Binary WebSocket frames (bytes) are decoded and parsed."""
    msg = json.dumps({"event_type": "last_trade_price", "price": "0.50"}).encode("utf-8")

    result = _parse_ws_message(msg)

    assert result is not None
    assert result["event_type"] == "last_trade_price"


def test_websocket_message_parsing_invalid_json():
    """Unparseable frames return None without raising."""
    result = _parse_ws_message("not json at all {{")

    assert result is None


def test_websocket_message_parsing_list():
    """A JSON array returns all elements as a list."""
    msg = json.dumps([
        {"event_type": "book", "asset_id": "999"},
        {"event_type": "price_change", "asset_id": "999"},
    ])

    result = _parse_ws_message(msg)

    assert result is not None
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["event_type"] == "book"
    assert result[1]["event_type"] == "price_change"


def test_websocket_message_parsing_empty_list():
    """An empty JSON array returns None."""
    result = _parse_ws_message("[]")

    assert result is None


# ---------------------------------------------------------------------------
# Tests — EIP-712 signing (smoke test — verify signature is non-empty hex)
# ---------------------------------------------------------------------------


def test_sign_order_produces_hex_signature():
    """_sign_order returns a non-empty hex string starting with 0x or without prefix."""
    http_mock = AsyncMock(spec=httpx.AsyncClient)
    client = CLOBClient(
        private_key=TEST_PRIVATE_KEY,
        wallet_address=TEST_ADDRESS,
        httpx_client=http_mock,
    )

    order_data = {
        "salt": 12345678,
        "maker": TEST_ADDRESS,
        "signer": TEST_ADDRESS,
        "taker": "0x0000000000000000000000000000000000000000",
        "tokenId": 999,
        "makerAmount": 24000000,
        "takerAmount": 10 ** 6,
        "expiration": 0,
        "nonce": 0,
        "feeRateBps": 0,
        "side": 0,
        "signatureType": 0,
    }

    sig = client._sign_order(order_data)

    assert isinstance(sig, str)
    assert len(sig) > 0
    # eth_account returns hex without leading 0x from .hex() call
    assert all(c in "0123456789abcdefABCDEF" for c in sig)


def test_build_order_payload_buy():
    """_build_order_payload for BUY produces correct side and amount structure."""
    http_mock = AsyncMock(spec=httpx.AsyncClient)
    client = CLOBClient(
        private_key=TEST_PRIVATE_KEY,
        wallet_address=TEST_ADDRESS,
        httpx_client=http_mock,
    )

    payload = client._build_order_payload(
        token_id="999",
        side="BUY",
        price=Decimal("0.48"),
        size=Decimal("50"),
        post_only=True,
    )

    order = payload["order"]
    assert order["side"] == 0  # BUY
    assert order["signatureType"] == 0
    assert payload["postOnly"] is True
    assert payload["owner"] == TEST_ADDRESS
    # makerAmount = 0.48 * 50 * 1e6 = 24_000_000
    assert int(order["makerAmount"]) == 24_000_000
    # takerAmount = 50 * 1e6 (shares at 6 decimal places)
    assert int(order["takerAmount"]) == 50 * (10 ** 6)


def test_build_order_payload_sell():
    """_build_order_payload for SELL swaps maker/taker amounts correctly."""
    http_mock = AsyncMock(spec=httpx.AsyncClient)
    client = CLOBClient(
        private_key=TEST_PRIVATE_KEY,
        wallet_address=TEST_ADDRESS,
        httpx_client=http_mock,
    )

    payload = client._build_order_payload(
        token_id="999",
        side="SELL",
        price=Decimal("0.52"),
        size=Decimal("25"),
        post_only=False,
    )

    order = payload["order"]
    assert order["side"] == 1  # SELL
    assert payload["postOnly"] is False
    # makerAmount = 25 * 1e6 (shares sold at 6 decimal places)
    assert int(order["makerAmount"]) == 25 * (10 ** 6)
    # takerAmount = 0.52 * 25 * 1e6 = 13_000_000 (USDC received)
    assert int(order["takerAmount"]) == 13_000_000
