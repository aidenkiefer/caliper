# 2. Database Selection for Time-Series

date: 2026-01-25
status: accepted

## Context
The core of a quantitative trading platform is time-series data (OHLCV bars, tick data). We need a database that can:
- Efficiently store millions of resulting rows.
- Perform fast "windowed" queries (e.g., "Give me 5-minute bars for AAPL for last year").
- Handle transactional data (Orders, Positions) with ACID compliance.

## Decision
We will use **PostgreSQL with the TimescaleDB extension**.

## Consequences
### Positive
- **Unified DB:** No need to manage a separate Transactional DB (Postgres) and Time-Series DB (Influx). Timescale handles both.
- **SQL Interface:** We can use standard SQL and SQLAlchemy/Pydantic, reducing learning curve compared to specialized time-series query languages.
- **Continuous Aggregates:** Timescale's built-in feature to auto-calculate 1h/1d bars from 1m bars saves application complexity.

### Negative
- **Operational Overhead:** Managing a Timescale instance (or Docker container) is slightly heavier than a plain SQLite file, but necessary for concurrency.

## Alternatives Considered
- **InfluxDB:** Great for metrics, but weak for relational data (Trades, Accounts). Would require a second DB for relational data (Complexity ↑).
- **ClickHouse:** Excellent performance, but overkill for v1 data volume and harder to manage operationally for a single dev.
