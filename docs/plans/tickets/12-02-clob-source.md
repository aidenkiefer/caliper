# Ticket: 12-02-clob-source

## Task
Implement `services/features/polymarket/sources/clob.py`: an async CLOB data source that maintains a live orderbook buffer via WebSocket and provides REST-based snapshots for recovery, reward config, and fee rate lookups.

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- Create: `services/features/polymarket/sources/__init__.py`
- Create: `services/features/polymarket/sources/clob.py`
- Modify: `docs/plans/PROGRESS.md` (completion note)

### Required read-only references
- `docs/plans/specs/sprint-12-feature-layer-spec.md` (sections: Feature Families 1–2, Data Sources table, Architecture)
- `docs/research/microstructure-model.md` (sections: Data sources and pipeline, Operational constraints)

### Optional read-only references
- `services/polymarket/clients/clob_client.py` (existing CLOB client patterns — do NOT import directly; read for reference only)
- `services/features/polymarket/schemas.py` (SourceTimestamps, FeatureSnapshot field names)

### Example files (read-only, optional)
- `services/polymarket/data_feed.py` (existing WebSocket feed reconnect pattern)

## Agent type
backend-agent

## Skill pack
- `async-python-patterns` (WebSocket buffer, reconnect logic)

## Context + tool budget
- Max file reads: 6
- Max grep/glob operations: 4
- Max total tool calls: 12

## Done criteria

**`CLOBSource` class in `sources/clob.py`:**
- `async def connect(token_id: str) -> None` — opens WebSocket to `wss://ws-subscriptions-clob.polymarket.com/ws/market`, subscribes to `book`, `price_change`, `last_trade_price` channels for the given token
- Internal buffer stores the latest `OrderbookState`: `best_bid`, `best_ask`, `bids_depth_5tick`, `asks_depth_5tick`, `last_trade_price`, `last_trade_ts`, `last_price_change_ts`
- `get_orderbook_state() -> OrderbookState` — returns a copy of current buffer (raises `DataUnavailable` if no data yet)
- `async def reconnect() -> None` — reconnects and re-fetches REST snapshot on disconnect; uses exponential backoff (1s, 2s, 4s, max 30s)
- Heartbeat loop: sends POST to `/heartbeat` every 5 seconds while connected; if liveness lost, marks buffer stale
- `async def fetch_fee_rate(token_id: str) -> Decimal` — GET `/fee-rate?token_id=...`; returns 0 if not fee-enabled
- `async def fetch_reward_config(token_id: str) -> RewardConfig` — returns `RewardConfig(eligible: bool, max_spread: Optional[Decimal], min_size: Optional[Decimal])` from CLOB rewards endpoint; cached for 24h
- `async def restore_from_rest(token_id: str) -> None` — GET `/book?token_id=...`; populates buffer on startup or after reconnect
- `source_timestamp: datetime` attribute updated on every message received (used for staleness checks)
- Handles HTTP 425 (weekly restart) with exponential backoff

**`OrderbookState` dataclass in `sources/clob.py`:**
- Fields: `best_bid`, `best_ask`, `bids_depth_5tick`, `asks_depth_5tick`, `last_trade_price`, `last_trade_ts`, `last_price_change_ts`, `received_at: datetime`

**`RewardConfig` dataclass** defined in the same file

**`sources/__init__.py`** exports `CLOBSource`, `OrderbookState`, `RewardConfig`

**`docs/plans/PROGRESS.md`** updated
