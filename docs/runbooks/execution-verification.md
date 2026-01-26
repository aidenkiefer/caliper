# Execution & Risk Verification Runbook

## Summary

This runbook provides step-by-step verification procedures for the execution and risk management services implemented in Sprint 5. Use this to verify that all risk limits, kill switches, and execution flows work correctly.

**Test Summary (Sprint 5):**
- **Unit Tests:** 75 tests (39 RiskManager + 36 Execution)
- **Integration Tests:** 41 tests (21 order flow + 20 kill switch)
- **Total:** 116 tests
- **Passing:** 114 tests
- **Skipped:** 2 tests (pending Backend integration)

---

## Prerequisites

Before running verification:

1. **Environment Setup**
   ```bash
   # Install dependencies
   poetry install
   
   # Ensure test dependencies are installed
   pip install pytest pytest-asyncio httpx
   ```

2. **Services Running** (for integration tests)
   ```bash
   # Start API server (optional - TestClient handles this)
   make run-api
   ```

---

## 1. Unit Test Verification

### 1.1 Run All Unit Tests

```bash
# Run all unit tests
poetry run pytest tests/unit/ -v

# Run with coverage
poetry run pytest tests/unit/ --cov=services/risk --cov=services/execution --cov-report=html
```

**Expected Output:**
- All tests pass (30+ RiskManager tests, 30+ execution tests)
- Coverage report generated in `htmlcov/`

### 1.2 Risk Manager Tests

```bash
# Run risk manager tests specifically
poetry run pytest tests/unit/test_risk_manager.py -v
```

**Verify these test categories pass:**

| Category | Test Count | Purpose |
|----------|------------|---------|
| TestPortfolioLimits | 9 | Daily/total drawdown, capital, positions |
| TestOrderLimits | 10 | Risk per trade, notional, price, min price |
| TestKillSwitch | 6 | Global/strategy kill switch |
| TestCircuitBreaker | 6 | Auto-trigger, warning, reset |
| TestStrategyLimits | 2 | Allocation, paused strategy |
| TestEdgeCases | 4 | Multiple violations, zero values |
| TestPortfolioLimitsClass | 2 | Default values match policy |
| TestOrderLimitsClass | 2 | Blocked symbols |

### 1.3 Execution Tests

```bash
# Run execution tests specifically
poetry run pytest tests/unit/test_execution.py -v
```

**Verify these test categories pass:**

| Category | Test Count | Purpose |
|----------|------------|---------|
| TestBrokerClientInterface | 6 | Abstract interface, models |
| TestOrderStateTransitions | 10 | State machine transitions |
| TestOrderIdempotency | 6 | Duplicate order handling |
| TestPositionTracking | 5 | Order queries, cancellation |
| TestManagedOrderModel | 3 | Model helper methods |
| TestUpdateFromBroker | 2 | Broker status updates |

---

## 2. Integration Test Verification

### 2.1 Run All Integration Tests

```bash
# Run all integration tests
poetry run pytest tests/integration/test_order_flow.py tests/integration/test_kill_switch.py -v
```

### 2.2 Order Flow Tests

```bash
poetry run pytest tests/integration/test_order_flow.py -v
```

**Verify:**
- [ ] Orders within limits return 200
- [ ] Orders exceeding notional ($25k) return 400
- [ ] Orders for penny stocks (<$5) return 400
- [ ] Rejection response includes violation details
- [ ] Idempotent orders return existing order

### 2.3 Kill Switch Tests

```bash
poetry run pytest tests/integration/test_kill_switch.py -v
```

**Verify:**
- [ ] POST /v1/controls/kill-switch activates
- [ ] Deactivation requires admin code
- [ ] Invalid admin code returns 403
- [ ] Active kill switch blocks orders

---

## 3. Risk Limit Verification Checklist

Verify each risk limit from `docs/risk-policy.md`:

### 3.1 Portfolio-Level Limits

| Limit | Value | Test | Status |
|-------|-------|------|--------|
| Max Daily Drawdown | 3% | `test_rejects_order_when_daily_drawdown_exceeded` | ☐ |
| Max Total Drawdown | 10% | `test_rejects_order_when_total_drawdown_exceeded` | ☐ |
| Max Capital Deployed | 80% | `test_rejects_order_when_capital_deployed_exceeded` | ☐ |
| Max Open Positions | 20 | `test_rejects_order_when_max_positions_exceeded` | ☐ |

### 3.2 Order-Level Limits

| Limit | Value | Test | Status |
|-------|-------|------|--------|
| Max Risk Per Trade | 2% | `test_rejects_order_exceeding_max_risk_per_trade` | ☐ |
| Max Notional | $25,000 | `test_rejects_order_exceeding_max_notional` | ☐ |
| Price Deviation | >5% | `test_rejects_order_with_price_deviation` | ☐ |
| Min Stock Price | $5.00 | `test_rejects_penny_stock_order` | ☐ |

### 3.3 Kill Switch

| Feature | Test | Status |
|---------|------|--------|
| Global Blocks All | `test_kill_switch_blocks_all_orders` | ☐ |
| Activation | `test_kill_switch_activation` | ☐ |
| Deactivation Auth | `test_kill_switch_deactivation_requires_admin` | ☐ |
| Strategy-Level | `test_strategy_level_kill_switch` | ☐ |

---

## 4. Manual API Verification

### 4.1 Start API Server

```bash
make run-api
# Or: poetry run uvicorn services.api.main:app --reload
```

### 4.2 Test Order Submission

**Submit Valid Order:**
```bash
curl -X POST http://localhost:8000/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "side": "BUY",
    "quantity": "100",
    "order_type": "LIMIT",
    "limit_price": "150.00",
    "time_in_force": "DAY",
    "strategy_id": "test_strategy"
  }'
```

**Expected:** 200 with order details

**Submit Order Exceeding Notional:**
```bash
curl -X POST http://localhost:8000/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "NVDA",
    "side": "BUY",
    "quantity": "300",
    "order_type": "LIMIT",
    "limit_price": "100.00",
    "time_in_force": "DAY",
    "strategy_id": "test_strategy"
  }'
```

**Expected:** 400 with max_notional violation

### 4.3 Test Kill Switch

**Activate Kill Switch:**
```bash
curl -X POST http://localhost:8000/v1/controls/kill-switch \
  -H "Content-Type: application/json" \
  -d '{
    "action": "activate",
    "reason": "Manual test"
  }'
```

**Verify Order Blocked:**
```bash
curl -X POST http://localhost:8000/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "side": "BUY",
    "quantity": "10",
    "order_type": "MARKET",
    "time_in_force": "DAY",
    "strategy_id": "test"
  }'
```

**Expected:** 400 with kill_switch_active violation

**Deactivate Kill Switch:**
```bash
curl -X POST http://localhost:8000/v1/controls/kill-switch \
  -H "Content-Type: application/json" \
  -d '{
    "action": "deactivate",
    "reason": "Test complete",
    "admin_code": "EMERGENCY_OVERRIDE_2026"
  }'
```

---

## 5. Verification Summary Template

Use this template to record verification results:

```
Verification Date: YYYY-MM-DD
Verified By: [Name]

Unit Tests:
  - tests/unit/test_risk_manager.py: [ ] PASS / [ ] FAIL
  - tests/unit/test_execution.py: [ ] PASS / [ ] FAIL

Integration Tests:
  - tests/integration/test_order_flow.py: [ ] PASS / [ ] FAIL
  - tests/integration/test_kill_switch.py: [ ] PASS / [ ] FAIL

Risk Limits (all checked):
  [ ] Max Daily Drawdown (3%)
  [ ] Max Total Drawdown (10%)
  [ ] Max Capital Deployed (80%)
  [ ] Max Open Positions (20)
  [ ] Max Risk Per Trade (2%)
  [ ] Max Notional ($25,000)
  [ ] Price Deviation (>5%)
  [ ] Min Stock Price ($5.00)

Kill Switch:
  [ ] Global activation/deactivation
  [ ] Strategy-level activation/deactivation
  [ ] Admin code required for deactivation
  [ ] Orders blocked when active

Notes:
[Any issues found or observations]
```

---

## 6. Troubleshooting

### Tests Fail with Import Errors

```bash
# Ensure you're in the project root
cd /path/to/quant

# Install in development mode
poetry install

# Or set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### API Server Won't Start

```bash
# Check port not in use
lsof -i :8000

# Try different port
poetry run uvicorn services.api.main:app --port 8001
```

### Kill Switch Won't Deactivate

The admin code is `EMERGENCY_OVERRIDE_2026` by default. If changed, check:
- `services/risk/kill_switch.py` - `DEFAULT_ADMIN_CODE`
- `services/api/routers/controls.py` - `VALID_ADMIN_CODES`

---

## 7. Known Issues and Limitations

### 7.1 Kill Switch Integration Incomplete

**Issue:** The orders router (`services/api/routers/orders.py`) uses a mock `_kill_switch_active` flag that is not connected to the actual kill switch state maintained in the controls router (`services/api/routers/controls.py`).

**Impact:** Activating the kill switch via `POST /v1/controls/kill-switch` does not block orders submitted via `POST /v1/orders`.

**Skipped Tests:**
- `test_kill_switch_blocks_order_endpoint` - Orders should be blocked when kill switch is active
- `test_global_switch_affects_all_strategies` - Global switch should block all strategies

**Resolution:** Backend Agent needs to integrate the RiskManager service with the orders router, or share kill switch state between routers.

### 7.2 Circuit Breaker and Drawdown Checks

**Behavior:** When daily drawdown exceeds 3% or total drawdown exceeds 10%, the circuit breaker trips and activates the kill switch. This means individual drawdown violation messages (MAX_DAILY_DRAWDOWN, MAX_TOTAL_DRAWDOWN) may be replaced by KILL_SWITCH_ACTIVE violation.

**This is correct behavior** - the kill switch takes precedence and halts all trading immediately.

---

## 8. Related Documentation

- `docs/risk-policy.md` - Risk limits and policy
- `docs/api-contracts.md` - API endpoint specifications
- `docs/architecture.md` - System architecture
- `adr/0007-execution-architecture.md` - Architecture decisions
