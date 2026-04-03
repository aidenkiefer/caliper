# Polymarket BTC Hourly Market-Making Service

This service implements automated market making on Polymarket's binary BTC hourly resolution markets. It runs a concurrent quoting loop — data feed, executor, heartbeat, and recorder — that places post-only limit orders on both sides of the YES/NO orderbook during a configurable daily session window (defaulting to 9 AM ET). Orders are EIP-712 signed on-chain via `py-clob-client` / `eth_account`; safety controls include cancel-all on error, an inventory cap, post-only enforcement, and a per-session loss limit. All trade and snapshot data is written to the shared TimescaleDB instance under the `pm.*` schema.

## Documentation

- [Setup Guide](docs/SETUP.md)
- [Configuration Reference](docs/CONFIG.md)
- [Operations Runbook](docs/RUNBOOK.md)

## Links

- Feature spec: `docs/plans/specs/polymarket-btc-hourly-mm.md`
- Tickets: `docs/plans/tickets/` (prefix `10-xx`)
- Progress summary: `docs/plans/POLYMARKET-TICKETS-1-5-SUMMARY.md`
- Config reference: `services/polymarket/config.py` (`PolymarketConfig`)
- Constants reference: `services/polymarket/constants.py`
