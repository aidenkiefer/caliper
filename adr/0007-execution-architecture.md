# 7. Execution Architecture Decisions

date: 2026-01-26
status: accepted

## Context

Sprint 5 introduces the execution engine (`services/execution`) and risk management (`services/risk`) services. These services enable paper trading with Alpaca Paper API and comprehensive risk controls.

We needed to decide:
1. Which broker API to use for v1 (Alpaca vs Interactive Brokers vs others)
2. How to structure the execution service (single service vs per-broker microservices)
3. Order placement pattern (synchronous vs asynchronous)
4. How to handle order status updates (polling vs webhooks)

**Requirements:**
- Paper trading support (no real money at risk)
- Order lifecycle tracking (pending → filled/rejected/cancelled)
- Position reconciliation with broker
- Order idempotency (prevent duplicate submissions)
- Integration with risk management service

## Decision

### Decision 1: Alpaca Paper API for v1

We will use **Alpaca Paper Trading API** as the sole broker integration for v1.

**Implementation:**
- `services/execution/broker/alpaca.py` - `AlpacaClient` implementing `BrokerClient` interface
- Paper trading endpoint: `https://paper-api.alpaca.markets`
- Library: `alpaca-py` (official Alpaca Python SDK)
- Interactive Brokers support deferred to v2

### Decision 2: Single Execution Service (Not Per-Broker Microservices)

We will implement a **single execution service** (`services/execution`) that supports multiple brokers via the adapter pattern.

**Architecture:**
- `BrokerClient` abstract base class defines interface
- `AlpacaClient` implements interface for Alpaca
- Future: `IBClient` can be added without changing service structure
- OMS (Order Management System) tracks orders regardless of broker

**Rationale:**
- Simpler deployment (one service vs multiple)
- Shared OMS logic (order state machine, position tracking)
- Easier testing (mock broker clients)
- Broker abstraction allows switching brokers without code changes

### Decision 3: Synchronous Order Placement, Async Status Polling

We will use **synchronous order placement** with **asynchronous status polling**.

**Pattern:**
- `place_order()` blocks until broker confirms order submission (returns `order_id`)
- Order state transitions: `PENDING` → `SUBMITTED` immediately after `place_order()` returns
- Background task polls `get_order_status()` every 5 seconds to update state
- Order state transitions: `SUBMITTED` → `FILLED`/`REJECTED`/`CANCELLED` via polling

**Rationale:**
- Immediate feedback on submission success/failure
- Non-blocking status updates (doesn't hold request thread)
- Simpler than webhooks (no webhook endpoint management)
- Polling interval (5s) acceptable for Risk Level 6 trading

## Rationale

### Why Alpaca Paper API?

1. **Paper Trading Support**: Alpaca provides a full-featured paper trading API that mirrors live trading
2. **Developer-Friendly**: Well-documented REST API, official Python SDK (`alpaca-py`)
3. **No Real Money Risk**: Paper trading eliminates financial risk during development
4. **Free**: Paper trading API is free (no commission, no account minimum)
5. **Sufficient for v1**: Supports market and limit orders, position tracking, account info

### Why Not Interactive Brokers (IB)?

1. **Complexity**: IB API (`ib_insync`) requires TWS/Gateway running, more complex setup
2. **Paper Trading**: IB paper trading requires TWS login, less automated
3. **Deferred to v2**: Can add IB support later via same `BrokerClient` interface
4. **Alpaca Sufficient**: Alpaca meets v1 requirements (paper trading, order execution)

### Why Single Service vs Microservices?

1. **Simplicity**: One service to deploy, monitor, and maintain
2. **Shared Logic**: OMS (order state machine, position tracking) shared across brokers
3. **Adapter Pattern**: Broker abstraction allows multiple brokers without service proliferation
4. **Scaling**: Can scale execution service horizontally if needed (not broker-specific)

**Alternative Considered:** Per-broker microservices (`execution-alpaca`, `execution-ib`)
- **Rejected because**: Adds deployment complexity, duplicate OMS logic, harder to test

### Why Synchronous Placement + Async Polling?

1. **Immediate Feedback**: `place_order()` returns immediately with success/failure
2. **Non-Blocking Status**: Status updates don't block request threads
3. **Simplicity**: No webhook infrastructure needed (no webhook endpoint, SSL certs, etc.)
4. **Acceptable Latency**: 5-second polling sufficient for Risk Level 6 trading (not HFT)

**Alternatives Considered:**

1. **Fully Asynchronous Order Placement**
   - **Approach**: `place_order()` returns immediately, status via webhook/polling
   - **Rejected because**: More complex error handling, harder to debug

2. **Webhook-Based Status Updates**
   - **Approach**: Broker calls webhook when order fills
   - **Rejected because**: Requires webhook endpoint, SSL certificates, public URL (complexity)

3. **Blocking Status Polling**
   - **Approach**: `place_order()` polls until fill/rejection
   - **Rejected because**: Blocks request thread, poor scalability

## Consequences

### Positive

- **Simple Integration**: Alpaca API is straightforward, well-documented
- **Paper Trading Safety**: No real money at risk during development
- **Broker Abstraction**: `BrokerClient` interface allows adding IB later without code changes
- **Immediate Feedback**: Synchronous placement provides instant success/failure
- **Non-Blocking**: Async polling doesn't block request threads

### Negative

- **Single Broker**: Only Alpaca supported in v1 (IB deferred)
- **Polling Overhead**: Status polling every 5 seconds adds API calls (acceptable for v1)
- **Status Latency**: Up to 5 seconds delay between fill and status update (acceptable for Risk Level 6)
- **Vendor Lock-in Risk**: Alpaca-specific features may leak into code (mitigated by `BrokerClient` abstraction)

### Neutral

- **Scaling**: Single service can scale horizontally if needed
- **Testing**: Mock `BrokerClient` implementations easy to create for testing

## Alternatives Considered

### 1. Interactive Brokers for v1
**Approach:** Use IB API (`ib_insync`) instead of Alpaca  
**Rejected because:**
- More complex setup (TWS/Gateway required)
- Less automated paper trading
- Alpaca sufficient for v1 requirements

### 2. Per-Broker Microservices
**Approach:** Separate services (`execution-alpaca`, `execution-ib`)  
**Rejected because:**
- Duplicate OMS logic across services
- More complex deployment and monitoring
- Adapter pattern achieves same goal with less complexity

### 3. Webhook-Based Status Updates
**Approach:** Broker calls webhook when order status changes  
**Rejected because:**
- Requires webhook endpoint with public URL
- SSL certificate management
- More complex error handling (webhook failures)
- Polling sufficient for v1 (5s latency acceptable)

### 4. Fully Asynchronous Order Placement
**Approach:** `place_order()` returns immediately, status via callback  
**Rejected because:**
- More complex error handling
- Harder to debug (no immediate feedback)
- Synchronous placement provides better developer experience

## Implementation Notes

### Order Idempotency

Every order must include a unique `client_order_id`:
- Format: `{strategy_id}-{timestamp}-{uuid}`
- Prevents duplicate submissions on retry
- Broker validates uniqueness (rejects duplicates)

### Position Reconciliation

- Periodic reconciliation every 1 minute
- Compare local positions (database) vs broker positions (API)
- Alert on mismatches, pause trading until resolved

### Error Handling

- Network errors: Retry with exponential backoff (max 3 retries)
- Rate limiting: Respect Alpaca API limits (200 req/min), queue requests if needed
- Invalid orders: Return clear error messages to caller

## Future Considerations

When these requirements emerge, consider:

1. **Interactive Brokers Support**
   - Add `IBClient` implementing `BrokerClient` interface
   - No changes to OMS or service structure needed

2. **Webhook-Based Status Updates**
   - If sub-second status updates needed (HFT)
   - Requires webhook endpoint infrastructure

3. **Multi-Broker Support**
   - Allow strategies to specify broker preference
   - Route orders to appropriate broker client

4. **Order Routing**
   - Smart order routing across brokers
   - Best execution logic

## Related Decisions

- ADR-0001: Monorepo Organization (service structure)
- ADR-0003: FastAPI Backend (API integration)
- `docs/risk-policy.md`: Risk limits and kill switch protocol
- `docs/api-contracts.md`: Order submission endpoints
