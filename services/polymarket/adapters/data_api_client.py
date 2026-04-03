"""
Data API client for fetching historical trades, wallet activity, and rebate data
from the Polymarket Data API.

The Data API (https://data-api.polymarket.com) provides:

- `DataAPIClient` — async HTTP client wrapping the Data REST API

Usage::

    async with httpx.AsyncClient() as client:
        data = DataAPIClient(config=config, http_client=client)
        trades = await data.get_trades(
            token_id="0xabc",
            start_time=datetime(2026, 3, 25, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 3, 25, 1, tzinfo=timezone.utc),
        )
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime
from typing import Any, List, Optional

import httpx

from services.polymarket.adapters.gamma_client import (
    APIError,
    PolymarketError,
    RateLimitError,
)
from services.polymarket.config import PolymarketConfig
from services.polymarket.constants import DATA_API_URL

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Retry configuration
# ---------------------------------------------------------------------------

_RETRY_DELAYS = [1, 2, 4]   # seconds; 3 retries (4 total attempts)
_RETRYABLE_STATUSES = {429, 500, 502, 503, 504}

# Maximum trades to fetch per paginated request
_PAGE_LIMIT = 500


# ---------------------------------------------------------------------------
# DataAPIClient
# ---------------------------------------------------------------------------


class DataAPIClient:
    """Async HTTP client for the Polymarket Data REST API.

    Parameters
    ----------
    config:
        ``PolymarketConfig`` instance (used for wallet address and API settings).
    http_client:
        Pre-configured ``httpx.AsyncClient``.  The caller is responsible for
        closing the client.
    base_url:
        Data API base URL.  Defaults to ``DATA_API_URL`` from ``constants.py``.
    """

    def __init__(
        self,
        config: PolymarketConfig,
        http_client: httpx.AsyncClient,
        base_url: str = DATA_API_URL,
    ) -> None:
        self._config = config
        self._client = http_client
        self._base_url = base_url.rstrip("/")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_trades(
        self,
        token_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> List[dict]:
        """Fetch historical trades for *token_id* within the given time range.

        Follows pagination via ``next_cursor`` until all pages are exhausted.

        Parameters
        ----------
        token_id:
            The Polymarket CLOB token ID.
        start_time:
            Start of the query range (timezone-aware).
        end_time:
            End of the query range (timezone-aware).

        Returns
        -------
        List[dict]
            Each trade dict contains: ``timestamp``, ``price``, ``size``,
            ``side``, ``maker_address``, ``taker_address``.

        Raises
        ------
        ValueError
            If ``start_time`` or ``end_time`` is timezone-naive.
        APIError / RateLimitError
            On unrecoverable HTTP errors.
        """
        _require_aware(start_time, "start_time")
        _require_aware(end_time, "end_time")

        params: dict[str, Any] = {
            "token_id": token_id,
            "startTime": _to_unix(start_time),
            "endTime": _to_unix(end_time),
            "limit": _PAGE_LIMIT,
        }

        trades: List[dict] = []

        while True:
            page = await self._get_json("/trades", params=params)
            raw_trades: list = page.get("data") or page if isinstance(page, list) else []
            trades.extend(_parse_trade(t) for t in raw_trades)

            next_cursor = page.get("next_cursor") if isinstance(page, dict) else None
            if not next_cursor or next_cursor == "LTE=":
                break

            params = dict(params)
            params["next_cursor"] = next_cursor

        return trades

    async def get_activity(
        self,
        wallet_address: str,
        start_time: datetime,
        end_time: datetime,
    ) -> List[dict]:
        """Fetch wallet activity for *wallet_address* within the given time range.

        Parameters
        ----------
        wallet_address:
            The Polygon wallet address to query.
        start_time:
            Start of the query range (timezone-aware).
        end_time:
            End of the query range (timezone-aware).

        Returns
        -------
        List[dict]
            Raw activity records from the Data API.

        Raises
        ------
        ValueError
            If ``start_time`` or ``end_time`` is timezone-naive.
        APIError / RateLimitError
            On unrecoverable HTTP errors.
        """
        _require_aware(start_time, "start_time")
        _require_aware(end_time, "end_time")

        params: dict[str, Any] = {
            "user": wallet_address,
            "startTime": _to_unix(start_time),
            "endTime": _to_unix(end_time),
        }

        result = await self._get_json("/activity", params=params)
        if isinstance(result, list):
            return result
        return result.get("data") or []

    async def get_rebates(self, wallet_address: str, date_: date) -> dict:
        """Fetch daily maker rebates for *wallet_address* on *date_*.

        Parameters
        ----------
        wallet_address:
            The Polygon wallet address to query.
        date_:
            The calendar date for which to retrieve rebate data.

        Returns
        -------
        dict
            Raw rebate record from the Data API.

        Raises
        ------
        APIError / RateLimitError
            On unrecoverable HTTP errors.
        """
        params: dict[str, Any] = {
            "user": wallet_address,
            "date": date_.strftime("%Y-%m-%d"),
        }

        result = await self._get_json("/rewards/rebates", params=params)
        if isinstance(result, list):
            return result[0] if result else {}
        return result

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
                    "Data API retry %d/%d after %ds (url=%s)",
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
                logger.warning("Data API request error (attempt %d): %s", attempt, exc)
                continue

            if response.status_code == 200:
                return response.json()

            if response.status_code == 429:
                last_exc = RateLimitError(
                    f"Data API rate limited (429) after {attempt + 1} attempt(s)"
                )
                logger.warning("Data API rate limit hit (attempt %d)", attempt)
                continue  # retry

            if response.status_code in _RETRYABLE_STATUSES:
                last_exc = APIError(
                    f"Data API returned {response.status_code} (attempt {attempt + 1}): "
                    f"{response.text[:200]}"
                )
                logger.warning(
                    "Data API error %d (attempt %d)", response.status_code, attempt
                )
                continue  # retry

            # Non-retryable error
            raise APIError(
                f"Data API returned {response.status_code}: {response.text[:200]}"
            )

        # Exhausted retries
        if isinstance(last_exc, RateLimitError):
            raise last_exc
        raise APIError(
            f"Data API request failed after {len(_RETRY_DELAYS) + 1} attempts"
        ) from last_exc


# ---------------------------------------------------------------------------
# Parsing / conversion helpers
# ---------------------------------------------------------------------------


def _require_aware(dt: datetime, name: str) -> None:
    """Raise ValueError if *dt* is timezone-naive."""
    if dt.tzinfo is None:
        raise ValueError(
            f"{name} must be timezone-aware, got naive datetime: {dt!r}. "
            "Attach tzinfo explicitly, e.g. datetime(..., tzinfo=timezone.utc)."
        )


def _to_unix(dt: datetime) -> int:
    """Convert a timezone-aware datetime to a Unix timestamp (seconds)."""
    return int(dt.timestamp())


def _parse_trade(raw: dict) -> dict:
    """Extract the canonical trade fields from a raw Data API trade record."""
    return {
        "timestamp": raw.get("timestamp"),
        "price": raw.get("price"),
        "size": raw.get("size"),
        "side": raw.get("side"),
        "maker_address": raw.get("maker_address"),
        "taker_address": raw.get("taker_address"),
    }
