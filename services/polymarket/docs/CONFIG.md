# Polymarket Service — Configuration Reference

All configuration is loaded via `PolymarketConfig` (Pydantic `BaseSettings`) from environment variables with the prefix `POLYMARKET_`. See `services/polymarket/config.py` for the source of truth.

---

## Configuration Fields

| Field | Env Var | Type | Default | Description | Example |
|---|---|---|---|---|---|
| `private_key` | `POLYMARKET_PRIVATE_KEY` | `SecretStr` | **required** | Polygon wallet private key used to sign EIP-712 CLOB orders. Never logged or committed. | `0xabc123...` |
| `wallet_address` | `POLYMARKET_WALLET_ADDRESS` | `str` | **required** | Public Polygon wallet address corresponding to `private_key`. | `0xDEF456...` |
| `database_url` | `POLYMARKET_DATABASE_URL` | `str` | **required** | PostgreSQL connection string for the TimescaleDB instance. Must point to a DB with the `pm.*` schema migrated. | `postgresql://caliper:caliper@localhost:5432/caliper` |
| `target_hour_local` | `POLYMARKET_TARGET_HOUR_LOCAL` | `int` | `9` | Local hour (24-hour clock) at which the daily trading session starts. Interpreted in `target_timezone`. | `9` |
| `target_timezone` | `POLYMARKET_TARGET_TIMEZONE` | `str` | `America/New_York` | IANA timezone name for `target_hour_local`. | `America/Chicago` |
| `pre_session_minutes` | `POLYMARKET_PRE_SESSION_MINUTES` | `int` | `5` | Minutes before `target_hour_local` to begin pre-session preparation (market resolution, connectivity checks). | `10` |
| `wind_down_minutes` | `POLYMARKET_WIND_DOWN_MINUTES` | `int` | `5` | Minutes before market expiry to stop placing new quotes and cancel open orders. | `3` |
| `quote_spread` | `POLYMARKET_QUOTE_SPREAD` | `Decimal` | `0.02` | Half-spread added/subtracted from the mid-price when computing bid/ask in probability units (0–1). A value of `0.02` means ±2 cents on a 50-cent market. | `0.03` |
| `quote_size` | `POLYMARKET_QUOTE_SIZE` | `Decimal` | `50` | Size of each individual quote in USDC. Both the YES bid and NO bid are placed at this size per requote cycle. | `100` |
| `inventory_cap` | `POLYMARKET_INVENTORY_CAP` | `Decimal` | `200` | Maximum net inventory in USDC the service will hold at any time. New quotes are suppressed when inventory would exceed this cap. | `300` |
| `requote_interval_seconds` | `POLYMARKET_REQUOTE_INTERVAL_SECONDS` | `int` | `10` | Seconds between consecutive requote cycles. Lower values increase order activity and API usage. | `15` |
| `max_session_loss_usdc` | `POLYMARKET_MAX_SESSION_LOSS_USDC` | `Decimal` | `20` | Per-session realized loss limit in USDC. When breached, the session is terminated and all open orders are cancelled. | `50` |
| `heartbeat_interval_seconds` | `POLYMARKET_HEARTBEAT_INTERVAL_SECONDS` | `int` | `5` | Seconds between heartbeat pings written to the database and logs. Used for liveness monitoring. | `10` |
| `cancel_all_on_error` | `POLYMARKET_CANCEL_ALL_ON_ERROR` | `bool` | `true` | When `true`, an unhandled exception in any concurrent task triggers a cancel-all-orders call before exit. Recommended to leave enabled. | `true` |
| `snapshot_interval_seconds` | `POLYMARKET_SNAPSHOT_INTERVAL_SECONDS` | `int` | `5` | Seconds between orderbook snapshot recordings written to `pm.snapshots`. | `10` |
| `gamma_api_url` | `POLYMARKET_GAMMA_API_URL` | `str` | `https://gamma-api.polymarket.com` | Base URL for the Gamma REST API (market metadata and resolution). | — |
| `clob_api_url` | `POLYMARKET_CLOB_API_URL` | `str` | `https://clob.polymarket.com` | Base URL for the CLOB REST API (order placement, cancellation, book queries). | — |
| `data_api_url` | `POLYMARKET_DATA_API_URL` | `str` | `https://data-api.polymarket.com` | Base URL for the Data API (historical fills, market stats). | — |
| `clob_ws_url` | `POLYMARKET_CLOB_WS_URL` | `str` | `wss://ws-subscriptions-clob.polymarket.com/ws/` | WebSocket URL for real-time CLOB order book and fill updates. | — |
| `binance_api_url` | `POLYMARKET_BINANCE_API_URL` | `str` | `https://api.binance.com` | Base URL for the Binance REST API used to fetch the BTC/USDT reference price for regime detection. | — |
| `binance_stale_seconds` | `POLYMARKET_BINANCE_STALE_SECONDS` | `int` | `30` | Maximum age in seconds of a cached Binance price before it is considered stale. A stale price causes quoting to pause. | `60` |

---

## Notes

- Fields marked **required** have no default and must be set; the service will refuse to start without them.
- `private_key` is stored as a Pydantic `SecretStr` and is never included in logs, tracebacks, or serialized config dumps.
- All `Decimal` fields accept standard decimal string notation in environment variables (e.g. `"0.025"`, `"100"`).
- API endpoint defaults point to Polymarket's production environment. Do not change them unless you are testing against a staging environment.
