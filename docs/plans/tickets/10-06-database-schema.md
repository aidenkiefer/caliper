# Ticket: 10-06-database-schema

## Task
Create Alembic migration for Polymarket schema (`pm.*` tables) in the shared TimescaleDB.

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- Create: `services/data/alembic/versions/<timestamp>_create_polymarket_schema.py`
- Modify: `docs/plans/PROGRESS.md` (completion note)

### Required read-only references
- `docs/plans/specs/polymarket-btc-trading-spec.md` (section 3, all tables)

### Optional read-only references
- `services/data/alembic/versions/` (example migration patterns)
- TimescaleDB hypertable docs

## Agent type
backend-agent

## Skill pack
None required (straightforward migration)

## Context + tool budget
- Max file reads: 6
- Max grep/glob operations: 3
- Max total tool calls: 10

## Done criteria
- Migration creates schema `pm` if not exists
- Creates all 8 tables: `pm.sessions`, `pm.orders`, `pm.fills`, `pm.orderbook_snapshots`, `pm.binance_candles`, `pm.pnl_snapshots`, `pm.market_metadata`, `pm.toxic_flow_by_minute`
- Hypertables: `pm.orderbook_snapshots`, `pm.binance_candles`, `pm.pnl_snapshots` (on `timestamp` column)
- Regular tables: `pm.sessions`, `pm.orders`, `pm.fills`, `pm.market_metadata`, `pm.toxic_flow_by_minute`
- All indexes from spec section 3 are created
- All CHECK constraints and foreign keys are defined
- Migration includes `downgrade()` to drop schema
- `docs/plans/PROGRESS.md` updated
