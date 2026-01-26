# Planning Findings

## Key Insights from Research

### Project Scope
- **Goal:** Build modular platform for multiple ML-driven trading strategies (stocks + options)
- **Time Horizon:** Short-to-medium term holds (1 day to ~1 week)
- **Risk Profile:** Risk level 6–7 (moderate), emphasizing risk-adjusted returns
- **Deployment:** React + Next.js dashboard on Vercel, trading services on separate infra

### Critical Design Decisions

#### ✅ Architecture: Monorepo Structure
**Rationale:** From floorplan.md - separates concerns while keeping code together
- `/apps/dashboard` - Next.js UI (Vercel)
- `/services/*` - Python services (data, features, backtest, execution, risk, monitoring)
- `/packages/*` - Shared code (strategies, models, common utilities)

#### ✅ Data Layer: Postgres + Object Storage
**Rationale:** Structured data (trades, positions, metrics) in Postgres, artifacts (models, reports) in object storage

#### ✅ Strategy Plugin Architecture
**Rationale:** Stable interface allows rapid strategy experimentation
- `initialize(config)`
- `on_market_data(bar/quote)`
- `generate_signals(state) -> signals`
- `risk_check(signals, portfolio_state) -> approved_orders`

#### ✅ Risk-First Design
**Rationale:** Trading involves real financial risk - safety controls are mandatory
- Position sizing (max 0.5%-2% risk per trade)
- Exposure limits (max 50%-80% capital deployed)
- Kill switches (daily loss limit, max drawdown trigger)
- Paper trading mode required before live

### Technology Stack Validation

#### Backend (Python)
- ✅ **FastAPI** - API layer
- ✅ **pandas/numpy** - Data manipulation
- ✅ **ta-lib or pandas-ta** - Technical indicators
- ✅ **scikit-learn, xgboost/lightgbm** - ML models
- ✅ **backtrader or vectorbt** - Backtesting
- ✅ **Postgres** - Database

#### Frontend (Next.js)
- ✅ **Next.js App Router** - Modern React patterns
- ✅ **NextAuth or JWT** - Authentication
- ✅ **Lightweight Charts** - Performance visualizations
- ✅ **Vercel** - Deployment platform

### Research Highlights

#### ML Approaches (from research.md)
1. **Supervised Learning:** Predict price movements (classification: up/down, regression: price targets)
   - Models: Random Forest, XGBoost for noisy financial data
   - LSTM for sequence patterns (use cautiously - risk of overfitting)

2. **Reinforcement Learning:** Train agent to make trading decisions
   - FinRL library for financial RL
   - Reward function: +1 per % profit, penalties for drawdowns
   - Higher complexity, requires more data

#### Risk Management Principles
- **Position Sizing:** Fixed-fractional (e.g., risk 1% per trade)
- **Stop-Loss/Take-Profit:** Every trade needs exit plan
- **Exposure Limits:** Max positions, per-asset caps
- **Kill Switch:** Halt trading if losses exceed threshold

#### Backtesting Requirements
- Walk-forward/rolling evaluation (avoid look-ahead bias)
- Realistic costs: commissions + slippage
- Metrics: Sharpe/Sortino, max drawdown, win-rate, profit factor
- Compare to benchmark (SPY)

### Open Questions

#### For Architecture Lead (Agent A)
- [ ] Where do model training jobs run? (local vs cloud, scheduling)
- [ ] How to handle real-time data feed failures? (fallback strategies)
- [ ] Event-driven vs polling for market data?

#### For Data Lead (Agent B)  
- [ ] Data retention policy for historical bars?
- [ ] Schema versioning strategy?
- [ ] How to handle corporate actions (splits, dividends)?

#### For API/Security Lead (Agent C)
- [ ] Which secrets manager? (AWS Secrets Manager, Doppler, environment-based?)
- [ ] Rate limiting strategy for broker APIs?
- [ ] How to separate paper vs live API keys in deployment?

#### For Agent Systems Lead (Agent D)
- [ ] What memory/state does each agent type need to persist?
- [ ] Human approval mechanism for transitioning paper → live?
- [ ] How to handle agent failures/retries?

#### For Dashboard Lead (Agent E)
- [ ] Real-time updates vs polling for dashboard data?
- [ ] Authentication: NextAuth.js or custom JWT?
- [ ] Charting library: TradingView Lightweight Charts or Recharts?

## Assumptions

1. **Single User:** V1 assumes deployed for personal use (single trader)
2. **U.S. Markets:** Primary focus on U.S. equities and options
3. **Broker:** Alpaca (stocks) and/or Interactive Brokers (options)
4. **Hosting:** Dashboard on Vercel, trading services on AWS/GCP/DigitalOcean VMs
5. **Development Timeline:** Planning phase → 2-week implementation sprint

## Risk Factors

### Technical Risks
- **Model Overfitting:** ML models may perform well in backtest but fail in live trading
  - Mitigation: Walk-forward validation, paper trading period
- **Data Quality:** Bad data leads to bad signals
  - Mitigation: Data validation, multiple source verification
- **Latency:** Slow execution can erode profits
  - Mitigation: Optimize critical paths, consider co-location if needed (future)

### Financial Risks
- **Market Risk:** Strategies may not work in all market regimes
  - Mitigation: Diversify strategies, circuit breakers
- **Black Swan Events:** Unexpected market crashes
  - Mitigation: Hard stop-loss limits, max drawdown kill switch
- **Broker API Failures:** Trading halted if broker API down
  - Mitigation: Monitoring, alerts, manual intervention capability

### Operational Risks
- **Key Management:** Leaked broker API keys = catastrophic
  - Mitigation: Secrets manager, least-privilege, separate paper/live keys
- **Deployment Failures:** Bad deployment could trigger unwanted trades
  - Mitigation: Blue-green deployments, canary releases, rollback plan

## Next Steps
1. Launch specialist agents in parallel
2. Each agent addresses their open questions
3. Consolidate findings into ADRs for key decisions
