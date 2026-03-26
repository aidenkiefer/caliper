# Polymarket Bot Quick Start Guide

**Complete documentation:** `docs/runbooks/polymarket-operations.md`

---

## 5-Minute Setup Checklist

### 1. Prerequisites (One-Time Setup)

- [ ] **Polymarket account** — Sign up at https://polymarket.com
- [ ] **Polygon wallet** — Create new wallet (MetaMask or similar)
- [ ] **Fund wallet:**
  - 5-10 MATIC (~$5-10) for gas fees
  - $100-200 USDC for trading (Phase 1 dust capital)
  - **IMPORTANT:** Withdraw on Polygon network, not Ethereum mainnet
- [ ] **Export private key** — Store securely (never commit to git)
- [ ] **Update contract addresses** — Edit `services/polymarket/constants.py`:
  ```python
  CTF_CONTRACT_ADDRESS = "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"
  USDC_CONTRACT_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
  ```

### 2. Environment Configuration

Create `.env.polymarket` in repo root:

```bash
# Wallet (REQUIRED)
POLYMARKET_WALLET_ADDRESS=0xYourWalletAddressHere
POLYMARKET_PRIVATE_KEY=0xYourPrivateKeyHere

# Trading Window (REQUIRED)
POLYMARKET_TARGET_HOUR_LOCAL=14        # 2 PM local time
POLYMARKET_TARGET_TIMEZONE=America/New_York

# Database (REQUIRED)
POLYMARKET_DATABASE_URL=postgresql://user:password@localhost:5432/caliper

# Optional (defaults shown)
POLYMARKET_QUOTE_SPREAD=0.02           # 2 cents each side
POLYMARKET_QUOTE_SIZE=50               # 50 shares per side
POLYMARKET_MAX_SESSION_LOSS_USDC=50    # Stop if lose $50
```

**Security:**
```bash
chmod 600 .env.polymarket  # Restrict permissions
```

### 3. Database Setup

```bash
cd services/data
poetry run alembic upgrade head
```

Verify:
```sql
SELECT tablename FROM pg_tables WHERE schemaname = 'pm';
-- Should show 8 tables
```

### 4. Test Run (Dry-Run)

```bash
cd services/polymarket
poetry install  # First time only
poetry run polymarket-session --dry-run
```

**Expected:** Bot discovers market, computes quotes, logs "[DRY-RUN] Would place..." (no real orders).

### 5. Live Session

⚠️ **WARNING:** Real money. Max loss = `max_session_loss_usdc`.

```bash
poetry run polymarket-session
```

**Monitor:**
```bash
tail -f logs/polymarket_<session_id>.log
```

---

## Key Commands

```bash
# Dry-run (no real orders)
poetry run polymarket-session --dry-run

# Live session
poetry run polymarket-session

# Override target hour
poetry run polymarket-session --target-hour 15

# Emergency stop
Ctrl+C  # Graceful shutdown (cancels all orders)
```

---

## Quick Monitoring

### Real-Time (During Session)

**Latest snapshot:**
```sql
SELECT timestamp, best_bid, best_ask, midpoint, spread,
       our_bid_price, our_ask_price
FROM pm.orderbook_snapshots
WHERE session_id = '<session_id>'
ORDER BY timestamp DESC LIMIT 1;
```

**Recent fills:**
```sql
SELECT side, price, size, filled_at, adverse_selection_flag
FROM pm.fills
WHERE session_id = '<session_id>'
ORDER BY filled_at DESC LIMIT 5;
```

### Post-Session Analysis

**Session summary:**
```sql
SELECT session_id, realized_pnl, total_fills, total_volume_usdc,
       volatility_regime, spread_regime
FROM pm.sessions
WHERE session_id = '<session_id>';
```

**Adverse selection rate:**
```sql
SELECT 
    COUNT(*) FILTER (WHERE adverse_selection_flag = TRUE) * 100.0 / COUNT(*) AS adverse_pct
FROM pm.fills
WHERE session_id = '<session_id>';
```

**Queue position:**
```sql
SELECT AVG(our_bid_queue_ahead_size) AS avg_queue_ahead
FROM pm.orderbook_snapshots
WHERE session_id = '<session_id>';
```

---

## Troubleshooting

| Issue | Quick Fix |
|-------|-----------|
| **Market not found** | Try different hour; markets may not exist yet |
| **Insufficient balance** | Fund wallet with more USDC |
| **Heartbeat failure** | Check internet; restart session |
| **Order rejected** | Widen spread (increase `POLYMARKET_QUOTE_SPREAD`) |
| **No fills** | Tighten spread (decrease `POLYMARKET_QUOTE_SPREAD`) |
| **High adverse selection** | Widen spread or reduce wind-down time |

---

## Phase 1 Goals (1-2 Weeks)

1. **Run 1-2 sessions per day** with dust capital ($100-200)
2. **Collect 10-20 sessions** across different regimes
3. **Analyze data:**
   - Queue position vs fill rate
   - Adverse selection by minute (toxic flow curve)
   - Fill probability vs distance from mid
   - Regime-specific performance
4. **Tune parameters:**
   - Requote interval (default: 10s)
   - Wind-down time (default: 5 min)
   - Quote spread (default: 0.02)
   - Quote size (default: 50)

**Success criteria:**
- 10+ sessions with fills
- Adverse selection < 30%
- Clear toxic flow pattern identified
- Ready for Phase 2 (inventory skew, dynamic spread)

---

## Documentation Index

| Document | Purpose |
|----------|---------|
| **This file** | Quick start (5 minutes) |
| `docs/runbooks/polymarket-operations.md` | Complete operations guide (18,000 words) |
| `docs/plans/summaries/SPRINT-10-POLYMARKET-COMPLETE.md` | Implementation summary (14,000 words) |
| `docs/plans/specs/polymarket-btc-trading-spec.md` | Technical specification (full design) |
| `services/polymarket/docs/SETUP.md` | Detailed setup instructions |
| `services/polymarket/docs/CONFIG.md` | All config fields documented |
| `services/polymarket/docs/RUNBOOK.md` | Service-specific operations |

---

## Emergency Contacts

**Stop trading immediately:**
```bash
# Option 1: Graceful (recommended)
Ctrl+C in terminal

# Option 2: Kill process
pkill -f polymarket-session

# Option 3: Manual cancel via Polymarket UI
# Visit https://polymarket.com → Portfolio → Open Orders → Cancel All
```

**Withdraw funds:**
1. Stop all sessions
2. Wait 30s for orders to cancel (heartbeat timeout)
3. Go to https://polymarket.com → Withdraw
4. Enter amount and destination
5. Confirm transaction

---

## Next Steps

After completing Phase 1 data collection:

1. **Review results** — Analyze all metrics (queue position, adverse selection, toxic flow)
2. **Tune parameters** — Adjust based on empirical data
3. **Prioritize Phase 2** — Choose features based on Phase 1 insights:
   - Inventory skew (if adverse selection high)
   - Dynamic spread (if fill rate low)
   - Reward optimization (if reward eligibility low)
4. **Scale capital** — If profitable, increase from $100-200 to $500-1000

See `docs/plans/specs/polymarket-btc-trading-spec.md` section 10 for full Phase 2/3 roadmap.
