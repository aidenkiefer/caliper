# API Service

FastAPI backend service for the quant trading platform dashboard.

## Overview

This service provides REST API endpoints for:
- **Metrics**: Aggregated performance metrics for dashboard overview
- **Strategies**: CRUD operations for trading strategies
- **Positions**: View open positions across strategies
- **Runs**: Backtest runs and trading session management
- **Health**: System health monitoring

## Quick Start

### Prerequisites

- Python 3.11+
- Poetry (recommended) or pip

### Installation

```bash
# From project root
cd services/api

# Using Poetry
poetry install

# Or using pip
pip install fastapi uvicorn[standard] pydantic
```

### Running the Server

Run from the project root directory:

```bash
# Set PYTHONPATH and run (Linux/Mac)
PYTHONPATH=. uvicorn services.api.main:app --reload --host 0.0.0.0 --port 8000

# Set PYTHONPATH and run (Windows PowerShell)
$env:PYTHONPATH = "."; uvicorn services.api.main:app --reload --host 0.0.0.0 --port 8000

# Set PYTHONPATH and run (Windows CMD)
set PYTHONPATH=. && uvicorn services.api.main:app --reload --host 0.0.0.0 --port 8000

# Production mode (with workers)
PYTHONPATH=. uvicorn services.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### API Documentation

Once running, access the interactive docs:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## API Endpoints

All endpoints are prefixed with `/v1/`.

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/v1/health` | System health check |

### Metrics

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/v1/metrics/summary` | Aggregated metrics summary |

Query parameters:
- `period`: `1d`, `1w`, `1m`, `3m`, `1y`, `all` (default: `1m`)
- `mode`: `PAPER`, `LIVE` (optional)

### Strategies

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/v1/strategies` | List all strategies |
| GET | `/v1/strategies/{id}` | Get strategy details |
| PATCH | `/v1/strategies/{id}` | Update strategy |

Query parameters for list:
- `status`: `active`, `inactive`, `all`
- `mode`: `BACKTEST`, `PAPER`, `LIVE`

### Positions

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/v1/positions` | List open positions |
| GET | `/v1/positions/{id}` | Get position details |

Query parameters for list:
- `strategy_id`: Filter by strategy
- `symbol`: Filter by symbol
- `mode`: `PAPER`, `LIVE`
- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 20, max: 100)

### Runs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/v1/runs` | List backtest/trading runs |
| GET | `/v1/runs/{id}` | Get run details |
| POST | `/v1/runs` | Trigger new backtest |

Query parameters for list:
- `strategy_id`: Filter by strategy
- `run_type`: `BACKTEST`, `PAPER`, `LIVE`
- `status`: `RUNNING`, `COMPLETED`, `FAILED`
- `page`, `per_page`

## Example Requests

### Get Health Status

```bash
curl http://localhost:8000/v1/health
```

### Get Metrics Summary

```bash
curl "http://localhost:8000/v1/metrics/summary?period=1m"
```

### List Strategies

```bash
curl http://localhost:8000/v1/strategies
```

### Get Strategy Details

```bash
curl http://localhost:8000/v1/strategies/momentum_v1
```

### Update Strategy Status

```bash
curl -X PATCH http://localhost:8000/v1/strategies/momentum_v1 \
  -H "Content-Type: application/json" \
  -d '{"status": "inactive"}'
```

### List Positions

```bash
curl "http://localhost:8000/v1/positions?strategy_id=momentum_v1"
```

### Trigger Backtest

```bash
curl -X POST http://localhost:8000/v1/runs \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_id": "momentum_v1",
    "start_date": "2024-01-01",
    "end_date": "2025-12-31",
    "initial_capital": "100000.00"
  }'
```

## Project Structure

```
services/api/
├── __init__.py          # Package init
├── main.py              # FastAPI app entry point
├── dependencies.py      # Shared dependencies (DB, auth)
├── pyproject.toml       # Poetry dependencies
├── README.md            # This file
└── routers/
    ├── __init__.py
    ├── health.py        # Health check endpoints
    ├── metrics.py       # Metrics endpoints
    ├── strategies.py    # Strategy CRUD endpoints
    ├── runs.py          # Backtest run endpoints
    └── positions.py     # Position endpoints
```

## Response Format

All responses follow a consistent format:

### Success Response

```json
{
  "data": { ... },
  "meta": {
    "total_count": 10,
    "page": 1,
    "per_page": 20
  }
}
```

### Error Response

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request parameters",
    "details": [
      { "field": "quantity", "message": "Must be positive" }
    ]
  },
  "request_id": "abc123"
}
```

## Configuration

Environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | - |
| `REDIS_URL` | Redis connection string | - |
| `JWT_SECRET` | JWT signing secret | - |
| `CORS_ORIGINS` | Allowed CORS origins | `localhost:3000` |

## TODO

- [ ] Wire to actual PostgreSQL database
- [ ] Implement JWT authentication
- [ ] Add rate limiting with slowapi
- [ ] Add WebSocket endpoints for real-time updates
- [ ] Add integration tests
