# Ticket: 10-16-shared-schemas

## Task
Add Polymarket Pydantic schemas to `packages/common/polymarket_schemas.py` for API integration.

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- Create: `packages/common/polymarket_schemas.py`
- Modify: `packages/common/__init__.py` (export new schemas)
- Modify: `docs/plans/PROGRESS.md` (completion note)

### Required read-only references
- `docs/plans/specs/polymarket-btc-trading-spec.md` (section 7.2)

### Optional read-only references
- `packages/common/schemas.py` (example patterns)

## Agent type
backend-agent

## Skill pack
None required (straightforward schema definitions)

## Context + tool budget
- Max file reads: 4
- Max grep/glob operations: 2
- Max total tool calls: 8

## Done criteria
- `polymarket_schemas.py` defines Pydantic models:
  - `PolymarketSessionResponse` (session summary)
  - `PolymarketOrderResponse` (order details)
  - `PolymarketFillResponse` (fill details)
  - `PolymarketSnapshotResponse` (orderbook snapshot)
  - `PolymarketPnLResponse` (PnL breakdown)
  - `PolymarketSessionListResponse` (list of sessions)
- All models use `Decimal` for money fields, `datetime` for timestamps (UTC)
- Models match database schema from spec section 3
- `__init__.py` exports all new models
- `docs/plans/PROGRESS.md` updated
