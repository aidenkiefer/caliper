# Data Contracts - Canonical Schemas

## Summary

This document defines the **single source of truth** for all data schemas used across the quantitative ML trading platform. These contracts ensure that all services (data ingestion, feature engineering, backtesting, execution, dashboard) speak the same language.

**Design Principles:**
- **Explicit over Implicit:** Every field has a defined type, format, and validation rule
- **Versioned:** Schemas include version numbers for backwards compatibility
- **Timezone-Aware:** All timestamps use UTC with explicit timezone specification
- **Nullable Fields:** Clearly marked as optional with default values

---

## Key Decisions

### ✅ TimescaleDB for Time-Series Data
**Decision:** Use PostgreSQL with TimescaleDB extension for price bars and metrics  
**Rationale:**
- Optimized for time-series queries (automatic partitioning by time)
- Supports standard SQL (easier than learning ClickHouse or InfluxDB)
- Continuous aggregates for pre-computed metrics

### ✅ UTC Timestamps Everywhere
**Decision:** Store all timestamps in UTC, convert to local timezone only in UI  
**Rationale:**
- Avoids timezone confusion (especially around DST transitions)
- Market hours vary by exchange, UTC is neutral
- ISO 8601 format with explicit 'Z' suffix

### ✅ Decimal for Money
**Decision:** Use `DECIMAL(20, 8)` for prices and monetary amounts  
**Rationale:**
- Avoids floating-point rounding errors
- 8 decimal places supports crypto (future-proof) and fractional shares

### ✅ Symbol Normalization
**Decision:** Store symbols in uppercase, separate ticker from exchange  
**Rationale:**
- Different data providers use different formats (AAPL vs NASDAQ:AAPL)
- Normalize to `{ticker}:{exchange}` format (e.g., "AAPL:NASDAQ")
- For stocks without exchange ambiguity, exchange can be NULL (defaults to primary listing)

---

## Core Schemas

### 1. Price Bar (OHLCV)

Represents a candlestick bar for a given symbol and timeframe.

**Table:** `market_data.price_bars`

```sql
CREATE TABLE market_data.price_bars (
    id                BIGSERIAL PRIMARY KEY,
    symbol            VARCHAR(20) NOT NULL,           -- e.g., "AAPL", "SPY"
    exchange          VARCHAR(10),                     -- e.g., "NASDAQ", "NYSE" (nullable for unambiguous symbols)
    timestamp         TIMESTAMP WITH TIME ZONE NOT NULL,  -- Bar start time in UTC
    timeframe         VARCHAR(10) NOT NULL,            -- "1min", "5min", "1hour", "1day"
    open              DECIMAL(20, 8) NOT NULL,
    high              DECIMAL(20, 8) NOT NULL,
    low               DECIMAL(20, 8) NOT NULL,
    close             DECIMAL(20, 8) NOT NULL,
    volume            BIGINT NOT NULL,
    vwap              DECIMAL(20, 8),                  -- Volume-weighted average price (optional)
    trade_count       INTEGER,                         -- Number of trades in bar (optional)
    source            VARCHAR(50) NOT NULL,            -- Data provider: "alpaca", "polygon", "iex"
    created_at        TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(symbol, exchange, timestamp, timeframe, source)  -- Prevent duplicates
);

-- TimescaleDB hypertable for efficient time-series queries
SELECT create_hypertable('market_data.price_bars', 'timestamp', chunk_time_interval => INTERVAL '1 day');

-- Indexes
CREATE INDEX idx_price_bars_symbol_time ON market_data.price_bars (symbol, timestamp DESC);
CREATE INDEX idx_price_bars_timeframe ON market_data.price_bars (timeframe, timestamp DESC);
```

**Pydantic Model:**
```python
from pydantic import BaseModel, Field, validator
from datetime import datetime
from decimal import Decimal
from typing import Optional

class PriceBar(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    exchange: Optional[str] = Field(None, max_length=10)
    timestamp: datetime  # UTC timezone-aware
    timeframe: str = Field(..., pattern=r"^\d+(min|hour|day)$")  # e.g., "1min", "1day"
    open: Decimal = Field(..., gt=0, decimal_places=8)
    high: Decimal = Field(..., gt=0, decimal_places=8)
    low: Decimal = Field(..., gt=0, decimal_places=8)
    close: Decimal = Field(..., gt=0, decimal_places=8)
    volume: int = Field(..., ge=0)
    vwap: Optional[Decimal] = Field(None, decimal_places=8)
    trade_count: Optional[int] = Field(None, ge=0)
    source: str
    
    @validator('timestamp')
    def timestamp_must_be_utc(cls, v):
        if v.tzinfo is None:
            raise ValueError('timestamp must be timezone-aware (UTC)')
        return v
    
    @validator('high')
    def high_must_be_highest(cls, v, values):
        assert v >= values['open'] and v >= values['close'] and v >= values['low']
        return v
    
    @validator('low')
    def low_must_be_lowest(cls, v, values):
        assert v <= values['open'] and v <= values['close']
        return v
```

---

### 2. Options Quote

Represents a snapshot of an options contract quote.

**Table:** `market_data.options_quotes`

```sql
CREATE TABLE market_data.options_quotes (
    id                BIGSERIAL PRIMARY KEY,
    underlying        VARCHAR(20) NOT NULL,            -- e.g., "AAPL"
    expiration        DATE NOT NULL,                   -- Expiration date (YYYY-MM-DD)
    strike            DECIMAL(20, 8) NOT NULL,         -- Strike price
    right             VARCHAR(4) NOT NULL CHECK (right IN ('CALL', 'PUT')),
    timestamp         TIMESTAMP WITH TIME ZONE NOT NULL,  -- Quote timestamp (UTC)
    bid               DECIMAL(20, 8),                  -- Bid price (nullable if no bid)
    ask               DECIMAL(20, 8),                  -- Ask price (nullable if no ask)
    mid               DECIMAL(20, 8),                  -- Midpoint (bid + ask) / 2
    last              DECIMAL(20, 8),                  -- Last trade price
    volume            BIGINT DEFAULT 0,                -- Daily volume
    open_interest     BIGINT DEFAULT 0,                -- Open interest
    implied_volatility DECIMAL(10, 6),                 -- IV as decimal (e.g., 0.25 = 25%)
    delta             DECIMAL(8, 6),                   -- Greeks (optional)
    gamma             DECIMAL(8, 6),
    theta             DECIMAL(8, 6),
    vega              DECIMAL(8, 6),
    source            VARCHAR(50) NOT NULL,            -- Data provider
    created_at        TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(underlying, expiration, strike, right, timestamp, source)
);

-- TimescaleDB hypertable
SELECT create_hypertable('market_data.options_quotes', 'timestamp', chunk_time_interval => INTERVAL '1 day');

-- Indexes
CREATE INDEX idx_options_underlying_exp ON market_data.options_quotes (underlying, expiration, timestamp DESC);
CREATE INDEX idx_options_liquidity ON market_data.options_quotes (volume DESC, open_interest DESC) WHERE volume > 0;
```

**Pydantic Model:**
```python
from enum import Enum

class OptionRight(str, Enum):
    CALL = "CALL"
    PUT = "PUT"

class OptionsQuote(BaseModel):
    underlying: str = Field(..., min_length=1, max_length=20)
    expiration: date
    strike: Decimal = Field(..., gt=0, decimal_places=8)
    right: OptionRight
    timestamp: datetime  # UTC
    bid: Optional[Decimal] = Field(None, ge=0, decimal_places=8)
    ask: Optional[Decimal] = Field(None, ge=0, decimal_places=8)
    mid: Optional[Decimal] = Field(None, ge=0, decimal_places=8)
    last: Optional[Decimal] = Field(None, ge=0, decimal_places=8)
    volume: int = Field(0, ge=0)
    open_interest: int = Field(0, ge=0)
    implied_volatility: Optional[Decimal] = Field(None, ge=0, le=10, decimal_places=6)  # Max IV = 1000%
    delta: Optional[Decimal] = Field(None, ge=-1, le=1, decimal_places=6)
    gamma: Optional[Decimal] = Field(None, ge=0, decimal_places=6)
    theta: Optional[Decimal] = Field(None, decimal_places=6)
    vega: Optional[Decimal] = Field(None, ge=0, decimal_places=6)
    source: str
```

---

### 3. Orders

Represents an order sent to the broker (paper or live).

**Table:** `execution.orders`

```sql
CREATE TABLE execution.orders (
    order_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id       VARCHAR(100) NOT NULL,           -- Strategy that generated this order
    symbol            VARCHAR(20) NOT NULL,
    contract_type     VARCHAR(10) NOT NULL CHECK (contract_type IN ('STOCK', 'OPTION')),
    side              VARCHAR(4) NOT NULL CHECK (side IN ('BUY', 'SELL')),
    quantity          DECIMAL(20, 8) NOT NULL CHECK (quantity > 0),  -- Supports fractional shares
    order_type        VARCHAR(20) NOT NULL CHECK (order_type IN ('MARKET', 'LIMIT', 'STOP', 'STOP_LIMIT')),
    limit_price       DECIMAL(20, 8),                  -- Required for LIMIT orders
    stop_price        DECIMAL(20, 8),                  -- Required for STOP orders
    time_in_force     VARCHAR(10) NOT NULL DEFAULT 'DAY' CHECK (time_in_force IN ('DAY', 'GTC', 'IOC', 'FOK')),
    status            VARCHAR(20) NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'SUBMITTED', 'FILLED', 'PARTIALLY_FILLED', 'CANCELLED', 'REJECTED')),
    broker_order_id   VARCHAR(100),                    -- Broker's order ID for tracking
    submitted_at      TIMESTAMP WITH TIME ZONE,
    filled_at         TIMESTAMP WITH TIME ZONE,
    cancelled_at      TIMESTAMP WITH TIME ZONE,
    filled_quantity   DECIMAL(20, 8) DEFAULT 0,
    average_fill_price DECIMAL(20, 8),
    fees              DECIMAL(20, 8) DEFAULT 0,
    reject_reason     TEXT,
    mode              VARCHAR(10) NOT NULL CHECK (mode IN ('BACKTEST', 'PAPER', 'LIVE')),
    created_at        TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at        TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_orders_strategy ON execution.orders (strategy_id, created_at DESC);
CREATE INDEX idx_orders_status ON execution.orders (status, created_at DESC);
CREATE INDEX idx_orders_broker ON execution.orders (broker_order_id) WHERE broker_order_id IS NOT NULL;
```

**Pydantic Model:**
```python
from enum import Enum
from uuid import UUID

class ContractType(str, Enum):
    STOCK = "STOCK"
    OPTION = "OPTION"

class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"

class TimeInForce(str, Enum):
    DAY = "DAY"
    GTC = "GTC"  # Good-til-cancelled
    IOC = "IOC"  # Immediate-or-cancel
    FOK = "FOK"  # Fill-or-kill

class OrderStatus(str, Enum):
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"

class TradingMode(str, Enum):
    BACKTEST = "BACKTEST"
    PAPER = "PAPER"
    LIVE = "LIVE"

class Order(BaseModel):
    order_id: UUID
    strategy_id: str
    symbol: str
    contract_type: ContractType
    side: OrderSide
    quantity: Decimal = Field(..., gt=0)
    order_type: OrderType
    limit_price: Optional[Decimal] = Field(None, gt=0)
    stop_price: Optional[Decimal] = Field(None, gt=0)
    time_in_force: TimeInForce = TimeInForce.DAY
    status: OrderStatus = OrderStatus.PENDING
    broker_order_id: Optional[str] = None
    submitted_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    filled_quantity: Decimal = Decimal(0)
    average_fill_price: Optional[Decimal] = None
    fees: Decimal = Decimal(0)
    reject_reason: Optional[str] = None
    mode: TradingMode
    created_at: datetime
    updated_at: datetime
```

---

### 4. Positions

Represents current holdings (stocks or options).

**Table:** `execution.positions`

```sql
CREATE TABLE execution.positions (
    position_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id       VARCHAR(100) NOT NULL,
    symbol            VARCHAR(20) NOT NULL,
    contract_type     VARCHAR(10) NOT NULL CHECK (contract_type IN ('STOCK', 'OPTION')),
    quantity          DECIMAL(20, 8) NOT NULL,         -- Positive = long, Negative = short
    average_entry_price DECIMAL(20, 8) NOT NULL,
    current_price     DECIMAL(20, 8),                  -- Latest market price
    unrealized_pnl    DECIMAL(20, 8),                  -- (current_price - avg_entry) * quantity
    realized_pnl      DECIMAL(20, 8) DEFAULT 0,        -- Locked-in P&L from closed portions
    cost_basis        DECIMAL(20, 8),                  -- Total cost including fees
    market_value      DECIMAL(20, 8),                  -- quantity * current_price
    mode              VARCHAR(10) NOT NULL CHECK (mode IN ('PAPER', 'LIVE')),
    opened_at         TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at        TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(strategy_id, symbol, mode)  -- One position per symbol per strategy per mode
);

-- Indexes
CREATE INDEX idx_positions_strategy ON execution.positions (strategy_id);
CREATE INDEX idx_positions_symbol ON execution.positions (symbol);
```

**Pydantic Model:**
```python
class Position(BaseModel):
    position_id: UUID
    strategy_id: str
    symbol: str
    contract_type: ContractType
    quantity: Decimal  # Can be negative for short positions
    average_entry_price: Decimal = Field(..., gt=0)
    current_price: Optional[Decimal] = Field(None, gt=0)
    unrealized_pnl: Optional[Decimal] = None
    realized_pnl: Decimal = Decimal(0)
    cost_basis: Optional[Decimal] = None
    market_value: Optional[Decimal] = None
    mode: TradingMode
    opened_at: datetime
    updated_at: datetime
    
    @validator('unrealized_pnl', always=True)
    def compute_unrealized_pnl(cls, v, values):
        if 'current_price' in values and values['current_price']:
            return (values['current_price'] - values['average_entry_price']) * values['quantity']
        return v
```

---

### 5. Strategy Runs (Backtests & Live)

Represents a single execution of a strategy (backtest or live trading session).

**Table:** `backtests.strategy_runs`

```sql
CREATE TABLE backtests.strategy_runs (
    run_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id       VARCHAR(100) NOT NULL,
    run_type          VARCHAR(20) NOT NULL CHECK (run_type IN ('BACKTEST', 'PAPER', 'LIVE')),
    config_hash       VARCHAR(64) NOT NULL,            -- SHA256 of strategy config for reproducibility
    git_commit        VARCHAR(40),                     -- Git commit hash of code version
    start_date        DATE NOT NULL,
    end_date          DATE NOT NULL,
    initial_capital   DECIMAL(20, 2) NOT NULL,
    final_capital     DECIMAL(20, 2),
    total_return      DECIMAL(10, 4),                  -- e.g., 0.15 = 15%
    sharpe_ratio      DECIMAL(10, 4),
    sortino_ratio     DECIMAL(10, 4),
    max_drawdown      DECIMAL(10, 4),                  -- e.g., -0.12 = -12%
    win_rate          DECIMAL(10, 4),                  -- e.g., 0.55 = 55%
    profit_factor     DECIMAL(10, 4),
    total_trades      INTEGER,
    avg_trade_duration_hours DECIMAL(10, 2),
    report_url        TEXT,                            -- URL to detailed report (S3/R2)
    status            VARCHAR(20) NOT NULL DEFAULT 'RUNNING' CHECK (status IN ('RUNNING', 'COMPLETED', 'FAILED')),
    error_message     TEXT,
    created_at        TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at      TIMESTAMP WITH TIME ZONE
);

-- Indexes
CREATE INDEX idx_runs_strategy ON backtests.strategy_runs (strategy_id, created_at DESC);
CREATE INDEX idx_runs_type ON backtests.strategy_runs (run_type, created_at DESC);
```

---

## Data Lifecycle & Retention

### Hot Data (Fast Access)
- **Price Bars:** Last 1 year in Postgres TimescaleDB
- **Options Quotes:** Last 3 months in Postgres
- **Orders:** All orders (indefinite retention for audit)
- **Positions:** Current positions only (closed positions archived)
- **Strategy Runs:** All runs (indefinite retention)

### Cold Storage (Archival)
- **Price Bars:** Older than 1 year → compressed to Parquet files in S3/R2
- **Options Quotes:** Older than 3 months → Parquet files
- **Trade History:** Summarized quarterly reports in object storage

### Retention Policy
- **Logs:** 30 days in structured logging service (CloudWatch, Datadog)
- **Metrics:** 90 days high-resolution, infinite low-resolution (daily aggregates)

---

## Schema Versioning

**Strategy:** Alembic migrations for Postgres schema changes

**Version Tracking:**
```sql
CREATE TABLE schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    description TEXT
);
```

**Backwards Compatibility Rules:**
1. **Never remove columns** - mark as deprecated, remove in v2
2. **Always add new columns as nullable** - or provide defaults
3. **Use separate tables for breaking changes** - e.g., `price_bars_v2`

---

## Interfaces / Contracts

### Data Access Patterns

**For Read-Heavy Services (Dashboard, Backtesting):**
- Use database connection pooling (pgbouncer)
- Cache frequently accessed data (Redis)
- Pre-compute aggregates with TimescaleDB continuous aggregates

**For Write-Heavy Services (Data Ingestion):**
- Batch inserts (bulk upsert)
- Use `ON CONFLICT` for idempotent writes
- Async writes for non-critical data

### API Response Format (JSON)
```typescript
// Example: GET /api/positions
{
  "data": [
    {
      "position_id": "uuid",
      "symbol": "AAPL",
      "quantity": "100.00",  // Decimals as strings to preserve precision
      "unrealized_pnl": "1234.56",
      ...
    }
  ],
  "meta": {
    "total_count": 10,
    "page": 1,
    "per_page": 20
  }
}
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| **Schema drift** (dev vs prod mismatch) | Alembic migrations in CI/CD, schema validation tests |
| **Data corruption** (bad data from provider) | Validation on ingestion, quality checks, alerts on anomalies |
| **Duplicate data** (same bar from multiple sources) | UNIQUE constraints, upsert logic |
| **Timezone bugs** (mixed UTC and local times) | Enforce UTC everywhere, validator in Pydantic models |
| **Precision loss** (float rounding errors) | Use DECIMAL for money, Decimal type in Python |

---

## Open Questions

1. **Historical Data Storage:**
   - Archive to S3/R2 or keep in TimescaleDB with compression?
   - Parquet or CSV for cold storage?

2. **Real-Time Data:**
   - Store every tick or just snapshots (1-second aggregates)?
   - Separate table for real-time vs historical?

3. **Corporate Actions:**
   - How to handle stock splits, dividends in price_bars?
   - Separate `corporate_actions` table with adjustment factors?

4. **Data Quality:**
   - Automated anomaly detection (price jumps > 20%, volume = 0)?
   - Flag suspicious data vs auto-reject?

5. **Multi-Asset Support:**
   - Separate tables for stocks vs options, or unified `instruments` table?
   - How to add futures, forex later?

---

## Next Steps

1. Implement Alembic migration scripts for all tables
2. Create Pydantic models in `packages/common/schemas.py`
3. Build data ingestion service with validation logic
4. Set up TimescaleDB continuous aggregates for dashboard metrics
