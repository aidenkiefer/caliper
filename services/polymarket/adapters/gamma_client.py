"""
Gamma API client for discovering and fetching Polymarket BTC hourly market metadata.

The Gamma API (https://gamma-api.polymarket.com) is Polymarket's REST API for
market metadata. This module provides:

- `GammaClient` — async HTTP client wrapping the Gamma REST API
- Custom exceptions: `PolymarketError`, `MarketNotFoundError`, `MarketClosedError`,
  `APIError`, `RateLimitError`

Usage::

    async with httpx.AsyncClient() as client:
        gamma = GammaClient(httpx_client=client)
        market = await gamma.find_hourly_btc_market(
            target_hour_utc=14, target_date=date(2026, 3, 25)
        )
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Optional

import httpx

from services.polymarket.constants import GAMMA_API_URL, YES_OUTCOME, NO_OUTCOME
from services.polymarket.schemas import MarketInfo

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Retry configuration
# ---------------------------------------------------------------------------

_RETRY_DELAYS = [1, 2, 4]   # seconds; 3 attempts total (len(_RETRY_DELAYS))
_RETRYABLE_STATUSES = {429, 500, 502, 503, 504}


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class PolymarketError(Exception):
    """Base class for all Polymarket client errors."""


class MarketNotFoundError(PolymarketError):
    """Raised when no market matches the requested hour/date."""


class MarketClosedError(PolymarketError):
    """Raised when the matching market is already closed."""


class APIError(PolymarketError):
    """Raised on unexpected non-2xx API responses."""


class RateLimitError(APIError):
    """Raised when the Gamma API rate-limit is exhausted after all retries."""


# ---------------------------------------------------------------------------
# GammaClient
# ---------------------------------------------------------------------------


class GammaClient:
    """Async HTTP client for the Polymarket Gamma REST API.

    Parameters
    ----------
    base_url:
        Gamma API base URL.  Defaults to the constant in ``constants.py``.
    httpx_client:
        Optional pre-configured ``httpx.AsyncClient``.  When *None* (default)
        the client creates and owns its own instance which is closed by
        ``GammaClient.close()``.  Pass an explicit client to share a session
        (useful for testing and for composing clients in the quoting loop).
    """

    def __init__(
        self,
        base_url: str = GAMMA_API_URL,
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

    async def find_hourly_btc_market(
        self, target_hour_utc: int, target_date: date
    ) -> MarketInfo:
        """Find the Polymarket binary market for a specific BTC hourly window.

        Parameters
        ----------
        target_hour_utc:
            The UTC hour (0–23) of the *start* of the hourly resolution window.
        target_date:
            The calendar date (UTC) on which the window starts.

        Returns
        -------
        MarketInfo
            Fully populated market metadata.

        Raises
        ------
        MarketNotFoundError
            If no active market exists for the requested window.
        MarketClosedError
            If the matching market is already closed.
        APIError / RateLimitError
            On unrecoverable HTTP errors.
        """
        params: dict[str, Any] = {
            "tag_slug": "btc",
            "active": "true",
            "closed": "false",
            "limit": 100,
        }
        raw_markets: list[dict] = await self._get_json("/markets", params=params)

        # Filter to markets whose startDate matches target_date and target_hour_utc
        candidates = _filter_btc_hourly(raw_markets, target_hour_utc, target_date)

        if not candidates:
            # Also try fetching without active/closed filters to give a better error
            raise MarketNotFoundError(
                f"No active BTC hourly market found for "
                f"{target_date.isoformat()} hour={target_hour_utc:02d}:00 UTC"
            )

        # Prefer the market with the highest cumulative volume
        best = max(candidates, key=lambda m: Decimal(m.get("volume") or "0"))

        if best.get("closed"):
            raise MarketClosedError(
                f"Market {best.get('conditionId')} for hour {target_hour_utc:02d}:00 UTC "
                f"on {target_date.isoformat()} is already closed."
            )

        return _parse_market_info(best)

    async def get_market_metadata(self, condition_id: str) -> dict:
        """Return the raw metadata dict for a specific market.

        Parameters
        ----------
        condition_id:
            The on-chain condition ID (``conditionId`` field in Gamma API
            responses).

        Returns
        -------
        dict
            Raw JSON response from the Gamma API for this market.
        """
        markets: list[dict] = await self._get_json(
            "/markets", params={"condition_id": condition_id, "limit": 1}
        )
        if not markets:
            raise MarketNotFoundError(
                f"No market found for condition_id={condition_id!r}"
            )
        return markets[0]

    async def close(self) -> None:
        """Close the underlying HTTP client if this instance owns it."""
        if self._owns_client:
            await self._client.aclose()

    # ------------------------------------------------------------------
    # Async context manager support
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "GammaClient":
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
                    "Gamma API retry %d/%d after %ds (url=%s)",
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
                logger.warning("Gamma API request error (attempt %d): %s", attempt, exc)
                continue

            if response.status_code == 200:
                return response.json()

            if response.status_code == 429:
                last_exc = RateLimitError(
                    f"Gamma API rate limited (429) after {attempt + 1} attempt(s)"
                )
                logger.warning("Gamma API rate limit hit (attempt %d)", attempt)
                continue  # retry

            if response.status_code in _RETRYABLE_STATUSES:
                last_exc = APIError(
                    f"Gamma API returned {response.status_code} (attempt {attempt + 1}): "
                    f"{response.text[:200]}"
                )
                logger.warning(
                    "Gamma API error %d (attempt %d)", response.status_code, attempt
                )
                continue  # retry

            # Non-retryable error
            raise APIError(
                f"Gamma API returned {response.status_code}: {response.text[:200]}"
            )

        # Exhausted retries
        if isinstance(last_exc, RateLimitError):
            raise last_exc
        raise APIError(
            f"Gamma API request failed after {len(_RETRY_DELAYS) + 1} attempts"
        ) from last_exc


# ---------------------------------------------------------------------------
# Parsing helpers (module-level to keep the class body lean)
# ---------------------------------------------------------------------------


def _parse_window_start(market: dict) -> datetime | None:
    """Parse ``startDate`` field to a timezone-aware UTC datetime."""
    raw = market.get("startDate")
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _filter_btc_hourly(
    markets: list[dict], target_hour_utc: int, target_date: date
) -> list[dict]:
    """Return markets whose startDate matches target_date and target_hour_utc."""
    results = []
    for m in markets:
        window_start = _parse_window_start(m)
        if window_start is None:
            continue
        utc_dt = window_start.astimezone(timezone.utc)
        if utc_dt.date() == target_date and utc_dt.hour == target_hour_utc:
            results.append(m)
    return results


def _extract_token_ids(tokens: list[dict]) -> tuple[str, str]:
    """Return (token_id_yes, token_id_no) from the tokens list."""
    yes_id = ""
    no_id = ""
    for tok in tokens:
        outcome = (tok.get("outcome") or "").strip().upper()
        token_id = tok.get("token_id") or tok.get("tokenId") or ""
        if outcome == YES_OUTCOME:
            yes_id = token_id
        elif outcome == NO_OUTCOME:
            no_id = token_id
    return yes_id, no_id


def _parse_market_info(market: dict) -> MarketInfo:
    """Convert a raw Gamma API market dict to a ``MarketInfo`` instance."""
    tokens: list[dict] = market.get("tokens") or []
    token_id_yes, token_id_no = _extract_token_ids(tokens)

    window_start = _parse_window_start(market)
    if window_start is None:
        raise APIError(f"Market {market.get('conditionId')} has no startDate")

    raw_end = market.get("endDate")
    if raw_end:
        try:
            window_end = datetime.fromisoformat(raw_end.replace("Z", "+00:00"))
        except ValueError as exc:
            raise APIError(
                f"Market {market.get('conditionId')} has an invalid endDate: {raw_end!r}"
            ) from exc
        if window_end.tzinfo is None:
            window_end = window_end.replace(tzinfo=timezone.utc)
    else:
        # Fallback: assume 1-hour window
        from datetime import timedelta
        window_end = window_start + timedelta(hours=1)

    raw_tick = market.get("minimumTickSize") or market.get("tick_size") or "0.01"
    tick_size = Decimal(str(raw_tick))

    raw_volume = market.get("volume") or "0"
    total_volume = Decimal(str(raw_volume))

    # Fees — Gamma may expose these; default to enabled=True (conservative)
    fees_enabled: bool = bool(market.get("enableOrderBook", True))

    return MarketInfo(
        condition_id=market.get("conditionId") or market.get("condition_id") or "",
        token_id_yes=token_id_yes,
        token_id_no=token_id_no,
        slug=market.get("slug"),
        question=market.get("question"),
        window_start=window_start,
        window_end=window_end,
        tick_size=tick_size,
        fees_enabled=fees_enabled,
        total_volume=total_volume,
    )
