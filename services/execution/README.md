# Execution Engine Service

The execution service handles order execution for paper and live trading.

## Overview

This service provides:
- **BrokerClient Interface**: Abstract interface for broker adapters
- **AlpacaClient**: Alpaca Paper/Live API implementation
- **Order Management System (OMS)**: State machine for order lifecycle
- **Position Tracking**: Real-time position tracking and reconciliation

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Execution Engine                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌─────────────────┐    ┌────────────────┐ │
│  │  Order       │───▶│  Risk Manager   │───▶│  BrokerClient  │ │
│  │  Request     │    │  (Pre-Trade)    │    │  (Alpaca)      │ │
│  └──────────────┘    └─────────────────┘    └───────┬────────┘ │
│                                                      │          │
│                                                      ▼          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                Order Management System (OMS)              │  │
│  │                                                           │  │
│  │   PENDING ──▶ SUBMITTED ──▶ FILLED/REJECTED/CANCELLED    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                      │          │
│                                                      ▼          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Position Tracker & Reconciliation            │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Order State Machine

```
     ┌───────────────────────────────────────────────────────┐
     │                                                       │
     │   PENDING ────────────────┬──────────────────────┐   │
     │      │                    │                      │   │
     │      │ submit()           │ reject()             │   │
     │      ▼                    ▼                      │   │
     │   SUBMITTED ──────────▶ REJECTED                 │   │
     │      │                                           │   │
     │      ├─────── partial_fill() ─────┐              │   │
     │      │                            │              │   │
     │      │                            ▼              │   │
     │      │                   PARTIALLY_FILLED ──┐    │   │
     │      │                            │         │    │   │
     │      │ fill()                     │ fill()  │    │   │
     │      │                            │         │    │   │
     │      ▼                            ▼         │    │   │
     │   FILLED ◀────────────────────────┘         │    │   │
     │                                             │    │   │
     │   CANCELLED ◀───────────────────────────────┴────┘   │
     │                                                       │
     └───────────────────────────────────────────────────────┘
```

## Usage

### Basic Order Placement

```python
from services.execution import AlpacaClient, OrderManagementSystem
from packages.common.execution_schemas import OrderRequest

# Initialize client
client = AlpacaClient(
    api_key="your_api_key",
    secret_key="your_secret_key",
    paper=True,  # Use paper trading
)

# Initialize OMS
oms = OrderManagementSystem()

# Create order request
order_request = OrderRequest(
    symbol="AAPL",
    side="BUY",
    quantity=10,
    order_type="MARKET",
    strategy_id="momentum_v1",
)

# Place order
order = await client.place_order(order_request)

# Track in OMS
oms.add_order(order)
```

### Position Tracking

```python
from services.execution import PositionTracker

tracker = PositionTracker()

# Get positions from broker
broker_positions = await client.get_positions()

# Update tracker
tracker.update_from_broker(broker_positions)

# Check for discrepancies
result = await tracker.reconcile(client)
if result.has_discrepancies:
    print(f"Discrepancies found: {result.discrepancies}")
```

## Configuration

Environment variables:
- `ALPACA_API_KEY`: Alpaca API key
- `ALPACA_SECRET_KEY`: Alpaca secret key
- `ALPACA_BASE_URL`: API base URL (paper vs live)
- `TRADING_MODE`: "PAPER" or "LIVE"

## Risk Integration

All orders pass through the Risk Manager before submission:
1. Position sizing validation
2. Portfolio exposure check
3. Order limit validation
4. Kill switch status check

See `services/risk/` for risk management implementation.

## Testing

```bash
# Run tests
pytest services/execution/ -v

# Run with coverage
pytest services/execution/ --cov=services.execution --cov-report=html
```
