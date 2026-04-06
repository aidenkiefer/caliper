from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, List

from packages.common.market_schemas import SignalType
from services.fleet.paper_store import PaperTradeStore
from services.fleet.schemas import PaperTrade


class FakeConnection:
    def __init__(self) -> None:
        self.executed: List[tuple[str, tuple[Any, ...]]] = []
        self.rows: List[dict[str, Any]] = []

    async def execute(self, sql: str, *params: Any) -> str:
        self.executed.append((sql, params))
        return "INSERT 0 1"

    async def fetch(self, sql: str, *params: Any) -> List[dict[str, Any]]:
        self.executed.append((sql, params))
        return list(self.rows)

    async def fetchrow(self, sql: str, *params: Any) -> dict[str, Any] | None:
        self.executed.append((sql, params))
        return self.rows[0] if self.rows else None


class FakeAcquire:
    def __init__(self, conn: FakeConnection) -> None:
        self._conn = conn

    async def __aenter__(self) -> FakeConnection:
        return self._conn

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class FakePool:
    def __init__(self) -> None:
        self.connection = FakeConnection()

    def acquire(self) -> FakeAcquire:
        return FakeAcquire(self.connection)

    async def close(self) -> None:
        return None


def _trade() -> PaperTrade:
    return PaperTrade(
        executed_at=datetime.now(timezone.utc),
        strategy_id="maker",
        market_id="market-1",
        signal_type=SignalType.MARKET_MAKING,
        direction="none",
        side="BUY",
        price=Decimal("0.48"),
        quantity=Decimal("3"),
        notional=Decimal("1.44"),
        confidence=Decimal("1"),
        regime="R1",
        allocation_weight=Decimal("1"),
        metadata={"hello": "world"},
    )


def test_paper_trade_store_writes_and_reads_rows() -> None:
    pool = FakePool()
    store = PaperTradeStore(pool=pool)
    trade = _trade()

    asyncio.run(store.write_fill(trade))
    assert pool.connection.executed
    sql, params = pool.connection.executed[0]
    assert "pm.paper_trades" in sql
    assert params[2] == "maker"

    pool.connection.rows = [
        {
            "trade_id": trade.trade_id,
            "executed_at": trade.executed_at,
            "strategy_id": trade.strategy_id,
            "market_id": trade.market_id,
            "signal_type": trade.signal_type.value,
            "direction": trade.direction,
            "side": trade.side,
            "price": trade.price,
            "quantity": trade.quantity,
            "notional": trade.notional,
            "confidence": trade.confidence,
            "status": trade.status,
            "regime": trade.regime,
            "allocation_weight": trade.allocation_weight,
            "metadata": trade.metadata,
        }
    ]

    latest = asyncio.run(store.read_latest())
    assert latest is not None
    assert latest.strategy_id == "maker"
    assert latest.metadata["hello"] == "world"

