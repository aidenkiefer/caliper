# System Architecture - Quant ML Trading Platform

## Summary

This document defines the system architecture for a modular quantitative ML trading platform. The platform supports multiple trading strategies (stocks and options), emphasizes risk management (target level 6-7), and separates concerns between trading services (Python backend) and monitoring dashboard (Next.js on Vercel).

**Core Principle:** Separation of concerns with clear boundaries. Each service has a single responsibility, communicates via well-defined contracts, and can be developed, tested, and deployed independently.

**Deployment Model:**
- **Trading Services:** Containerized Python services running on VM/cloud infrastructure (AWS/GCP/DigitalOcean)
- **Dashboard:** Next.js application deployed to Vercel
- **Communication:** REST API (FastAPI) serving dashboard and external integrations

---

## Key Decisions

### ✅ Monorepo Structure
**Decision:** Use a monorepo to manage all services, packages, and apps  
**Rationale:**
- Shared code (types, schemas, utilities) easily referenced across services
- Atomic commits across multiple components
- Simplified dependency management and versioning
- Better suited for small team or solo developer

**Trade-off:** Monorepo can become unwieldy at scale, but for v1 with ~8 services, this is optimal.

### ✅ Service-Oriented Architecture (SOA)
**Decision:** Decompose system into independent services  
**Rationale:**
- Each service can scale independently (e.g., scale data ingestion separate from backtesting)
- Failure isolation (if feature pipeline fails, execution can continue with last known features)
- Technology flexibility (could use different languages/frameworks per service if needed)

**Services:**
1. **data** - Market data ingestion and normalization
2. **features** - Feature engineering pipeline
3. **research** - Model training and experimentation (notebooks + scripts)
4. **backtest** - Backtesting engine
5. **execution** - Paper and live trade execution
6. **risk** - Risk management and circuit breakers
7. **monitoring** - Metrics collection, logging, alerts
8. **api** - FastAPI backend serving dashboard

### ✅ Event-Driven + Polling Hybrid
**Decision:** Use event-driven architecture for real-time signals, polling for dashboard updates  
**Rationale:**
- Market data events trigger strategy signals (low latency)
- Dashboard polls API every 5-10 seconds (acceptable latency for monitoring)
- Simpler than WebSockets for v1; can upgrade later

**Technology:** Simple message queue (Redis Pub/Sub) for inter-service events

### ✅ Database: Postgres + Object Storage
**Decision:** Postgres for structured data, S3/R2 for artifacts  
**Rationale:**
- Postgres handles relational data well (trades, positions, time-series metrics)
- Object storage for large files (trained models, backtest reports, historical data archives)
- Avoid complexity of multiple databases for v1

### ✅ Containerization with Docker
**Decision:** Docker + docker-compose for local dev, Docker on cloud VMs for prod  
**Rationale:**
- Consistent environments across dev/prod
- Easy service orchestration
- Can upgrade to Kubernetes later if needed, but docker-compose sufficient for v1

---

## System Components

### 1. Market Data Layer (`services/data`)

**Responsibilities:**
- Fetch historical and live market data from providers (Alpaca, IEX, Polygon, etc.)
- Normalize data into canonical schemas
- Store in Postgres (recent data) and object storage (historical archives)
- Provide data access API for other services

**Key Interfaces:**
- `DataProvider` abstract class with adapter pattern for different sources
- `get_bars(symbol, start_date, end_date, timeframe)` → Price bars
- `stream_live_quotes(symbols)` → Real-time quote stream
- Database: `market_data.price_bars` table

**Technology:**
- Python 3.11+, pandas, requests/httpx for API calls
- Postgres with TimescaleDB extension (optimized for time-series)

---

### 2. Feature & Label Pipeline (`services/features`)

**Responsibilities:**
- Compute technical indicators (RSI, MACD, Bollinger Bands, etc.)
- Generate features for ML models (rolling statistics, volatility, momentum)
- Create labels for supervised learning (e.g., "price up 2% in 5 days")
- Cache computed features to avoid redundant calculations

**Key Interfaces:**
- `FeaturePipeline.compute(symbol, lookback_days)` → Feature DataFrame
- `LabelGenerator.generate(symbol, horizon_days, threshold)` → Labels
- Database: `features.computed_features` table

**Technology:**
- Python, pandas, ta-lib or pandas-ta
- Feature store pattern (cache features with versioning)

---

### 3. Strategy & Model Layer (`packages/strategies`)

**Responsibilities:**
- Define strategy plugin interface
- Implement multiple strategy types (momentum, mean reversion, options spreads)
- Load and execute ML models for signal generation
- Each strategy is a self-contained module following plugin pattern

**Plugin Interface:**
```python
class Strategy(ABC):
    def initialize(self, config: StrategyConfig) -> None
    def on_market_data(self, bar: PriceBar) -> None
    def generate_signals(self, state: PortfolioState) -> List[Signal]
    def risk_check(self, signals: List[Signal], portfolio: Portfolio) -> List[Order]
    def on_fill(self, fill: Fill) -> None
    def daily_close(self) -> None
```

**Model Interface:**
```python
class TradingModel(ABC):
    def fit(self, train_data: DataFrame, params: dict) -> ModelArtifact
    def predict(self, features: DataFrame) -> Predictions
    def explain(self, features: DataFrame) -> Explanations  # SHAP, feature importance
```

**Configuration:**
- YAML config per strategy: `configs/strategies/momentum_v1.yaml`
- Includes: universe selection, model type, feature set, signal thresholds, risk caps

**Technology:**
- Python, scikit-learn, xgboost/lightgbm, torch (optional for LSTM/RL)
- FinRL for reinforcement learning strategies (optional)

---

### 4. Backtesting Engine (`services/backtest`)

**Responsibilities:**
- Simulate strategy on historical data
- Model realistic fills, fees, slippage
- Generate performance reports (Sharpe, max drawdown, win rate, etc.)
- Walk-forward optimization with parameter search ✅

**Implementation Status:** ✅ Complete (Sprint 3, Walk-Forward added)

**Key Interfaces:**

```python
class BacktestEngine:
    """Execute strategies on historical price data."""
    def run(
        strategy: Strategy,
        data: List[PriceBar],
        config: BacktestConfig
    ) -> BacktestResult

class BacktestConfig:
    """Configuration for backtest runs."""
    initial_capital: Decimal       # Starting capital
    commission_per_trade: Decimal  # Commission per trade (default: $1.00)
    slippage_bps: Decimal          # Slippage in basis points (default: 10 bps)
    start_date: Optional[datetime] # Filter start date (UTC)
    end_date: Optional[datetime]   # Filter end date (UTC)

class BacktestResult:
    """Complete backtest results."""
    backtest_id: UUID
    strategy_id: str
    config: BacktestConfig
    equity_curve: List[EquityPoint]
    trades: List[Trade]
    metrics: PerformanceMetrics
    start_time: datetime
    end_time: datetime
    metadata: Dict[str, Any]

class PerformanceMetrics:
    """Calculated performance metrics."""
    total_return: Decimal
    total_return_pct: Decimal
    sharpe_ratio: Optional[Decimal]  # Annualized
    max_drawdown: Decimal
    max_drawdown_pct: Decimal
    win_rate: Decimal
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_win: Optional[Decimal]
    avg_loss: Optional[Decimal]
    profit_factor: Optional[Decimal]

class ReportGenerator:
    """Generate machine and human-readable reports."""
    def generate_json(result: BacktestResult) -> Dict[str, Any]
    def generate_html(result: BacktestResult) -> str

# Walk-Forward Optimization (added Sprint 3)
class WalkForwardEngine:
    """Walk-forward optimization with parameter grid search."""
    def run(
        strategy_factory: StrategyFactory,  # Callable[[str, Dict], Strategy]
        base_config: Dict[str, Any],
        data: List[PriceBar],
        wf_config: WalkForwardConfig,
        backtest_config: BacktestConfig
    ) -> WalkForwardResult

class WalkForwardConfig:
    """Configuration for walk-forward analysis."""
    in_sample_days: int            # Training period (e.g., 252 = 1 year)
    out_of_sample_days: int        # Test period (e.g., 63 = 3 months)
    step_days: int                 # Step forward each iteration
    window_type: WindowType        # ROLLING or ANCHORED
    parameter_grid: ParameterGrid  # Parameters to optimize (optional)
    objective: OptimizationObjective  # SHARPE_RATIO, TOTAL_RETURN, etc.
    min_trades_required: int       # Minimum trades for valid optimization

class WalkForwardResult:
    """Complete walk-forward results."""
    walk_forward_id: UUID
    strategy_id: str
    config: WalkForwardConfig
    windows: List[WalkForwardWindowResult]
    aggregated_metrics: PerformanceMetrics  # Combined OOS performance
    aggregated_trades: List[Trade]
    aggregated_equity_curve: List[EquityPoint]
    parameter_stability: List[ParameterStability]  # Stability analysis
```

**Walk-Forward Data Flow:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      WALK-FORWARD OPTIMIZATION FLOW                         │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────┐
│  Historical Data │
│   (3+ years)     │
└────────┬─────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                        WalkForwardEngine                                 │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │ Window 1                                                            │ │
│  │  ┌──────────────────────┐  ┌──────────────────┐                     │ │
│  │  │ In-Sample (1 year)   │─▶│ Out-of-Sample    │                     │ │
│  │  │ Optimize parameters  │  │ Test best params │                     │ │
│  │  └──────────────────────┘  └──────────────────┘                     │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │ Window 2 (step forward)                                             │ │
│  │  ┌──────────────────────┐  ┌──────────────────┐                     │ │
│  │  │ In-Sample            │─▶│ Out-of-Sample    │                     │ │
│  │  │ Re-optimize          │  │ Test best params │                     │ │
│  │  └──────────────────────┘  └──────────────────┘                     │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│  ... (repeat for all windows)                                            │
└─────────────────────────────────────────────────────────────────────────┬┘
                                                                          │
                                                                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         WalkForwardResult                                   │
│                                                                             │
│  ┌──────────────────────┐  ┌─────────────────────┐  ┌──────────────────┐   │
│  │ Aggregated Metrics   │  │ Aggregated Trades   │  │ Parameter        │   │
│  │ (OOS only - realistic)│  │ (All OOS trades)   │  │ Stability        │   │
│  └──────────────────────┘  └─────────────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Data Flow Diagram:**

```
┌─────────────────────────────────────────────────────────────────────┐
│                        BACKTEST DATA FLOW                           │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────┐      ┌──────────────┐      ┌─────────────────────────┐
│  Historical  │      │   Strategy   │      │     BacktestEngine      │
│    Data      │ ───▶ │   Instance   │ ───▶ │                         │
│ (PriceBar[]) │      │ (implements  │      │  1. _reset_state()      │
└──────────────┘      │  Strategy)   │      │  2. strategy.init()     │
                      └──────────────┘      │  3. For each bar:       │
                                            │     a. on_market_data() │
┌──────────────┐                            │     b. generate_signals │
│  Backtest    │                            │     c. risk_check()     │
│   Config     │ ──────────────────────────▶│     d. execute_order()  │
│              │                            │     e. update_equity()  │
└──────────────┘                            │  4. calculate_metrics() │
                                            └───────────┬─────────────┘
                                                        │
                           ┌────────────────────────────┴────────────────────────────┐
                           │                                                         │
                           ▼                                                         ▼
               ┌───────────────────┐                                   ┌─────────────────────┐
               │  BacktestResult   │                                   │   ReportGenerator   │
               │                   │                                   │                     │
               │ - equity_curve    │ ─────────────────────────────────▶│  - generate_json()  │
               │ - trades          │                                   │  - generate_html()  │
               │ - metrics         │                                   │                     │
               └───────────────────┘                                   └─────────────────────┘
                                                                                  │
                                                                                  ▼
                                                                       ┌─────────────────────┐
                                                                       │   Report Output     │
                                                                       │                     │
                                                                       │ - JSON (machine)    │
                                                                       │ - HTML (Plotly)     │
                                                                       └─────────────────────┘
```

**Order Execution Flow:**

```
Signal → risk_check() → Order → _execute_order() → Fill Simulation
                                      │
                         ┌────────────┴────────────┐
                         │                         │
                         ▼                         ▼
                    BUY Order                 SELL Order
                         │                         │
                         ▼                         ▼
              Calculate fill price      Calculate fill price
              (close × (1 + slippage))  (close × (1 - slippage))
                         │                         │
                         ▼                         ▼
              Deduct cost from cash     Add proceeds to cash
              Create/Update Position    Close Position → Record Trade
                         │                         │
                         └────────────┬────────────┘
                                      ▼
                            Update Equity Curve
```

**Technology:**
- **Custom Implementation** - Lightweight, purpose-built engine (see ADR-0005)
- **No External Libraries** - Avoids Backtrader/vectorbt complexity for v1
- **Plotly** - Interactive HTML charts for report visualization
- **Pydantic** - Type-safe configuration and result models
- **NumPy** - Performance metrics calculations (Sharpe ratio, statistics)

**P&L Calculation:**

Trade-level P&L:
```
P&L = (exit_price - entry_price) × quantity - total_commission
```

Fill Price with Slippage:
```
BUY:  fill_price = bar.close × (1 + slippage_bps / 10000)
SELL: fill_price = bar.close × (1 - slippage_bps / 10000)
```

**Current Limitations:**
- Single symbol backtesting only (multi-symbol planned for v2)
- Market orders only (limit/stop orders planned for v2)
- Fixed basis points slippage (volume-based slippage planned for v2)
- No partial fills simulation

**Extension Points:**
- Strategy interface (`packages/strategies/base.py`) allows any strategy implementation
- Config is Pydantic model - easily extensible with new parameters
- Metrics calculation is modular - new metrics can be added
- Report generator supports custom templates

---

### 5. Execution Engine (`services/execution`)

**Responsibilities:**
- Execute orders in paper or live mode
- Connect to broker APIs (Alpaca, Interactive Brokers)
- Track order status (pending, filled, cancelled)
- Manage position tracking and reconciliation

**Broker Adapter Pattern:**
```python
class BrokerClient(ABC):
    def place_order(self, order: Order) -> OrderID
    def get_positions(self) -> List[Position]
    def get_account(self) -> Account
    def stream_quotes(self, symbols: List[str]) -> QuoteStream
```

**Modes:**
- `BACKTEST`: Uses historical fills simulator
- `PAPER`: Broker paper trading API
- `LIVE`: Real money (requires strict risk gates)

**Technology:**
- Python, alpaca-trade-api, ib_insync for Interactive Brokers
- OMS (Order Management System) with state machine for order lifecycle

---

### 6. Risk Management (`services/risk`)

**Responsibilities:**
- Pre-trade risk checks (position sizing, exposure limits)
- Post-trade monitoring (drawdown tracking)
- Circuit breakers and kill switches
- Enforce risk policy rules

**Key Checks:**
- Max risk per trade (0.5-2% of equity)
- Max capital deployed (50-80%)
- Max concurrent positions (5-15)
- Daily loss limit (1-3% triggers pause)
- Max drawdown kill switch (5-12% halts trading)

**Interfaces:**
- `RiskManager.check_order(order, portfolio)` → Approved/Rejected
- `CircuitBreaker.check_drawdown(equity_curve)` → Active/Inactive

**Technology:**
- Python, real-time metrics from monitoring service

---

### 7. Monitoring, Metrics & Alerts (`services/monitoring`)

**Responsibilities:**
- Collect metrics from all services (PnL, Sharpe, fill rates, latency)
- Log aggregation and structured logging
- Alert generation (Slack, email, SMS)
- Health checks for services

**Metrics:**
- Trading: PnL, Sharpe/Sortino, max drawdown, win rate, turnover
- System: Data feed status, API latency, error rates

**Technology:**
- Python structlog for logging
- Prometheus + Grafana (optional for v2)
- Simple alerting via Slack webhooks or email (SendGrid)

---

### 8. Dashboard UI (`apps/dashboard`)

**Responsibilities:**
- Real-time monitoring of strategies and positions
- Backtest run history and comparisons
- Admin controls (enable/disable strategies, adjust risk parameters)
- System health dashboard

**Pages:** (See `dashboard-spec.md` for details)
- Overview, Strategies, Positions, Runs, Controls, System Health

**Technology:**
- Next.js 14 (App Router), React, TypeScript
- TradingView Lightweight Charts or Recharts
- NextAuth.js for authentication
- Deployed on Vercel

---

### 9. API Backend (`services/api`)

**Responsibilities:**
- Serve dashboard with REST API
- Aggregate data from services
- Handle authentication and authorization

**Endpoints:** (See `api-contracts.md` for details)
- `/metrics/summary`, `/strategies`, `/positions`, `/runs`, `/alerts`, `/controls`

**Technology:**
- FastAPI, Python 3.11+
- Pydantic for request/response validation

---

## Data Flow Diagrams

### Strategy Execution Flow
```
Market Data → Feature Pipeline → Strategy Plugin → Risk Check → Execution Engine → Broker
                                         ↓
                                   Monitoring Service
                                         ↓
                                   Metrics Database
                                         ↓
                                     Dashboard
```

### Backtest Flow
```
Historical Data → Feature Pipeline → Strategy Plugin → Backtest Engine → Report Generator
                                                              ↓
                                                        Metrics Database
                                                              ↓
                                                          Dashboard
```

---

## Deployment Topology

### Local Development
```
docker-compose.yml:
  - postgres (TimescaleDB)
  - redis
  - data service
  - features service
  - api service
  - monitoring service
```

### Production
```
Cloud VM (AWS/DigitalOcean):
  - Docker containers for Python services
  - Postgres managed database (RDS or DigitalOcean Managed DB)
  - Redis (managed or self-hosted)

Vercel:
  - Next.js dashboard

Object Storage:
  - S3 or Cloudflare R2 for model artifacts and reports
```

---

## AI Agent Tool Definitions

### Agent Roles

#### 1. Data Agent
**Purpose:** Fetch and validate market data  
**Tools:**
- `fetch_historical_data(symbol, start_date, end_date)` → Price bars
- `validate_data_quality(data)` → Quality report
- `check_data_freshness(symbol)` → Staleness check

#### 2. Strategy Agent
**Purpose:** Generate trading signals  
**Tools:**
- `compute_features(symbol, lookback)` → Feature DataFrame
- `load_model(model_id)` → Model object
- `generate_signals(features, model)` → Signals
- `backtest_strategy(strategy_config, date_range)` → Performance metrics

#### 3. Risk Agent
**Purpose:** Enforce risk policies  
**Tools:**
- `check_position_size(order, portfolio)` → Compliance check
- `compute_portfolio_exposure()` → Exposure metrics
- `check_kill_switch(equity_curve)` → Active/Inactive
- `generate_risk_report()` → Risk summary

#### 4. Execution Agent
**Purpose:** Execute trades  
**Tools:**
- `place_order(order)` → Order ID
- `check_order_status(order_id)` → Status
- `get_positions()` → Current positions
- `reconcile_positions(expected, actual)` → Discrepancies

#### 5. Monitoring Agent
**Purpose:** Track system health  
**Tools:**
- `collect_metrics(service_name)` → Metrics snapshot
- `check_service_health(service_name)` → Healthy/Unhealthy
- `send_alert(message, severity)` → Alert sent
- `generate_daily_summary()` → Summary report

### Memory Strategy
- **Short-term:** Redis for session state (active orders, current signals)
- **Long-term:** Postgres for historical trades, positions, metrics
- **Agent Context:** Each agent maintains state in Redis with TTL (e.g., "Data Agent last fetch timestamp")

### Human-in-the-Loop Checkpoints
1. **Strategy Approval:** New strategies must be reviewed before backtest
2. **Paper Trading Approval:** Backtest results must be approved before paper trading
3. **Live Trading Approval:** Paper trading results must be approved before live
4. **Risk Limit Changes:** Manual approval required to modify risk caps

---

## Interfaces / Contracts

### Inter-Service Communication
- **Protocol:** HTTP REST for synchronous calls, Redis Pub/Sub for async events
- **Data Format:** JSON for API, Protobuf optional for high-frequency events
- **Authentication:** Service-to-service via API keys (short-lived tokens)

### Database Contracts
- **Schema Versioning:** Alembic migrations for Postgres
- **Backwards Compatibility:** Never break existing queries; add new columns/tables
- **Data Types:** Use canonical types from `data-contracts.md`

### External Integrations
- **Broker APIs:** Abstracted via `BrokerClient` interface
- **Data Providers:** Abstracted via `DataProvider` interface
- **Alert Channels:** Plugin pattern for Slack, email, SMS (future: PagerDuty)

---

## Risks & Mitigations

### Technical Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Data feed outage | High - No trading possible | Medium | Fallback to secondary provider; alert on staleness |
| Model drift | High - Poor signals | High | Monitor model performance; retrain on schedule |
| Latency spikes | Medium - Missed fills | Medium | Optimize critical paths; broker co-location (v2) |
| Service crashes | Medium - Trading halted | Medium | Health checks, auto-restart, circuit breakers |

### Financial Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Overfitting | High - Real losses | High | Walk-forward validation, paper trading first |
| Flash crashes | Very High - Catastrophic loss | Low | Kill switches, stop-losses, max drawdown limits |
| Broker API failures | High - Unable to exit positions | Low | Manual intervention capability, alerts |

### Operational Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Leaked API keys | Very High - Unauthorized trading | Low | Secrets manager, key rotation, alerts on unusual activity |
| Bad deployment | High - Unwanted trades | Medium | Blue-green deployments, dry-run mode |
| Configuration errors | Medium - Incorrect parameters | Medium | YAML validation, schema checks, dry-run mode |

---

## Open Questions

### For Implementation (Cursor Phase)

1. **Model Training Infrastructure:**
   - Run locally or cloud (AWS SageMaker, GCP Vertex AI)?
   - Scheduled retraining frequency (weekly, monthly)?
   - Where to store training logs and artifacts?

2. **Real-Time Data:**
   - Use WebSocket streams or HTTP polling for live quotes?
   - Which provider(s) for low-latency data (Alpaca vs Polygon vs IEX)?
   - Fallback strategy if primary feed fails?

3. **Scheduler:**
   - Simple cron jobs or upgrade to Airflow/Prefect?
   - How to handle missed jobs (retry logic)?

4. **Secrets Management:**
   - AWS Secrets Manager, GCP Secret Manager, or Doppler?
   - How to inject secrets into containers?

5. **Testing Strategy:**
   - Unit test coverage target (80%+)?
   - Integration test setup (docker-compose with test database)?
   - End-to-end test for full backtest → execution flow?

### For Future Iterations

- **Multi-user support:** If deploying for multiple users, need user isolation
- **Advanced analytics:** Portfolio optimization, factor analysis
- **Alternative data:** Sentiment, news, social media signals
- **HFT capabilities:** If moving to sub-second strategies, major architecture changes needed

---

## Next Steps

1. **Implement Data Contracts** - Define exact schemas in `data-contracts.md`
2. **Specify API Contracts** - Define all endpoints in `api-contracts.md`
3. **Finalize Risk Policy** - Codify rules in `risk-policy.md`
4. **Design Dashboard** - Create wireframes and component hierarchy in `dashboard-spec.md`
5. **Create ADRs** - Document key decisions (monorepo, SOA, database choice) in `/adr`
