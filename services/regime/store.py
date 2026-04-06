from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

import asyncpg
from pydantic import ValidationError

from services.regime.schemas import RegimeState

logger = logging.getLogger(__name__)


class RegimeStoreError(Exception):
    """Raised when a database operation in RegimeStore fails."""


class RegimeStore:
    """Async read/write interface for `pm.regime_states`."""

    def __init__(self, db_url: str) -> None:
        self._db_url = db_url
        self._pool: Optional[asyncpg.Pool] = None  # type: ignore[type-arg]

    async def connect(self) -> None:
        self._pool = await asyncpg.create_pool(self._db_url, min_size=1, max_size=5)

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    def _require_pool(self) -> asyncpg.Pool:  # type: ignore[type-arg]
        if self._pool is None:
            raise RuntimeError("RegimeStore not connected")
        return self._pool

    async def write_state(self, state: RegimeState) -> UUID:
        pool = self._require_pool()
        sql = """
            INSERT INTO pm.regime_states (
                detected_at,
                market_id,
                primary_regime,
                probabilities,
                quality,
                source
            )
            VALUES ($1, $2, $3, $4::jsonb, $5::jsonb, $6)
            RETURNING state_id
        """
        probs_json = json.dumps(state.regime_probabilities)
        quality_json = json.dumps(state.quality.model_dump(mode="json"))
        try:
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    sql,
                    state.detected_at,
                    state.market_id,
                    state.primary_regime,
                    probs_json,
                    quality_json,
                    state.source,
                )
        except asyncpg.PostgresError as exc:
            logger.error("RegimeStore.write_state failed: %s", exc)
            raise RegimeStoreError(str(exc)) from exc
        assert row is not None
        return row["state_id"]

    async def read_latest(self, market_id: Optional[str] = None) -> Optional[RegimeState]:
        pool = self._require_pool()
        sql = """
            SELECT detected_at, market_id, primary_regime, probabilities, quality, source
            FROM pm.regime_states
            WHERE ($1::text IS NULL AND market_id IS NULL) OR (market_id = $1)
            ORDER BY detected_at DESC
            LIMIT 1
        """
        try:
            async with pool.acquire() as conn:
                row = await conn.fetchrow(sql, market_id)
        except asyncpg.PostgresError as exc:
            logger.error("RegimeStore.read_latest failed: %s", exc)
            raise RegimeStoreError(str(exc)) from exc

        if row is None:
            return None
        try:
            return RegimeState.model_validate(
                {
                    "detected_at": row["detected_at"],
                    "market_id": row["market_id"],
                    "primary_regime": row["primary_regime"],
                    "regime_probabilities": row["probabilities"],
                    "quality": row["quality"],
                    "source": row["source"],
                }
            )
        except ValidationError as exc:
            raise RegimeStoreError(f"Malformed regime_state row: {exc}") from exc

    async def read_window(
        self,
        start: datetime,
        end: datetime,
        market_id: Optional[str] = None,
        limit: int = 10000,
    ) -> List[RegimeState]:
        pool = self._require_pool()
        sql = """
            SELECT detected_at, market_id, primary_regime, probabilities, quality, source
            FROM pm.regime_states
            WHERE detected_at >= $1
              AND detected_at <= $2
              AND ( ($3::text IS NULL AND market_id IS NULL) OR (market_id = $3) )
            ORDER BY detected_at ASC
            LIMIT $4
        """
        try:
            async with pool.acquire() as conn:
                rows = await conn.fetch(sql, start, end, market_id, limit)
        except asyncpg.PostgresError as exc:
            logger.error("RegimeStore.read_window failed: %s", exc)
            raise RegimeStoreError(str(exc)) from exc

        results: List[RegimeState] = []
        for row in rows:
            try:
                results.append(
                    RegimeState.model_validate(
                        {
                            "detected_at": row["detected_at"],
                            "market_id": row["market_id"],
                            "primary_regime": row["primary_regime"],
                            "regime_probabilities": row["probabilities"],
                            "quality": row["quality"],
                            "source": row["source"],
                        }
                    )
                )
            except ValidationError as exc:
                raise RegimeStoreError(f"Malformed regime_state row: {exc}") from exc
        return results

    async def read_latest_with_id(self, market_id: Optional[str] = None) -> Optional[tuple[UUID, RegimeState]]:
        pool = self._require_pool()
        sql = """
            SELECT state_id, detected_at, market_id, primary_regime, probabilities, quality, source
            FROM pm.regime_states
            WHERE ($1::text IS NULL AND market_id IS NULL) OR (market_id = $1)
            ORDER BY detected_at DESC
            LIMIT 1
        """
        try:
            async with pool.acquire() as conn:
                row = await conn.fetchrow(sql, market_id)
        except asyncpg.PostgresError as exc:
            logger.error("RegimeStore.read_latest_with_id failed: %s", exc)
            raise RegimeStoreError(str(exc)) from exc
        if row is None:
            return None
        state = RegimeState.model_validate(
            {
                "detected_at": row["detected_at"],
                "market_id": row["market_id"],
                "primary_regime": row["primary_regime"],
                "regime_probabilities": row["probabilities"],
                "quality": row["quality"],
                "source": row["source"],
            }
        )
        return row["state_id"], state
