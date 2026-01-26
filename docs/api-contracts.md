# API Contracts - FastAPI Backend Specification

## Summary

This document defines all REST API endpoints for the quantitative ML trading platform backend. The FastAPI service sits between the Python trading services and the Next.js dashboard, aggregating data and providing a clean HTTP interface.

**Base URL:** `https://api.quant-platform.com/v1` (production)  
**Local Dev:** `http://localhost:8000/v1`

**Design Principles:**
- **RESTful:** Resource-oriented endpoints with standard HTTP verbs
- **Versioned:** `/v1` prefix for API versioning
- **JSON:** All requests and responses use JSON with snake_case
- **Paginated:** List endpoints support pagination
- **Typed:** Pydantic models for request/response validation
- **Documented:** Auto-generated OpenAPI/Swagger docs at `/docs`

---

## Key Decisions

### ✅ FastAPI Framework
**Decision:** Use FastAPI for API layer  
**Rationale:**
- Built-in Pydantic validation
- Auto-generated OpenAPI documentation
- Excellent performance (async/await support)
- Type safety (Python 3.11+ type hints)

### ✅ API Versioning via URL Path
**Decision:** Version in path (`/v1/`, `/v2/`) rather than headers  
**Rationale:**
- Simpler for clients (can test multiple versions side-by-side)
- Clear in logs and monitoring

### ✅ Token-Based Authentication
**Decision:** JWT tokens for authentication  
**Rationale:**
- Stateless (no server session storage)
- Can embed user claims (user_id, roles)
- Compatible with NextAuth.js on frontend

### ✅ Rate Limiting
**Decision:** Rate limit by API key/user  
**Rationale:**
- Protect against abuse
- Fair usage across strategies
- Use slowapi library for FastAPI

---

## Authentication

### Endpoint: `POST /v1/auth/login`

**Request:**
```json
{
  "email": "user@example.com",
  "password": "********"
}
```

**Response (Success - 200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**Response (Error - 401):**
```json
{
  "detail": "Invalid credentials"
}
```

### Endpoint: `POST /v1/auth/refresh`

**Headers:**
```
Authorization: Bearer {refresh_token}
```

**Response (200):**
```json
{
  "access_token": "new_token...",
  "expires_in": 3600
}
```

### Protected Endpoints

All endpoints except `/auth/*` require:
```
Authorization: Bearer {access_token}
```

---

## Metrics & Summary

### Endpoint: `GET /v1/metrics/summary`

Aggregate metrics across all strategies for dashboard overview.

**Query Parameters:**
- `period` (optional): `1d`, `1w`, `1m`, `3m`, `1y`, `all` (default: `1m`)
- `mode` (optional): `PAPER | LIVE` (default: includes both)

**Response (200):**
```json
{
  "data": {
    "total_pnl": "12345.67",
    "total_pnl_percent": "15.23",
    "sharpe_ratio": "1.85",
    "max_drawdown": "-8.45",
    "win_rate": "0.58",
    "total_trades": 142,
    "active_positions": 8,
    "capital_deployed": "45000.00",
    "available_capital": "55000.00",
    "equity_curve": [
      {"date": "2026-01-01", "value": "100000.00"},
      {"date": "2026-01-02", "value": "101234.56"},
      ...
    ]
  },
  "meta": {
    "period": "1m",
    "updated_at": "2026-01-25T22:30:00Z"
  }
}
```

---

## Strategies

### Endpoint: `GET /v1/strategies`

List all configured strategies.

**Query Parameters:**
- `status` (optional): `active | inactive | all` (default: `all`)
- `mode` (optional): `BACKTEST | PAPER | LIVE`

**Response (200):**
```json
{
  "data": [
    {
      "strategy_id": "momentum_v1",
      "name": "Momentum Strategy V1",
      "description": "XGBoost-based momentum trading on S&P 500 stocks",
      "status": "active",
      "mode": "PAPER",
      "universe_size": 50,
      "max_positions": 10,
      "risk_per_trade_pct": "1.5",
      "created_at": "2026-01-15T10:00:00Z",
      "updated_at": "2026-01-25T08:00:00Z"
    },
    ...
  ],
  "meta": {
    "total_count": 5,
    "active_count": 3
  }
}
```

### Endpoint: `GET /v1/strategies/{strategy_id}`

Get details for a specific strategy.

**Response (200):**
```json
{
  "data": {
    "strategy_id": "momentum_v1",
    "name": "Momentum Strategy V1",
    "description": "...",
    "status": "active",
    "config": {
      "model_type": "xgboost",
      "features": ["rsi_14", "macd", "volume_sma_20"],
      "signal_threshold": 0.6,
      "stop_loss_pct": "2.0",
      "take_profit_pct": "5.0"
    },
    "performance": {
      "total_pnl": "2345.67",
      "sharpe_ratio": "2.1",
      "max_drawdown": "-5.2",
      "win_rate": "0.62"
    }
  }
}
```

### Endpoint: `PATCH /v1/strategies/{strategy_id}`

Update strategy configuration (e.g., enable/disable, adjust risk parameters).

**Request:**
```json
{
  "status": "inactive",  // or "active"
  "config": {
    "risk_per_trade_pct": "1.0"  // Reduce risk
  }
}
```

**Response (200):**
```json
{
  "message": "Strategy updated successfully",
  "data": {
    "strategy_id": "momentum_v1",
    "status": "inactive",
    ...
  }
}
```

**Authorization:** Requires `admin` role or strategy owner.

---

## Positions

### Endpoint: `GET /v1/positions`

List current open positions across all strategies.

**Query Parameters:**
- `strategy_id` (optional): Filter by strategy
- `symbol` (optional): Filter by symbol
- `mode` (optional): `PAPER | LIVE`
- `page` (optional): Page number (default: 1)
- `per_page` (optional): Items per page (default: 20, max: 100)

**Response (200):**
```json
{
  "data": [
    {
      "position_id": "uuid-123",
      "strategy_id": "momentum_v1",
      "symbol": "AAPL",
      "contract_type": "STOCK",
      "quantity": "100.00",
      "average_entry_price": "150.25",
      "current_price": "155.80",
      "unrealized_pnl": "555.00",
      "unrealized_pnl_pct": "3.69",
      "market_value": "15580.00",
      "opened_at": "2026-01-20T14:30:00Z",
      "days_held": 5
    },
    ...
  ],
  "meta": {
    "total_count": 8,
    "page": 1,
    "per_page": 20,
    "total_unrealized_pnl": "1234.56"
  }
}
```

### Endpoint: `GET /v1/positions/{position_id}`

Get detailed information for a specific position.

**Response (200):**
```json
{
  "data": {
    "position_id": "uuid-123",
    "strategy_id": "momentum_v1",
    "symbol": "AAPL",
    "quantity": "100.00",
    "entry_orders": [
      {
        "order_id": "uuid-456",
        "filled_at": "2026-01-20T14:30:00Z",
        "quantity": "100.00",
        "price": "150.25"
      }
    ],
    "unrealized_pnl": "555.00",
    "risk_metrics": {
      "stop_loss_price": "147.25",
      "take_profit_price": "157.76",
      "max_loss": "-300.00",
      "max_profit": "751.00"
    }
  }
}
```

---

## Orders

### Endpoint: `GET /v1/orders`

List orders (recent first).

**Query Parameters:**
- `strategy_id` (optional)
- `status` (optional): `PENDING | SUBMITTED | FILLED | CANCELLED | REJECTED`
- `mode` (optional): `BACKTEST | PAPER | LIVE`
- `from_date` (optional): ISO 8601 date
- `to_date` (optional): ISO 8601 date
- `page`, `per_page`

**Response (200):**
```json
{
  "data": [
    {
      "order_id": "uuid-789",
      "strategy_id": "momentum_v1",
      "symbol": "MSFT",
      "side": "BUY",
      "quantity": "50.00",
      "order_type": "LIMIT",
      "limit_price": "380.00",
      "status": "FILLED",
      "filled_quantity": "50.00",
      "average_fill_price": "379.85",
      "fees": "1.25",
      "submitted_at": "2026-01-25T10:00:00Z",
      "filled_at": "2026-01-25T10:02:15Z"
    },
    ...
  ],
  "meta": {
    "total_count": 142,
    "page": 1,
    "per_page": 20
  }
}
```

---

## Runs (Backtests & Live Sessions)

### Endpoint: `GET /v1/runs`

List strategy runs (backtests, paper trading sessions, live sessions).

**Query Parameters:**
- `strategy_id` (optional)
- `run_type` (optional): `BACKTEST | PAPER | LIVE`
- `status` (optional): `RUNNING | COMPLETED | FAILED`
- `page`, `per_page`

**Response (200):**
```json
{
  "data": [
    {
      "run_id": "uuid-abc",
      "strategy_id": "momentum_v1",
      "run_type": "BACKTEST",
      "start_date": "2024-01-01",
      "end_date": "2025-12-31",
      "total_return": "18.45",
      "sharpe_ratio": "2.15",
      "max_drawdown": "-9.23",
      "total_trades": 87,
      "status": "COMPLETED",
      "report_url": "https://s3.../reports/uuid-abc.html",
      "created_at": "2026-01-24T12:00:00Z",
      "completed_at": "2026-01-24T12:15:30Z"
    },
    ...
  ],
  "meta": {
    "total_count": 24,
    "page": 1,
    "per_page": 20
  }
}
```

### Endpoint: `POST /v1/runs`

Trigger a new backtest run.

**Request:**
```json
{
  "strategy_id": "momentum_v1",
  "start_date": "2024-01-01",
  "end_date": "2025-12-31",
  "initial_capital": "100000.00"
}
```

**Response (202 Accepted):**
```json
{
  "message": "Backtest started",
  "data": {
    "run_id": "uuid-new",
    "status": "RUNNING",
    "estimated_completion": "2026-01-25T22:45:00Z"
  }
}
```

### Endpoint: `GET /v1/runs/{run_id}`

Get detailed run results.

**Response (200):**
```json
{
  "data": {
    "run_id": "uuid-abc",
    "strategy_id": "momentum_v1",
    "metrics": {
      "total_return": "18.45",
      "cagr": "17.82",
      "sharpe_ratio": "2.15",
      "sortino_ratio": "2.87",
      "max_drawdown": "-9.23",
      "win_rate": "0.61",
      "profit_factor": "2.34",
      "total_trades": 87,
      "avg_trade_duration_hours": "72.50"
    },
    "equity_curve": [...],
    "trades": [...]  // Full trade history
  }
}
```

---

## Alerts

### Endpoint: `GET /v1/alerts`

List recent alerts (kill switch triggers, system errors, etc.).

**Query Parameters:**
- `severity` (optional): `INFO | WARNING | ERROR | CRITICAL`
- `acknowledged` (optional): `true | false`
- `from_date`, `to_date`
- `page`, `per_page`

**Response (200):**
```json
{
  "data": [
    {
      "alert_id": "uuid-alert",
      "severity": "CRITICAL",
      "message": "Kill switch triggered: Max drawdown exceeded -10%",
      "context": {
        "strategy_id": "momentum_v1",
        "current_drawdown": "-10.5",
        "threshold": "-10.0"
      },
      "acknowledged": false,
      "created_at": "2026-01-25T15:30:00Z"
    },
    ...
  ],
  "meta": {
    "total_count": 5,
    "unacknowledged_count": 2
  }
}
```

### Endpoint: `PATCH /v1/alerts/{alert_id}/acknowledge`

Mark alert as acknowledged.

**Response (200):**
```json
{
  "message": "Alert acknowledged",
  "data": {
    "alert_id": "uuid-alert",
    "acknowledged": true,
    "acknowledged_at": "2026-01-25T22:35:00Z"
  }
}
```

---

## Controls (Admin Actions)

### Endpoint: `POST /v1/controls/kill-switch`

Manually trigger or release kill switch for a strategy or globally.

**Request:**
```json
{
  "action": "activate",  // or "deactivate"
  "strategy_id": "momentum_v1",  // optional, omit for global
  "reason": "Manual intervention due to unusual market volatility"
}
```

**Response (200):**
```json
{
  "message": "Kill switch activated for momentum_v1",
  "data": {
    "kill_switch_active": true,
    "affected_strategies": ["momentum_v1"],
    "activated_at": "2026-01-25T22:35:00Z"
  }
}
```

**Authorization:** Requires `admin` role.

### Endpoint: `POST /v1/controls/mode-transition`

Transition a strategy between paper and live mode.

**Request:**
```json
{
  "strategy_id": "momentum_v1",
  "from_mode": "PAPER",
  "to_mode": "LIVE",
  "approval_code": "ABC123"  // Human approval checkpoint
}
```

**Response (200):**
```json
{
  "message": "Strategy transitioned to LIVE mode",
  "data": {
    "strategy_id": "momentum_v1",
    "mode": "LIVE",
    "transitioned_at": "2026-01-25T22:35:00Z"
  }
}
```

**Authorization:** Requires `admin` role and valid approval code.

---

## System Health

### Endpoint: `GET /v1/health`

Overall system health check.

**Response (200):**
```json
{
  "status": "healthy",  // or "degraded", "unhealthy"
  "services": {
    "database": {
      "status": "healthy",
      "latency_ms": 12
    },
    "data_feed": {
      "status": "healthy",
      "last_update": "2026-01-25T22:34:50Z",
      "staleness_seconds": 10
    },
    "broker_connection": {
      "status": "healthy",
      "broker": "alpaca",
      "mode": "PAPER"
    },
    "redis": {
      "status": "healthy"
    }
  },
  "timestamp": "2026-01-25T22:35:00Z"
}
```

### Endpoint: `GET /v1/health/services/{service_name}`

Detailed health check for a specific service.

---

## Error Handling

### Standard Error Response Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request parameters",
    "details": [
      {
        "field": "quantity",
        "message": "Quantity must be positive"
      }
    ]
  },
  "request_id": "req-uuid" // For debugging
}
```

### HTTP Status Codes
- `200 OK` - Success
- `201 Created` - Resource created
- `202 Accepted` - Async operation started
- `400 Bad Request` - Invalid input
- `401 Unauthorized` - Missing or invalid token
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `409 Conflict` - Resource conflict (e.g., duplicate strategy ID)
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server error
- `503 Service Unavailable` - System maintenance or degraded

---

## Rate Limiting

**Limits:**
- **Dashboard endpoints** (`/metrics`, `/strategies`, `/positions`): 100 requests/minute
- **Admin controls** (`/controls/*`): 10 requests/minute
- **Backtest triggers** (`POST /runs`): 5 requests/minute

**Headers:**
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1706227200  // Unix timestamp
```

**Error (429):**
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests. Try again in 42 seconds.",
    "retry_after": 42
  }
}
```

---

## Interfaces / Contracts

### Request/Response Models (Pydantic)

All models defined in `packages/common/api_schemas.py`:
```python
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

class MetricsSummaryResponse(BaseModel):
    data: MetricsSummaryData
    meta: MetaSummary

class MetricsSummaryData(BaseModel):
    total_pnl: Decimal
    total_pnl_percent: Decimal
    sharpe_ratio: Decimal
    max_drawdown: Decimal
    ...
```

### OpenAPI Specification

Auto-generated at `/openapi.json`  
Interactive docs at `/docs` (Swagger UI)  
Alternative docs at `/redoc`

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| **API abuse** (excessive requests) | Rate limiting per user/API key |
| **Unauthorized access** (leaked tokens) | Short-lived JWTs, token rotation, IP whitelisting |
| **Stale data** (cache inconsistency) | Cache TTL ≤ 5 seconds, WebSocket for real-time (v2) |
| **Slow queries** (dashboard lag) | Database indexes, query optimization, pagination |
| **Breaking changes** (frontend breaks) | API versioning, deprecation notices |

---

## Open Questions

1. **WebSockets for Real-Time:** When to upgrade from polling to WebSockets?
2. **GraphQL Alternative:** Would GraphQL reduce over-fetching for complex dashboard queries?
3. **API Gateway:** Use Kong/AWS API Gateway or keep FastAPI standalone?
4. **Multi-Tenancy:** How to isolate data if supporting multiple users?
5. **Audit Logging:** Log all admin actions (controls, mode transitions)?

---

## Next Steps

1. Implement FastAPI app structure with routers
2. Create Pydantic models for all request/response schemas
3. Set up JWT authentication with NextAuth.js integration
4. Configure rate limiting with slowapi
5. Write OpenAPI spec documentation
