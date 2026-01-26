# API Verification Runbook

## Overview

This runbook provides procedures for verifying the FastAPI backend is functioning correctly. Use this for deployment verification, troubleshooting, and routine health checks.

## Prerequisites

- Python 3.11+ installed
- Poetry installed
- API dependencies installed: `poetry install`
- Docker running (if using containerized services)

## Quick Verification Commands

### Run All API Tests

```bash
# Run all API unit tests
poetry run pytest services/api/test_*.py -v

# Run with coverage report
poetry run pytest services/api/test_*.py --cov=services/api --cov-report=term-missing

# Run integration tests
poetry run pytest tests/integration/test_api_e2e.py -v

# Run all tests together
poetry run pytest services/api/test_*.py tests/integration/test_api_e2e.py -v
```

### Start the API Server

```bash
# Start development server
poetry run uvicorn services.api.main:app --reload --port 8000

# Start production server
poetry run uvicorn services.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## Manual Verification Procedures

### 1. Health Check

**Purpose:** Verify the API is running and all services are healthy.

```bash
# Check health endpoint
curl -X GET http://localhost:8000/v1/health

# Expected response (status 200):
{
  "status": "healthy",
  "services": {
    "database": {"status": "healthy", "latency_ms": 12},
    "data_feed": {"status": "healthy", "staleness_seconds": 10},
    "broker_connection": {"status": "healthy", "broker": "alpaca", "mode": "PAPER"},
    "redis": {"status": "healthy"}
  },
  "timestamp": "2026-01-26T10:00:00Z"
}
```

**Success Criteria:**
- Status code is 200
- `status` is "healthy" or "degraded"
- All expected services are listed
- Timestamp is recent

---

### 2. Metrics Summary

**Purpose:** Verify metrics aggregation is working.

```bash
# Get metrics with default period
curl -X GET http://localhost:8000/v1/metrics/summary

# Get metrics with specific period
curl -X GET "http://localhost:8000/v1/metrics/summary?period=1w"

# Get metrics for specific mode
curl -X GET "http://localhost:8000/v1/metrics/summary?mode=PAPER"
```

**Expected Response:**
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
    "equity_curve": [...]
  },
  "meta": {
    "period": "1m",
    "updated_at": "2026-01-26T10:00:00Z"
  }
}
```

---

### 3. Strategies

**Purpose:** Verify strategy CRUD operations.

```bash
# List all strategies
curl -X GET http://localhost:8000/v1/strategies

# List active strategies only
curl -X GET "http://localhost:8000/v1/strategies?status=active"

# Get strategy details
curl -X GET http://localhost:8000/v1/strategies/momentum_v1

# Update strategy status
curl -X PATCH http://localhost:8000/v1/strategies/momentum_v1 \
  -H "Content-Type: application/json" \
  -d '{"status": "inactive"}'

# Update strategy config
curl -X PATCH http://localhost:8000/v1/strategies/momentum_v1 \
  -H "Content-Type: application/json" \
  -d '{"config": {"signal_threshold": 0.75}}'
```

**Verify 404 handling:**
```bash
curl -X GET http://localhost:8000/v1/strategies/nonexistent-strategy
# Expected: 404 status with detail message
```

---

### 4. Runs (Backtests)

**Purpose:** Verify backtest run operations.

```bash
# List all runs
curl -X GET http://localhost:8000/v1/runs

# Filter by strategy
curl -X GET "http://localhost:8000/v1/runs?strategy_id=momentum_v1"

# Filter by type and status
curl -X GET "http://localhost:8000/v1/runs?run_type=BACKTEST&status=COMPLETED"

# Get run details
curl -X GET http://localhost:8000/v1/runs/run-001

# Create new backtest run
curl -X POST http://localhost:8000/v1/runs \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_id": "momentum_v1",
    "start_date": "2024-01-01",
    "end_date": "2025-12-31",
    "initial_capital": "100000.00"
  }'
# Expected: 202 Accepted with run_id
```

---

### 5. Positions

**Purpose:** Verify position queries.

```bash
# List all positions
curl -X GET http://localhost:8000/v1/positions

# Filter by strategy
curl -X GET "http://localhost:8000/v1/positions?strategy_id=momentum_v1"

# Filter by symbol
curl -X GET "http://localhost:8000/v1/positions?symbol=AAPL"

# Get position details
curl -X GET http://localhost:8000/v1/positions/pos-001
```

---

### 6. Pagination Testing

**Purpose:** Verify pagination works correctly.

```bash
# Test pagination parameters
curl -X GET "http://localhost:8000/v1/runs?page=1&per_page=5"
curl -X GET "http://localhost:8000/v1/positions?page=2&per_page=10"

# Verify pagination limits
curl -X GET "http://localhost:8000/v1/runs?per_page=200"
# Expected: 422 Validation Error (max is 100)
```

---

### 7. Error Handling

**Purpose:** Verify error responses are formatted correctly.

```bash
# Test 404 error
curl -X GET http://localhost:8000/v1/strategies/invalid-id
# Expected: 404 with {"detail": "Strategy 'invalid-id' not found"}

# Test validation error (missing required fields)
curl -X POST http://localhost:8000/v1/runs \
  -H "Content-Type: application/json" \
  -d '{}'
# Expected: 400 with custom error format:
# {
#   "error": {
#     "code": "VALIDATION_ERROR",
#     "message": "Invalid request parameters",
#     "details": [...]
#   },
#   "request_id": "uuid"
# }

# Test invalid query parameters
curl -X GET "http://localhost:8000/v1/metrics/summary?period=invalid"
# Expected: 400 Bad Request (custom handler returns 400, not 422)
```

**Note:** The API uses a custom exception handler that returns 400 Bad Request
for validation errors instead of the default FastAPI 422 Unprocessable Entity.

---

## API Documentation

The API provides auto-generated documentation:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **OpenAPI JSON:** http://localhost:8000/openapi.json

---

## Troubleshooting

### API Won't Start

**Symptoms:** `uvicorn` fails to start, import errors.

**Solutions:**
1. Check Python version: `python --version` (need 3.11+)
2. Reinstall dependencies: `poetry install`
3. Check for syntax errors: `poetry run python -c "from services.api.main import app"`

### Tests Failing

**Symptoms:** `pytest` reports failures.

**Solutions:**
1. Run tests with verbose output: `pytest -v --tb=long`
2. Check if API code changed without updating tests
3. Verify test fixtures match current API schemas

### Health Check Returns "unhealthy"

**Symptoms:** Health endpoint shows unhealthy services.

**Solutions:**
1. Check database connection: Verify DB is running
2. Check Redis: Verify Redis is running
3. Check broker connection: Verify API keys are configured
4. Review service-specific health in response

### Slow Response Times

**Symptoms:** API responses take >1 second.

**Solutions:**
1. Check database query performance
2. Review logging for slow operations
3. Check for N+1 query issues
4. Consider adding caching

### CORS Errors

**Symptoms:** Dashboard can't connect to API.

**Solutions:**
1. Verify CORS origins in `services/api/main.py`
2. Add dashboard origin to `CORS_ORIGINS` list
3. For local dev, ensure ports match

---

## Verification Checklist

Use this checklist when deploying or verifying the API:

- [ ] API server starts without errors
- [ ] Health check returns 200 and "healthy" status
- [ ] Metrics summary returns valid data
- [ ] Strategies list returns expected items
- [ ] Strategy detail works for known IDs
- [ ] Strategy update reflects changes
- [ ] Runs list returns expected items
- [ ] Run detail includes metrics and trades
- [ ] Creating a run returns 202 Accepted
- [ ] Positions list returns expected items
- [ ] Position detail includes risk metrics
- [ ] 404 errors have detail messages
- [ ] Validation errors return 422
- [ ] Pagination works correctly
- [ ] Swagger docs accessible at /docs

---

## Test Coverage Summary

| Endpoint | Unit Tests | Integration Tests |
|----------|-----------|-------------------|
| GET /v1/health | ✅ test_health.py | ✅ test_api_e2e.py |
| GET /v1/metrics/summary | ✅ test_metrics.py | ✅ test_api_e2e.py |
| GET /v1/strategies | ✅ test_strategies.py | ✅ test_api_e2e.py |
| GET /v1/strategies/{id} | ✅ test_strategies.py | ✅ test_api_e2e.py |
| PATCH /v1/strategies/{id} | ✅ test_strategies.py | ✅ test_api_e2e.py |
| GET /v1/runs | ✅ test_runs.py | ✅ test_api_e2e.py |
| GET /v1/runs/{id} | ✅ test_runs.py | ✅ test_api_e2e.py |
| POST /v1/runs | ✅ test_runs.py | ✅ test_api_e2e.py |
| GET /v1/positions | ✅ test_positions.py | ✅ test_api_e2e.py |
| GET /v1/positions/{id} | ✅ test_positions.py | ✅ test_api_e2e.py |

---

## Contact

For API issues:
- Review the [api-contracts.md](../api-contracts.md) specification
- Check the [architecture.md](../architecture.md) documentation
- Run the test suite for automated verification
