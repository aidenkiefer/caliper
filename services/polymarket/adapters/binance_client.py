"""
Binance REST API client for fetching BTC/USDT kline (candlestick) data.

Provides:

- `BinanceClient` — async HTTP client wrapping the Binance klines endpoint
- Custom exceptions: `BinanceError`, `BinanceAPIError`, `CandleNotAvailableError`,
  `RateLimitError`

Usage::

    async with httpx.AsyncClient() as client:
        binance = BinanceClient(httpx_client=client)
        candle = await binance.get_1h_candle("BTCUSDT", datetime(2026, 3, 25, 14, tzinfo=timezone.utc))
        price = await binance.get_current_price("BTCUSDT")
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, List, Optional

import httpx

from services.polymarket.constants import BINANCE_API_URL, BTCUSDT_SYMBOL

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Retry configuration
# ---------------------------------------------------------------------------

_RETRY_DELAYS = [1, 2, 4]   # seconds; 3 retries (4 total attempts)
_RETRYABLE_STATUSES = {429, 500, 502, 503, 504}

# Milliseconds in one hour
_ONE_HOUR_MS = 3_600_000


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class BinanceError(Exception):
    """Base class for all Binance client errors."""


class BinanceAPIError(BinanceError):
    """Raised on unexpected non-2xx API responses."""


class CandleNotAvailableError(BinanceError):
    """Raised when the requested candle has not yet closed or no data is returned."""


class RateLimitError(BinanceAPIError):
    """Raised when the Binance API rate limit is exhausted after all retries."""


# ---------------------------------------------------------------------------
# BinanceClient
# ---------------------------------------------------------------------------


class BinanceClient:
    """Async HTTP client for the Binance REST klines API.

    Parameters
    ----------
    base_url:
        Binance API base URL.  Defaults to ``BINANCE_API_URL`` from ``constants.py``.
    httpx_client:
        Optional pre-configured ``httpx.AsyncClient``.  When *None* (default) the
        client creates and owns its own instance, closed by ``BinanceClient.close()``.
        Pass an explicit client to share a session (useful for testing).
    """

    def __init__(
        self,
        base_url: str = BINANCE_API_URL,
        httpx_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._owns_client = httpx_client is None
        self._client: httpx.AsyncClient = httpx_client or httpx.AsyncClient(
            timeout=httpx.Timeout(10.0),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_1h_candle(self, symbol: str, timestamp: datetime) -> dict:
        """Fetch the 1-hour OHLCV candle starting at *timestamp*.

        Parameters
        ----------
        symbol:
            Trading pair symbol, e.g. ``"BTCUSDT"``.
        timestamp:
            UTC datetime indicating the **start** of the 1H candle.

        Returns
        -------
        dict
            Keys: ``open_time`` (datetime), ``open``, ``high``, ``low``, ``close``,
            ``volume`` (all Decimal), ``close_time`` (datetime).

        Raises
        ------
        CandleNotAvailableError
            If the API returns an empty result (candle not yet closed).
        BinanceAPIError / RateLimitError
            On unrecoverable HTTP errors.
        """
        start_ms = _to_ms(timestamp)
        end_ms = start_ms + _ONE_HOUR_MS - 1

        params: dict[str, Any] = {
            "symbol": symbol,
            "interval": "1h",
            "startTime": start_ms,
            "endTime": end_ms,
            "limit": 1,
        }
        raw: list = await self._get_json("/api/v3/klines", params=params)

        if not raw:
            raise CandleNotAvailableError(
                f"No 1h candle available for {symbol} at {timestamp.isoformat()}"
            )

        return _parse_candle(raw[0])

    async def get_current_price(self, symbol: str) -> Decimal:
        """Return the close price of the most recent 1-minute candle.

        Parameters
        ----------
        symbol:
            Trading pair symbol, e.g. ``"BTCUSDT"``.

        Returns
        -------
        Decimal
            Latest close price.

        Raises
        ------
        CandleNotAvailableError
            If the API returns no data.
        BinanceAPIError / RateLimitError
            On unrecoverable HTTP errors.
        """
        params: dict[str, Any] = {
            "symbol": symbol,
            "interval": "1m",
            "limit": 1,
        }
        raw: list = await self._get_json("/api/v3/klines", params=params)

        if not raw:
            raise CandleNotAvailableError(
                f"No current price data returned for {symbol}"
            )

        candle = _parse_candle(raw[0])
        return candle["close"]

    async def get_1h_candles_range(
        self, symbol: str, start: datetime, end: datetime
    ) -> List[dict]:
        """Fetch all 1-hour candles between *start* and *end*.

        Parameters
        ----------
        symbol:
            Trading pair symbol, e.g. ``"BTCUSDT"``.
        start:
            UTC datetime of the first candle's open time (inclusive).
        end:
            UTC datetime of the last candle's open time (inclusive).

        Returns
        -------
        List[dict]
            Each dict has the same structure as ``get_1h_candle``.

        Raises
        ------
        BinanceAPIError / RateLimitError
            On unrecoverable HTTP errors.
        """
        start_ms = _to_ms(start)
        end_ms = _to_ms(end) + _ONE_HOUR_MS - 1

        expected_candles = (end_ms - start_ms) // _ONE_HOUR_MS + 1
        if expected_candles > 1000:
            raise ValueError(
                f"Range spans ~{expected_candles} hourly candles; Binance limit is 1000 per request. "
                "Split into smaller ranges."
            )

        params: dict[str, Any] = {
            "symbol": symbol,
            "interval": "1h",
            "startTime": start_ms,
            "endTime": end_ms,
            "limit": 1000,  # Binance max per request
        }
        raw: list = await self._get_json("/api/v3/klines", params=params)

        return [_parse_candle(row) for row in raw]

    async def close(self) -> None:
        """Close the underlying HTTP client if this instance owns it."""
        if self._owns_client:
            await self._client.aclose()

    # ------------------------------------------------------------------
    # Async context manager support
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "BinanceClient":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_json(self, path: str, params: dict | None = None) -> Any:
        """GET *path* with retry/back-off; return parsed JSON body."""
        url = f"{self._base_url}{path}"
        last_exc: Exception | None = None

        for attempt, delay in enumerate([0] + _RETRY_DELAYS):
            if delay:
                logger.debug(
                    "Binance API retry %d/%d after %ds (url=%s)",
                    attempt,
                    len(_RETRY_DELAYS),
                    delay,
                    url,
                )
                await asyncio.sleep(delay)

            try:
                response = await self._client.get(url, params=params)
            except httpx.RequestError as exc:
                last_exc = exc
                logger.warning("Binance API request error (attempt %d): %s", attempt, exc)
                continue

            if response.status_code == 200:
                return response.json()

            if response.status_code == 429:
                last_exc = RateLimitError(
                    f"Binance API rate limited (429) after {attempt + 1} attempt(s)"
                )
                logger.warning("Binance API rate limit hit (attempt %d)", attempt)
                continue  # retry

            if response.status_code in _RETRYABLE_STATUSES:
                last_exc = BinanceAPIError(
                    f"Binance API returned {response.status_code} (attempt {attempt + 1}): "
                    f"{response.text[:200]}"
                )
                logger.warning(
                    "Binance API error %d (attempt %d)", response.status_code, attempt
                )
                continue  # retry

            # Non-retryable error
            raise BinanceAPIError(
                f"Binance API returned {response.status_code}: {response.text[:200]}"
            )

        # Exhausted retries
        if isinstance(last_exc, RateLimitError):
            raise last_exc
        raise BinanceAPIError(
            f"Binance API request failed after {len(_RETRY_DELAYS) + 1} attempts"
        ) from last_exc


# ---------------------------------------------------------------------------
# Parsing helpers (module-level to keep the class body lean)
# ---------------------------------------------------------------------------


def _to_ms(dt: datetime) -> int:
    """Convert a UTC datetime to a millisecond Unix timestamp."""
    if dt.tzinfo is None:
        raise ValueError(
            f"_to_ms requires a timezone-aware datetime, got naive: {dt!r}. "
            "Use datetime.now(tz=timezone.utc) or attach tzinfo explicitly."
        )
    return int(dt.timestamp() * 1000)


def _parse_candle(row: list) -> dict:
    """Convert a raw Binance kline array to a structured dict.

    Binance kline array indices:
        0  open_time (ms)
        1  open
        2  high
        3  low
        4  close
        5  volume
        6  close_time (ms)
        7  quote asset volume
        8  number of trades
        9  taker buy base asset volume
        10 taker buy quote asset volume
        11 ignore
    """
    return {
        "open_time": datetime.fromtimestamp(row[0] / 1000, tz=timezone.utc),
        "open": Decimal(str(row[1])),
        "high": Decimal(str(row[2])),
        "low": Decimal(str(row[3])),
        "close": Decimal(str(row[4])),
        "volume": Decimal(str(row[5])),
        "close_time": datetime.fromtimestamp(row[6] / 1000, tz=timezone.utc),
    }
