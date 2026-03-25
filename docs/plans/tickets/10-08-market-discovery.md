# Ticket: 10-08-market-discovery

## Task
Implement market discovery module to find the target hourly BTC market and cache metadata to the database.

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- Create: `services/polymarket/market_discovery.py`
- Create: `tests/unit/polymarket/test_market_discovery.py`
- Modify: `docs/plans/PROGRESS.md` (completion note)

### Required read-only references
- `docs/plans/specs/polymarket-btc-trading-spec.md` (section 6.2)

### Optional read-only references
- `services/polymarket/adapters/gamma_client.py`
- `services/polymarket/config.py`

## Agent type
backend-agent

## Skill pack
- `test-driven-development`

## Context + tool budget
- Max file reads: 7
- Max grep/glob operations: 3
- Max total tool calls: 15

## Done criteria
- `market_discovery.py` implements `MarketDiscovery` class with methods:
  - `async def discover_target_market(config: PolymarketConfig, db_conn) -> MarketInfo`
  - `async def cache_market_metadata(market: MarketInfo, db_conn) -> None`
- Uses `GammaClient` to find market matching `target_hour_local` and `target_timezone` (DST-aware)
- Writes to `pm.market_metadata` table
- Raises `MarketNotFoundError` if no matching market exists
- Unit tests cover: successful discovery, market not found, DST boundary handling, DB write
- `docs/plans/PROGRESS.md` updated
