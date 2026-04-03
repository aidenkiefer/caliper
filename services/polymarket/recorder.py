"""
Recorder for the Polymarket BTC hourly market-making service.

Persists session state, orders, fills, orderbook snapshots, PnL snapshots,
and Binance candles to TimescaleDB via asyncpg. Snapshot inserts are batched
(buffer of 10 rows, flushed every 30 s or when the buffer is full). All other
inserts are immediate.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

import asyncpg

from services.polymarket.config import PolymarketConfig
from services.polymarket.schemas import MarketInfo, OrderbookState

logger = logging.getLogger(__name__)

_SNAPSHOT_BATCH_SIZE = 10
_FLUSH_INTERVAL_SECONDS = 30


class Recorder:
    """
    Persists Polymarket session data to the ``pm`` schema in TimescaleDB.

    Batched tables
    --------------
    * ``pm.orderbook_snapshots`` — buffered, flushed at 10 rows or every 30 s
    * ``pm.pnl_snapshots``       — buffered, flushed at 10 rows or every 30 s

    Immediate tables
    ----------------
    * ``pm.sessions``, ``pm.orders``, ``pm.fills``, ``pm.binance_candles``
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool
        self._snapshot_buffer: list[dict[str, Any]] = []
        self._pnl_buffer: list[dict[str, Any]] = []
        self._flush_task: Optional[asyncio.Task] = None  # type: ignore[type-arg]
        self._snapshot_lock = asyncio.Lock()
        self._pnl_lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the periodic background flush task."""
        if self._flush_task is not None and not self._flush_task.done():
            return
        self._flush_task = asyncio.create_task(self._periodic_flush())

    async def stop(self) -> None:
        """Flush remaining buffers and cancel the background task."""
        if self._flush_task is not None:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
            self._flush_task = None
        await self._flush_all()

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    async def create_session(self, market: MarketInfo, config: PolymarketConfig) -> UUID:
        """
        Insert a new row into ``pm.sessions`` and return the generated session_id.
        """
        config_snapshot = {
            "quote_spread": str(config.quote_spread),
            "quote_size": str(config.quote_size),
            "inventory_cap": str(config.inventory_cap),
            "max_session_loss_usdc": str(config.max_session_loss_usdc),
            "requote_interval_seconds": config.requote_interval_seconds,
            "wind_down_minutes": config.wind_down_minutes,
            "fees_enabled": market.fees_enabled,
        }
        sql = """
            INSERT INTO pm.sessions (
                market_condition_id,
                market_slug,
                token_id_yes,
                token_id_no,
                window_start,
                window_end,
                initial_usdc,
                fees_enabled,
                config_snapshot,
                status
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb, $10)
            RETURNING session_id
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                sql,
                market.condition_id,
                market.slug,
                market.token_id_yes,
                market.token_id_no,
                market.window_start,
                market.window_end,
                Decimal("0"),
                market.fees_enabled,
                json.dumps(config_snapshot),
                "ACTIVE",
            )
        return UUID(str(row["session_id"]))

    async def finalize_session(self, session_id: UUID, final_state: dict) -> None:
        """
        Update ``pm.sessions`` with final metrics and compute + store regime tags.

        Regime classification
        ---------------------
        * ``volatility_regime``: derived from avg spread in orderbook_snapshots
          — 'LOW' if avg_spread < 0.02, 'HIGH' if > 0.05, else 'MEDIUM'
        * ``spread_regime``:     'TIGHT' if avg_spread < 0.02, 'WIDE' if > 0.05
          (note: DB CHECK allows only 'TIGHT'/'WIDE' per migration)
        * ``volume_regime``:     fill count — 'LOW' < 5, 'MEDIUM' < 20, 'HIGH' >= 20
        * ``btc_trend_regime``:  first vs last BTC close price — 'UP' > 1%,
          'DOWN' < -1%, 'FLAT' otherwise
        """
        # ---- gather regime inputs from the DB --------------------------------
        async with self._pool.acquire() as conn:
            snap_row = await conn.fetchrow(
                """
                SELECT AVG(spread) AS avg_spread
                FROM pm.orderbook_snapshots
                WHERE session_id = $1
                """,
                session_id,
            )
            fill_count_row = await conn.fetchrow(
                "SELECT COUNT(*) AS cnt FROM pm.fills WHERE session_id = $1",
                session_id,
            )
            candle_row = await conn.fetchrow(
                """
                SELECT
                    FIRST(close, open_time) AS first_close,
                    LAST(close, open_time)  AS last_close
                FROM pm.binance_candles
                WHERE open_time >= (
                    SELECT window_start FROM pm.sessions WHERE session_id = $1
                )
                AND open_time <= (
                    SELECT window_end FROM pm.sessions WHERE session_id = $1
                )
                """,
                session_id,
            )

        # ---- derive regime labels ---------------------------------------------
        avg_spread = Decimal(str(snap_row["avg_spread"])) if snap_row["avg_spread"] is not None else None
        fill_count = int(fill_count_row["cnt"]) if fill_count_row else 0

        # TIGHT for spreads < 0.05 (mid-range included), WIDE for >= 0.05.
        # The DB CHECK constraint only allows 'TIGHT' or 'WIDE'; mid-range spreads
        # (0.02–0.05) are classified as 'TIGHT' by convention.
        if avg_spread is None:
            volatility_regime = "MEDIUM"
            spread_regime = "TIGHT"
        elif avg_spread < Decimal("0.02"):
            volatility_regime = "LOW"
            spread_regime = "TIGHT"
        elif avg_spread >= Decimal("0.05"):
            volatility_regime = "HIGH"
            spread_regime = "WIDE"
        else:
            volatility_regime = "MEDIUM"
            # Mid-range spread (0.02 <= avg_spread < 0.05): classified TIGHT by convention
            spread_regime = "TIGHT"

        if fill_count < 5:
            volume_regime = "LOW"
        elif fill_count < 20:
            volume_regime = "MEDIUM"
        else:
            volume_regime = "HIGH"

        btc_trend_regime = "FLAT"
        if candle_row and candle_row["first_close"] is not None and candle_row["last_close"] is not None:
            first_close = Decimal(str(candle_row["first_close"]))
            last_close = Decimal(str(candle_row["last_close"]))
            if first_close > 0:
                pct_change = (last_close - first_close) / first_close * 100
                if pct_change > Decimal("1"):
                    btc_trend_regime = "UP"
                elif pct_change < Decimal("-1"):
                    btc_trend_regime = "DOWN"

        # ---- update session row -----------------------------------------------
        update_sql = """
            UPDATE pm.sessions SET
                final_usdc          = $2,
                realized_pnl        = $3,
                spread_capture_pnl  = $4,
                inventory_drift_pnl = $5,
                total_orders_placed = $6,
                total_fills         = $7,
                total_volume_usdc   = $8,
                avg_spread_quoted   = $9,
                volatility_regime   = $10,
                spread_regime       = $11,
                volume_regime       = $12,
                btc_trend_regime    = $13,
                status              = $14,
                completed_at        = $15,
                error_message       = $16
            WHERE session_id = $1
        """
        async with self._pool.acquire() as conn:
            await conn.execute(
                update_sql,
                session_id,
                final_state.get("final_usdc"),
                final_state.get("realized_pnl"),
                final_state.get("spread_capture_pnl"),
                final_state.get("inventory_drift_pnl"),
                final_state.get("total_orders_placed"),
                final_state.get("total_fills"),
                final_state.get("total_volume_usdc"),
                avg_spread,
                volatility_regime,
                spread_regime,
                volume_regime,
                btc_trend_regime,
                final_state.get("status", "COMPLETED"),
                datetime.now(tz=timezone.utc),
                final_state.get("error_message"),
            )

    # ------------------------------------------------------------------
    # Immediate inserts
    # ------------------------------------------------------------------

    async def record_order(self, order_data: dict, session_id: UUID) -> None:
        """Insert one row into ``pm.orders``."""
        sql = """
            INSERT INTO pm.orders (
                session_id,
                polymarket_order_id,
                token_id,
                side,
                price,
                original_size,
                filled_size,
                order_type,
                post_only,
                status,
                midpoint_at_place,
                spread_at_place,
                quote_version_id
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
        """
        async with self._pool.acquire() as conn:
            await conn.execute(
                sql,
                session_id,
                order_data.get("polymarket_order_id"),
                order_data["token_id"],
                order_data["side"],
                order_data["price"],
                order_data["original_size"],
                order_data.get("filled_size", Decimal("0")),
                order_data.get("order_type", "GTC"),
                order_data.get("post_only", True),
                order_data.get("status", "PENDING"),
                order_data.get("midpoint_at_place"),
                order_data.get("spread_at_place"),
                order_data.get("quote_version_id"),
            )

    async def record_fill(self, fill_data: dict, session_id: UUID) -> None:
        """Insert one row into ``pm.fills``."""
        sql = """
            INSERT INTO pm.fills (
                session_id,
                order_id,
                token_id,
                side,
                price,
                size,
                fee,
                is_maker,
                filled_at,
                midpoint_at_fill,
                binance_price_at_fill,
                inventory_after,
                edge_at_fill,
                quote_version_id
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
        """
        async with self._pool.acquire() as conn:
            await conn.execute(
                sql,
                session_id,
                fill_data.get("order_id"),
                fill_data["token_id"],
                fill_data["side"],
                fill_data["price"],
                fill_data["size"],
                fill_data.get("fee", Decimal("0")),
                fill_data.get("is_maker", True),
                fill_data.get("filled_at", datetime.now(tz=timezone.utc)),
                fill_data.get("midpoint_at_fill"),
                fill_data.get("binance_price_at_fill"),
                fill_data.get("inventory_after"),
                fill_data.get("edge_at_fill"),
                fill_data.get("quote_version_id"),
            )

    async def record_binance_candle(self, candle: dict, session_id: UUID) -> None:
        """Insert one row into ``pm.binance_candles``."""
        sql = """
            INSERT INTO pm.binance_candles (
                open_time,
                close_time,
                open,
                high,
                low,
                close,
                volume,
                source
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (source, open_time) DO NOTHING
        """
        async with self._pool.acquire() as conn:
            await conn.execute(
                sql,
                candle["open_time"],
                candle["close_time"],
                candle["open"],
                candle["high"],
                candle["low"],
                candle["close"],
                candle.get("volume"),
                candle.get("source", "binance"),
            )

    # ------------------------------------------------------------------
    # Buffered inserts
    # ------------------------------------------------------------------

    async def record_snapshot(self, snapshot: OrderbookState, session_id: UUID) -> None:
        """
        Buffer an orderbook snapshot row. Flushes automatically when the
        buffer reaches ``_SNAPSHOT_BATCH_SIZE``.
        """
        row: dict[str, Any] = {
            "session_id": session_id,
            "timestamp": snapshot.last_updated,
            "best_bid": snapshot.best_bid,
            "best_ask": snapshot.best_ask,
            "midpoint": snapshot.midpoint,
            "spread": snapshot.spread,
            "bid_depth_1pct": snapshot.bid_depth_1pct,
            "ask_depth_1pct": snapshot.ask_depth_1pct,
            "imbalance": snapshot.imbalance,
        }
        async with self._snapshot_lock:
            self._snapshot_buffer.append(row)
            should_flush = len(self._snapshot_buffer) >= _SNAPSHOT_BATCH_SIZE
        if should_flush:
            await self._flush_snapshots()

    async def record_pnl_snapshot(self, pnl_data: dict, session_id: UUID) -> None:
        """
        Buffer a PnL snapshot row. Flushes automatically when the buffer
        reaches ``_SNAPSHOT_BATCH_SIZE``.
        """
        row: dict[str, Any] = {
            "session_id": session_id,
            **pnl_data,
        }
        async with self._pnl_lock:
            self._pnl_buffer.append(row)
            should_flush = len(self._pnl_buffer) >= _SNAPSHOT_BATCH_SIZE
        if should_flush:
            await self._flush_pnl_snapshots()

    # ------------------------------------------------------------------
    # Adverse selection
    # ------------------------------------------------------------------

    async def update_adverse_selection_async(
        self,
        fill_id: UUID,
        midpoint_5s: Decimal,
        midpoint_10s: Decimal,
    ) -> None:
        """
        Update a fill row with post-fill midpoint observations and derive
        the ``adverse_selection_flag`` (True when the market moved against
        the maker position after the fill).
        """
        sql = """
            UPDATE pm.fills SET
                midpoint_5s_after       = $2,
                midpoint_10s_after      = $3,
                edge_5s_after           = CASE
                    WHEN side = 'BUY'  THEN $2 - price
                    WHEN side = 'SELL' THEN price - $2
                    ELSE NULL
                END,
                adverse_selection_flag  = CASE
                    WHEN side = 'BUY'  THEN $2 < price
                    WHEN side = 'SELL' THEN $2 > price
                    ELSE NULL
                END
            WHERE fill_id = $1
        """
        async with self._pool.acquire() as conn:
            await conn.execute(sql, fill_id, midpoint_5s, midpoint_10s)

    async def compute_toxic_flow_by_minute(self, session_id: UUID) -> None:
        """
        Aggregate fill-level adverse selection data into
        ``pm.toxic_flow_by_minute`` for the given session.

        The minute_offset is computed relative to the session's ``window_start``
        and is clamped to [0, 59] by the table's CHECK constraint — only the
        first hour of each session is bucketed here.
        """
        sql = """
            INSERT INTO pm.toxic_flow_by_minute (
                session_id,
                minute_offset,
                total_fills,
                adverse_fills,
                adverse_fill_pct,
                avg_edge_realized
            )
            SELECT
                f.session_id,
                EXTRACT(MINUTE FROM (f.filled_at - s.window_start))::int AS minute_offset,
                COUNT(*)                                                   AS total_fills,
                COUNT(*) FILTER (WHERE f.adverse_selection_flag = TRUE)    AS adverse_fills,
                ROUND(
                    100.0 * COUNT(*) FILTER (WHERE f.adverse_selection_flag = TRUE)
                    / NULLIF(COUNT(*), 0),
                    2
                )                                                           AS adverse_fill_pct,
                AVG(f.edge_at_fill)                                        AS avg_edge_realized
            FROM pm.fills f
            JOIN pm.sessions s ON s.session_id = f.session_id
            WHERE f.session_id = $1
              AND EXTRACT(MINUTE FROM (f.filled_at - s.window_start)) BETWEEN 0 AND 59
            GROUP BY f.session_id, minute_offset
            ON CONFLICT (session_id, minute_offset) DO UPDATE SET
                total_fills      = EXCLUDED.total_fills,
                adverse_fills    = EXCLUDED.adverse_fills,
                adverse_fill_pct = EXCLUDED.adverse_fill_pct,
                avg_edge_realized = EXCLUDED.avg_edge_realized
        """
        async with self._pool.acquire() as conn:
            await conn.execute(sql, session_id)

    # ------------------------------------------------------------------
    # Internal flush helpers
    # ------------------------------------------------------------------

    async def _flush_snapshots(self) -> None:
        """Write buffered orderbook snapshot rows to the DB and clear the buffer."""
        async with self._snapshot_lock:
            if not self._snapshot_buffer:
                return
            rows = self._snapshot_buffer[:]
        sql = """
            INSERT INTO pm.orderbook_snapshots (
                session_id,
                timestamp,
                best_bid,
                best_ask,
                midpoint,
                spread,
                bid_depth_1pct,
                ask_depth_1pct,
                imbalance
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """
        try:
            async with self._pool.acquire() as conn:
                await conn.executemany(
                    sql,
                    [
                        (
                            r["session_id"],
                            r["timestamp"],
                            r.get("best_bid"),
                            r.get("best_ask"),
                            r.get("midpoint"),
                            r.get("spread"),
                            r.get("bid_depth_1pct"),
                            r.get("ask_depth_1pct"),
                            r.get("imbalance"),
                        )
                        for r in rows
                    ],
                )
            async with self._snapshot_lock:
                self._snapshot_buffer.clear()  # only clear after successful DB write
        except Exception:
            raise

    async def _flush_pnl_snapshots(self) -> None:
        """Write buffered PnL snapshot rows to the DB and clear the buffer."""
        async with self._pnl_lock:
            if not self._pnl_buffer:
                return
            rows = self._pnl_buffer[:]
        sql = """
            INSERT INTO pm.pnl_snapshots (
                session_id,
                timestamp,
                mark_to_market_pnl,
                realized_pnl,
                spread_capture,
                inventory_value,
                cash_balance
            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
        """
        try:
            async with self._pool.acquire() as conn:
                await conn.executemany(
                    sql,
                    [
                        (
                            r["session_id"],
                            r.get("timestamp", datetime.now(tz=timezone.utc)),
                            r.get("mark_to_market_pnl"),
                            r.get("realized_pnl"),
                            r.get("spread_capture"),
                            r.get("inventory_value"),
                            r.get("cash_balance"),
                        )
                        for r in rows
                    ],
                )
            async with self._pnl_lock:
                self._pnl_buffer.clear()  # only clear after successful DB write
        except Exception:
            raise

    async def _flush_all(self) -> None:
        """Flush both snapshot buffers."""
        await self._flush_snapshots()
        await self._flush_pnl_snapshots()

    async def _periodic_flush(self) -> None:
        """Background task: flush buffers every ``_FLUSH_INTERVAL_SECONDS`` seconds."""
        while True:
            await asyncio.sleep(_FLUSH_INTERVAL_SECONDS)
            try:
                await self._flush_all()
            except Exception:
                logger.exception("Error during periodic flush of snapshot buffers")
