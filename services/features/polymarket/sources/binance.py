"""
Binance data source for the Polymarket feature pipeline (Sprint 12).

Polls 1-minute spot klines and perpetual futures premium index from Binance,
maintaining rolling buffers for volatility and momentum calculations.
"""

import asyncio
import logging
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, NamedTuple, Optional

import httpx

from services.features.polymarket.sources import DataUnavailable

logger = logging.getLogger(__name__)

_KLINES_URL = "https://api.binance.com/api/v3/klines"
_PREMIUM_INDEX_URL = "https://fapi.binance.com/fapi/v1/premiumIndex"
_KLINES_PARAMS = {"symbol": "BTCUSDT", "interval": "1m", "limit": 60}
_PREMIUM_PARAMS = {"symbol": "BTCUSDT"}
_HTTP_TIMEOUT = 10.0
_MAX_RETRIES = 3
_RETRY_BACKOFF = 2.0


class KlineBar(NamedTuple):
    """One 1-minute OHLCV kline bar from Binance spot."""

    open_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


@dataclass
class PremiumIndex:
    """Perpetual futures premium index snapshot from Binance."""

    mark_price: Decimal
    index_price: Decimal
    last_funding_rate: Decimal
    next_funding_time: datetime
    received_at: datetime


class BinanceSource:
    """
    Async Binance data source.

    Launches two background polling tasks:
      - Klines every 60s (rolling 60-bar buffer)
      - Premium index every 30s

    All public getters raise DataUnavailable if no data has been fetched yet.
    """

    def __init__(self) -> None:
        self._kline_buffer: deque[KlineBar] = deque(maxlen=60)
        self._premium_index: Optional[PremiumIndex] = None
        self.source_timestamp: Optional[datetime] = None
        self._kline_task: Optional[asyncio.Task] = None
        self._premium_task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Launch background polling tasks."""
        self._kline_task = asyncio.create_task(self._poll_klines(), name="binance_klines")
        self._premium_task = asyncio.create_task(
            self._poll_premium_index(), name="binance_premium"
        )

    async def stop(self) -> None:
        """Cancel background polling tasks and wait for them to finish."""
        tasks = [t for t in (self._kline_task, self._premium_task) if t is not None]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._kline_task = None
        self._premium_task = None

    # ------------------------------------------------------------------
    # Public accessors
    # ------------------------------------------------------------------

    def get_btc_price(self) -> Decimal:
        """Return close price of the most recent 1m kline."""
        if not self._kline_buffer:
            raise DataUnavailable("BinanceSource: kline buffer is empty")
        return self._kline_buffer[-1].close

    def get_hour_open(self) -> Decimal:
        """
        Return the open price of the first kline in the current UTC hour.

        Falls back to the oldest kline's open if no kline falls within the
        current hour (e.g., buffer hasn't refreshed yet this hour).
        """
        if not self._kline_buffer:
            raise DataUnavailable("BinanceSource: kline buffer is empty")
        now = datetime.now(tz=timezone.utc)
        current_hour = now.replace(minute=0, second=0, microsecond=0)
        for bar in self._kline_buffer:
            bar_hour = bar.open_time.replace(minute=0, second=0, microsecond=0)
            if bar_hour == current_hour:
                return bar.open
        # Fallback: oldest kline
        return self._kline_buffer[0].open

    def get_kline_buffer(self) -> List[KlineBar]:
        """Return a snapshot copy of the rolling kline buffer."""
        if not self._kline_buffer:
            raise DataUnavailable("BinanceSource: kline buffer is empty")
        return list(self._kline_buffer)

    def get_premium_index(self) -> PremiumIndex:
        """Return the latest premium index data."""
        if self._premium_index is None:
            raise DataUnavailable("BinanceSource: premium index not yet fetched")
        return self._premium_index

    # ------------------------------------------------------------------
    # Internal polling helpers
    # ------------------------------------------------------------------

    async def _fetch_with_retry(
        self, client: httpx.AsyncClient, url: str, params: dict
    ) -> dict:
        """
        GET `url` with `params`, retrying up to _MAX_RETRIES times.

        Raises the last exception if all attempts fail.
        """
        last_exc: Optional[Exception] = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()
            except Exception as exc:
                last_exc = exc
                if attempt < _MAX_RETRIES:
                    logger.warning(
                        "BinanceSource: fetch failed (attempt %d/%d): %s — retrying in %ss",
                        attempt,
                        _MAX_RETRIES,
                        exc,
                        _RETRY_BACKOFF,
                    )
                    await asyncio.sleep(_RETRY_BACKOFF)
        raise last_exc  # type: ignore[misc]

    async def _poll_klines(self) -> None:
        """Poll klines every 60 seconds; update rolling buffer."""
        while True:
            try:
                async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                    raw = await self._fetch_with_retry(client, _KLINES_URL, _KLINES_PARAMS)
                self._kline_buffer.clear()
                for entry in raw:
                    bar = KlineBar(
                        open_time=datetime.fromtimestamp(entry[0] / 1000, tz=timezone.utc),
                        open=Decimal(str(entry[1])),
                        high=Decimal(str(entry[2])),
                        low=Decimal(str(entry[3])),
                        close=Decimal(str(entry[4])),
                        volume=Decimal(str(entry[5])),
                    )
                    self._kline_buffer.append(bar)
                self.source_timestamp = datetime.now(tz=timezone.utc)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("BinanceSource: kline poll failed after retries: %s", exc)
            await asyncio.sleep(60)

    async def _poll_premium_index(self) -> None:
        """Poll premium index every 30 seconds."""
        while True:
            try:
                async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
                    data = await self._fetch_with_retry(
                        client, _PREMIUM_INDEX_URL, _PREMIUM_PARAMS
                    )
                self._premium_index = PremiumIndex(
                    mark_price=Decimal(str(data["markPrice"])),
                    index_price=Decimal(str(data["indexPrice"])),
                    last_funding_rate=Decimal(str(data["lastFundingRate"])),
                    next_funding_time=datetime.fromtimestamp(
                        data["nextFundingTime"] / 1000, tz=timezone.utc
                    ),
                    received_at=datetime.now(tz=timezone.utc),
                )
                self.source_timestamp = datetime.now(tz=timezone.utc)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("BinanceSource: premium index poll failed after retries: %s", exc)
            await asyncio.sleep(30)
