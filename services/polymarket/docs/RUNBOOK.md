# Polymarket Service — Operations Runbook

## 1. Starting a Session

### Command

```bash
# Standard session (uses defaults from environment)
polymarket-session

# With explicit target hour override
polymarket-session --target-hour 9

# Dry run — validates config and connectivity without placing orders
polymarket-session --dry-run --target-hour 9

# Via Python module (equivalent)
python -m polymarket
```

### What to Expect in Logs

Logs are written to `logs/polymarket_<uuid>.log` and to stdout. A normal startup sequence looks like:

```
INFO  [polymarket] Session starting (dry_run=False, target_hour=9, tz=America/New_York)
INFO  [polymarket] Resolved market: BTC-25MAR2026-<suffix> (condition_id=0x...)
INFO  [polymarket] Pre-session checks passed — wallet balance OK, CLOB reachable
INFO  [polymarket] Session record created (session_id=<uuid>)
INFO  [polymarket] Quoting loop started — requote_interval=10s
INFO  [polymarket] Placed BID YES @ 0.48 size=50 USDC (order_id=...)
INFO  [polymarket] Placed ASK NO  @ 0.52 size=50 USDC (order_id=...)
INFO  [polymarket] Heartbeat — inventory=0.00 USDC, session_pnl=0.00 USDC
```

Wind-down logs:

```
INFO  [polymarket] Wind-down triggered (5 min before expiry) — cancelling open orders
INFO  [polymarket] All orders cancelled
INFO  [polymarket] Session ended — realized_pnl=2.34 USDC, fills=6, fees=0.12 USDC
```

---

## 2. Monitoring

### Tail Logs

```bash
# Most recent session log
tail -f logs/polymarket_*.log

# If running via Docker / systemd, follow service output:
docker logs -f polymarket
```

### Active Session Query

```sql
-- Check currently running sessions
SELECT session_id, started_at, status, realized_pnl_usdc, fill_count
FROM pm.sessions
WHERE status = 'running'
ORDER BY started_at DESC;
```

### Active Open Orders

```sql
-- Open orders for the latest session
SELECT order_id, side, price, size_usdc, status, created_at
FROM pm.orders
WHERE session_id = (
    SELECT session_id FROM pm.sessions WHERE status = 'running' LIMIT 1
)
AND status = 'open'
ORDER BY created_at DESC;
```

### Recent Fills

```sql
-- Last 20 fills across all sessions
SELECT f.fill_id, f.session_id, f.side, f.price, f.size_usdc, f.fee_usdc,
       f.adverse_selection_flag, f.filled_at
FROM pm.fills f
ORDER BY f.filled_at DESC
LIMIT 20;
```

---

## 3. Emergency Shutdown

### Graceful Stop (SIGINT / SIGTERM)

Send `SIGINT` (Ctrl+C) or `SIGTERM` to the running process. With `cancel_all_on_error=true` (default), the service will:

1. Cancel all open orders on the CLOB
2. Write a final session record with `status='terminated'`
3. Exit cleanly

```bash
# Find the PID
pgrep -f polymarket-session

# Send graceful stop
kill -SIGTERM <pid>
```

### Force Cancel All Open Orders (Manual)

If the process exits uncleanly and orders may still be open on the CLOB, use the Polymarket CLOB API directly or the `py-clob-client` CLI:

```bash
# Using py-clob-client (installed as a dep of this service)
python - <<'EOF'
from py_clob_client.client import ClobClient
import os

client = ClobClient(
    host=os.environ["POLYMARKET_CLOB_API_URL"],
    key=os.environ["POLYMARKET_PRIVATE_KEY"],
    chain_id=137,  # Polygon mainnet
)
result = client.cancel_all()
print("Cancelled:", result)
EOF
```

### Kill Switch — Mark Session Terminated in DB

If you need to mark a session as terminated without restarting the service:

```sql
UPDATE pm.sessions
SET status = 'terminated', ended_at = NOW()
WHERE status = 'running';
```

---

## 4. Post-Session Analysis

### PnL by Session

```sql
SELECT session_id, realized_pnl_usdc, total_fees_paid, fill_count
FROM pm.sessions
ORDER BY started_at DESC;
```

### Adverse Selection Rate

```sql
SELECT
    session_id,
    COUNT(*) FILTER (WHERE adverse_selection_flag) AS adverse_fills,
    COUNT(*) AS total_fills,
    ROUND(COUNT(*) FILTER (WHERE adverse_selection_flag)::numeric / COUNT(*), 3) AS adverse_rate
FROM pm.fills
GROUP BY session_id;
```

### Regime Performance

```sql
SELECT volatility_regime, spread_regime, AVG(realized_pnl_usdc) AS avg_pnl
FROM pm.sessions
WHERE status = 'completed'
GROUP BY volatility_regime, spread_regime;
```

### Fee Impact

```sql
SELECT
    session_id,
    realized_pnl_usdc,
    total_fees_paid,
    realized_pnl_usdc - total_fees_paid AS net_pnl
FROM pm.sessions
ORDER BY started_at DESC;
```

---

## 5. Common Errors and Troubleshooting

| Error / Symptom | Likely Cause | Resolution |
|---|---|---|
| `ConfigValidationError: private_key field required` | `POLYMARKET_PRIVATE_KEY` env var not set | Export the variable or load `.env.polymarket` before starting |
| `ConfigValidationError: wallet_address field required` | `POLYMARKET_WALLET_ADDRESS` not set | Same as above |
| `DatabaseError: relation "pm.sessions" does not exist` | Migration not run | `cd services/data && poetry run alembic upgrade head` |
| `CLOBClientError: 401 Unauthorized` | Invalid or expired API key / wrong private key | Verify `POLYMARKET_PRIVATE_KEY` matches the account that generated the API key |
| `MarketNotFoundError: no BTC hourly market for target hour` | No Polymarket market resolves at the configured hour | Check Polymarket for available BTC hourly markets; adjust `--target-hour` |
| `BinancePriceStale: last price older than 30s` | Binance API unreachable or rate-limited | Check network connectivity; increase `POLYMARKET_BINANCE_STALE_SECONDS` temporarily |
| `SessionLossLimitBreached` | Realized loss exceeded `max_session_loss_usdc` | Expected behavior — session terminates. Review fills for adverse selection. Consider widening `quote_spread`. |
| `InventoryCapReached` | Net inventory hit `inventory_cap` | Expected behavior — quoting pauses until inventory unwinds. Consider reducing `quote_size` or increasing `inventory_cap`. |
| Orders not filling / no fills after many cycles | Quotes too wide or market is one-sided | Reduce `quote_spread`; check current Polymarket order book depth |
| High adverse selection rate (> 30%) | Quotes are being picked off systematically | Widen `quote_spread`; shorten `requote_interval_seconds`; review regime signals |
| Service exits immediately after start | Pre-session check failure | Check logs for specific error; common causes: DB unreachable, CLOB unreachable, insufficient USDC/MATIC balance |
| `WebSocketDisconnected` during session | CLOB WebSocket dropped | Service should reconnect automatically. If persistent, check network stability and CLOB status page. |
