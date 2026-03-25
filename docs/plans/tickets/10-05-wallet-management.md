# Ticket: 10-05-wallet-management

## Task
Implement wallet management for Polygon operations: balance checks, order signing, USDC split/merge, and token redemption.

## Scope boundaries

### Allowed files (ONLY these — edit nothing else)
- Create: `services/polymarket/wallet.py`
- Create: `tests/unit/polymarket/test_wallet.py`
- Modify: `docs/plans/PROGRESS.md` (completion note)

### Required read-only references
- `docs/plans/specs/polymarket-btc-trading-spec.md` (section 6.8)

### Optional read-only references
- Polymarket CTF docs: `https://docs.polymarket.com/resources/contract-addresses`
- `py-clob-client` signing examples
- `eth_account` library docs

## Agent type
backend-agent

## Skill pack
- `test-driven-development`

## Context + tool budget
- Max file reads: 6
- Max grep/glob operations: 3
- Max total tool calls: 15

## Done criteria
- `wallet.py` implements `WalletManager` class with methods:
  - `async def get_usdc_balance() -> Decimal`
  - `async def get_token_balance(token_id: str) -> Decimal`
  - `def sign_order(order_data: dict) -> str` (EIP-712 signature)
  - `async def split_usdc(amount: Decimal, condition_id: str) -> dict` (split into YES+NO)
  - `async def merge_tokens(amount: Decimal, condition_id: str) -> dict` (merge YES+NO back to USDC)
  - `async def redeem_tokens(token_id: str) -> dict` (after market resolution)
- Uses `eth_account` for signing and Web3 for contract calls
- CTF contract addresses loaded from `constants.py` (placeholder values for now)
- Private key loaded from config, never logged
- Unit tests use mock Web3 provider and cover: balance queries, signing, split/merge logic, redemption
- `docs/plans/PROGRESS.md` updated
