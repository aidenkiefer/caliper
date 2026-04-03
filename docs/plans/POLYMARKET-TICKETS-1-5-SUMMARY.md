# Polymarket BTC Trading — Tickets 1-5 Implementation Summary

**Date:** 2026-03-25

## Overview

Tickets 1-5 build the foundation of `services/polymarket/`, a self-contained market-making service for Polymarket binary BTC hourly resolution markets. The service does not extend the equity Strategy ABC or OMS; it runs its own concurrent quoting loop with EIP-712 order signing, post-only enforcement, and per-session safety controls. Data is persisted to TimescaleDB under the `pm.*` schema.

---

## Ticket 1 — Service Scaffolding [COMPLETE]

**Ticket ID:** 10-01

**What was built:**
- `services/polymarket/__init__.py` — package marker with service description
- `services/polymarket/pyproject.toml` — Poetry config with all required dependencies (`pydantic`, `pydantic-settings`, `py-clob-client`, `web3`, `eth-account`, `httpx`, `websockets`, `asyncpg`, `sqlalchemy`, `pytest`, `pytest-asyncio`)
- `services/polymarket/config.py` — `PolymarketConfig(BaseSettings)` with wallet, window, quoting, safety, recording, database, and API URL fields; `POLYMARKET_` env prefix
- `services/polymarket/constants.py` — API base URLs, fee regime parameters (pre/post Mar 30 2026), CTF contract address placeholders, timing constants, and token/outcome identifiers
- `services/polymarket/schemas.py` — internal Pydantic models: `MarketInfo`, `OrderbookState`, `QuoteDecision`
- `services/polymarket/adapters/__init__.py` — adapter sub-package placeholder
- `services/polymarket/README.md` — one-paragraph service description with links to spec and tickets

**Key design decisions:**
- Used Pydantic v2 `model_config` dict instead of inner `class Config` to align with the rest of the codebase's Pydantic v2 usage.
- Fee regime constants use `Decimal` for precision consistency with all price/size values elsewhere in the service.
- CTF contract addresses are left as zero-address placeholders with a comment pointing to the official docs; real values will be injected in a later ticket once confirmed on Polygon mainnet.

---

## Ticket 2 — Gamma API Client [COMPLETE]

**Ticket ID:** 10-02

**What was built:**
- `services/polymarket/adapters/gamma_client.py` — `GammaClient` async HTTP client for the Polymarket Gamma REST API
- `tests/unit/polymarket/__init__.py` — test sub-package marker
- `tests/unit/polymarket/test_gamma_client.py` — 9 unit tests covering all required scenarios

**Key design decisions:**
- Dependency-injected `httpx.AsyncClient` makes the client fully testable without real network I/O; when no client is supplied the `GammaClient` creates and owns one (closed by `GammaClient.close()` / async context manager).
- Retry logic is table-driven (`_RETRY_DELAYS = [1, 2, 4]`) and applies to all 5xx responses and 429s; non-retryable 4xx errors raise immediately to avoid unnecessary waits.
- `asyncio.sleep` is used for back-off delays, allowing tests to patch it and run instantly.
- Multiple markets matching the same window are resolved by choosing the maximum `volume`, satisfying the "highest volume wins" requirement without additional API calls.
- Custom exception hierarchy (`PolymarketError` → `APIError` → `RateLimitError`; `MarketNotFoundError`; `MarketClosedError`) is defined in the same module to keep the adapter self-contained.
- `MarketInfo` is constructed from the raw Gamma dict with safe fallbacks for missing `endDate` (defaults to `startDate + 1 hour`) and missing token IDs.

---

## Ticket 3 — CLOB API Client [COMPLETE]

**Ticket ID:** 10-03

**What was built:**
- `services/polymarket/adapters/clob_client.py` — `CLOBClient` async HTTP + WebSocket client for the Polymarket CLOB API
- `tests/unit/polymarket/test_clob_client.py` — 18 unit tests covering all required scenarios

**Key design decisions:**
- EIP-712 signing is implemented directly with `eth_account.messages.encode_typed_data` and `Account.sign_message` — no py-clob-client SDK dependency. This keeps the signing path explicit and fully testable.
- Retry logic for 425 (engine restart) and 429 (rate limit) shares the same `_request_with_retry` path with table-driven delays `[1, 2, 4]`; 4 total attempts (initial + 3 retries). `asyncio.sleep` is used for back-off so tests can patch it for instant execution.
- The `httpx_client` dependency is injected, making all REST tests fully mock-based without real network I/O.
- BUY vs SELL amount encoding: BUY orders have `makerAmount` = USDC (6-decimal scaled), `takerAmount` = shares (18-decimal scaled); SELL is the reverse — this matches the Polymarket CLOB semantics.
- WebSocket reconnect uses exponential back-off (delay doubles after each disconnect, capped at 30 s) with up to 3 retries; `_parse_ws_message` is a module-level helper for isolated testability.
- Custom exception hierarchy: `CLOBError` → `CLOBEngineError` (425), `RateLimitError` (429), `OrderRejectedError`, `HeartbeatError`.

---

## Ticket 4 — Binance API Client [COMPLETE]

**Ticket ID:** 10-04

**What was built:**
- `services/polymarket/adapters/binance_client.py` — `BinanceClient` async HTTP client for the Binance REST klines endpoint
- `tests/unit/polymarket/test_binance_client.py` — 12 unit tests covering all required scenarios

**Key design decisions:**
- Same dependency-injected `httpx.AsyncClient` pattern as `GammaClient` and `CLOBClient` — when no client is provided the `BinanceClient` creates and owns one (closed via `close()` / async context manager).
- Retry logic is identical to the other adapters: `_RETRY_DELAYS = [1, 2, 4]`, retries on 429 and 5xx, `asyncio.sleep` for back-off (patchable in tests). Non-retryable 4xx errors raise `BinanceAPIError` immediately.
- `get_1h_candle` queries with `startTime={ms}` and `endTime={ms + 3_600_000 - 1}` so the window is exactly one hour, avoiding overlap with the next candle's open.
- `get_current_price` polls `GET /api/v3/klines?interval=1m&limit=1` and returns the `close` price as `Decimal`; callers drive the 5-second polling cadence externally (as per the V1 spec).
- `get_1h_candles_range` passes `limit=1000` (Binance max per request) for efficient range queries.
- All price/volume fields are parsed as `Decimal(str(...))` to prevent float imprecision.
- Module-level `_parse_candle` and `_to_ms` helpers are kept separate from the class body for isolated testability.
- Custom exception hierarchy: `BinanceError` → `BinanceAPIError` → `RateLimitError`; `CandleNotAvailableError` inherits from `BinanceError` directly (not from `BinanceAPIError`) since it signals a data-availability condition rather than an HTTP error.

---

## Ticket 5 — Wallet Management [COMPLETE]

**Ticket ID:** 10-05

**What was built:**
- `services/polymarket/wallet.py` — `WalletManager` class with all required methods
- `tests/unit/polymarket/test_wallet.py` — 11 unit tests covering all required scenarios
- `services/polymarket/constants.py` — added `POLYGON_RPC_URL = "https://polygon-rpc.com"`

**Key design decisions:**
- Dependency-injected `web3_provider` parameter makes `WalletManager` fully testable without real RPC calls; when omitted, connects to `POLYGON_RPC_URL` via `Web3.HTTPProvider`.
- Private key is stored as `_private_key` and only used in `__init__` (for `Account.from_key` validation) and at signing/transaction-signing time; it is never logged.
- EIP-712 signing constants (`_ORDER_EIP712_TYPES`, `_DOMAIN`) are duplicated from `clob_client.py` rather than cross-imported, keeping V1 modules isolated as per the spec.
- `split_usdc` and `merge_tokens` both use `partition=[1, 2]` (NO=index 0, YES=index 1) and `parentCollectionId=bytes32(0)`, matching the CTF contract semantics.
- `redeem_tokens` tries `indexSets=[2]` (YES) first, then falls back to `[1]` (NO), catching any exception on each attempt. Re-raises the last error if both fail.
- Web3.py contract calls are synchronous (V1 known limitation); they will block the event loop. Documented in the module docstring.
- Placeholder contract address check mirrors the `CLOBClient` pattern: a `UserWarning` is issued at construction time if either `CTF_CONTRACT_ADDRESS` or `USDC_CONTRACT_ADDRESS` is the zero address.
- Minimal ABIs: only `balanceOf` (ERC-20), `balanceOf` (ERC-1155), and `splitPosition`/`mergePositions`/`redeemPositions` (CTF) are included.

---

## Tickets 6-10

### Ticket 6 — Database Schema Migration [COMPLETE]

**Ticket ID:** 10-06

**What was built:**
- `services/data/alembic/versions/002_create_polymarket_schema.py` — Alembic migration that creates the `pm` schema and all 8 tables

**Tables created:**
- `pm.sessions` — regular table; one row per market-making session; includes CHECK constraints for `outcome`, `volatility_regime`, `spread_regime`, `volume_regime`, `btc_trend_regime`, and `status`
- `pm.orders` — regular table; one row per placed order; FK to `pm.sessions`; CHECK constraints for `side` and `status`
- `pm.fills` — regular table; one row per fill event; FK to `pm.sessions` and `pm.orders`; CHECK constraint for `side`; partial index on `adverse_selection_flag`
- `pm.orderbook_snapshots` — **TimescaleDB hypertable** on `timestamp` (1-hour chunks); composite PK `(snapshot_id, timestamp)`; FK to `pm.sessions`
- `pm.binance_candles` — **TimescaleDB hypertable** on `open_time` (1-day chunks); composite PK `(candle_id, open_time)`
- `pm.pnl_snapshots` — **TimescaleDB hypertable** on `timestamp` (1-hour chunks); composite PK `(snapshot_id, timestamp)`; FK to `pm.sessions`
- `pm.market_metadata` — regular table; one row per discovered market; PK on `condition_id`
- `pm.toxic_flow_by_minute` — regular table; composite PK `(session_id, minute_offset)`; CHECK constraint `minute_offset >= 0 AND minute_offset < 60`; FK to `pm.sessions`

**Key design decisions:**
- All indexes from the spec are created via `op.execute()` raw SQL to support partial index expressions (e.g., `WHERE status IN (...)`, `WHERE adverse_selection_flag = TRUE`) which Alembic's `op.create_index()` cannot express natively.
- Hypertable creation uses `op.execute("SELECT create_hypertable(...)")` following the same pattern as `001_initial_schema.py`.
- `down_revision = '001_initial'` chains this migration after the initial schema.
- `downgrade()` drops the entire `pm` schema with `CASCADE`, which cleanly removes all tables, indexes, constraints, and sequences in a single statement.

---

### Ticket 7 — Fee Model [COMPLETE]

**Ticket ID:** 10-07

**What was built:**
- `services/polymarket/fee_model.py` — `FeeModel` class with `compute_fee`, `compute_rebate`, and `compute_net_pnl` methods
- `tests/unit/polymarket/test_fee_model.py` — 17 unit tests covering both fee regimes, edge cases, and all public methods

**Fee regimes implemented:**
- Pre-March 30, 2026: flat 2% taker fee (`price × size × 0.02`); maker fee = 0; rebate = 0
- Post-March 30, 2026 (on or after `FEE_REGIME_CHANGE_DATE`): curved taker fee `price × size × 0.02 × (1 - 2|price - 0.5|)`; maker fee = 0; maker rebate `price × size × 0.01 × (1 - 2|price - 0.5|)`

**Key design decisions:**
- `as_of_date` is dependency-injected (defaults to `date.today()`) so tests can exercise both regimes without patching.
- `_fee_curve_factor(price)` is a `@staticmethod` that clamps the result to `[0, 1]`, preventing negative fees for out-of-range prices.
- All arithmetic uses `Decimal` throughout; no float arithmetic.
- `MAKER_REBATE_FRACTION` from constants is documented but not used in the per-fill formula — V1 uses the simplified rebate formula rather than pool mechanics, as specified.
- Makers never pay fees in either regime; `is_maker=True` short-circuits to `Decimal("0")` before any regime check.
- `fees_enabled=False` short-circuits before regime or role checks, returning `Decimal("0")`.

---

### Ticket 8 — Market Discovery [COMPLETE]

**Ticket ID:** 10-08

**What was built:**
- `services/polymarket/market_discovery.py` — `MarketDiscovery` class with `discover_target_market` and `cache_market_metadata` methods, plus the module-level `_local_hour_to_utc` helper
- `tests/unit/polymarket/test_market_discovery.py` — 6 unit tests covering all required scenarios

**Key design decisions:**
- `_local_hour_to_utc` uses `zoneinfo.ZoneInfo` to construct a timezone-aware `datetime` in the target local timezone, then calls `.astimezone(timezone.utc)` to obtain the DST-correct UTC hour. No manual offset arithmetic is needed.
- `MarketDiscovery.__init__` accepts an optional `gamma_client` parameter (dependency injection) so tests can supply a mock without patching module-level imports.
- `discover_target_market` defaults `target_date` to today UTC (`datetime.now(tz=timezone.utc).date()`), making the default behaviour deterministic with respect to UTC rather than the server's local clock.
- When `db_conn=None` is passed, the DB write is skipped entirely. This allows dry-run and test usage without a real database connection.
- `cache_market_metadata` uses asyncpg's positional `$N` parameter style with `INSERT … ON CONFLICT (condition_id) DO UPDATE`, so re-discovery of the same market is an idempotent upsert that refreshes `total_volume` and `discovered_at` without duplicating rows.
- `MarketNotFoundError` from `GammaClient` propagates unchanged — `MarketDiscovery` does not catch it, keeping error handling at the call site.

---

### Ticket 9 — Data Feed [COMPLETE]

**Ticket ID:** 10-09

**What was built:**
- `services/polymarket/data_feed.py` — `DataFeed` class aggregating Polymarket CLOB WebSocket and Binance price polling into a unified real-time state
- `tests/unit/polymarket/test_data_feed.py` — 12 unit tests covering all required scenarios

**Key components:**
- `DataFeedState` — internal dataclass holding all mutable state: bids/asks lists, derived metrics, Binance price, timestamps, and reward eligibility flags
- `DataFeed.start(token_id)` — creates two concurrent asyncio tasks: one for WebSocket subscription, one for Binance polling
- `DataFeed.stop()` — cancels all tasks and waits for them to complete
- `DataFeed.get_current_state()` — returns an `OrderbookState` snapshot (from `schemas.py`); raises `StaleDataError` if Binance price is older than `config.binance_stale_seconds`
- `DataFeed._on_book_update(book_data)` — dispatches on `event_type`/`type`: `book` (full snapshot), `price_change` (delta), `last_trade_price`, `tick_size_change`
- `DataFeed._poll_binance()` — polls `BinanceClient.get_current_price("BTCUSDT")` every `BINANCE_POLL_INTERVAL_SECONDS` (5 s); errors are logged and the loop continues
- `_compute_book_metrics(bids, asks)` — module-level helper computing best_bid/ask, midpoint, spread, 1%-depth, imbalance, top-3 depth, and order counts
- `_apply_price_change(existing, delta, descending)` — applies a delta to an existing level list (add, update, remove size-0 entries)
- `StaleDataError` — raised by `get_current_state()` when Binance data is stale
- Thread safety: all state mutations hold `asyncio.Lock`; `get_current_state()` reads state directly (safe under asyncio's single-threaded event loop)

**Key design decisions:**
- `DataFeedState` is a private internal dataclass; `get_current_state()` converts it to `OrderbookState` from `schemas.py`. `schemas.py` is not modified.
- `OrderbookState` does not carry Binance price or extended fields (the existing schema is used as-is); the quoting engine reads `DataFeedState` fields directly if needed, or the schema can be extended in a later ticket.
- Queue position estimates (`our_bid_queue_ahead_size`, `our_ask_queue_ahead_size`) default to the full size at best bid/ask — a conservative assumption that all existing liquidity is ahead of our orders.
- Reward eligibility is computed using `config.quote_spread` and `config.quote_size` as proxies when `MarketInfo.rewards_max_spread` / `rewards_min_size` are not available at DataFeed construction time.
- `_poll_binance()` breaks out of its sleep via `asyncio.CancelledError` on task cancellation, ensuring a prompt and clean shutdown.
- Binance staleness check is only triggered when `binance_last_updated is not None`; a feed that has never polled Binance does not raise `StaleDataError` (e.g., during cold start).

---

### Ticket 10 — Quoting Engine [COMPLETE]

**Ticket ID:** 10-10

**What was built:**
- `services/polymarket/quoting_engine.py` — `QuotingEngine` class with `compute_quotes` method and module-level `round_to_tick` helper
- `tests/unit/polymarket/test_quoting_engine.py` — 18 unit tests covering all required scenarios

**V1 quoting formula implemented:**
- `spread_offset = config.quote_spread / 2`
- `bid_price = round_to_tick(midpoint - spread_offset, tick_size)`
- `ask_price = round_to_tick(midpoint + spread_offset, tick_size)`
- `bid_size = ask_size = config.quote_size`

**Quoting suppression gates (in priority order):**
1. `midpoint is None` → both sides suppressed, reason="no midpoint"
2. `spread > 0.10` → both sides suppressed, reason="wide spread"
3. `inventory_yes >= config.inventory_cap` → bid suppressed, reason="inventory cap reached"
4. `inventory_yes <= 0` → ask suppressed, reason="no YES inventory for asks"

**Key design decisions:**
- `QuotingEngine.compute_quotes` accepts any object with `midpoint` and `spread` attributes, so it works with both `DataFeedState` (production) and simple mock/dataclass objects (tests) without importing `DataFeedState` directly.
- `round_to_tick` uses `ROUND_HALF_UP` and is exposed as a module-level function for independent testability.
- When both inventory gates fire simultaneously (e.g. inventory=0 and inventory_cap=0), the bid-cap reason takes priority in the `reason` field; both sides are correctly suppressed.
- `spread=None` with a valid midpoint does not trigger the wide-spread gate — the check is `spread is not None and spread > MAX_QUOTED_SPREAD`.
- Suppressed sides have `price=None` and `size=Decimal("0")`, satisfying the `QuoteDecision` model validator constraint.

---

## Tickets 11-15

### Ticket 11 — Executor [COMPLETE]

**Ticket ID:** 10-11

**What was built:**
- `services/polymarket/executor.py` — `Executor` class bridging the quoting engine and the Polymarket CLOB API
- `tests/unit/polymarket/test_executor.py` — 18 unit tests covering all required scenarios

**Methods implemented:**
- `place_quotes(quote, token_id, quote_version) -> Tuple[Optional[str], Optional[str]]` — cancels existing tracked orders for the token, places bid and/or ask with `post_only=True` always enforced, tracks metadata per order (`placed_at`, `quote_version`, `side`, `price`, `size`, `token_id`)
- `cancel_all_orders() -> int` — delegates to `CLOBClient.cancel_all()`, clears `_live_orders`, returns CLOB-reported count
- `start_heartbeat() -> None` — creates a background `asyncio.Task` running `_heartbeat_loop()`; idempotent if already running
- `stop_heartbeat() -> None` — cancels the task, awaits it, sets `_heartbeat_task = None`
- `handle_fill(fill_data: dict) -> None` — computes `time_on_book_seconds`, updates `_inventory_delta` (BUY → +size, SELL → −size), calls `on_fill_callback` (sync or async), removes order from `_live_orders`
- `inventory_delta` property — read-only net YES token inventory change from fills in this session

**Key design decisions:**
- `post_only=True` is hardcoded in both `place_order` calls inside `place_quotes`; the parameter is never forwarded from the caller, making the post-only constraint impossible to bypass.
- Per-token cancellation: `place_quotes` only cancels orders whose `token_id` matches the requested token, leaving orders on other tokens untouched.
- Cancellation failures on old orders are caught and logged; the old order is removed from tracking regardless, preventing stale references from blocking the next quote cycle.
- `_heartbeat_loop` catches all exceptions from `send_heartbeat` and logs them without re-raising, so a transient heartbeat failure never crashes the main session.
- Fill callback supports both sync and async callables: a coroutine return value is detected with `asyncio.iscoroutine()` and awaited.
- V1 treats every fill notification as a full fill (order removed from `_live_orders`). Partial-fill tracking is deferred to a future enhancement.
- Fills for untracked orders (e.g., placed in a prior session) still update `_inventory_delta` and invoke the callback; only the `time_on_book_seconds` computation is skipped (logged as a warning).

---

### Ticket 12 — Safety Layer [COMPLETE]

**Ticket ID:** 10-12

**What was built:**
- `services/polymarket/safety.py` — `SafetyLayer` class consolidating all pre-trade safety checks for the session orchestrator
- `tests/unit/polymarket/test_safety.py` — 16 unit tests covering all required scenarios

**Methods implemented:**
- `check_inventory_cap(inventory, config=None) -> bool` — returns `False` when `inventory >= config.inventory_cap`; used by the quoting engine for side-specific suppression
- `check_session_loss_limit(session_pnl, config=None) -> bool` — returns `False` when `session_pnl < -config.max_session_loss_usdc`
- `check_binance_staleness(last_update: Optional[datetime]) -> bool` — returns `True` when the feed is older than `config.binance_stale_seconds`; `None` returns `False` (cold-start grace)
- `should_wind_down(time_to_close_minutes, config=None) -> bool` — returns `True` when `time_to_close_minutes <= config.wind_down_minutes`
- `check_quote_safety(quote, session_state) -> Tuple[bool, str]` — runs session-level checks in order (loss limit → Binance staleness → wind-down); returns `(False, reason)` at first failure or `(True, "")` if all pass
- `emergency_shutdown(executor, reason) -> None` — sets `_killed = True`, logs at CRITICAL, calls `executor.cancel_all_orders()`; errors from cancel are caught and logged rather than re-raised; idempotent
- `is_killed` property — read-only flag indicating shutdown has occurred

**Key design decisions:**
- `check_inventory_cap` is intentionally excluded from `check_quote_safety`; inventory limits are side-specific and are already handled inside `QuotingEngine.compute_quotes`.
- All check methods accept an optional `config` parameter for override in tests, defaulting to `self._config`. This avoids patching and keeps tests free of environment-variable requirements.
- `check_binance_staleness` treats a `None` timestamp as not-stale (cold-start grace period), matching the `DataFeed` staleness policy established in Ticket 9.
- `emergency_shutdown` swallows cancellation errors intentionally — the orchestrator's teardown must not be blocked by a CLOB outage during shutdown.
- Timezone awareness: `check_binance_staleness` adds UTC tzinfo to a naive `last_binance_update` datetime before comparison to avoid `TypeError` on subtraction.
- `QuoteSafetyResult` TypedDict added for the `check_quote_safety` return type, providing static type safety on `safe`, `reason`, and `wind_down` keys.
- `asyncio.get_running_loop().create_task()` used in `emergency_shutdown` for fire-and-forget async cancel; gracefully degrades if no event loop is running.

---

### Ticket 13 — Recorder [COMPLETE]

**Ticket ID:** 10-13

**What was built:**
- `services/polymarket/recorder.py` — `Recorder` class for writing all session data to TimescaleDB via asyncpg
- `tests/unit/polymarket/test_recorder.py` — 11 unit tests covering session creation, order/fill recording, snapshot batching, candle recording, regime computation, and lifecycle

**Methods implemented:**
- `create_session(market, config) -> UUID` — inserts into `pm.sessions`, returns generated `session_id`
- `record_order(order_data, session_id)` / `record_fill(fill_data, session_id)` — immediate inserts
- `record_snapshot(snapshot, session_id)` / `record_pnl_snapshot(pnl_data, session_id)` — buffered with `asyncio.Lock`; auto-flushes at 10 rows
- `record_binance_candle(candle, session_id)` — immediate insert with `ON CONFLICT (source, open_time) DO NOTHING`
- `finalize_session(session_id, final_state)` — queries DB stats, computes 4 regime tags (`volatility_regime`, `spread_regime`, `volume_regime`, `btc_trend_regime`), updates session record
- `compute_toxic_flow_by_minute(session_id)` — aggregates fills by minute into `pm.toxic_flow_by_minute`
- `update_adverse_selection_async(fill_id, midpoint_5s, midpoint_10s)` — updates `pm.fills` with post-fill adverse selection metrics
- `start()` / `stop()` — manage background periodic flush task (30s interval)

**Key design decisions:**
- Buffer-before-flush with `asyncio.Lock` in both `record_snapshot` and `record_pnl_snapshot` prevents race conditions between periodic flush and buffer-full flush paths.
- Buffer is cleared AFTER successful DB write to prevent silent data loss on `executemany` failure.
- Regime data lives as columns on `pm.sessions`; `spread_regime` uses two-value enum ('TIGHT'/'WIDE') matching DB CHECK constraint.

---

### Ticket 14 — Session Orchestrator [COMPLETE]

**Ticket ID:** 10-14

**What was built:**
- `services/polymarket/session.py` — `SessionOrchestrator` class coordinating all components for a single trading session
- `tests/integration/polymarket/test_session.py` — 5 integration tests with mocked dependencies
- `tests/integration/polymarket/__init__.py` — package marker

**Execution flow in `run_session(config)`:**
1. Market discovery via `MarketDiscovery.discover_target_market`
2. Wallet balance check — raises `ValueError` if `usdc_balance < quote_size * 2`
3. Session creation via `Recorder.create_session` → `session_id`
4. Data feed start + recorder start; fill callback wired to `executor._on_fill`
5. Heartbeat start
6. Main loop every `requote_interval_seconds`: snapshot (tracked task), safety check, wind-down/end break, quote computation, quote placement
7. `finally` block: drain pending snapshot tasks, cancel all orders, stop heartbeat, stop data feed and recorder, compute toxic flow, finalize session
8. `except ValueError`: re-raise without emergency shutdown (pre-flight guard)
9. `except Exception`: call `safety_layer.emergency_shutdown(executor)` then re-raise

**Key design decisions:**
- `_pending_tasks` list tracks all snapshot `asyncio.create_task` calls; gathered with `return_exceptions=True` in `finally` to prevent orphaned tasks.
- `_on_fill` callback tracks `_realized_pnl` from fills and is registered on the executor before the main loop starts.
- `except ValueError` is caught before `except Exception` to exclude pre-flight failures from triggering emergency shutdown.

---

### Ticket 15 — CLI Entrypoint [COMPLETE]

**Ticket ID:** 10-15

**What was built:**
- `services/polymarket/cli.py` — typer CLI with `main()` function
- `services/polymarket/__main__.py` — enables `python -m polymarket` invocation
- `services/polymarket/pyproject.toml` updated — added `typer` dependency and `polymarket-session` script entry

**CLI interface:**
- `--dry-run` (bool, default False) — monkeypatches `executor.place_quotes` to log intent and return `{}` without placing real orders
- `--target-hour` (optional int) — overrides `config.target_hour_local` via `model_copy(update=...)`
- Logging: stdout + `logs/polymarket_<uuid>.log` via `setup_logging()`
- Exit code 1 on any unhandled exception

**Dependency wiring:**
- All components (GammaClient, CLOBClient, BinanceClient, WalletManager, MarketDiscovery, DataFeed, QuotingEngine, Executor, SafetyLayer, Recorder, SessionOrchestrator) wired inside an `httpx.AsyncClient` context and `asyncpg` pool lifecycle
- `asyncio.run(_run(...))` drives the session

---

## Tickets 16-20

### Ticket 16 — Shared Schemas [COMPLETE]

**Ticket ID:** 10-16

**What was built:**
- `packages/common/polymarket_schemas.py` — 7 Pydantic v2 response models for the Polymarket API
- `packages/common/__init__.py` updated — exports all new models

**Models defined:**
- `PolymarketSessionResponse` — session summary with regime tags and PnL
- `PolymarketOrderResponse` — order details (price, size, status, timestamps)
- `PolymarketFillResponse` — fill details with adverse selection fields
- `PolymarketSnapshotResponse` — orderbook snapshot (bid/ask/midpoint/spread)
- `PolymarketPnLResponse` — PnL breakdown (realized, unrealized, fees)
- `PolymarketToxicFlowResponse` — per-minute toxic flow metrics
- `PolymarketSessionListResponse` — paginated session list wrapper
- `PolymarketSnapshotListResponse` — paginated snapshot list wrapper (added during API router integration)

All models use `model_config = ConfigDict(from_attributes=True)` for ORM compatibility.

---

### Ticket 17 — API Router [COMPLETE]

**Ticket ID:** 10-17

**What was built:**
- `services/api/routers/polymarket.py` — FastAPI router with 7 Polymarket endpoints
- `services/api/main.py` updated — router registered at `/v1` with `tags=["polymarket"]`
- `services/api/routers/__init__.py` updated — exports `polymarket` module

**Endpoints:**
- `GET /polymarket/sessions` — paginated list with status, regime, date filters
- `GET /polymarket/sessions/{session_id}` — session detail (404 if not found)
- `GET /polymarket/sessions/{session_id}/orders` — orders with status filter
- `GET /polymarket/sessions/{session_id}/fills` — fills with `adverse_only` filter
- `GET /polymarket/sessions/{session_id}/snapshots` — paginated snapshots with `PolymarketSnapshotListResponse` envelope
- `GET /polymarket/sessions/{session_id}/pnl` — latest PnL snapshot
- `GET /polymarket/sessions/{session_id}/toxic-flow` — per-minute toxic flow metrics

All endpoints are stubbed (return empty/mock data) following the existing API pattern; real asyncpg queries are documented in comments.

---

### Ticket 18 — Data API Client [COMPLETE]

**Ticket ID:** 10-18

**What was built:**
- `services/polymarket/adapters/data_api_client.py` — `DataAPIClient` class for the Polymarket Data API
- `tests/unit/polymarket/test_data_api_client.py` — 11 unit tests

**Methods implemented:**
- `get_trades(token_id, start_time, end_time)` — paginated via `next_cursor` cursor; returns dicts with `timestamp`, `price`, `size`, `side`, `maker_address`, `taker_address`
- `get_activity(wallet_address, start_time, end_time)` — wallet activity with date range
- `get_rebates(wallet_address, date)` — daily rebate data

**Key design decisions:**
- `_require_aware` validates timezone-aware datetimes; raises `ValueError` on naive input
- `_RETRY_DELAYS = [1, 2, 4]` with `asyncio.sleep` backoff (patchable in tests)
- Pagination sentinel: `"LTE="` cursor signals end of results
- Imports `RateLimitError`, `APIError` from `gamma_client` for consistent error handling

---

### Ticket 19 — Integration Test [COMPLETE]

**Ticket ID:** 10-19

**What was built:**
- `tests/integration/polymarket/test_full_session.py` — 3 end-to-end integration tests
- `tests/integration/polymarket/fixtures.py` — reusable test factory functions

**Tests:**
- `test_full_session_flow` — happy path: session created, quotes placed, wind-down triggered, session finalized
- `test_wind_down_immediate` — safety returns `wind_down=True` immediately; no quotes placed, snapshots still recorded
- `test_emergency_shutdown_scenario` — `data_feed.get_current_state` raises; `emergency_shutdown` called, `finalize_session` still called in `finally`

**Fixtures (`fixtures.py`):**
- `make_market_info(window_start, window_end)` — `MarketInfo` with short 2-minute default window
- `make_data_feed_state(midpoint)` — `DataFeedState` with symmetric bid/ask
- `make_quote_decision()` — `QuoteDecision` with both sides active
- `make_config(**overrides)` — `PolymarketConfig` with dummy credentials and fast `requote_interval_seconds=1`

All tests patch `asyncio.sleep` to run without real delays.

---

### Ticket 20 — Documentation [COMPLETE]

**Ticket ID:** 10-20

**What was built:**
- `services/polymarket/docs/SETUP.md` — prerequisites, `.env.polymarket` template, migration, install, dry-run
- `services/polymarket/docs/CONFIG.md` — full table of all `PolymarketConfig` fields with env vars, types, defaults, descriptions, examples
- `services/polymarket/docs/RUNBOOK.md` — starting sessions, monitoring SQL queries, emergency shutdown procedures, post-session analysis queries, 11-row troubleshooting table
- `services/polymarket/README.md` updated — links to all three new docs

---

## Sprint 10 Complete

All 20 tickets for the Polymarket BTC hourly market-making feature are complete as of 2026-03-25.

**Files created across all 20 tickets:**
- `services/polymarket/` — 15 Python source files (config, constants, schemas, adapters ×4, wallet, market_discovery, data_feed, quoting_engine, executor, safety, recorder, session, cli, __main__)
- `services/polymarket/docs/` — 3 documentation files (SETUP.md, CONFIG.md, RUNBOOK.md)
- `services/data/alembic/versions/002_create_polymarket_schema.py` — DB migration (pm.* schema, 8 tables, 3 hypertables)
- `packages/common/polymarket_schemas.py` — 8 API response schemas
- `services/api/routers/polymarket.py` — 7 REST endpoints
- `tests/unit/polymarket/` — 10 test files, 130+ unit tests
- `tests/integration/polymarket/` — 2 test files, 5 integration tests

