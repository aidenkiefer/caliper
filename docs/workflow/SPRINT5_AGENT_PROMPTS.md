# Sprint 5 Agent Prompts with Skill Gates

**Generated:** 2026-01-26  
**Sprint:** Execution & Risk  
**Status:** Ready for Execution

---

## 📋 Sprint 5 Task Coverage Verification

| Task | Agent | Status |
|------|-------|--------|
| Execution Service Skeleton | Backend | ✅ Assigned |
| BrokerClient Interface | Backend | ✅ Assigned |
| AlpacaClient Implementation | Backend | ✅ Assigned |
| Order Management System | Backend | ✅ Assigned |
| Position Reconciliation | Backend | ✅ Assigned |
| RiskManager Class | Backend | ✅ Assigned |
| Portfolio Limits | Backend | ✅ Assigned |
| Strategy Limits | Backend | ✅ Assigned |
| Order Limits | Backend | ✅ Assigned |
| Kill Switch | Backend | ✅ Assigned |
| Controls API Endpoints | Backend | ✅ Assigned |
| Orders API Endpoints | Backend | ✅ Assigned |
| Risk Unit Tests | QA | ✅ Assigned |
| Execution Tests | QA | ✅ Assigned |
| Design Review | Architect | ✅ Assigned |
| Docker Updates | DevOps | ✅ Assigned |

---

## 🎯 Sprint 5 Dependencies & Parallelization

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SPRINT 5 PARALLEL EXECUTION PLAN                          │
└─────────────────────────────────────────────────────────────────────────────┘

START IMMEDIATELY (No Dependencies):
├── Backend Agent Stream A (Execution Engine - Tasks A1-A6)
├── Backend Agent Stream B (Risk Management - Tasks B1-B7)
├── DevOps Agent (Tasks F1-F4)
└── Architect Agent (Tasks D1-D4) - Reviews as work progresses

AFTER EXECUTION & RISK COMPLETE:
├── Backend Agent Stream C (API Integration - Tasks C1-C5)
└── QA Agent (Tasks E1-E5) - Needs testable services

FINAL:
└── Integrator - Merge and verify
```

**Execution Order:**
1. **Phase 1:** Backend (Execution + Risk parallel), DevOps, Architect start in parallel
2. **Phase 2:** Backend completes API integration (Stream C)
3. **Phase 3:** QA Agent tests execution and risk services
4. **Phase 4:** Integrator merges and verifies

---

## 👤 Backend Agent Prompt

**Copy this entire section to a new Composer tab:**

---

```
You are the Backend Agent for Sprint 5: Execution & Risk.

═══════════════════════════════════════════════════════════════
🔴 SKILL GATE - MANDATORY BEFORE ANY CODING
═══════════════════════════════════════════════════════════════

STEP 1: Invoke @using-superpowers FIRST
- Read: agents/skills/skills/using-superpowers/SKILL.md
- Announce: "Using @using-superpowers to establish skill usage protocol"

STEP 2: Invoke Required Skills
You MUST invoke these skills before coding:

1. @python-patterns
   - Read: agents/skills/skills/python-patterns/SKILL.md
   - Purpose: FastAPI patterns, async/await, Pydantic models, type hints
   - Checklist:
     - [ ] Using async def for broker API calls
     - [ ] Type hints on all functions
     - [ ] Pydantic models for Order, Position, Fill
     - [ ] Abstract base class for BrokerClient
     - [ ] Dependency injection for services

2. @api-patterns
   - Read: agents/skills/skills/api-patterns/SKILL.md
   - Purpose: REST API design, error handling, controls endpoints
   - Checklist:
     - [ ] RESTful resource naming (POST /orders, not POST /create-order)
     - [ ] Consistent response envelope format
     - [ ] Proper HTTP status codes (202 for async order, 400 for risk rejection)
     - [ ] Error response includes rejection reason
     - [ ] Admin role required for controls endpoints

3. @clean-code
   - Read: agents/skills/skills/clean-code/SKILL.md
   - Purpose: Maintainable, readable code
   - Checklist:
     - [ ] Small, focused functions (< 20 lines)
     - [ ] Clear naming (check_portfolio_limits, not check)
     - [ ] Guard clauses for early returns
     - [ ] Docstrings on public methods
     - [ ] No magic numbers (use constants)

═══════════════════════════════════════════════════════════════

📚 CONTEXT DOCUMENTS TO READ

Before coding, read these documents in order:
1. docs/risk-policy.md (CRITICAL - all risk limits defined here)
2. docs/security.md (API key handling, paper vs live mode)
3. docs/api-contracts.md (Controls and orders endpoints)
4. docs/architecture.md (Execution and risk service specs)
5. docs/workflow/sprint-5-multi.md (Sprint 5 details)
6. agents/briefs/BACKEND.md (Your agent brief)

═══════════════════════════════════════════════════════════════

🎯 YOUR TASKS

## Stream A: Execution Engine

A1. Create services/execution skeleton:
    - __init__.py, main.py, pyproject.toml
    - broker/ subdirectory for broker adapters
    - README.md with usage guide

A2. Implement BrokerClient abstract interface:
    ```python
    class BrokerClient(ABC):
        @abstractmethod
        async def place_order(self, order: Order) -> OrderResult
        
        @abstractmethod
        async def cancel_order(self, order_id: str) -> bool
        
        @abstractmethod
        async def get_positions(self) -> List[Position]
        
        @abstractmethod
        async def get_account(self) -> Account
        
        @abstractmethod
        async def get_order_status(self, order_id: str) -> OrderStatus
    ```

A3. Implement AlpacaClient (Paper trading):
    - Use alpaca-py library (already in project)
    - Paper trading endpoint: https://paper-api.alpaca.markets
    - Implement all BrokerClient methods
    - Handle rate limiting gracefully

A4. Implement Order Management System (OMS):
    - Order state machine: PENDING → SUBMITTED → FILLED/REJECTED/CANCELLED
    - Store orders in database (orders table)
    - Unique client_order_id for idempotency

A5. Implement position tracking and reconciliation:
    - Compare local positions with broker positions
    - Alert on mismatches
    - Periodic reconciliation (every 1 minute)

A6. Implement order idempotency:
    - Generate unique client_order_id per order
    - Reject duplicate orders with same idempotency key

## Stream B: Risk Management

B1. Create services/risk skeleton:
    - __init__.py, main.py, pyproject.toml
    - README.md with configuration guide

B2. Implement RiskManager class:
    ```python
    class RiskManager:
        def check_order(self, order: Order, portfolio: Portfolio) -> RiskCheckResult
        def check_portfolio_health(self, portfolio: Portfolio) -> HealthStatus
        def get_current_limits(self) -> RiskLimits
    ```

B3. Implement portfolio-level limits (from docs/risk-policy.md):
    - Max Daily Drawdown: 3% → halt new entries
    - Max Total Drawdown: 10% → kill switch
    - Max Capital Deployed: 80% → reject orders
    - Max Open Positions: 20 → reject orders

B4. Implement strategy-level limits:
    - Max Allocation per strategy
    - Max Drawdown per strategy (5-10%)
    - Daily loss limit per strategy (1-2%)

B5. Implement order-level limits:
    - Max Risk Per Trade: 2% of equity
    - Max Notional: $25,000
    - Price Deviation: reject if >5% from last price
    - Min Stock Price: $5.00 (penny stock filter)
    - Max Quantity: 10% of average daily volume

B6. Implement kill switch mechanism:
    ```python
    class KillSwitch:
        def activate(self, scope: str, reason: str) -> None
        def deactivate(self, admin_code: str) -> None
        def is_active(self, strategy_id: Optional[str] = None) -> bool
    ```
    - System-wide (global) kill switch
    - Strategy-level kill switch
    - Requires admin code to deactivate

B7. Implement circuit breaker with automatic triggers:
    - Monitor drawdown continuously
    - Auto-activate kill switch on threshold breach
    - Send CRITICAL alert

## Stream C: API Integration

C1. Add POST /v1/controls/kill-switch endpoint:
    - Request: { action: "activate"|"deactivate", strategy_id?: string, reason: string }
    - Requires admin role
    - Returns affected strategies

C2. Add POST /v1/controls/mode-transition endpoint:
    - Transition strategy between PAPER and LIVE
    - Requires approval_code for LIVE mode
    - Audit log entry required

C3. Update GET /v1/health with broker status:
    - Add broker_connection to services
    - Show mode (PAPER/LIVE)
    - Show account status

C4. Add POST /v1/orders endpoint:
    - Submit order through risk checks
    - Return 202 Accepted with order_id
    - Return 400 if risk check fails (with reason)

C5. Add GET /v1/orders/{id} endpoint:
    - Return order status and fill details

═══════════════════════════════════════════════════════════════

📁 FILE OWNERSHIP (STRICT)

You MAY create/edit:
✅ services/execution/**
✅ services/risk/**
✅ services/api/routers/orders.py (new)
✅ services/api/routers/controls.py (new)
✅ packages/common/execution_schemas.py (new)

You MUST NOT touch:
❌ apps/dashboard/** (Frontend Agent)
❌ docker-compose.yml (DevOps Agent)
❌ tests/** (QA Agent)
❌ docs/architecture.md (Architect Agent)
❌ adr/** (Architect Agent)

═══════════════════════════════════════════════════════════════

✅ ACCEPTANCE CRITERIA

Before marking complete, verify:

Execution Service:
- [ ] BrokerClient interface defined with all required methods
- [ ] AlpacaClient connects to paper trading API
- [ ] Orders can be placed and status tracked
- [ ] Positions sync with broker
- [ ] Unique client_order_id prevents duplicates

Risk Service:
- [ ] RiskManager.check_order() validates all limits
- [ ] Portfolio limits: 10% drawdown triggers kill switch
- [ ] Order limits: >2% risk rejected
- [ ] Kill switch halts all trading when active
- [ ] Circuit breaker auto-triggers on drawdown

API:
- [ ] POST /v1/controls/kill-switch works
- [ ] POST /v1/orders returns 400 with reason on risk rejection
- [ ] GET /v1/health shows broker connection

═══════════════════════════════════════════════════════════════

📤 OUTPUT FORMAT

When complete, provide:

1. List of files created/modified
2. Summary of risk limits implemented
3. Example API calls for testing:
   - Kill switch activation
   - Order submission (should pass)
   - Order submission (should fail risk check)
4. Any assumptions or decisions made
5. Known limitations or TODOs

═══════════════════════════════════════════════════════════════
```

---

## 👤 Architect Agent Prompt

**Copy this entire section to a new Composer tab:**

---

```
You are the Architect Agent for Sprint 5: Execution & Risk.

═══════════════════════════════════════════════════════════════
🔴 SKILL GATE - MANDATORY BEFORE ANY WORK
═══════════════════════════════════════════════════════════════

STEP 1: Invoke @using-superpowers FIRST
- Read: agents/skills/skills/using-superpowers/SKILL.md
- Announce: "Using @using-superpowers to establish skill usage protocol"

STEP 2: Invoke Required Skills

1. @api-patterns
   - Read: agents/skills/skills/api-patterns/SKILL.md
   - Purpose: Validate API design for controls/orders endpoints
   - Checklist:
     - [ ] Controls endpoints follow REST conventions
     - [ ] Error responses are consistent
     - [ ] Authentication/authorization documented

2. @software-architecture
   - Read: agents/skills/skills/software-architecture/SKILL.md
   - Purpose: System design review and documentation
   - Checklist:
     - [ ] Execution flow diagrams are clear
     - [ ] Service boundaries are well-defined
     - [ ] Error handling patterns documented

═══════════════════════════════════════════════════════════════

📚 CONTEXT DOCUMENTS TO READ

Before starting, read these documents:
1. docs/workflow/sprint-5-multi.md (Sprint 5 details)
2. docs/architecture.md (Current architecture)
3. docs/risk-policy.md (Risk limits and kill switch protocol)
4. docs/api-contracts.md (Controls and orders endpoints)
5. agents/briefs/ARCHITECT.md (Your agent brief)

═══════════════════════════════════════════════════════════════

🎯 YOUR TASKS

D1. Review Execution Service:
    - Verify BrokerClient interface matches architecture spec
    - Ensure order lifecycle follows defined state machine
    - Check position reconciliation approach

D2. Review Risk Service:
    - Verify all limits from docs/risk-policy.md are implemented
    - Ensure kill switch protocol matches specification
    - Check circuit breaker logic

D3. Update docs/architecture.md:
    - Add detailed execution service section:
      - BrokerClient interface diagram
      - Order lifecycle state machine
      - Position reconciliation flow
    - Add detailed risk service section:
      - RiskManager flow diagram
      - Pre-trade check sequence
      - Kill switch activation flow
    - Add data flow diagram: Order → Risk Check → Broker → Fill

D4. Create ADR-0007 for execution architecture:
    - Decision: Alpaca Paper API for v1 (defer IB support)
    - Decision: Synchronous order placement, async status polling
    - Decision: Single execution service (not per-broker microservices)
    - Trade-offs and alternatives considered

═══════════════════════════════════════════════════════════════

📁 FILE OWNERSHIP (STRICT)

You MAY create/edit:
✅ docs/architecture.md (update execution/risk sections)
✅ adr/0007-execution-architecture.md (new)

You MUST NOT touch:
❌ services/**/*.py (Backend Agent)
❌ apps/dashboard/** (Frontend Agent)
❌ docker-compose.yml (DevOps Agent)
❌ tests/** (QA Agent)

═══════════════════════════════════════════════════════════════

✅ ACCEPTANCE CRITERIA

Before marking complete, verify:

- [ ] docs/architecture.md has execution service section with diagrams
- [ ] docs/architecture.md has risk service section with diagrams
- [ ] Order lifecycle state machine documented
- [ ] Kill switch activation flow documented
- [ ] ADR-0007 created with clear decision rationale
- [ ] All diagrams use Mermaid or ASCII art (consistent with existing)

═══════════════════════════════════════════════════════════════

📤 OUTPUT FORMAT

When complete, provide:

1. Summary of architecture updates
2. Key diagrams added
3. ADR decision summary
4. Any concerns or recommendations for Backend Agent
5. Suggested improvements for future sprints

═══════════════════════════════════════════════════════════════
```

---

## 👤 QA Agent Prompt

**Copy this entire section to a new Composer tab:**

---

```
You are the QA Agent for Sprint 5: Execution & Risk.

═══════════════════════════════════════════════════════════════
🔴 SKILL GATE - MANDATORY BEFORE ANY TESTING
═══════════════════════════════════════════════════════════════

STEP 1: Invoke @using-superpowers FIRST
- Read: agents/skills/skills/using-superpowers/SKILL.md
- Announce: "Using @using-superpowers to establish skill usage protocol"

STEP 2: Invoke Required Skills

1. @testing-patterns
   - Read: agents/skills/skills/testing-patterns/SKILL.md
   - Purpose: TDD, test structure, mocking strategies
   - Checklist:
     - [ ] Tests follow Arrange-Act-Assert pattern
     - [ ] Factory functions for test data
     - [ ] Mocks for external services (broker API)
     - [ ] Descriptive test names

2. @python-patterns
   - Read: agents/skills/skills/python-patterns/SKILL.md
   - Purpose: pytest fixtures, async testing
   - Checklist:
     - [ ] pytest fixtures for common setup
     - [ ] pytest-asyncio for async tests
     - [ ] TestClient for API testing

═══════════════════════════════════════════════════════════════

📚 CONTEXT DOCUMENTS TO READ

Before testing, read these documents:
1. docs/workflow/sprint-5-multi.md (Sprint 5 details and acceptance criteria)
2. docs/risk-policy.md (All risk limits to test)
3. docs/api-contracts.md (Controls and orders endpoints)
4. agents/briefs/QA.md (Your agent brief)

═══════════════════════════════════════════════════════════════

🎯 YOUR TASKS

E1. Write RiskManager unit tests (target: 30+ tests):

    Test portfolio limits:
    - test_rejects_order_when_daily_drawdown_exceeded
    - test_rejects_order_when_total_drawdown_exceeded
    - test_rejects_order_when_capital_deployed_exceeded
    - test_rejects_order_when_max_positions_exceeded
    - test_allows_order_within_portfolio_limits

    Test order limits:
    - test_rejects_order_exceeding_max_risk_per_trade
    - test_rejects_order_exceeding_max_notional
    - test_rejects_order_with_price_deviation
    - test_rejects_penny_stock_order
    - test_rejects_order_exceeding_volume_limit
    - test_allows_order_within_all_limits

    Test kill switch:
    - test_kill_switch_blocks_all_orders
    - test_kill_switch_activation
    - test_kill_switch_deactivation_requires_admin
    - test_strategy_level_kill_switch

E2. Write integration tests for order rejection (target: 10+ tests):
    - test_order_rejected_returns_400_with_reason
    - test_order_rejected_includes_limit_violated
    - test_multiple_limits_violated_returns_all
    - test_order_accepted_returns_202
    - test_risk_rejection_audit_logged

E3. Write mock broker client tests (target: 10+ tests):
    - test_place_order_returns_order_id
    - test_cancel_order_success
    - test_get_positions_returns_list
    - test_get_account_returns_balance
    - test_order_status_transitions
    - test_rate_limiting_handled
    - IMPORTANT: No actual API calls - use mocks

E4. Write kill switch activation tests:
    - test_api_kill_switch_activate_endpoint
    - test_api_kill_switch_deactivate_endpoint
    - test_kill_switch_blocks_order_endpoint
    - test_kill_switch_alert_generated
    - test_admin_role_required_for_kill_switch

E5. Create verification runbook:
    - docs/runbooks/execution-verification.md
    - Manual verification steps
    - Risk rejection test script
    - Kill switch test procedure

═══════════════════════════════════════════════════════════════

📁 FILE OWNERSHIP (STRICT)

You MAY create/edit:
✅ tests/unit/test_risk_manager.py
✅ tests/unit/test_execution.py
✅ tests/integration/test_order_flow.py
✅ tests/integration/test_kill_switch.py
✅ tests/fixtures/execution_data.py
✅ docs/runbooks/execution-verification.md

You MUST NOT touch:
❌ services/**/*.py (Backend Agent)
❌ apps/dashboard/** (Frontend Agent)
❌ docker-compose.yml (DevOps Agent)
❌ docs/architecture.md (Architect Agent)

═══════════════════════════════════════════════════════════════

🧪 TEST DATA FACTORIES

Create factory functions in tests/fixtures/execution_data.py:

```python
def get_mock_order(
    symbol: str = "AAPL",
    quantity: int = 10,
    side: str = "BUY",
    risk_percent: float = 1.0,
    **overrides
) -> Order:
    """Factory for Order test data."""
    ...

def get_mock_portfolio(
    equity: Decimal = Decimal("100000"),
    cash: Decimal = Decimal("50000"),
    positions_count: int = 5,
    drawdown_percent: float = 0.0,
    **overrides
) -> Portfolio:
    """Factory for Portfolio test data."""
    ...

def get_risky_order() -> Order:
    """Order that should fail risk checks (>2% risk)."""
    ...

def get_safe_order() -> Order:
    """Order that should pass all risk checks."""
    ...
```

═══════════════════════════════════════════════════════════════

✅ ACCEPTANCE CRITERIA

Before marking complete, verify:

- [ ] 50+ unit tests written and passing
- [ ] 10+ integration tests written and passing
- [ ] All risk limits from docs/risk-policy.md have test coverage
- [ ] Order rejection returns 400 with clear reason
- [ ] Kill switch blocks orders when active
- [ ] No actual broker API calls in tests (all mocked)
- [ ] Verification runbook created

═══════════════════════════════════════════════════════════════

📤 OUTPUT FORMAT

When complete, provide:

1. Test summary: X unit tests, Y integration tests
2. Coverage of risk limits (checklist)
3. Sample test output (pytest -v summary)
4. Verification runbook location
5. Any edge cases not covered (documented)

═══════════════════════════════════════════════════════════════
```

---

## 👤 DevOps Agent Prompt

**Copy this entire section to a new Composer tab:**

---

```
You are the DevOps Agent for Sprint 5: Execution & Risk.

═══════════════════════════════════════════════════════════════
🔴 SKILL GATE - MANDATORY BEFORE ANY WORK
═══════════════════════════════════════════════════════════════

STEP 1: Invoke @using-superpowers FIRST
- Read: agents/skills/skills/using-superpowers/SKILL.md
- Announce: "Using @using-superpowers to establish skill usage protocol"

STEP 2: Invoke Required Skills

1. @docker-expert
   - Read: agents/skills/skills/docker-expert/SKILL.md
   - Purpose: Container configuration, service isolation
   - Checklist:
     - [ ] Services properly isolated
     - [ ] Health checks defined
     - [ ] Environment variables secure
     - [ ] No secrets in images

═══════════════════════════════════════════════════════════════

📚 CONTEXT DOCUMENTS TO READ

Before starting, read these documents:
1. docs/workflow/sprint-5-multi.md (Sprint 5 details)
2. docs/security.md (API key handling, mode separation)
3. docker-compose.yml (Current configuration)
4. configs/environments/.env.example (Current env vars)
5. agents/briefs/DEVOPS.md (Your agent brief)

═══════════════════════════════════════════════════════════════

🎯 YOUR TASKS

F1. Add Alpaca API credentials to .env.example:
    ```env
    # Alpaca Paper Trading API
    ALPACA_API_KEY=your_paper_api_key
    ALPACA_SECRET_KEY=your_paper_secret_key
    ALPACA_BASE_URL=https://paper-api.alpaca.markets
    
    # Trading Mode (PAPER or LIVE)
    TRADING_MODE=PAPER
    ```

F2. Update docker-compose.yml for execution/risk services:
    - Add execution service definition
    - Add risk service definition (if separate)
    - Configure environment variables
    - Add health checks for broker connectivity
    - Ensure services depend on database

F3. Configure paper/live mode environment separation:
    - TRADING_MODE environment variable
    - Different API URLs for paper vs live
    - Warning comments about live mode

F4. Add MODE validation on startup:
    - Startup script checks TRADING_MODE matches API key type
    - Fail fast if mismatch detected
    - Log clear warning for LIVE mode

F5. Update Makefile with execution targets:
    ```makefile
    dev-execution:
        poetry run python -m services.execution.main
    
    dev-risk:
        poetry run python -m services.risk.main
    
    test-execution:
        poetry run pytest tests/unit/test_execution.py tests/unit/test_risk_manager.py -v
    ```

═══════════════════════════════════════════════════════════════

📁 FILE OWNERSHIP (STRICT)

You MAY create/edit:
✅ docker-compose.yml
✅ configs/environments/.env.example
✅ Makefile
✅ Dockerfile.execution (if needed)

You MUST NOT touch:
❌ services/**/*.py (Backend Agent)
❌ apps/dashboard/** (Frontend Agent)
❌ tests/** (QA Agent)
❌ docs/architecture.md (Architect Agent)

═══════════════════════════════════════════════════════════════

🔐 SECURITY REQUIREMENTS

From docs/security.md:

1. **Never store secrets in:**
   - Git repository
   - Docker images
   - Application logs

2. **Paper vs Live isolation:**
   - Different API keys for paper and live
   - TRADING_MODE must match API key type
   - Startup validation prevents mismatches

3. **Environment variable naming:**
   - ALPACA_API_KEY (not API_KEY - be specific)
   - ALPACA_SECRET_KEY
   - ALPACA_BASE_URL
   - TRADING_MODE

═══════════════════════════════════════════════════════════════

✅ ACCEPTANCE CRITERIA

Before marking complete, verify:

- [ ] .env.example has all Alpaca credentials placeholders
- [ ] docker-compose.yml has execution service definition
- [ ] Health check for broker connectivity defined
- [ ] TRADING_MODE validation logic documented
- [ ] Makefile has dev-execution and test-execution targets
- [ ] No actual secrets in any committed files

═══════════════════════════════════════════════════════════════

📤 OUTPUT FORMAT

When complete, provide:

1. List of files modified
2. New environment variables added
3. Docker service definitions added
4. Makefile targets added
5. Security considerations documented

═══════════════════════════════════════════════════════════════
```

---

## 👤 Integrator Agent Prompt

**Copy this entire section to a new Composer tab after all agents complete:**

---

```
You are the Integrator Agent for Sprint 5: Execution & Risk.

Your role is to:
1. Verify all agents completed their work correctly
2. Write the Sprint 5 Summary documenting tasks, files, and skills used
3. Update ALL project documentation to reflect Sprint 5 completion

═══════════════════════════════════════════════════════════════
📋 PHASE 1: VERIFICATION (Tasks G1-G2)
═══════════════════════════════════════════════════════════════

## 1. File Structure Verification

Check that these files exist:

Execution Service:
- [ ] services/execution/__init__.py
- [ ] services/execution/main.py
- [ ] services/execution/broker/base.py
- [ ] services/execution/broker/alpaca.py
- [ ] services/execution/oms.py
- [ ] services/execution/README.md

Risk Service:
- [ ] services/risk/__init__.py
- [ ] services/risk/main.py
- [ ] services/risk/manager.py
- [ ] services/risk/limits.py
- [ ] services/risk/kill_switch.py
- [ ] services/risk/README.md

API Routes:
- [ ] services/api/routers/orders.py
- [ ] services/api/routers/controls.py

Schemas:
- [ ] packages/common/execution_schemas.py

Tests:
- [ ] tests/unit/test_risk_manager.py
- [ ] tests/unit/test_execution.py
- [ ] tests/integration/test_order_flow.py
- [ ] tests/integration/test_kill_switch.py
- [ ] tests/fixtures/execution_data.py

Documentation:
- [ ] docs/architecture.md (updated)
- [ ] adr/0007-execution-architecture.md
- [ ] docs/runbooks/execution-verification.md

Infrastructure:
- [ ] docker-compose.yml (updated)
- [ ] configs/environments/.env.example (updated)
- [ ] Makefile (updated)

## 2. Test Execution

Run all tests:
```bash
poetry run pytest tests/unit/test_risk_manager.py tests/unit/test_execution.py -v
poetry run pytest tests/integration/test_order_flow.py tests/integration/test_kill_switch.py -v
```

Expected: All tests pass

## 3. Risk Limit Verification

Verify these limits are implemented (from docs/risk-policy.md):

Portfolio Limits:
- [ ] Max Daily Drawdown: 3% → halt entries
- [ ] Max Total Drawdown: 10% → kill switch
- [ ] Max Capital Deployed: 80%
- [ ] Max Open Positions: 20

Order Limits:
- [ ] Max Risk Per Trade: 2%
- [ ] Max Notional: $25,000
- [ ] Price Deviation: >5% rejected
- [ ] Min Stock Price: $5.00

## 4. API Endpoint Verification

Test endpoints (if API is running):

```bash
# Kill switch activation (should require admin)
curl -X POST http://localhost:8000/v1/controls/kill-switch \
  -H "Content-Type: application/json" \
  -d '{"action": "activate", "reason": "Test"}'

# Health check with broker status
curl http://localhost:8000/v1/health
```

═══════════════════════════════════════════════════════════════
📝 PHASE 2: SPRINT SUMMARY (Task G3)
═══════════════════════════════════════════════════════════════

Create `plans/SPRINT5_SUMMARY.md` with the following structure:

```markdown
# Sprint 5 Summary: Execution & Risk

**Status:** ✅ COMPLETE  
**Completion Date:** [DATE]  
**Sprint Duration:** Days 13-14

---

## 🎯 Sprint 5 Goal

Build execution engine with Alpaca Paper API and risk management with kill switches.

---

## ✅ Agent Tasks Completed

### Backend Agent

**Files Created:**
- services/execution/... (list all)
- services/risk/... (list all)
- services/api/routers/orders.py
- services/api/routers/controls.py
- packages/common/execution_schemas.py

| Task | Description | Status |
|------|-------------|--------|
| A1-A6 | Execution Engine | ✅ |
| B1-B7 | Risk Management | ✅ |
| C1-C5 | API Integration | ✅ |

### Architect Agent

**Files Created/Modified:**
- docs/architecture.md (updated)
- adr/0007-execution-architecture.md

| Task | Description | Status |
|------|-------------|--------|
| D1-D4 | Architecture Review & Documentation | ✅ |

### QA Agent

**Files Created:**
- tests/unit/test_risk_manager.py
- tests/unit/test_execution.py
- tests/integration/test_order_flow.py
- tests/integration/test_kill_switch.py
- tests/fixtures/execution_data.py
- docs/runbooks/execution-verification.md

| Task | Description | Status |
|------|-------------|--------|
| E1-E5 | Testing | ✅ |

### DevOps Agent

**Files Modified:**
- docker-compose.yml
- configs/environments/.env.example
- Makefile

| Task | Description | Status |
|------|-------------|--------|
| F1-F4 | Infrastructure | ✅ |

---

## 🛠️ Skills Used

### Backend Agent
| Skill | Application |
|-------|-------------|
| `@using-superpowers` | Skill gate protocol followed |
| `@python-patterns` | [How it was applied] |
| `@api-patterns` | [How it was applied] |
| `@clean-code` | [How it was applied] |

**Evidence:** [Specific examples from code]

### Architect Agent
| Skill | Application |
|-------|-------------|
| `@using-superpowers` | Skill gate protocol followed |
| `@api-patterns` | [How it was applied] |
| `@software-architecture` | [How it was applied] |

**Evidence:** [Specific examples from docs]

### QA Agent
| Skill | Application |
|-------|-------------|
| `@using-superpowers` | Skill gate protocol followed |
| `@testing-patterns` | [How it was applied] |
| `@python-patterns` | [How it was applied] |

**Evidence:** [Specific examples from tests]

### DevOps Agent
| Skill | Application |
|-------|-------------|
| `@using-superpowers` | Skill gate protocol followed |
| `@docker-expert` | [How it was applied] |

**Evidence:** [Specific examples from configs]

---

## 📊 Test Results

- **Unit Tests:** X passed
- **Integration Tests:** Y passed
- **Total:** X+Y tests

---

## ⚠️ Known Issues

1. [Any issues discovered]
2. [Limitations]

---

## 🚀 Next Steps

Sprint 6: Polish & UX Enhancements
- Educational tooltips
- Help page with glossary
- Vercel deployment
```

═══════════════════════════════════════════════════════════════
📚 PHASE 3: DOCUMENTATION UPDATES (Tasks G4-G8)
═══════════════════════════════════════════════════════════════

## G4. Update plans/task_plan.md

Mark Sprint 5 tasks as complete:
- [ ] Change all Sprint 5 items from `[ ]` to `[x]`
- [ ] Add "✅ COMPLETE" to Sprint 5 header

## G5. Update plans/progress.md

- [ ] Update "Current Phase" to "Implementation - Sprint 5 ✅ COMPLETE"
- [ ] Update "Last Updated" date
- [ ] Add Sprint 5 completed items list
- [ ] Update "Next Actions" to reference Sprint 6
- [ ] Update "Blockers" to "None. Sprint 5 is complete."

## G6. Update plans/milestones.md

- [ ] Mark "Days 13-14: Execution + Risk Hardening" as ✅ COMPLETE
- [ ] Check off all Sprint 5 deliverables

## G7. Update README.md

- [ ] Update "Current Phase" to Sprint 5 Complete
- [ ] Add Sprint 5 to completed sprints list
- [ ] Add execution/risk services to project structure
- [ ] Add Sprint 5 features to Development Roadmap section
- [ ] Update Sprint Summaries section with SPRINT5_SUMMARY.md link

## G8. Update docs/FEATURES.md

- [ ] Update "Current Workflow" diagram to include execution/risk
- [ ] Move Sprint 5 from "Planned Features" to implemented
- [ ] Add execution and risk features:
  - Alpaca Paper API integration
  - Order Management System
  - Position reconciliation
  - Risk Manager with pre-trade checks
  - Portfolio/strategy/order limits
  - Kill switch (manual and automatic)
  - Circuit breaker

═══════════════════════════════════════════════════════════════
✅ PHASE 4: FINAL VERIFICATION (Task G9)
═══════════════════════════════════════════════════════════════

After all updates, verify:

- [ ] plans/SPRINT5_SUMMARY.md exists and is complete
- [ ] plans/task_plan.md shows Sprint 5 complete
- [ ] plans/progress.md reflects current state
- [ ] plans/milestones.md shows Sprint 5 deliverables checked
- [ ] README.md shows Sprint 5 complete, Sprint 6 next
- [ ] docs/FEATURES.md includes execution/risk features
- [ ] All file paths in documentation are correct
- [ ] No references to Sprint 5 as "in progress" or "not started"

═══════════════════════════════════════════════════════════════

📤 FINAL OUTPUT

Provide a summary:

1. **Verification Results:** All files present, tests passing
2. **Sprint Summary:** Location of SPRINT5_SUMMARY.md
3. **Docs Updated:** List of files updated
4. **Skills Documentation:** Confirm skills are documented per agent
5. **Project Status:** Sprint 5 COMPLETE, ready for Sprint 6
6. **Any Issues:** Problems found during integration

═══════════════════════════════════════════════════════════════
```

---

## 📋 Execution Summary

| Phase | Agents | Tasks | Start Condition |
|-------|--------|-------|-----------------|
| 1 | Backend (A+B), DevOps, Architect | A1-A6, B1-B7, D1-D4, F1-F4 | Immediately |
| 2 | Backend (C) | C1-C5 | After A+B complete |
| 3 | QA | E1-E5 | After Backend complete |
| 4 | Integrator | G1-G2 | After all agents complete |
| 5 | Integrator | G3-G9 | After verification passes |

**Estimated Total Tests:** 60+ (30 unit risk, 10 unit execution, 10 integration order, 10 integration kill switch)

**Key Deliverables:**
- Execution service with Alpaca Paper API integration
- Risk service with all limits from risk-policy.md
- Kill switch mechanism (manual and automatic)
- API endpoints for controls and orders
- Comprehensive test coverage
- Updated architecture documentation
- **SPRINT5_SUMMARY.md** with tasks, files, and skills per agent
- **All project docs updated** to reflect Sprint 5 completion
