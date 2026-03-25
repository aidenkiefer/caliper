# Ticket: 10-18-data-api-client

## Task
Implement the Polymarket Data API client for fetching trades, activity, and rebate data.

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- Create: `services/polymarket/adapters/data_api_client.py`
- Create: `tests/unit/polymarket/test_data_api_client.py`
- Modify: `docs/plans/PROGRESS.md` (completion note)

### Required read-only references
- `docs/plans/specs/polymarket-btc-trading-spec.md` (section 6.7, Phase 2 notes)

### Optional read-only references
- Polymarket Data API docs: `https://docs.polymarket.com/api-reference/data/get-trades`

## Agent type
backend-agent

## Skill pack
- `test-driven-development`

## Context + tool budget
- Max file reads: 5
- Max grep/glob operations: 3
- Max total tool calls: 12

## Done criteria
- `data_api_client.py` implements `DataAPIClient` class with methods:
  - `async def get_trades(token_id: str, start_time: datetime, end_time: datetime) -> List[dict]`
  - `async def get_activity(wallet_address: str, start_time: datetime, end_time: datetime) -> List[dict]`
  - `async def get_rebates(wallet_address: str, date: date) -> dict`
- Returns trade data with: `timestamp`, `price`, `size`, `side`, `maker_address`, `taker_address`
- Handles pagination for large result sets
- Rate limiting with exponential backoff
- Unit tests cover: successful fetch, pagination, date range filtering, API errors
- `docs/plans/PROGRESS.md` updated
