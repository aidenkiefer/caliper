"""
Market discovery module for Polymarket BTC hourly markets.

Wraps ``GammaClient.find_hourly_btc_market`` with:

1. DST-aware conversion of ``target_hour_local`` + ``target_timezone`` → UTC hour
   using ``zoneinfo`` (Python 3.9+).
2. Database caching of the discovered ``MarketInfo`` to ``pm.market_metadata``
   via an asyncpg connection.

Usage::

    async with asyncpg.create_pool(dsn) as pool:
        async with pool.acquire() as conn:
            discovery = MarketDiscovery()
            market = await discovery.discover_target_market(config, conn)
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
from typing import Optional

from services.polymarket.adapters.gamma_client import GammaClient, MarketNotFoundError
from services.polymarket.config import PolymarketConfig
from services.polymarket.schemas import MarketInfo

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# DST-aware UTC conversion helper
# ---------------------------------------------------------------------------


def _local_hour_to_utc(target_hour_local: int, target_timezone: str, target_date: date) -> int:
    """Convert a local target hour to UTC hour, DST-aware.

    Parameters
    ----------
    target_hour_local:
        The hour in local time (0–23).
    target_timezone:
        IANA timezone name (e.g. ``"America/New_York"``).
    target_date:
        The calendar date for which the conversion is performed (DST
        status may differ by date).

    Returns
    -------
    int
        UTC hour (0–23) corresponding to ``target_hour_local`` on
        ``target_date`` in ``target_timezone``.
    """
    tz = ZoneInfo(target_timezone)
    local_dt = datetime(
        target_date.year,
        target_date.month,
        target_date.day,
        target_hour_local,
        0,
        0,
        tzinfo=tz,
    )
    utc_dt = local_dt.astimezone(timezone.utc)
    return utc_dt.hour


# ---------------------------------------------------------------------------
# MarketDiscovery
# ---------------------------------------------------------------------------


class MarketDiscovery:
    """Discovers the target Polymarket BTC hourly market and caches its metadata.

    Parameters
    ----------
    gamma_client:
        Optional pre-configured ``GammaClient`` instance.  When *None*
        (default) a fresh ``GammaClient`` is created.  Pass an explicit
        client for testing (dependency injection).
    """

    def __init__(self, gamma_client: Optional[GammaClient] = None) -> None:
        self._gamma = gamma_client or GammaClient()

    async def discover_target_market(
        self,
        config: PolymarketConfig,
        db_conn,
        target_date: Optional[date] = None,
    ) -> MarketInfo:
        """Find the BTC hourly market for today's target window.

        Parameters
        ----------
        config:
            ``PolymarketConfig`` carrying ``target_hour_local`` and
            ``target_timezone``.
        db_conn:
            asyncpg connection used for caching.  If *None*, the DB write
            is skipped (useful in tests or dry-run mode).
        target_date:
            The date for which to find the market.  Defaults to today in
            UTC.

        Returns
        -------
        MarketInfo
            Fully populated market metadata.

        Raises
        ------
        MarketNotFoundError
            Propagated from ``GammaClient`` when no matching market exists.
        """
        if target_date is None:
            target_date = datetime.now(tz=timezone.utc).date()

        target_hour_utc = _local_hour_to_utc(
            config.target_hour_local,
            config.target_timezone,
            target_date,
        )

        logger.info(
            "Discovering BTC hourly market: date=%s local_hour=%d tz=%s → utc_hour=%d",
            target_date.isoformat(),
            config.target_hour_local,
            config.target_timezone,
            target_hour_utc,
        )

        market: MarketInfo = await self._gamma.find_hourly_btc_market(
            target_hour_utc=target_hour_utc,
            target_date=target_date,
        )

        logger.info(
            "Discovered market: condition_id=%s question=%r",
            market.condition_id,
            market.question,
        )

        if db_conn is not None:
            await self.cache_market_metadata(market, db_conn)

        return market

    async def cache_market_metadata(self, market: MarketInfo, db_conn) -> None:
        """Upsert a ``MarketInfo`` record to ``pm.market_metadata``.

        Parameters
        ----------
        market:
            The market metadata to persist.
        db_conn:
            asyncpg connection.
        """
        await db_conn.execute(
            """
            INSERT INTO pm.market_metadata (
                condition_id, slug, question, token_id_yes, token_id_no,
                window_start, window_end, tick_size, fees_enabled, fee_rate_bps,
                rewards_max_spread, rewards_min_size, total_volume, discovered_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, NOW())
            ON CONFLICT (condition_id) DO UPDATE SET
                slug = EXCLUDED.slug,
                question = EXCLUDED.question,
                token_id_yes = EXCLUDED.token_id_yes,
                token_id_no = EXCLUDED.token_id_no,
                window_start = EXCLUDED.window_start,
                window_end = EXCLUDED.window_end,
                tick_size = EXCLUDED.tick_size,
                fees_enabled = EXCLUDED.fees_enabled,
                fee_rate_bps = EXCLUDED.fee_rate_bps,
                rewards_max_spread = EXCLUDED.rewards_max_spread,
                rewards_min_size = EXCLUDED.rewards_min_size,
                total_volume = EXCLUDED.total_volume,
                discovered_at = NOW()
            """,
            market.condition_id,
            market.slug,
            market.question,
            market.token_id_yes,
            market.token_id_no,
            market.window_start,
            market.window_end,
            market.tick_size,
            market.fees_enabled,
            market.fee_rate_bps,
            market.rewards_max_spread,
            market.rewards_min_size,
            market.total_volume,
        )
        logger.debug(
            "Cached market metadata: condition_id=%s", market.condition_id
        )
