from __future__ import annotations

import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import asyncpg
from pydantic import ValidationError

from services.allocation.schemas import AllocationDecision, PerformanceMatrix

logger = logging.getLogger(__name__)


class AllocationStoreError(Exception):
    """Raised when allocation persistence operations fail."""


class PerformanceMatrixStore:
    """Async read/write interface for `pm.performance_matrices`."""

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
            raise RuntimeError("PerformanceMatrixStore not connected")
        return self._pool

    async def write_matrix(self, matrix: PerformanceMatrix) -> None:
        pool = self._require_pool()
        sql = """
            INSERT INTO pm.performance_matrices (computed_at, matrix)
            VALUES ($1, $2::jsonb)
        """
        payload = json.dumps(matrix.model_dump(mode="json"))
        try:
            async with pool.acquire() as conn:
                await conn.execute(sql, matrix.computed_at, payload)
        except asyncpg.PostgresError as exc:
            logger.error("PerformanceMatrixStore.write_matrix failed: %s", exc)
            raise AllocationStoreError(str(exc)) from exc

    async def read_latest(self) -> Optional[PerformanceMatrix]:
        pool = self._require_pool()
        sql = """
            SELECT matrix
            FROM pm.performance_matrices
            ORDER BY computed_at DESC
            LIMIT 1
        """
        try:
            async with pool.acquire() as conn:
                row = await conn.fetchrow(sql)
        except asyncpg.PostgresError as exc:
            logger.error("PerformanceMatrixStore.read_latest failed: %s", exc)
            raise AllocationStoreError(str(exc)) from exc

        if row is None:
            return None
        try:
            return PerformanceMatrix.model_validate(row["matrix"])
        except ValidationError as exc:
            raise AllocationStoreError(f"Malformed performance matrix row: {exc}") from exc


class AllocationDecisionStore:
    """Async read/write interface for `pm.allocation_decisions`."""

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
            raise RuntimeError("AllocationDecisionStore not connected")
        return self._pool

    async def write_decision(self, decision: AllocationDecision, *, regime_id: Optional[UUID] = None) -> None:
        pool = self._require_pool()
        sql = """
            INSERT INTO pm.allocation_decisions (
                decided_at, weights, method, regime_id, confidence
            )
            VALUES ($1, $2::jsonb, $3, $4::uuid, $5)
        """
        # The column is named "weights" per spec; persist only strategy weights.
        weights_json = json.dumps({k: str(v) for k, v in decision.weights.items()})
        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    sql,
                    decision.decided_at,
                    weights_json,
                    decision.method_used,
                    str(regime_id) if regime_id is not None else None,
                    decision.confidence,
                )
        except asyncpg.PostgresError as exc:
            logger.error("AllocationDecisionStore.write_decision failed: %s", exc)
            raise AllocationStoreError(str(exc)) from exc

    @staticmethod
    def _parse_weights(payload: Any) -> Dict[str, Decimal]:
        if payload is None:
            return {}
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                return {}
        if not isinstance(payload, dict):
            return {}
        out: Dict[str, Decimal] = {}
        for k, v in payload.items():
            try:
                out[str(k)] = Decimal(str(v))
            except Exception:
                out[str(k)] = Decimal("0")
        return out

    async def read_latest(self) -> Optional[Tuple[datetime, Dict[str, Decimal], str, Optional[UUID], Optional[Decimal]]]:
        pool = self._require_pool()
        sql = """
            SELECT decided_at, weights, method, regime_id, confidence
            FROM pm.allocation_decisions
            ORDER BY decided_at DESC
            LIMIT 1
        """
        try:
            async with pool.acquire() as conn:
                row = await conn.fetchrow(sql)
        except asyncpg.PostgresError as exc:
            logger.error("AllocationDecisionStore.read_latest failed: %s", exc)
            raise AllocationStoreError(str(exc)) from exc

        if row is None:
            return None
        weights = self._parse_weights(row["weights"])
        return (
            row["decided_at"],
            weights,
            row["method"],
            row["regime_id"],
            row["confidence"],
        )

    async def read_window(
        self,
        start: datetime,
        end: datetime,
        limit: int = 10000,
    ) -> List[Tuple[datetime, Dict[str, Decimal], str, Optional[UUID], Optional[Decimal]]]:
        pool = self._require_pool()
        sql = """
            SELECT decided_at, weights, method, regime_id, confidence
            FROM pm.allocation_decisions
            WHERE decided_at >= $1 AND decided_at <= $2
            ORDER BY decided_at ASC
            LIMIT $3
        """
        try:
            async with pool.acquire() as conn:
                rows = await conn.fetch(sql, start, end, limit)
        except asyncpg.PostgresError as exc:
            logger.error("AllocationDecisionStore.read_window failed: %s", exc)
            raise AllocationStoreError(str(exc)) from exc

        results: List[Tuple[datetime, Dict[str, Decimal], str, Optional[UUID], Optional[Decimal]]] = []
        for r in rows:
            results.append(
                (
                    r["decided_at"],
                    self._parse_weights(r["weights"]),
                    r["method"],
                    r["regime_id"],
                    r["confidence"],
                )
            )
        return results


class AllocationStore(AllocationDecisionStore):
    """Back-compat alias used by AllocationEngine."""
