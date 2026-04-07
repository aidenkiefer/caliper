from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import List, Optional

import asyncpg
from pydantic import ValidationError

from packages.common.db_url import resolve_db_url
from services.fleet.schemas import FleetStatus as FleetStatusSnapshot
from services.fleet.schemas import SignalLogEntry
from services.fleet.schemas import PaperTrade

logger = logging.getLogger(__name__)


class PaperTradeStoreError(Exception):
    """Raised when a paper-trade DB operation fails."""


class PaperTradeStore:
    """Async read/write store for ``pm.paper_trades``."""

    def __init__(self, db_url: Optional[str] = None, pool: Optional[asyncpg.Pool] = None) -> None:  # type: ignore[type-arg]
        self._db_url = db_url
        self._pool: Optional[asyncpg.Pool] = pool  # type: ignore[type-arg]

    async def connect(self) -> None:
        if self._pool is not None:
            return
        db_url = self._db_url or resolve_db_url().url
        self._pool = await asyncpg.create_pool(db_url, min_size=1, max_size=5)

    async def close(self) -> None:
        if self._pool is not None and hasattr(self._pool, "close"):
            await self._pool.close()
        self._pool = None

    def _require_pool(self) -> asyncpg.Pool:  # type: ignore[type-arg]
        if self._pool is None:
            raise RuntimeError("PaperTradeStore not connected")
        return self._pool

    async def write_fill(self, trade: PaperTrade) -> None:
        pool = self._require_pool()
        sql = """
            INSERT INTO pm.paper_trades (
                trade_id, executed_at, strategy_id, market_id, signal_type,
                direction, side, price, quantity, notional, confidence,
                status, regime, allocation_weight, metadata
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15::jsonb)
            ON CONFLICT DO NOTHING
        """
        params = (
            trade.trade_id,
            trade.executed_at,
            trade.strategy_id,
            trade.market_id,
            trade.signal_type.value,
            trade.direction,
            trade.side,
            trade.price,
            trade.quantity,
            trade.notional,
            trade.confidence,
            trade.status,
            trade.regime,
            trade.allocation_weight,
            json.dumps(trade.metadata, default=str),
        )
        try:
            async with pool.acquire() as conn:
                await conn.execute(sql, *params)
        except asyncpg.PostgresError as exc:
            logger.error(
                "PaperTradeStore.write_fill failed for strategy_id=%s market_id=%s: %s",
                trade.strategy_id,
                trade.market_id,
                exc,
            )
            raise PaperTradeStoreError(str(exc)) from exc

    async def write_fills(self, trades: List[PaperTrade]) -> None:
        for trade in trades:
            await self.write_fill(trade)

    async def write_fleet_status(self, status: FleetStatusSnapshot) -> None:
        pool = self._require_pool()
        sql = """
            INSERT INTO pm.fleet_status_snapshots (captured_at, mode, payload)
            VALUES ($1, $2, $3::jsonb)
        """
        payload = status.model_dump(mode="json")
        params = (status.captured_at, status.mode.value if hasattr(status.mode, "value") else str(status.mode), json.dumps(payload, default=str))
        try:
            async with pool.acquire() as conn:
                await conn.execute(sql, *params)
        except asyncpg.PostgresError as exc:
            logger.error("PaperTradeStore.write_fleet_status failed: %s", exc)
            raise PaperTradeStoreError(str(exc)) from exc

    async def write_signal_entries(self, entries: List[SignalLogEntry]) -> None:
        if not entries:
            return
        pool = self._require_pool()
        sql = """
            INSERT INTO pm.fleet_signals (
                recorded_at, strategy_id, market_id, signal_type, direction, confidence,
                action_taken, fill_price, quantity, regime, metadata
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11::jsonb)
        """
        try:
            async with pool.acquire() as conn:
                for entry in entries:
                    metadata = json.dumps(entry.metadata or {}, default=str)
                    await conn.execute(
                        sql,
                        entry.recorded_at,
                        entry.strategy_id,
                        entry.market_id,
                        entry.signal_type.value if hasattr(entry.signal_type, "value") else str(entry.signal_type),
                        entry.direction,
                        entry.confidence,
                        entry.action_taken,
                        entry.fill_price,
                        entry.quantity,
                        entry.regime,
                        metadata,
                    )
        except asyncpg.PostgresError as exc:
            logger.error("PaperTradeStore.write_signal_entries failed: %s", exc)
            raise PaperTradeStoreError(str(exc)) from exc

    async def read_latest(
        self,
        strategy_id: Optional[str] = None,
        market_id: Optional[str] = None,
    ) -> Optional[PaperTrade]:
        rows = await self.read_window(
            start=datetime(1970, 1, 1, tzinfo=timezone.utc),
            end=datetime.max.replace(tzinfo=timezone.utc),
            strategy_id=strategy_id,
            market_id=market_id,
            limit=1,
            newest_first=True,
        )
        return rows[0] if rows else None

    async def read_window(
        self,
        *,
        start: datetime,
        end: datetime,
        strategy_id: Optional[str] = None,
        market_id: Optional[str] = None,
        limit: int = 1000,
        newest_first: bool = False,
    ) -> List[PaperTrade]:
        pool = self._require_pool()
        clauses = ["executed_at >= $1", "executed_at <= $2"]
        params: List[object] = [start, end]
        if strategy_id is not None:
            clauses.append(f"strategy_id = ${len(params) + 1}")
            params.append(strategy_id)
        if market_id is not None:
            clauses.append(f"market_id = ${len(params) + 1}")
            params.append(market_id)
        params.append(limit)
        sql = f"""
            SELECT trade_id, executed_at, strategy_id, market_id, signal_type,
                   direction, side, price, quantity, notional, confidence,
                   status, regime, allocation_weight, metadata
            FROM pm.paper_trades
            WHERE {" AND ".join(clauses)}
            ORDER BY executed_at {'DESC' if newest_first else 'ASC'}
            LIMIT ${len(params)}
        """
        try:
            async with pool.acquire() as conn:
                rows = await conn.fetch(sql, *params)
        except asyncpg.PostgresError as exc:
            logger.error("PaperTradeStore.read_window failed: %s", exc)
            raise PaperTradeStoreError(str(exc)) from exc

        results: List[PaperTrade] = []
        for row in rows:
            try:
                payload = dict(row.items()) if hasattr(row, "items") else dict(row)
                if isinstance(payload.get("metadata"), str):
                    payload["metadata"] = json.loads(payload["metadata"])
                results.append(PaperTrade.model_validate(payload))
            except ValidationError as exc:
                logger.error("PaperTradeStore.read_window deserialization failed: %s", exc)
                raise PaperTradeStoreError(f"Malformed paper trade row: {exc}") from exc
        return results
