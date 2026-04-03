# Polymarket Service — Setup Guide

## Prerequisites

1. **Polymarket account and API key**
   - Create an account at [polymarket.com](https://polymarket.com)
   - Generate an API key from your account settings (used to sign CLOB orders)

2. **Polygon wallet with USDC and MATIC**
   - A funded Polygon (PoS) wallet is required; the private key signs EIP-712 order messages
   - You need USDC on Polygon for collateral and a small MATIC balance for gas
   - Minimum recommended: 200 USDC (matches default `inventory_cap`) + 1 MATIC for gas

3. **Python 3.11+**
   - Verify: `python --version`

4. **PostgreSQL with TimescaleDB**
   - The shared TimescaleDB instance (started via `make up` in the repo root) is used
   - The service writes to the `pm.*` schema

---

## Environment Setup

Create `configs/environments/.env.polymarket` (never commit real keys):

```dotenv
# Required — Polygon wallet credentials
POLYMARKET_PRIVATE_KEY=0xabc123...          # Polygon wallet private key (hex)
POLYMARKET_WALLET_ADDRESS=0xDEF456...       # Corresponding public wallet address

# Required — Database
POLYMARKET_DATABASE_URL=postgresql://caliper:caliper@localhost:5432/caliper

# Optional — Session timing
POLYMARKET_TARGET_HOUR_LOCAL=9              # Hour (24h) to start the session (default: 9)
POLYMARKET_TARGET_TIMEZONE=America/New_York # Timezone for target_hour_local (default: America/New_York)
POLYMARKET_PRE_SESSION_MINUTES=5            # Minutes before session to begin preparation (default: 5)
POLYMARKET_WIND_DOWN_MINUTES=5             # Minutes before end of session to stop quoting (default: 5)

# Optional — Market-making parameters
POLYMARKET_QUOTE_SPREAD=0.02               # Half-spread in probability units (default: 0.02)
POLYMARKET_QUOTE_SIZE=50                   # Size per quote in USDC (default: 50)
POLYMARKET_INVENTORY_CAP=200              # Max net inventory in USDC (default: 200)
POLYMARKET_REQUOTE_INTERVAL_SECONDS=10    # Seconds between requote cycles (default: 10)
POLYMARKET_MAX_SESSION_LOSS_USDC=20       # Per-session loss limit in USDC (default: 20)

# Optional — Internal timers
POLYMARKET_HEARTBEAT_INTERVAL_SECONDS=5   # Heartbeat ping interval (default: 5)
POLYMARKET_SNAPSHOT_INTERVAL_SECONDS=5    # Orderbook snapshot recording interval (default: 5)

# Optional — Safety
POLYMARKET_CANCEL_ALL_ON_ERROR=true       # Cancel all open orders on unhandled error (default: true)

# Optional — API endpoints (defaults shown; change only for staging/testing)
POLYMARKET_GAMMA_API_URL=https://gamma-api.polymarket.com
POLYMARKET_CLOB_API_URL=https://clob.polymarket.com
POLYMARKET_DATA_API_URL=https://data-api.polymarket.com
POLYMARKET_CLOB_WS_URL=wss://ws-subscriptions-clob.polymarket.com/ws/
POLYMARKET_BINANCE_API_URL=https://api.binance.com
POLYMARKET_BINANCE_STALE_SECONDS=30
```

Load the file before running the service:

```bash
export $(grep -v '^#' configs/environments/.env.polymarket | xargs)
```

---

## Database Migration

Run all pending Alembic migrations (this creates the `pm.*` schema):

```bash
cd services/data && poetry run alembic upgrade head
```

The migration `002_create_polymarket_schema.py` creates the `pm.sessions`, `pm.fills`, `pm.orders`, and `pm.snapshots` tables.

---

## Dependency Install

```bash
cd services/polymarket && poetry install
```

---

## Test Run (Dry Run)

A dry run validates configuration, market resolution, and connectivity without placing real orders:

```bash
POLYMARKET_PRIVATE_KEY=0xabc123... \
POLYMARKET_WALLET_ADDRESS=0xDEF456... \
POLYMARKET_DATABASE_URL=postgresql://caliper:caliper@localhost:5432/caliper \
polymarket-session --dry-run
```

Or with a custom target hour:

```bash
polymarket-session --dry-run --target-hour 9
```

Expected output on success:

```
INFO  [polymarket] Session starting (dry_run=True, target_hour=9, tz=America/New_York)
INFO  [polymarket] Resolved market: BTC-25MAR2026-... (condition_id=0x...)
INFO  [polymarket] Dry run complete — no orders placed
```

Log files are written to `logs/polymarket_<uuid>.log`.
