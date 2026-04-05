from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import List, Optional

import asyncpg

from services.simulation.schemas import SimEvent

logger = logging.getLogger(__name__)


class EventLoader:
    """
    Loads historical Polymarket events into a sorted stream of SimEvent objects.
    Two backends: database (pm.orderbook_snapshots + pm.trades) and file (JSONL).
    Determinism: sort keyed on (timestamp, event_id).
    """

    def __init__(self, db_url: Optional[str] = None) -> None:
        self._db_url = db_url

    async def load_from_db(
        self,
        market_id: str,
        token_id: str,
        start: datetime,
        end: datetime,
    ) -> List[SimEvent]:
        """Query pm.* tables and return sorted SimEvent list."""
        if not self._db_url:
            raise ValueError("db_url required for database backend")
        conn = await asyncpg.connect(self._db_url)
        try:
            events: List[SimEvent] = []
            snapshot_rows = await conn.fetch(
                """
                SELECT id::text, captured_at, market_id, token_id, snapshot_data
                FROM pm.orderbook_snapshots
                WHERE market_id = $1 AND token_id = $2
                  AND captured_at >= $3 AND captured_at <= $4
                ORDER BY captured_at
                """,
                market_id, token_id, start, end,
            )
            for row in snapshot_rows:
                payload = row["snapshot_data"] if isinstance(row["snapshot_data"], dict) else json.loads(row["snapshot_data"])
                events.append(SimEvent(
                    event_id=str(row["id"]),
                    timestamp=row["captured_at"],
                    event_type="snapshot",
                    market_id=row["market_id"],
                    token_id=row["token_id"],
                    payload=payload,
                ))
            trade_rows = await conn.fetch(
                """
                SELECT id::text, traded_at, market_id, token_id, side, price, size
                FROM pm.trades
                WHERE market_id = $1 AND token_id = $2
                  AND traded_at >= $3 AND traded_at <= $4
                ORDER BY traded_at
                """,
                market_id, token_id, start, end,
            )
            for row in trade_rows:
                events.append(SimEvent(
                    event_id=str(row["id"]),
                    timestamp=row["traded_at"],
                    event_type="trade",
                    market_id=row["market_id"],
                    token_id=row["token_id"],
                    payload={
                        "side": row["side"],
                        "price": str(row["price"]),
                        "size": str(row["size"]),
                    },
                ))
        finally:
            await conn.close()
        events.sort(key=lambda e: (e.timestamp, e.event_id))
        self._detect_gaps(events)
        return events

    def load_from_file(self, path: str) -> List[SimEvent]:
        """Read JSONL file, parse each line as SimEvent, sort by (timestamp, event_id)."""
        events: List[SimEvent] = []
        with open(path, "r") as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    events.append(SimEvent.model_validate(data))
                except Exception as exc:
                    logger.warning("Skipping line %d in %s: %s", line_num, path, exc)
        events.sort(key=lambda e: (e.timestamp, e.event_id))
        self._detect_gaps(events)
        return events

    async def load(
        self,
        market_id: str,
        token_id: str,
        start: datetime,
        end: datetime,
        file_path: Optional[str] = None,
    ) -> List[SimEvent]:
        """File backend if file_path given, else database backend. File results filtered to [start, end]."""
        if file_path is not None:
            events = self.load_from_file(file_path)
            return [e for e in events if start <= e.timestamp <= end]
        return await self.load_from_db(market_id, token_id, start, end)

    def _detect_gaps(
        self,
        events: List[SimEvent],
        threshold_seconds: int = 300,
    ) -> None:
        """Log warnings for gaps > threshold between consecutive snapshot events."""
        snapshots = [e for e in events if e.event_type == "snapshot"]
        for i in range(1, len(snapshots)):
            gap = (snapshots[i].timestamp - snapshots[i - 1].timestamp).total_seconds()
            if gap > threshold_seconds:
                logger.warning(
                    "Gap detected in event stream: %.1fs between %s and %s",
                    gap,
                    snapshots[i - 1].timestamp.isoformat(),
                    snapshots[i].timestamp.isoformat(),
                )
