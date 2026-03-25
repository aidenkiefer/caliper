# Ticket: 10-01-polymarket-scaffolding

## Task
Create the `services/polymarket/` directory structure, Poetry config, and core modules (config, constants, schemas) for the Polymarket trading service.

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- Create: `services/polymarket/__init__.py`
- Create: `services/polymarket/pyproject.toml`
- Create: `services/polymarket/config.py`
- Create: `services/polymarket/constants.py`
- Create: `services/polymarket/schemas.py`
- Create: `services/polymarket/adapters/__init__.py`
- Create: `services/polymarket/README.md`
- Modify: `docs/plans/PROGRESS.md` (completion note)

### Required read-only references
- `docs/plans/specs/polymarket-btc-trading-spec.md` (sections 2.1, 4.0, 4.1, 13)

### Optional read-only references
- `services/api/pyproject.toml` (example Poetry config pattern)
- `packages/common/schemas.py` (example Pydantic patterns)

## Agent type
backend-agent

## Skill pack
None required (straightforward scaffolding)

## Context + tool budget
- Max file reads: 5
- Max grep/glob operations: 3
- Max total tool calls: 10

## Done criteria
- `services/polymarket/` directory exists with all files listed above
- `pyproject.toml` includes dependencies: `pydantic`, `pydantic-settings`, `py-clob-client`, `web3`, `eth-account`, `httpx`, `websockets`, `asyncpg`, `sqlalchemy`
- `config.py` implements `PolymarketConfig(BaseSettings)` with all fields from spec section 4.1
- `constants.py` defines API URLs, fee parameters (pre/post Mar 30), CTF contract addresses (placeholder for now), timing constants
- `schemas.py` defines internal Pydantic models: `MarketInfo`, `OrderbookState`, `QuoteDecision`
- `README.md` has one-paragraph service description and links to spec
- `docs/plans/PROGRESS.md` updated with completion note
