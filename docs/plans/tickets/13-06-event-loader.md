# Ticket 13-06: Event Loader

## Task

Implement `EventLoader` with two backends: a database backend reading from `pm.orderbook_snapshots` and `pm.trades` TimescaleDB tables, and a file backend reading from JSONL log files. Events are sorted deterministically by timestamp then sequence number. Gaps are logged as warnings.

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- Create: `services/simulation/replay/loader.py`
- Modify: `services/simulation/replay/__init__.py` (exports)
- Modify: `docs/plans/PROGRESS.md` (completion note)

### Required read-only references
- `docs/plans/specs/sprint-13-simulation-evaluation-spec.md` (§ EventLoader)
- `services/simulation/schemas.py` (SimEvent)
- `services/features/polymarket/store.py` (asyncpg connection patterns)
- `services/data/alembic/versions/002_create_polymarket_schema.py` (pm.* table schemas)

## Done criteria

### `services/simulation/replay/loader.py` — `EventLoader`

```python
class EventLoader:
    def __init__(self, db_url: Optional[str] = None):
        self._db_url = db_url  # if None, only file backend available
```

**`load_from_db(market_id: str, token_id: str, start: datetime, end: datetime) -> List[SimEvent]`** (async):
- Queries `pm.orderbook_snapshots` for snapshot events: SELECT id, captured_at, market_id, token_id, snapshot_data FROM pm.orderbook_snapshots WHERE market_id=? AND token_id=? AND captured_at BETWEEN ? AND ? ORDER BY captured_at.
- Queries `pm.trades` for trade events: SELECT id, traded_at, market_id, token_id, side, price, size FROM pm.trades WHERE market_id=? AND token_id=? AND traded_at BETWEEN ? AND ? ORDER BY traded_at.
- Maps each DB row to `SimEvent` with `event_type="snapshot"` or `event_type="trade"`.
- Merges both lists, sorts by `(timestamp, event_id)` for determinism.
- Detects gaps: if the interval between consecutive snapshot events exceeds 5 minutes, logs a warning: `"Gap detected in event stream: {gap_seconds}s between {t1} and {t2}"`.
- Returns the fully sorted `List[SimEvent]`.

**`load_from_file(path: str) -> List[SimEvent]`**:
- Reads a JSONL file (one JSON object per line). Each line is parsed into a `SimEvent` via `SimEvent.model_validate(json.loads(line))`.
- Lines that fail parsing are logged as warnings and skipped (not raised).
- Sorts by `(timestamp, event_id)`.
- Returns `List[SimEvent]`.

**`load(market_id: str, token_id: str, start: datetime, end: datetime, file_path: Optional[str] = None) -> List[SimEvent]`** (async):
- If `file_path` is provided: returns `load_from_file(file_path)` filtered to `start <= timestamp <= end`.
- Else: returns `await load_from_db(market_id, token_id, start, end)`.
- Determinism guarantee: same input always returns same output (sort is stable and keyed on (timestamp, event_id)).

**`_detect_gaps(events: List[SimEvent], threshold_seconds: int = 300) -> None`**:
- Private helper called by both backends. Logs warnings for gaps > threshold.

Uses `asyncpg` for DB (consistent with `services/features/polymarket/store.py` patterns). No ORM.
