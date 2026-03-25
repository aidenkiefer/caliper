# Ticket: 10-02-gamma-client

## Task
Implement the Gamma API client for discovering hourly BTC markets and fetching market metadata.

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- Create: `services/polymarket/adapters/gamma_client.py`
- Create: `tests/unit/polymarket/test_gamma_client.py`
- Modify: `docs/plans/PROGRESS.md` (completion note)

### Required read-only references
- `docs/plans/specs/polymarket-btc-trading-spec.md` (section 6.2)

### Optional read-only references
- Polymarket Gamma API docs: `https://docs.polymarket.com/api-reference/markets/list-markets`
- `services/polymarket/constants.py` (for API URL)

## Agent type
backend-agent

## Skill pack
- `test-driven-development`

## Context + tool budget
- Max file reads: 6
- Max grep/glob operations: 4
- Max total tool calls: 15

## Done criteria
- `gamma_client.py` implements `GammaClient` class with methods:
  - `async def find_hourly_btc_market(target_hour_utc: int, target_date: date) -> MarketInfo`
  - `async def get_market_metadata(condition_id: str) -> dict`
- Client handles rate limits, retries with exponential backoff
- Returns `MarketInfo` with: `condition_id`, `token_id_yes`, `token_id_no`, `window_start`, `window_end`, `tick_size`, `total_volume`
- Unit tests cover: successful discovery, market not found, multiple markets for same hour (picks highest volume), API error handling
- `docs/plans/PROGRESS.md` updated
