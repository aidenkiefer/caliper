"""Feature store for the Polymarket unified feature pipeline (Sprint 12).

Reads and writes :class:`FeatureSnapshot` records to the ``pm.features``
TimescaleDB hypertable via asyncpg.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import List, Optional

import asyncpg
from pydantic import ValidationError

from packages.common.polymarket_schemas import FeatureSnapshot

logger = logging.getLogger(__name__)


class FeatureStoreError(Exception):
    """Raised when a database operation in :class:`FeatureStore` fails."""


class FeatureStore:
    """Async read/write interface for ``pm.features``.

    Usage::

        store = FeatureStore(db_url)
        await store.connect()
        try:
            await store.write(snapshot)
            latest = await store.read_latest(market_id)
        finally:
            await store.close()
    """

    def __init__(self, db_url: str) -> None:
        self._db_url = db_url
        self._pool: Optional[asyncpg.Pool] = None  # type: ignore[type-arg]

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Create the asyncpg connection pool."""
        self._pool = await asyncpg.create_pool(
            self._db_url,
            min_size=1,
            max_size=5,
        )

    async def close(self) -> None:
        """Close the asyncpg connection pool."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require_pool(self) -> asyncpg.Pool:  # type: ignore[type-arg]
        if self._pool is None:
            raise RuntimeError("FeatureStore not connected")
        return self._pool

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def write(self, snapshot: FeatureSnapshot) -> None:
        """Insert one :class:`FeatureSnapshot` into ``pm.features``.

        Uses ``ON CONFLICT DO NOTHING`` so duplicate (market_id, token_id,
        captured_at) rows are silently skipped.
        """
        pool = self._require_pool()
        features_json = json.dumps(snapshot.model_dump(mode="json"))
        sql = """
            INSERT INTO pm.features (market_id, token_id, captured_at, features)
            VALUES ($1, $2, $3, $4::jsonb)
            ON CONFLICT DO NOTHING
        """
        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    sql,
                    snapshot.market_id,
                    snapshot.token_id,
                    snapshot.captured_at,
                    features_json,
                )
        except asyncpg.PostgresError as exc:
            logger.error(
                "FeatureStore.write failed for market_id=%s token_id=%s: %s",
                snapshot.market_id,
                snapshot.token_id,
                exc,
            )
            raise FeatureStoreError(str(exc)) from exc

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def read_latest(self, market_id: str) -> Optional[FeatureSnapshot]:
        """Return the most recent :class:`FeatureSnapshot` for *market_id*.

        Returns ``None`` if no rows exist.
        """
        pool = self._require_pool()
        sql = """
            SELECT features
            FROM pm.features
            WHERE market_id = $1
            ORDER BY captured_at DESC
            LIMIT 1
        """
        try:
            async with pool.acquire() as conn:
                row = await conn.fetchrow(sql, market_id)
        except asyncpg.PostgresError as exc:
            logger.error(
                "FeatureStore.read_latest failed for market_id=%s: %s",
                market_id,
                exc,
            )
            raise FeatureStoreError(str(exc)) from exc

        if row is None:
            return None
        try:
            return FeatureSnapshot.model_validate(row["features"])
        except ValidationError as exc:
            logger.error(
                "FeatureStore.read_latest deserialization failed for market_id=%s: %s",
                market_id,
                exc,
            )
            raise FeatureStoreError(f"Malformed feature row: {exc}") from exc

    async def read_window(
        self,
        market_id: str,
        start: datetime,
        end: datetime,
        limit: int = 1000,
    ) -> List[FeatureSnapshot]:
        """Return :class:`FeatureSnapshot` records within [*start*, *end*].

        Results are ordered by ``captured_at ASC``. Returns an empty list if
        no rows match.
        """
        pool = self._require_pool()
        sql = """
            SELECT features
            FROM pm.features
            WHERE market_id = $1
              AND captured_at >= $2
              AND captured_at <= $3
            ORDER BY captured_at ASC
            LIMIT $4
        """
        try:
            async with pool.acquire() as conn:
                rows = await conn.fetch(sql, market_id, start, end, limit)
        except asyncpg.PostgresError as exc:
            logger.error(
                "FeatureStore.read_window failed for market_id=%s: %s",
                market_id,
                exc,
            )
            raise FeatureStoreError(str(exc)) from exc

        results: List[FeatureSnapshot] = []
        for row in rows:
            try:
                results.append(FeatureSnapshot.model_validate(row["features"]))
            except ValidationError as exc:
                logger.error(
                    "FeatureStore.read_window deserialization failed for market_id=%s: %s",
                    market_id,
                    exc,
                )
                raise FeatureStoreError(f"Malformed feature row: {exc}") from exc
        return results
