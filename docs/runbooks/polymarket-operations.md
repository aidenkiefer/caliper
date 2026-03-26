# Polymarket Trading Operations Runbook

**Service:** `services/polymarket/`  
**Spec:** `docs/plans/specs/polymarket-btc-trading-spec.md`  
**Summary:** `docs/plans/summaries/SPRINT-10-POLYMARKET-COMPLETE.md`

---

## Table of Contents

1. [Prerequisites & Setup](#prerequisites--setup)
2. [Environment Configuration](#environment-configuration)
3. [Database Setup](#database-setup)
4. [Running Your First Session](#running-your-first-session)
5. [Monitoring & Observability](#monitoring--observability)
6. [Post-Session Analysis](#post-session-analysis)
7. [Troubleshooting](#troubleshooting)
8. [Emergency Procedures](#emergency-procedures)
9. [Parameter Tuning](#parameter-tuning)
10. [Phase 2 Preparation](#phase-2-preparation)

---

## Prerequisites & Setup

### 1. Polymarket Account Setup

**Step 1: Create Polymarket account**
1. Visit https://polymarket.com
2. Click "Sign Up" or "Connect Wallet"
3. You'll need a Web3 wallet (MetaMask, WalletConnect, etc.)
4. No KYC required for small amounts (as of Mar 2026)

**Step 2: Verify account access**
1. Log in to Polymarket
2. Navigate to any BTC hourly market (search "BTC" → filter by "Hourly")
3. Verify you can see the orderbook and place test orders (don't execute)

**Step 3: Note your wallet address**
- This is your Polygon wallet address (starts with `0x...`)
- You'll use this for API authentication

---

### 2. Polygon Wallet Setup

**Step 1: Create a dedicated trading wallet**

Using MetaMask or any Ethereum wallet:
1. Create a new account (or use an existing one)
2. Switch network to **Polygon Mainnet**
   - Network Name: Polygon Mainnet
   - RPC URL: `https://polygon-rpc.com`
   - Chain ID: 137
   - Currency Symbol: MATIC
   - Block Explorer: `https://polygonscan.com`

**Step 2: Export private key**

⚠️ **SECURITY WARNING:** Never share your private key. Store it securely.

In MetaMask:
1. Click the three dots next to your account
2. Account Details → Export Private Key
3. Enter your password
4. Copy the private key (starts with `0x...`)
5. Store it in a password manager (NOT in your code or git repo)

**Step 3: Fund wallet with MATIC (for gas)**

You need MATIC to pay for transaction fees on Polygon:
1. Buy MATIC on an exchange (Coinbase, Binance, etc.)
2. Withdraw to your Polygon wallet address
3. **Recommended amount:** 5-10 MATIC (~$5-10 USD)
4. Verify receipt on https://polygonscan.com

**Step 4: Fund wallet with USDC**

You need USDC to trade on Polymarket:
1. Buy USDC on an exchange
2. Withdraw to your Polygon wallet address
   - **IMPORTANT:** Withdraw on Polygon network (NOT Ethereum mainnet)
   - Polygon USDC contract: `0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174`
3. **Recommended amount for Phase 1:** $100-200 USDC
4. Verify receipt on https://polygonscan.com

---

### 3. Polymarket API Access

**Step 1: Understand API authentication**

Polymarket uses EIP-712 signing for order placement:
- No API keys required
- Orders are signed with your wallet private key
- The bot handles signing automatically

**Step 2: Verify API access**

Test that you can reach the APIs:
```bash
# Gamma API (market discovery)
curl https://gamma-api.polymarket.com/markets | jq '.[0]'

# CLOB API (orderbook)
curl https://clob.polymarket.com/markets | jq '.[0]'

# Binance API (price feed)
curl https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1h&limit=1 | jq '.'
```

If any of these fail, check your internet connection and firewall settings.

---

### 4. CTF Contract Addresses

The bot needs to interact with Polymarket's Conditional Token Framework (CTF) contracts.

**Step 1: Get contract addresses**

Visit https://docs.polymarket.com/resources/contract-addresses

As of Mar 2026, the addresses are:
- **CTF Exchange:** `0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E`
- **Collateral Token (USDC):** `0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174`

**Step 2: Update constants.py**

Edit `services/polymarket/constants.py`:
```python
# Replace placeholder addresses with real ones
CTF_CONTRACT_ADDRESS = "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"
USDC_CONTRACT_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
```

---

## Environment Configuration

### 1. Create Environment File

Create `.env.polymarket` in the repo root:

```bash
# Wallet Configuration
POLYMARKET_WALLET_ADDRESS=0xYourWalletAddressHere
POLYMARKET_PRIVATE_KEY=0xYourPrivateKeyHere

# Trading Window Configuration
POLYMARKET_TARGET_HOUR_LOCAL=14        # 2 PM in your local timezone
POLYMARKET_TARGET_TIMEZONE=America/New_York

# Quoting Parameters (V1 defaults)
POLYMARKET_QUOTE_SPREAD=0.02           # 2 cents each side of mid
POLYMARKET_QUOTE_SIZE=50               # 50 shares per side
POLYMARKET_INVENTORY_CAP=200           # Max 200 YES shares held
POLYMARKET_REQUOTE_INTERVAL_SECONDS=10 # Refresh quotes every 10s

# Safety Limits
POLYMARKET_MAX_SESSION_LOSS_USDC=50    # Stop if session loses $50
POLYMARKET_WIND_DOWN_MINUTES=5         # Stop quoting 5 min before close
POLYMARKET_BINANCE_STALE_SECONDS=30    # Pause if Binance price >30s old

# Recording Configuration
POLYMARKET_SNAPSHOT_INTERVAL_SECONDS=5 # Orderbook snapshot every 5s
POLYMARKET_PNL_SNAPSHOT_INTERVAL_SECONDS=30

# Database Configuration
POLYMARKET_DATABASE_URL=postgresql://user:password@localhost:5432/caliper

# API URLs (defaults are fine, only override if needed)
# POLYMARKET_GAMMA_API_URL=https://gamma-api.polymarket.com
# POLYMARKET_CLOB_API_URL=https://clob.polymarket.com
# POLYMARKET_BINANCE_API_URL=https://api.binance.com
```

### 2. Load Environment Variables

The bot automatically loads `.env.polymarket` via `pydantic-settings`.

To verify your config:
```bash
cd services/polymarket
poetry run python -c "from config import PolymarketConfig; c = PolymarketConfig(); print(c.model_dump())"
```

### 3. Security Best Practices

⚠️ **CRITICAL SECURITY RULES:**

1. **Never commit `.env.polymarket` to git**
   - Already in `.gitignore`
   - Double-check: `git status` should not show it

2. **Restrict file permissions**
   ```bash
   chmod 600 .env.polymarket
   ```

3. **Use a dedicated trading wallet**
   - Don't use your main wallet with large holdings
   - Only fund with the amount you're willing to risk

4. **Rotate keys if compromised**
   - If you suspect key exposure, immediately:
     1. Stop all sessions
     2. Withdraw funds to a new wallet
     3. Generate new keys
     4. Update `.env.polymarket`

---

## Database Setup

### 1. Verify TimescaleDB Extension

The bot requires TimescaleDB for time-series data.

```bash
# Connect to your database
psql -U user -d caliper

# Check if TimescaleDB is installed
SELECT * FROM pg_extension WHERE extname = 'timescaledb';

# If not installed, install it:
CREATE EXTENSION IF NOT EXISTS timescaledb;
```

### 2. Run Migration

Apply the Polymarket schema migration:

```bash
cd services/data
poetry run alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Running upgrade 001_initial -> 002_polymarket_schema, Create Polymarket pm schema and tables
```

### 3. Verify Schema

Check that all tables were created:

```sql
-- List all pm.* tables
SELECT tablename FROM pg_tables WHERE schemaname = 'pm';

-- Expected output:
-- sessions
-- orders
-- fills
-- orderbook_snapshots
-- binance_candles
-- pnl_snapshots
-- market_metadata
-- toxic_flow_by_minute
```

### 4. Verify Hypertables

Check that TimescaleDB hypertables were created:

```sql
SELECT hypertable_name FROM timescaledb_information.hypertables WHERE hypertable_schema = 'pm';

-- Expected output:
-- orderbook_snapshots
-- binance_candles
-- pnl_snapshots
```

---

## Running Your First Session

### 1. Dry-Run Test (No Real Orders)

Before trading with real money, test the bot in dry-run mode:

```bash
cd services/polymarket
poetry install  # First time only
poetry run polymarket-session --dry-run
```

**What dry-run does:**
- Discovers the target market
- Checks wallet balance
- Starts data feed (real WebSocket + Binance data)
- Computes quotes
- **Logs what orders WOULD be placed** (doesn't actually place them)
- Records snapshots to database
- Runs until wind-down, then exits

**Expected log output:**
```
2026-03-25 14:00:00 INFO Starting Polymarket session (dry-run mode)
2026-03-25 14:00:01 INFO Market discovered: BTC 14:00-15:00 (condition_id=abc123)
2026-03-25 14:00:02 INFO Wallet balance: 150.00 USDC
2026-03-25 14:00:03 INFO Session created: session_id=...
2026-03-25 14:00:04 INFO Data feed started
2026-03-25 14:00:05 INFO [DRY-RUN] Would place BID at 0.48 for 50 shares
2026-03-25 14:00:05 INFO [DRY-RUN] Would place ASK at 0.52 for 50 shares
...
2026-03-25 14:55:00 INFO Wind-down triggered (5 minutes remaining)
2026-03-25 14:55:01 INFO Session completed: session_id=...
```

**Verify in database:**
```sql
SELECT session_id, status, started_at, completed_at 
FROM pm.sessions 
ORDER BY started_at DESC 
LIMIT 1;

-- Should show one COMPLETED session
```

### 2. Live Session (Real Orders)

⚠️ **WARNING:** This will place real orders with real money.

**Pre-flight checklist:**
- [ ] Wallet funded with USDC ($100-200) and MATIC (5-10)
- [ ] `.env.polymarket` configured and tested
- [ ] Database migration applied
- [ ] Dry-run completed successfully
- [ ] You understand the risks (max loss = `max_session_loss_usdc`)

**Run live session:**
```bash
cd services/polymarket
poetry run polymarket-session
```

**Expected behavior:**
1. Discovers target market (e.g., BTC 14:00-15:00)
2. Checks wallet balance (must have >= `quote_size * 2` USDC)
3. Splits USDC into YES+NO tokens (one-time per market)
4. Places bid and ask quotes every `requote_interval_seconds`
5. Sends heartbeat every 10 seconds
6. Records all data to database
7. Stops quoting `wind_down_minutes` before market close
8. Cancels all orders and exits

**Monitor logs:**
```bash
tail -f logs/polymarket_<session_id>.log
```

### 3. Override Target Hour

To run a session for a different hour than configured:

```bash
poetry run polymarket-session --target-hour 15  # 3 PM local time
```

---

## Monitoring & Observability

### 1. Real-Time Monitoring (During Session)

**Watch logs:**
```bash
tail -f logs/polymarket_<session_id>.log
```

**Key log events to watch for:**
- `INFO Data feed started` — WebSocket connected
- `INFO Heartbeat sent` — Every 10 seconds
- `INFO Quotes placed: bid=X, ask=Y` — Orders placed successfully
- `INFO Fill received: side=BUY, price=X, size=Y` — Order filled
- `WARNING Safety check failed: reason=...` — Safety gate triggered
- `CRITICAL Emergency shutdown: reason=...` — Critical error occurred

**Monitor database (live queries):**

```sql
-- Current session status
SELECT session_id, status, started_at, 
       total_orders_placed, total_fills, total_volume_usdc,
       realized_pnl
FROM pm.sessions 
WHERE status IN ('ACTIVE', 'WIND_DOWN')
ORDER BY started_at DESC;

-- Recent orders
SELECT order_id, side, price, original_size, status, placed_at
FROM pm.orders
WHERE session_id = '<current_session_id>'
ORDER BY placed_at DESC
LIMIT 10;

-- Recent fills
SELECT fill_id, side, price, size, filled_at, 
       midpoint_at_fill, adverse_selection_flag
FROM pm.fills
WHERE session_id = '<current_session_id>'
ORDER BY filled_at DESC
LIMIT 10;

-- Latest orderbook snapshot
SELECT timestamp, best_bid, best_ask, midpoint, spread,
       our_bid_price, our_ask_price,
       our_bid_queue_ahead_size, our_ask_queue_ahead_size
FROM pm.orderbook_snapshots
WHERE session_id = '<current_session_id>'
ORDER BY timestamp DESC
LIMIT 1;
```

### 2. Session Health Checks

**Check heartbeat status:**
```bash
# Should see "Heartbeat sent" every 10 seconds in logs
grep "Heartbeat" logs/polymarket_<session_id>.log | tail -5
```

**Check data feed freshness:**
```sql
-- Latest Binance price update
SELECT timestamp, binance_price
FROM pm.orderbook_snapshots
WHERE session_id = '<current_session_id>'
ORDER BY timestamp DESC
LIMIT 1;

-- Should be within last 30 seconds
```

**Check order placement rate:**
```sql
-- Orders placed per minute
SELECT 
    date_trunc('minute', placed_at) AS minute,
    COUNT(*) AS orders_placed
FROM pm.orders
WHERE session_id = '<current_session_id>'
GROUP BY minute
ORDER BY minute DESC
LIMIT 10;

-- Should be ~6 orders per minute (bid+ask every 10s)
```

### 3. Performance Metrics (Live)

**Current PnL:**
```sql
SELECT 
    realized_pnl,
    spread_capture_pnl,
    inventory_drift_pnl,
    total_volume_usdc,
    total_fills
FROM pm.sessions
WHERE session_id = '<current_session_id>';
```

**Fill rate:**
```sql
SELECT 
    COUNT(*) FILTER (WHERE status = 'MATCHED') AS filled_orders,
    COUNT(*) AS total_orders,
    ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'MATCHED') / COUNT(*), 2) AS fill_rate_pct
FROM pm.orders
WHERE session_id = '<current_session_id>';
```

**Adverse selection rate:**
```sql
SELECT 
    COUNT(*) FILTER (WHERE adverse_selection_flag = TRUE) AS adverse_fills,
    COUNT(*) AS total_fills,
    ROUND(100.0 * COUNT(*) FILTER (WHERE adverse_selection_flag = TRUE) / COUNT(*), 2) AS adverse_pct
FROM pm.fills
WHERE session_id = '<current_session_id>';
```

---

## Post-Session Analysis

### 1. Session Summary

**Get session overview:**
```sql
SELECT 
    session_id,
    window_start,
    window_end,
    outcome,
    realized_pnl,
    total_orders_placed,
    total_fills,
    total_volume_usdc,
    volatility_regime,
    spread_regime,
    volume_regime,
    btc_trend_regime,
    status,
    error_message
FROM pm.sessions
WHERE session_id = '<session_id>';
```

### 2. Queue Position Analysis

**Average queue position:**
```sql
SELECT 
    AVG(our_bid_queue_ahead_size) AS avg_bid_queue_ahead,
    AVG(our_ask_queue_ahead_size) AS avg_ask_queue_ahead,
    AVG(num_orders_at_best_bid) AS avg_competition_bid,
    AVG(num_orders_at_best_ask) AS avg_competition_ask
FROM pm.orderbook_snapshots
WHERE session_id = '<session_id>';
```

**Queue position vs fill rate:**
```sql
WITH order_queue AS (
    SELECT 
        o.order_id,
        o.side,
        o.status,
        o.queue_ahead_at_place,
        o.time_on_book_seconds
    FROM pm.orders o
    WHERE o.session_id = '<session_id>'
)
SELECT 
    side,
    CASE 
        WHEN queue_ahead_at_place < 100 THEN 'Near front'
        WHEN queue_ahead_at_place < 500 THEN 'Middle'
        ELSE 'Back'
    END AS queue_position,
    COUNT(*) FILTER (WHERE status = 'MATCHED') AS filled,
    COUNT(*) AS total,
    ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'MATCHED') / COUNT(*), 2) AS fill_rate_pct,
    AVG(time_on_book_seconds) AS avg_time_on_book
FROM order_queue
GROUP BY side, queue_position
ORDER BY side, queue_position;
```

### 3. Adverse Selection Analysis

**Overall adverse selection rate:**
```sql
SELECT 
    COUNT(*) FILTER (WHERE adverse_selection_flag = TRUE) AS adverse_fills,
    COUNT(*) AS total_fills,
    ROUND(100.0 * COUNT(*) FILTER (WHERE adverse_selection_flag = TRUE) / COUNT(*), 2) AS adverse_pct,
    AVG(edge_at_fill) AS avg_edge_at_fill,
    AVG(edge_5s_after) AS avg_edge_5s_after
FROM pm.fills
WHERE session_id = '<session_id>';
```

**Toxic flow by minute:**
```sql
SELECT 
    minute_offset,
    total_fills,
    adverse_fills,
    adverse_fill_pct,
    avg_edge_realized
FROM pm.toxic_flow_by_minute
WHERE session_id = '<session_id>'
ORDER BY minute_offset;
```

**Visualize toxic flow curve:**
```sql
-- Export to CSV for plotting
COPY (
    SELECT minute_offset, adverse_fill_pct
    FROM pm.toxic_flow_by_minute
    WHERE session_id = '<session_id>'
    ORDER BY minute_offset
) TO '/tmp/toxic_flow.csv' CSV HEADER;
```

### 4. Fill Probability Curve

**Fill rate vs distance from mid:**
```sql
WITH order_distance AS (
    SELECT 
        o.order_id,
        o.side,
        ABS(o.price - o.midpoint_at_place) AS distance_from_mid,
        CASE WHEN o.status = 'MATCHED' THEN 1 ELSE 0 END AS filled
    FROM pm.orders o
    WHERE o.session_id = '<session_id>'
      AND o.midpoint_at_place IS NOT NULL
)
SELECT 
    side,
    ROUND(distance_from_mid, 2) AS distance,
    COUNT(*) AS total_orders,
    SUM(filled) AS filled_orders,
    ROUND(100.0 * SUM(filled) / COUNT(*), 2) AS fill_rate_pct
FROM order_distance
GROUP BY side, ROUND(distance_from_mid, 2)
HAVING COUNT(*) >= 5  -- Only show distances with 5+ samples
ORDER BY side, distance;
```

### 5. Regime Performance

**PnL by regime:**
```sql
SELECT 
    volatility_regime,
    spread_regime,
    volume_regime,
    btc_trend_regime,
    COUNT(*) AS session_count,
    AVG(realized_pnl) AS avg_pnl,
    SUM(realized_pnl) AS total_pnl,
    AVG(total_fills) AS avg_fills,
    AVG(total_volume_usdc) AS avg_volume
FROM pm.sessions
WHERE status = 'COMPLETED'
GROUP BY volatility_regime, spread_regime, volume_regime, btc_trend_regime
ORDER BY avg_pnl DESC;
```

### 6. Quote Stickiness

**Requote frequency:**
```sql
SELECT 
    AVG(time_on_book_seconds) AS avg_time_on_book,
    MIN(time_on_book_seconds) AS min_time_on_book,
    MAX(time_on_book_seconds) AS max_time_on_book,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY time_on_book_seconds) AS median_time_on_book
FROM pm.orders
WHERE session_id = '<session_id>'
  AND time_on_book_seconds IS NOT NULL;
```

**Quote version analysis:**
```sql
SELECT 
    quote_version_id,
    COUNT(*) AS orders_in_version,
    COUNT(*) FILTER (WHERE status = 'MATCHED') AS fills_in_version,
    AVG(time_on_book_seconds) AS avg_time_on_book
FROM pm.orders
WHERE session_id = '<session_id>'
GROUP BY quote_version_id
ORDER BY quote_version_id;
```

---

## Troubleshooting

### Common Issues

| Issue | Symptoms | Diagnosis | Solution |
|-------|----------|-----------|----------|
| **Market not found** | `MarketNotFoundError` in logs | No hourly BTC market for target hour | Check Polymarket website; markets may not be created yet. Try a different hour or wait. |
| **Insufficient balance** | `ValueError: Insufficient USDC balance` | Wallet has < `quote_size * 2` USDC | Fund wallet with more USDC |
| **Heartbeat failure** | `HeartbeatError` in logs, orders cancelled | Network issue or CLOB API down | Check internet connection; restart session |
| **Binance feed stale** | `WARNING Binance feed stale` | Binance API slow or down | Wait for recovery; bot pauses quoting automatically |
| **Order rejected** | `OrderRejectedError` | Price outside tick size, or post-only would match | Check tick size (should be 0.01); widen spread if needed |
| **WebSocket disconnect** | `WARNING WebSocket disconnected` | Network blip or CLOB restart | Bot reconnects automatically (3 retries) |
| **Session loss limit** | `INFO Safety check failed: session loss limit` | Session lost > `max_session_loss_usdc` | Normal safety trigger; session stops quoting |
| **Wind-down early** | Session ends before market close | `wind_down_minutes` too large | Tune parameter (see Parameter Tuning section) |
| **No fills** | Orders placed but never filled | Quotes too far from mid, or bad queue position | Tighten spread; analyze queue position data |
| **High adverse selection** | Many fills with `adverse_selection_flag=TRUE` | Getting picked off by informed flow | Widen spread; reduce wind-down time |
| **Database connection error** | `asyncpg.exceptions.ConnectionError` | Database not running or wrong credentials | Check `POLYMARKET_DATABASE_URL`; verify DB is up |

### Debug Mode

Enable verbose logging:

```bash
# Set log level to DEBUG
export LOG_LEVEL=DEBUG
poetry run polymarket-session --dry-run
```

### Check API Connectivity

Test each API independently:

```bash
# Gamma API
curl -v https://gamma-api.polymarket.com/markets?limit=1

# CLOB API
curl -v https://clob.polymarket.com/markets?limit=1

# Binance API
curl -v https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1h&limit=1
```

### Verify Wallet Balance

```bash
# Check USDC balance on Polygonscan
# Visit: https://polygonscan.com/address/<your_wallet_address>
# Look for USDC token balance (contract: 0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174)

# Check MATIC balance (for gas)
# Should show on main balance line
```

### Inspect Session Logs

```bash
# View full session log
cat logs/polymarket_<session_id>.log

# Filter for errors
grep ERROR logs/polymarket_<session_id>.log

# Filter for warnings
grep WARNING logs/polymarket_<session_id>.log

# Filter for fills
grep "Fill received" logs/polymarket_<session_id>.log
```

---

## Emergency Procedures

### 1. Emergency Shutdown (Manual)

If you need to stop a session immediately:

**Option A: Graceful shutdown (Ctrl+C)**
```bash
# Press Ctrl+C in the terminal running the session
# Bot will:
# 1. Cancel all orders
# 2. Stop heartbeat
# 3. Finalize session record
# 4. Exit cleanly
```

**Option B: Kill process**
```bash
# Find process ID
ps aux | grep polymarket-session

# Kill process
kill <pid>

# Note: Orders will remain live until heartbeat timeout (30s)
```

**Option C: Cancel all orders via Polymarket UI**
1. Log in to https://polymarket.com
2. Go to "Portfolio" → "Open Orders"
3. Cancel all orders manually

### 2. Emergency Shutdown (Automatic)

The bot triggers emergency shutdown on:
- Session loss exceeds `max_session_loss_usdc`
- Critical error in data feed or executor
- Heartbeat failure (platform-enforced)

**What happens:**
1. `SafetyLayer.emergency_shutdown()` called
2. All orders cancelled via `executor.cancel_all_orders()`
3. Session status set to `KILLED`
4. Error logged at CRITICAL level
5. Process exits

**Recovery:**
1. Check logs for root cause
2. Fix issue (e.g., fund wallet, fix network)
3. Wait for market to close (don't restart mid-session)
4. Start fresh session for next hour

### 3. Withdraw Funds

If you need to withdraw funds immediately:

**Step 1: Stop all sessions**
```bash
# Kill any running sessions
pkill -f polymarket-session
```

**Step 2: Cancel all orders**
- Via Polymarket UI (see Option C above)
- Or wait 30 seconds for heartbeat timeout

**Step 3: Merge tokens back to USDC**

If you have residual YES/NO tokens:
```python
# Run this script to merge tokens
from services.polymarket.wallet import WalletManager
from services.polymarket.config import PolymarketConfig

config = PolymarketConfig()
wallet = WalletManager(config.wallet_address, config.private_key)

# Get token balances
yes_balance = await wallet.get_token_balance("<token_id_yes>")
no_balance = await wallet.get_token_balance("<token_id_no>")

# Merge (requires equal YES and NO)
merge_amount = min(yes_balance, no_balance)
if merge_amount > 0:
    await wallet.merge_tokens(merge_amount, "<condition_id>")
```

**Step 4: Withdraw USDC**
1. Go to https://polymarket.com
2. Click "Withdraw"
3. Enter amount and destination address
4. Confirm transaction

---

## Parameter Tuning

After collecting 10-20 sessions of data, tune parameters based on empirical results.

### 1. Requote Interval

**Default:** 10 seconds

**Analysis query:**
```sql
SELECT 
    AVG(time_on_book_seconds) AS avg_time_on_book,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY time_on_book_seconds) AS median_time_on_book,
    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY time_on_book_seconds) AS p25_time_on_book,
    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY time_on_book_seconds) AS p75_time_on_book
FROM pm.orders
WHERE status = 'MATCHED'
  AND time_on_book_seconds IS NOT NULL;
```

**Tuning guidance:**
- If median fill time > 20s → **decrease interval** (requote faster, e.g., 5-7s)
- If median fill time < 10s → **increase interval** (requote slower, e.g., 15-20s)
- Goal: Balance between queue priority and fill capture

### 2. Wind-Down Time

**Default:** 5 minutes

**Analysis query:**
```sql
SELECT 
    minute_offset,
    adverse_fill_pct
FROM pm.toxic_flow_by_minute
WHERE session_id IN (
    SELECT session_id FROM pm.sessions WHERE status = 'COMPLETED'
)
GROUP BY minute_offset
HAVING COUNT(*) >= 5  -- At least 5 sessions
ORDER BY minute_offset;
```

**Tuning guidance:**
- Plot `adverse_fill_pct` vs `minute_offset`
- Find the minute where adverse selection spikes
- Set `wind_down_minutes` to stop quoting before the spike
- Example: If spike at minute 55 → set `wind_down_minutes = 7`

### 3. Quote Spread

**Default:** 0.02 (2 cents)

**Analysis query:**
```sql
SELECT 
    ROUND(spread_at_place, 2) AS spread,
    COUNT(*) AS total_orders,
    COUNT(*) FILTER (WHERE status = 'MATCHED') AS filled_orders,
    ROUND(100.0 * COUNT(*) FILTER (WHERE status = 'MATCHED') / COUNT(*), 2) AS fill_rate_pct,
    AVG(CASE WHEN status = 'MATCHED' THEN time_on_book_seconds END) AS avg_fill_time
FROM pm.orders
WHERE spread_at_place IS NOT NULL
GROUP BY ROUND(spread_at_place, 2)
ORDER BY spread;
```

**Tuning guidance:**
- If fill rate < 20% → **tighten spread** (e.g., 0.015 or 0.01)
- If adverse selection > 30% → **widen spread** (e.g., 0.025 or 0.03)
- Goal: Balance between fill rate and adverse selection

### 4. Quote Size

**Default:** 50 shares

**Analysis query:**
```sql
SELECT 
    AVG(original_size) AS avg_size,
    AVG(CASE WHEN status = 'MATCHED' THEN original_size END) AS avg_filled_size,
    MAX(inventory_yes) AS max_inventory_held
FROM pm.orders o
JOIN pm.sessions s ON o.session_id = s.session_id
WHERE s.status = 'COMPLETED';
```

**Tuning guidance:**
- If `max_inventory_held` never approaches `inventory_cap` → **increase size** (e.g., 75 or 100)
- If frequently hitting `inventory_cap` → **decrease size** (e.g., 25 or 30)
- Goal: Maximize volume without hitting inventory limits

### 5. Inventory Cap

**Default:** 200 shares

**Analysis query:**
```sql
SELECT 
    session_id,
    max_inventory_held,
    inventory_cap
FROM pm.sessions
WHERE status = 'COMPLETED'
ORDER BY max_inventory_held DESC;
```

**Tuning guidance:**
- If `max_inventory_held` consistently < 50% of cap → **decrease cap** (tighter risk control)
- If frequently hitting cap and missing fills → **increase cap** (allow more directional exposure)
- Goal: Balance between risk control and fill opportunity

---

## Phase 2 Preparation

After Phase 1 data collection (10-20 sessions), prepare for Phase 2 advanced features.

### 1. Data Quality Check

Verify you have sufficient data for Phase 2 modeling:

```sql
-- Session count by regime
SELECT 
    volatility_regime,
    spread_regime,
    COUNT(*) AS session_count
FROM pm.sessions
WHERE status = 'COMPLETED'
GROUP BY volatility_regime, spread_regime
ORDER BY session_count DESC;

-- Should have at least 3-5 sessions per regime combination
```

```sql
-- Fill count
SELECT COUNT(*) AS total_fills
FROM pm.fills;

-- Should have at least 50-100 fills total
```

```sql
-- Adverse selection data completeness
SELECT 
    COUNT(*) AS total_fills,
    COUNT(*) FILTER (WHERE midpoint_5s_after IS NOT NULL) AS fills_with_5s_data,
    ROUND(100.0 * COUNT(*) FILTER (WHERE midpoint_5s_after IS NOT NULL) / COUNT(*), 2) AS completeness_pct
FROM pm.fills;

-- Should be >90% completeness
```

### 2. Phase 2 Feature Prioritization

Based on Phase 1 results, prioritize Phase 2 features:

**High priority if:**
- Adverse selection > 30% → **Implement inventory skew** (Avellaneda-Stoikov)
- Fill rate < 20% → **Implement dynamic spread** (fill probability curve)
- Toxic flow spikes early → **Optimize wind-down timing**

**Medium priority if:**
- Queue position consistently bad → **Implement spread optimization** (cross spread slightly)
- Reward eligibility low → **Implement reward tracking** (optimize for liquidity rewards)

**Low priority if:**
- Performance is profitable → **Scale up capital** before adding complexity

### 3. Export Data for Analysis

Export all Phase 1 data for offline analysis:

```bash
# Sessions
psql -d caliper -c "COPY (SELECT * FROM pm.sessions WHERE status = 'COMPLETED') TO STDOUT CSV HEADER" > sessions.csv

# Orders
psql -d caliper -c "COPY (SELECT * FROM pm.orders) TO STDOUT CSV HEADER" > orders.csv

# Fills
psql -d caliper -c "COPY (SELECT * FROM pm.fills) TO STDOUT CSV HEADER" > fills.csv

# Toxic flow
psql -d caliper -c "COPY (SELECT * FROM pm.toxic_flow_by_minute) TO STDOUT CSV HEADER" > toxic_flow.csv

# Snapshots (sample)
psql -d caliper -c "COPY (SELECT * FROM pm.orderbook_snapshots WHERE snapshot_id % 10 = 0) TO STDOUT CSV HEADER" > snapshots_sample.csv
```

### 4. Phase 2 Implementation Tickets

Once data analysis is complete, create Phase 2 tickets:

1. **Inventory skew** (Avellaneda-Stoikov model)
2. **Dynamic spread** (fill probability curve)
3. **Reward tracking** (maker rebates, liquidity rewards)
4. **PnL decomposition** (spread capture, inventory drift, incentives)
5. **Session wind-down optimization** (toxic flow curve)
6. **Binance WebSocket** (sub-second price updates)

See `docs/plans/specs/polymarket-btc-trading-spec.md` section 10 for detailed Phase 2 roadmap.

---

## Appendix: Quick Reference

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `POLYMARKET_WALLET_ADDRESS` | ✅ | - | Your Polygon wallet address |
| `POLYMARKET_PRIVATE_KEY` | ✅ | - | Your wallet private key |
| `POLYMARKET_TARGET_HOUR_LOCAL` | ✅ | - | Target hour (0-23) in local timezone |
| `POLYMARKET_TARGET_TIMEZONE` | ✅ | - | IANA timezone (e.g., America/New_York) |
| `POLYMARKET_QUOTE_SPREAD` | ❌ | 0.02 | Quote spread (each side of mid) |
| `POLYMARKET_QUOTE_SIZE` | ❌ | 50 | Quote size (shares per side) |
| `POLYMARKET_INVENTORY_CAP` | ❌ | 200 | Max YES shares held |
| `POLYMARKET_REQUOTE_INTERVAL_SECONDS` | ❌ | 10 | Requote frequency |
| `POLYMARKET_MAX_SESSION_LOSS_USDC` | ❌ | 50 | Session loss limit |
| `POLYMARKET_WIND_DOWN_MINUTES` | ❌ | 5 | Wind-down time before close |
| `POLYMARKET_DATABASE_URL` | ✅ | - | PostgreSQL connection string |

### CLI Commands

```bash
# Dry-run (no real orders)
poetry run polymarket-session --dry-run

# Live session
poetry run polymarket-session

# Override target hour
poetry run polymarket-session --target-hour 15

# Help
poetry run polymarket-session --help
```

### Database Queries

```sql
-- Latest session
SELECT * FROM pm.sessions ORDER BY started_at DESC LIMIT 1;

-- Session PnL
SELECT session_id, realized_pnl, total_fills, total_volume_usdc 
FROM pm.sessions WHERE status = 'COMPLETED';

-- Adverse selection rate
SELECT 
    COUNT(*) FILTER (WHERE adverse_selection_flag = TRUE) * 100.0 / COUNT(*) AS adverse_pct
FROM pm.fills;

-- Queue position
SELECT AVG(our_bid_queue_ahead_size) AS avg_queue_ahead
FROM pm.orderbook_snapshots;
```

### Support & Documentation

- **Spec:** `docs/plans/specs/polymarket-btc-trading-spec.md`
- **Summary:** `docs/plans/summaries/SPRINT-10-POLYMARKET-COMPLETE.md`
- **Setup:** `services/polymarket/docs/SETUP.md`
- **Config:** `services/polymarket/docs/CONFIG.md`
- **Polymarket Docs:** https://docs.polymarket.com
- **Polygon Docs:** https://docs.polygon.technology
