# Risk Management Service

The risk service enforces trading risk limits and provides kill switches.

## Overview

This service implements comprehensive risk management from `docs/risk-policy.md`:

- **Pre-trade Validation**: Check orders before submission
- **Portfolio Limits**: Max drawdown, capital deployed, position count
- **Strategy Limits**: Allocation caps, daily loss limits
- **Order Limits**: Position sizing, price sanity checks
- **Kill Switches**: Emergency halt mechanisms
- **Circuit Breakers**: Automatic triggers on threshold breaches

## Risk Limits

### Portfolio-Level Limits (System Wide)

| Metric | Default Limit | Action on Breach |
|--------|---------------|------------------|
| Max Daily Drawdown | 3% of Opening Equity | Halt new entries |
| Max Total Drawdown | 10% from High Water Mark | Kill Switch (halt all trading) |
| Max Capital Deployed | 80% of Total Liquidity | Reject new opening orders |
| Max Open Positions | 20 (across all strategies) | Reject new opening orders |

### Strategy-Level Limits

| Metric | Limit Range | Description |
|--------|-------------|-------------|
| Max Allocation | 0-100% of Portfolio | Hard cap on capital per strategy |
| Max Drawdown | 5-10% of Strategy Allocation | Pauses specific strategy |
| Daily Loss Limit | 1-2% of Strategy Allocation | Pauses strategy for session |

### Order-Level Limits (Pre-Trade Checks)

| Metric | Limit | Action |
|--------|-------|--------|
| Max Risk Per Trade | 2% of Portfolio Equity | Reject |
| Max Notional | $25,000 | Reject |
| Price Deviation | >5% from last price | Reject |
| Min Stock Price | $5.00 | Reject |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       Risk Manager                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐    ┌──────────────────┐                   │
│  │  Kill Switch     │    │  Circuit Breaker │                   │
│  │  (Manual + Auto) │    │  (Auto Triggers) │                   │
│  └────────┬─────────┘    └────────┬─────────┘                   │
│           │                       │                              │
│           ▼                       ▼                              │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    Pre-Trade Checks                         ││
│  │                                                              ││
│  │  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐    ││
│  │  │  Portfolio  │  │   Strategy   │  │     Order       │    ││
│  │  │   Limits    │  │    Limits    │  │    Limits       │    ││
│  │  └─────────────┘  └──────────────┘  └─────────────────┘    ││
│  │                                                              ││
│  └─────────────────────────────────────────────────────────────┘│
│                           │                                      │
│                           ▼                                      │
│                    APPROVE / REJECT                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Usage

### Basic Risk Check

```python
from services.risk import RiskManager, PortfolioLimits

# Initialize with default limits
manager = RiskManager()

# Or with custom limits
custom_limits = PortfolioLimits(
    max_daily_drawdown_pct=2.0,  # More conservative
    max_total_drawdown_pct=8.0,
    max_capital_deployed_pct=70.0,
    max_open_positions=15,
)
manager = RiskManager(portfolio_limits=custom_limits)

# Check an order
result = await manager.check_order(
    symbol="AAPL",
    side="BUY",
    quantity=100,
    price=150.00,
    strategy_id="momentum_v1",
    portfolio_value=100000,
    current_positions=5,
    capital_deployed=40000,
)

if result.approved:
    # Proceed with order
    pass
else:
    print(f"Order rejected: {result.rejection_reason}")
    for violation in result.violations:
        print(f"  - {violation.limit_type}: {violation.message}")
```

### Kill Switch

```python
from services.risk import KillSwitch

kill_switch = KillSwitch()

# Activate global kill switch
kill_switch.activate_global(reason="Market volatility")

# Check if trading is halted
if kill_switch.is_active():
    print("Trading halted!")

# Deactivate with admin code
kill_switch.deactivate_global(admin_code="ABC123")
```

### Circuit Breaker

```python
from services.risk import CircuitBreaker

breaker = CircuitBreaker()

# Update with current drawdown
breaker.update_drawdown(
    daily_drawdown_pct=2.5,
    total_drawdown_pct=8.0,
)

# Check if circuit breaker tripped
if breaker.is_tripped():
    print(f"Circuit breaker tripped: {breaker.state}")
```

## Configuration

Risk limits can be configured via:
1. Constructor parameters
2. YAML config files
3. Environment variables

Example YAML config:
```yaml
risk:
  portfolio:
    max_daily_drawdown_pct: 3.0
    max_total_drawdown_pct: 10.0
    max_capital_deployed_pct: 80.0
    max_open_positions: 20
  
  order:
    max_risk_per_trade_pct: 2.0
    max_notional: 25000
    max_price_deviation_pct: 5.0
    min_stock_price: 5.00
```

## Testing

```bash
# Run tests
pytest services/risk/ -v

# Run with coverage
pytest services/risk/ --cov=services.risk --cov-report=html
```
