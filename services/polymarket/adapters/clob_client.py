"""
CLOB API client for placing, cancelling, and querying orders on Polymarket.

The CLOB API (https://clob.polymarket.com) is Polymarket's Central Limit Order
Book REST and WebSocket interface. This module provides:

- `CLOBClient` — async HTTP + WebSocket client wrapping the CLOB API
- EIP-712 order signing via ``eth_account`` (no py-clob-client SDK dependency)
- Retry logic for HTTP 425 (engine restart) and 429 (rate limit)
- WebSocket market channel subscription with reconnect on disconnect
- Custom exceptions: `CLOBError`, `CLOBEngineError`, `OrderRejectedError`,
  `HeartbeatError`, `RateLimitError`

Usage::

    async with httpx.AsyncClient() as http:
        client = CLOBClient(
            private_key="0x...",
            wallet_address="0x...",
            httpx_client=http,
        )
        order_id = await client.place_order(
            token_id="12345",
            side="BUY",
            price=Decimal("0.48"),
            size=Decimal("50"),
        )
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import secrets
import time
from decimal import Decimal
from typing import Any, Callable, List, Optional

import httpx
import websockets
from eth_account import Account
from eth_account.messages import encode_typed_data

from services.polymarket.constants import (
    CLOB_API_URL,
    CLOB_WS_URL,
    EXCHANGE_CONTRACT_ADDRESS,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Retry configuration
# ---------------------------------------------------------------------------

_RETRY_DELAYS = [1, 2, 4]   # seconds; up to 3 retries (applies to 425 and 429)

# ---------------------------------------------------------------------------
# EIP-712 domain and type definitions
# ---------------------------------------------------------------------------

_ORDER_EIP712_TYPES = {
    "Order": [
        {"name": "salt", "type": "uint256"},
        {"name": "maker", "type": "address"},
        {"name": "signer", "type": "address"},
        {"name": "taker", "type": "address"},
        {"name": "tokenId", "type": "uint256"},
        {"name": "makerAmount", "type": "uint256"},
        {"name": "takerAmount", "type": "uint256"},
        {"name": "expiration", "type": "uint256"},
        {"name": "nonce", "type": "uint256"},
        {"name": "feeRateBps", "type": "uint256"},
        {"name": "side", "type": "uint8"},
        {"name": "signatureType", "type": "uint8"},
    ]
}

_SIDE_BUY = 0
_SIDE_SELL = 1
_SIGNATURE_TYPE_EOA = 0

# USDC has 6 decimals; Polymarket conditional tokens also use 6 decimal places (1e6 = 1 share)
_USDC_DECIMALS = 6
_SHARE_DECIMALS = 6  # Polymarket conditional tokens use 6 decimal places (same as USDC)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class CLOBError(Exception):
    """Base class for all CLOB client errors."""


class CLOBEngineError(CLOBError):
    """Raised when the CLOB engine returns HTTP 425 and all retries are exhausted."""


class OrderRejectedError(CLOBError):
    """Raised when the CLOB rejects an order placement."""


class HeartbeatError(CLOBError):
    """Raised when the heartbeat request fails."""


class RateLimitError(CLOBError):
    """Raised when the CLOB API rate-limit (429) is exhausted after all retries."""


# ---------------------------------------------------------------------------
# CLOBClient
# ---------------------------------------------------------------------------


class CLOBClient:
    """Async HTTP + WebSocket client for the Polymarket CLOB API.

    Parameters
    ----------
    private_key:
        Hex-encoded Ethereum private key (with or without ``0x`` prefix) used
        to sign EIP-712 orders.
    wallet_address:
        The checksum Ethereum wallet address corresponding to ``private_key``.
        Used as the ``maker`` and ``owner`` in order payloads.
    base_url:
        CLOB REST API base URL. Defaults to the constant in ``constants.py``.
    ws_url:
        CLOB WebSocket URL for market channel subscriptions. Defaults to the
        constant in ``constants.py``.
    httpx_client:
        Optional pre-configured ``httpx.AsyncClient``. When *None* (default)
        the client creates and owns its own instance, closed by ``close()``.
        Pass an explicit client to share a session (useful for testing).
    """

    def __init__(
        self,
        private_key: str,
        wallet_address: str,
        base_url: str = CLOB_API_URL,
        ws_url: str = CLOB_WS_URL,
        httpx_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self._private_key = private_key
        self._wallet_address = wallet_address
        self._base_url = base_url.rstrip("/")
        self._ws_url = ws_url
        self._owns_client = httpx_client is None
        self._client: httpx.AsyncClient = httpx_client or httpx.AsyncClient(
            timeout=httpx.Timeout(10.0),
        )

        # Warn if using placeholder contract addresses
        if EXCHANGE_CONTRACT_ADDRESS == "0x0000000000000000000000000000000000000000":
            import warnings
            warnings.warn(
                "EXCHANGE_CONTRACT_ADDRESS is a placeholder. EIP-712 signatures will be invalid against production. "
                "Update constants.py with real contract addresses from https://docs.polymarket.com/resources/contract-addresses",
                UserWarning,
                stacklevel=2,
            )

    # ------------------------------------------------------------------
    # Public API — orders
    # ------------------------------------------------------------------

    async def place_order(
        self,
        token_id: str,
        side: str,
        price: Decimal,
        size: Decimal,
        post_only: bool = True,
    ) -> str:
        """Build, sign (EIP-712), and submit a limit order.

        Parameters
        ----------
        token_id:
            The CLOB token ID (YES or NO outcome token).
        side:
            ``"BUY"`` or ``"SELL"``.
        price:
            Limit price in USDC (e.g. ``Decimal("0.48")``).
        size:
            Order size in shares (e.g. ``Decimal("50")``).
        post_only:
            If *True* (default), the order is flagged as post-only (maker only).

        Returns
        -------
        str
            The ``orderID`` assigned by the CLOB.

        Raises
        ------
        OrderRejectedError
            If the CLOB rejects the order.
        CLOBEngineError
            If the engine returns HTTP 425 after all retries.
        RateLimitError
            If the API returns HTTP 429 after all retries.
        """
        payload = self._build_order_payload(token_id, side, price, size, post_only)
        response_data = await self._post_with_retry("/order", payload)
        order_id: str = response_data.get("orderID") or response_data.get("order_id") or ""
        if not order_id:
            raise OrderRejectedError(
                f"Order placement returned no orderID: {response_data}"
            )
        logger.info(
            "Order placed: id=%s token=%s side=%s price=%s size=%s",
            order_id, token_id, side, price, size,
        )
        return order_id

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a specific open order.

        Parameters
        ----------
        order_id:
            The CLOB order ID to cancel.

        Returns
        -------
        bool
            ``True`` if the order was successfully cancelled.
        """
        payload = {"orderID": order_id}
        await self._delete_with_retry("/order", payload)
        logger.info("Order cancelled: id=%s", order_id)
        return True

    async def cancel_all(self) -> int:
        """Cancel all open orders.

        Returns
        -------
        int
            The number of orders cancelled.
        """
        response_data = await self._delete_with_retry("/cancel-all", body=None)
        count: int = response_data.get("count", 0) if isinstance(response_data, dict) else 0
        logger.info("Cancelled all orders: count=%d", count)
        return count

    # ------------------------------------------------------------------
    # Public API — heartbeat
    # ------------------------------------------------------------------

    async def send_heartbeat(self) -> dict:
        """Send a heartbeat to prevent the platform from cancelling resting orders.

        Returns
        -------
        dict
            The heartbeat response, expected to include ``heartbeatID``.

        Raises
        ------
        HeartbeatError
            If the heartbeat request fails.
        """
        try:
            response_data = await self._post_with_retry("/heartbeat", {})
        except CLOBError as exc:
            raise HeartbeatError(f"Heartbeat failed: {exc}") from exc
        logger.debug("Heartbeat sent: %s", response_data)
        return response_data

    # ------------------------------------------------------------------
    # Public API — queries
    # ------------------------------------------------------------------

    async def get_orderbook(self, token_id: str) -> dict:
        """Fetch the current orderbook snapshot for a token.

        Parameters
        ----------
        token_id:
            The CLOB token ID to fetch the book for.

        Returns
        -------
        dict
            ``{"bids": [...], "asks": [...], "timestamp": ...}``
        """
        response_data = await self._get_with_retry("/book", params={"token_id": token_id})
        return {
            "bids": response_data.get("bids", []),
            "asks": response_data.get("asks", []),
            "timestamp": response_data.get("timestamp"),
        }

    async def get_fee_rate(self, token_id: str) -> dict:
        """Fetch the fee rate for a token.

        Parameters
        ----------
        token_id:
            The CLOB token ID.

        Returns
        -------
        dict
            ``{"feesEnabled": bool, "rate": str}``
        """
        response_data = await self._get_with_retry("/fee-rate", params={"token_id": token_id})
        return {
            "feesEnabled": response_data.get("feesEnabled", False),
            "rate": str(response_data.get("rate", "0")),
        }

    async def get_order_scoring(self, order_ids: List[str]) -> dict:
        """Fetch order scoring information for a list of order IDs.

        Parameters
        ----------
        order_ids:
            List of CLOB order IDs to score.

        Returns
        -------
        dict
            The raw scoring response from the CLOB API.
        """
        payload = {"orderIDs": order_ids}
        return await self._post_with_retry("/order-scoring", payload)

    # ------------------------------------------------------------------
    # Public API — WebSocket
    # ------------------------------------------------------------------

    async def subscribe_market_channel(
        self,
        token_id: str,
        callback: Callable[[dict], Any],
    ) -> None:
        """Subscribe to the CLOB WebSocket market channel for a token.

        Connects to the market WebSocket, sends a subscription message, and
        calls ``callback`` with each parsed message dict. Automatically
        reconnects on disconnect with exponential back-off (up to 3 retries).

        The ``callback`` may be a regular function or a coroutine function; if
        it is a coroutine function it will be awaited.

        Parameters
        ----------
        token_id:
            The CLOB token ID to subscribe to.
        callback:
            Callable invoked with each parsed message dict.

        Raises
        ------
        CLOBError
            If the WebSocket connection fails after all reconnect attempts.
        """
        subscribe_msg = json.dumps({"assets_ids": [token_id], "type": "market"})
        max_retries = 3
        delay = 1

        for attempt in range(max_retries + 1):
            try:
                async with websockets.connect(self._ws_url) as ws:
                    await ws.send(subscribe_msg)
                    logger.info(
                        "Subscribed to CLOB market channel: token=%s", token_id
                    )
                    # Reset reconnect counter on a successful connection
                    delay = 1
                    async for raw_msg in ws:
                        parsed = _parse_ws_message(raw_msg)
                        if parsed is None:
                            continue
                        # _parse_ws_message returns a list for batch frames or a
                        # dict for single-message frames; normalise to a list so
                        # the callback is always called once per message.
                        messages = parsed if isinstance(parsed, list) else [parsed]
                        for msg in messages:
                            if asyncio.iscoroutinefunction(callback):
                                await callback(msg)
                            else:
                                callback(msg)
            except (
                websockets.exceptions.ConnectionClosed,
                websockets.exceptions.WebSocketException,
                OSError,
            ) as exc:
                if attempt >= max_retries:
                    raise CLOBError(
                        f"WebSocket disconnected and all {max_retries} reconnect attempts exhausted: {exc}"
                    ) from exc
                logger.warning(
                    "WebSocket disconnected (attempt %d/%d), reconnecting in %ds: %s",
                    attempt + 1, max_retries, delay, exc,
                )
                await asyncio.sleep(delay)
                delay = min(delay * 2, 30)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Close the underlying HTTP client if this instance owns it."""
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "CLOBClient":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    # ------------------------------------------------------------------
    # EIP-712 signing
    # ------------------------------------------------------------------

    def _build_order_payload(
        self,
        token_id: str,
        side: str,
        price: Decimal,
        size: Decimal,
        post_only: bool,
    ) -> dict:
        """Construct and sign the order payload for POST /order."""
        side_int = _SIDE_BUY if side.upper() == "BUY" else _SIDE_SELL
        salt = secrets.randbelow(2**256 - 1) + 1  # cryptographically random, full 256-bit space

        # Amount calculations:
        # BUY:  makerAmount = USDC spent (price * size, scaled to 6 decimals)
        #       takerAmount = shares received (size, scaled to 18 decimals)
        # SELL: makerAmount = shares sold (size, scaled to 18 decimals)
        #       takerAmount = USDC received (price * size, scaled to 6 decimals)
        if side_int == _SIDE_BUY:
            maker_amount = int((price * size) * Decimal(10 ** _USDC_DECIMALS))
            taker_amount = int(size * Decimal(10 ** _SHARE_DECIMALS))
        else:
            maker_amount = int(size * Decimal(10 ** _SHARE_DECIMALS))
            taker_amount = int((price * size) * Decimal(10 ** _USDC_DECIMALS))

        order_data = {
            "salt": salt,
            "maker": self._wallet_address,
            "signer": self._wallet_address,
            "taker": "0x0000000000000000000000000000000000000000",
            "tokenId": int(token_id),
            "makerAmount": maker_amount,
            "takerAmount": taker_amount,
            "expiration": 0,
            "nonce": 0,
            "feeRateBps": 0,
            "side": side_int,
            "signatureType": _SIGNATURE_TYPE_EOA,
        }

        signature = self._sign_order(order_data)

        return {
            "order": {
                "salt": salt,
                "maker": self._wallet_address,
                "signer": self._wallet_address,
                "taker": "0x0000000000000000000000000000000000000000",
                "tokenId": str(token_id),
                "makerAmount": str(maker_amount),
                "takerAmount": str(taker_amount),
                "expiration": "0",
                "nonce": "0",
                "feeRateBps": "0",
                "side": side_int,
                "signatureType": _SIGNATURE_TYPE_EOA,
                "signature": signature,
            },
            "owner": self._wallet_address,
            "orderType": "GTC",
            "postOnly": post_only,
        }

    def _sign_order(self, order_data: dict) -> str:
        """Sign an order dict with EIP-712 and return the hex signature string."""
        domain = {
            "name": "Polymarket CTF Exchange",
            "version": "1",
            "chainId": 137,
            "verifyingContract": EXCHANGE_CONTRACT_ADDRESS,
        }

        structured_data = {
            "types": {
                "EIP712Domain": [
                    {"name": "name", "type": "string"},
                    {"name": "version", "type": "string"},
                    {"name": "chainId", "type": "uint256"},
                    {"name": "verifyingContract", "type": "address"},
                ],
                **_ORDER_EIP712_TYPES,
            },
            "domain": domain,
            "primaryType": "Order",
            "message": order_data,
        }

        signable = encode_typed_data(full_message=structured_data)
        signed = Account.sign_message(signable, private_key=self._private_key)
        return signed.signature.hex()

    # ------------------------------------------------------------------
    # HTTP helpers with retry
    # ------------------------------------------------------------------

    async def _post_with_retry(self, path: str, body: dict) -> dict:
        """POST ``body`` to ``path`` with 425/429 retry logic."""
        url = f"{self._base_url}{path}"
        return await self._request_with_retry("POST", url, json_body=body)

    async def _delete_with_retry(self, path: str, body: Optional[dict]) -> dict:
        """DELETE to ``path`` with optional ``body`` and 425/429 retry logic."""
        url = f"{self._base_url}{path}"
        return await self._request_with_retry("DELETE", url, json_body=body)

    async def _get_with_retry(self, path: str, params: Optional[dict] = None) -> dict:
        """GET ``path`` with optional query ``params`` and 429 retry logic."""
        url = f"{self._base_url}{path}"
        return await self._request_with_retry("GET", url, params=params)

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        json_body: Optional[dict] = None,
        params: Optional[dict] = None,
    ) -> dict:
        """Execute an HTTP request with exponential back-off for 425 and 429.

        Retries up to 3 times with delays from ``_RETRY_DELAYS``.  Raises
        ``CLOBEngineError`` on exhausted 425 retries and ``RateLimitError``
        on exhausted 429 retries.
        """
        delays = [0] + _RETRY_DELAYS   # first attempt is immediate
        last_exc: Optional[Exception] = None

        for attempt, delay in enumerate(delays):
            if delay:
                logger.warning(
                    "CLOB %s %s retry %d/%d after %ds",
                    method, url, attempt, len(_RETRY_DELAYS), delay,
                )
                await asyncio.sleep(delay)

            try:
                response = await self._client.request(
                    method,
                    url,
                    json=json_body,
                    params=params,
                )
            except httpx.RequestError as exc:
                last_exc = exc
                logger.warning("CLOB request error (attempt %d): %s", attempt, exc)
                continue

            if response.status_code in (200, 201):
                try:
                    return response.json()
                except Exception:
                    return {}

            if response.status_code == 425:
                last_exc = CLOBEngineError(
                    f"CLOB engine restart (425) on attempt {attempt + 1}"
                )
                logger.warning("CLOB engine restart (425), attempt %d", attempt + 1)
                continue

            if response.status_code == 429:
                last_exc = RateLimitError(
                    f"CLOB rate limited (429) on attempt {attempt + 1}"
                )
                logger.warning("CLOB rate limit (429), attempt %d", attempt + 1)
                continue

            # Non-retryable error
            raise CLOBError(
                f"CLOB {method} {url} returned {response.status_code}: "
                f"{response.text[:200]}"
            )

        # Exhausted retries — raise the appropriate typed exception
        if isinstance(last_exc, CLOBEngineError):
            raise last_exc
        if isinstance(last_exc, RateLimitError):
            raise last_exc
        raise CLOBError(
            f"CLOB {method} {url} failed after {len(delays)} attempts"
        ) from last_exc


# ---------------------------------------------------------------------------
# WebSocket helpers (module-level for testability)
# ---------------------------------------------------------------------------

_WS_MESSAGE_TYPES = {"book", "price_change", "last_trade_price", "tick_size_change"}


def _parse_ws_message(raw: str | bytes) -> Optional[dict | list]:
    """Parse a raw WebSocket message string into a dict or list of dicts.

    Returns a single ``dict`` for a single-message frame, a ``list`` of dicts
    for a batch frame, or *None* if the message cannot be parsed or is an
    empty list.
    """
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.debug("Ignoring unparseable WebSocket message: %r", raw[:100])
        return None

    # The CLOB WebSocket may send a single message dict or a list of messages.
    # Return the full list so callers can dispatch each item individually.
    if isinstance(data, list):
        return data if data else None

    return data
