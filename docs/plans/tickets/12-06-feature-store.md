# Ticket: 12-06-feature-store

## Task
Implement `services/features/polymarket/store.py`: a `FeatureStore` that reads and writes `FeatureSnapshot` records to the `pm.features` TimescaleDB hypertable.

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- Create: `services/features/polymarket/store.py`
- Modify: `services/features/polymarket/__init__.py` (export `FeatureStore`)
- Modify: `docs/plans/PROGRESS.md` (completion note)

### Required read-only references
- `docs/plans/specs/sprint-12-feature-layer-spec.md` (sections: FeatureStore, Database Migration)

### Optional read-only references
- `packages/common/polymarket_schemas.py` (FeatureSnapshot, FeatureRecord — read-only)
- `services/data/` (existing DB connection patterns — read-only)
- Any existing `pm.*` recorder or repo for `asyncpg` / SQLAlchemy patterns

### Example files (read-only, optional)
- `services/polymarket/recorder.py` (existing asyncpg write pattern)

## Agent type
backend-agent

## Skill pack
- `data-engineering-data-pipeline` (TimescaleDB write patterns)

## Context + tool budget
- Max file reads: 6
- Max grep/glob operations: 3
- Max total tool calls: 10

## Done criteria

**`FeatureStore` class in `store.py`:**

*Initialization:*
- `__init__(db_url: str)` — accepts asyncpg connection string
- `async def connect() -> None` — creates asyncpg connection pool (min=1, max=5)
- `async def close() -> None` — closes pool

*Write:*
- `async def write(snapshot: FeatureSnapshot) -> None`
  - Serializes `FeatureSnapshot` to JSONB via `snapshot.model_dump(mode="json")`
  - Inserts into `pm.features (market_id, token_id, captured_at, features)` using `ON CONFLICT DO NOTHING`
  - Raises `FeatureStoreError` (defined in this file) on DB errors; logs `ERROR` before re-raising

*Read:*
- `async def read_latest(market_id: str) -> Optional[FeatureSnapshot]`
  - `SELECT features FROM pm.features WHERE market_id = $1 ORDER BY captured_at DESC LIMIT 1`
  - Deserializes JSONB → `FeatureSnapshot`; returns `None` if no rows

- `async def read_window(market_id: str, start: datetime, end: datetime, limit: int = 1000) -> List[FeatureSnapshot]`
  - `SELECT features FROM pm.features WHERE market_id = $1 AND captured_at >= $2 AND captured_at <= $3 ORDER BY captured_at ASC LIMIT $4`
  - Returns list of `FeatureSnapshot`; empty list if no rows

*Error handling:*
- `FeatureStoreError(Exception)` defined in this file
- All DB calls wrapped in try/except; log then re-raise as `FeatureStoreError`
- Raises `RuntimeError` if any method called before `connect()`

**`services/features/polymarket/__init__.py`** exports `FeatureStore`

**`docs/plans/PROGRESS.md`** updated
