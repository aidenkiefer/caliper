# Backtest Service

Backtesting engine for executing trading strategies on historical data.

## Overview

The backtest service provides:
- **BacktestEngine**: Execute strategies on historical price data
- **ReportGenerator**: Generate JSON and HTML reports with performance metrics
- **Performance Metrics**: Sharpe ratio, max drawdown, win rate, profit factor, and more

## Installation

```bash
cd services/backtest
poetry install
```

## Quick Start

### Basic Usage

```python
from datetime import datetime, timezone
from decimal import Decimal

from services.backtest import BacktestEngine, BacktestConfig
from packages.strategies.sma_crossover import SMACrossoverStrategy
from packages.common.schemas import PriceBar, TradingMode

# Create strategy
strategy = SMACrossoverStrategy(
    strategy_id='sma_test',
    config={
        'short_period': 20,
        'long_period': 50,
        'position_size_pct': 0.1,
    }
)

# Prepare historical data
data = [
    PriceBar(
        symbol='AAPL',
        timestamp=datetime.now(timezone.utc),
        timeframe='1day',
        open=Decimal('150.00'),
        high=Decimal('152.00'),
        low=Decimal('149.00'),
        close=Decimal('151.00'),
        volume=1000000,
        source='alpaca',
    ),
    # ... more bars
]

# Configure backtest
config = BacktestConfig(
    initial_capital=Decimal('100000'),
    commission_per_trade=Decimal('1.00'),
    slippage_bps=Decimal('10'),  # 0.1% slippage
)

# Run backtest
engine = BacktestEngine()
result = engine.run(strategy, data, config)

# View results
print(f"Total Return: {result.metrics.total_return_pct:.2f}%")
print(f"Sharpe Ratio: {result.metrics.sharpe_ratio:.2f}")
print(f"Max Drawdown: {result.metrics.max_drawdown_pct:.2f}%")
print(f"Win Rate: {result.metrics.win_rate * 100:.2f}%")
print(f"Total Trades: {result.metrics.total_trades}")
```

### Generate Reports

```python
from services.backtest import ReportGenerator

generator = ReportGenerator()

# Generate JSON report
json_report = generator.generate_json(result)
with open('backtest_report.json', 'w') as f:
    json.dump(json_report, f, indent=2)

# Generate HTML report
html_report = generator.generate_html(result)
with open('backtest_report.html', 'w') as f:
    f.write(html_report)
```

## Configuration

### BacktestConfig

- **initial_capital** (Decimal): Starting capital for the backtest
- **commission_per_trade** (Decimal): Commission charged per trade (default: $1.00)
- **slippage_bps** (Decimal): Slippage in basis points (default: 10 bps = 0.1%)
- **start_date** (Optional[datetime]): Start date filter (UTC timezone-aware)
- **end_date** (Optional[datetime]): End date filter (UTC timezone-aware)

### Example Configuration

```python
from datetime import datetime, timezone
from decimal import Decimal

config = BacktestConfig(
    initial_capital=Decimal('100000'),
    commission_per_trade=Decimal('1.00'),
    slippage_bps=Decimal('10'),  # 0.1% slippage
    start_date=datetime(2023, 1, 1, tzinfo=timezone.utc),
    end_date=datetime(2023, 12, 31, tzinfo=timezone.utc),
)
```

## Performance Metrics

The backtest engine calculates the following metrics:

- **Total Return**: Overall return percentage
- **Sharpe Ratio**: Annualized risk-adjusted return
- **Max Drawdown**: Maximum peak-to-trough decline
- **Win Rate**: Percentage of winning trades
- **Average Win/Loss**: Average P&L for winning and losing trades
- **Profit Factor**: Gross profit / Gross loss ratio

## P&L Calculation

### Trade-Level P&L

For each completed trade:
```
P&L = (exit_price - entry_price) × quantity - commission
```

### Example

- Buy 100 shares @ $150
- Sell 100 shares @ $155
- Commission: $1 per trade
- **P&L = (155 - 150) × 100 - 2 = $498**

### Portfolio Equity

Equity is calculated as:
```
Equity = Cash + Positions Value
```

The equity curve is updated after each bar, tracking:
- Total equity
- Cash balance
- Unrealized P&L

## Order Execution Simulation

### Fill Price Calculation

Market orders are filled with slippage:
- **Buy orders**: `fill_price = bar.close × (1 + slippage_bps / 10000)`
- **Sell orders**: `fill_price = bar.close × (1 - slippage_bps / 10000)`

### Commission

Commission is deducted from cash on each trade:
- Entry: `cash -= (quantity × fill_price + commission)`
- Exit: `cash += (quantity × fill_price - commission)`

## Strategy Integration

The backtest engine works with any strategy that implements the `Strategy` interface:

```python
from packages.strategies.base import Strategy, PortfolioState, Signal

class MyStrategy(Strategy):
    def initialize(self, mode: TradingMode) -> None:
        # Initialize strategy
        pass
    
    def on_market_data(self, bar: PriceBar) -> None:
        # Process new price bar
        pass
    
    def generate_signals(self, portfolio: PortfolioState) -> List[Signal]:
        # Generate trading signals
        pass
    
    def risk_check(
        self,
        signals: List[Signal],
        portfolio: PortfolioState
    ) -> List[Order]:
        # Convert signals to orders with risk checks
        pass
```

## Report Formats

### JSON Report

Machine-readable format with all backtest data:
- Configuration
- Performance metrics
- Complete trade list
- Equity curve points
- Metadata

### HTML Report

Human-readable format with:
- Performance metrics summary (cards)
- Interactive equity curve chart (Plotly)
- Trades table with P&L coloring
- Professional styling

## Example: SMA Crossover Backtest

```python
from services.backtest import BacktestEngine, BacktestConfig
from packages.strategies.sma_crossover import SMACrossoverStrategy

# Load historical data (from database or file)
# data = load_price_bars('AAPL', start_date, end_date)

strategy = SMACrossoverStrategy(
    strategy_id='sma_crossover_v1',
    config={
        'short_period': 20,
        'long_period': 50,
        'position_size_pct': 0.1,
    }
)

config = BacktestConfig(
    initial_capital=Decimal('100000'),
    commission_per_trade=Decimal('1.00'),
    slippage_bps=Decimal('10'),
)

engine = BacktestEngine()
result = engine.run(strategy, data, config)

# Generate reports
generator = ReportGenerator()
json_report = generator.generate_json(result)
html_report = generator.generate_html(result)
```

## Walk-Forward Optimization

Walk-forward optimization provides more realistic performance estimates by:
1. Dividing data into overlapping in-sample/out-of-sample windows
2. Optimizing parameters on each in-sample period
3. Testing optimized parameters on out-of-sample period
4. Aggregating all out-of-sample results

### Basic Walk-Forward Analysis

```python
from services.backtest import (
    WalkForwardEngine,
    WalkForwardConfig,
    BacktestConfig,
    ParameterGrid,
    ParameterRange,
    OptimizationObjective,
)
from packages.strategies.sma_crossover import SMACrossoverStrategy

# Define parameter grid for optimization
param_grid = ParameterGrid(parameters=[
    ParameterRange(name='short_period', min_value=10, max_value=30, step=5, param_type='int'),
    ParameterRange(name='long_period', min_value=40, max_value=80, step=10, param_type='int'),
])

# Configure walk-forward analysis
wf_config = WalkForwardConfig(
    in_sample_days=252,      # 1 year in-sample
    out_of_sample_days=63,   # 3 months out-of-sample
    step_days=63,            # Step forward by 3 months
    parameter_grid=param_grid,
    objective=OptimizationObjective.SHARPE_RATIO,
    min_trades_required=5,
)

# Backtest configuration
backtest_config = BacktestConfig(
    initial_capital=Decimal('100000'),
    commission_per_trade=Decimal('1.00'),
    slippage_bps=Decimal('10'),
)

# Strategy factory function
def create_strategy(strategy_id: str, config: dict) -> SMACrossoverStrategy:
    return SMACrossoverStrategy(strategy_id, config)

# Run walk-forward optimization
engine = WalkForwardEngine()
result = engine.run(
    strategy_factory=create_strategy,
    base_config={'position_size_pct': 0.1},  # Non-optimized params
    data=price_bars,
    wf_config=wf_config,
    backtest_config=backtest_config,
)

# View aggregated out-of-sample results
print(f"Aggregated Return: {result.aggregated_metrics.total_return_pct:.2f}%")
print(f"Aggregated Sharpe: {result.aggregated_metrics.sharpe_ratio:.2f}")
print(f"Total Windows: {result.total_windows}")
print(f"Successful Windows: {result.successful_windows}")

# View parameter stability
for stability in result.parameter_stability:
    print(f"{stability.parameter_name}: mean={stability.mean_value:.2f}, stability={stability.stability_score:.2f}")
```

### WalkForwardConfig Options

| Parameter | Description |
|-----------|-------------|
| `in_sample_days` | Days for in-sample (training) period |
| `out_of_sample_days` | Days for out-of-sample (test) period |
| `step_days` | Days to advance between windows |
| `window_type` | `ROLLING` (fixed window) or `ANCHORED` (expanding) |
| `parameter_grid` | Parameters to optimize (None = no optimization) |
| `objective` | Optimization objective function |
| `min_trades_required` | Minimum trades needed for valid optimization |

### Optimization Objectives

| Objective | Description |
|-----------|-------------|
| `SHARPE_RATIO` | Maximize Sharpe ratio (default) |
| `TOTAL_RETURN` | Maximize total return |
| `PROFIT_FACTOR` | Maximize profit factor |
| `WIN_RATE` | Maximize win rate |
| `MAX_DRAWDOWN` | Minimize maximum drawdown |

### Window Types

- **ROLLING**: Fixed-size window that moves forward through time
- **ANCHORED**: Start date fixed, end date expands (growing in-sample)

### Parameter Stability Analysis

The walk-forward engine analyzes parameter stability across windows:

```python
for stability in result.parameter_stability:
    print(f"Parameter: {stability.parameter_name}")
    print(f"  Mean Value: {stability.mean_value}")
    print(f"  Std Value: {stability.std_value}")
    print(f"  Stability Score: {stability.stability_score}")  # 0-1, higher is more stable
```

A stability score of 1.0 means the parameter was constant across all windows.
Lower scores indicate the optimal parameter varied, suggesting potential overfitting.

### Walk-Forward Results Structure

```python
result.windows                # List of per-window results
result.aggregated_metrics     # Combined out-of-sample performance
result.aggregated_trades      # All out-of-sample trades
result.aggregated_equity_curve# Combined equity curve
result.parameter_stability    # Parameter stability analysis

# Per-window results
for window_result in result.windows:
    print(f"Window {window_result.window.window_id}")
    print(f"  In-sample Sharpe: {window_result.in_sample_result.metrics.sharpe_ratio}")
    print(f"  Out-of-sample Sharpe: {window_result.out_of_sample_result.metrics.sharpe_ratio}")
    print(f"  Best Params: {window_result.params_used}")
```

## Limitations

- **Single Symbol**: Currently supports backtesting one symbol at a time
- **Market Orders Only**: Only market orders are simulated (limit/stop orders not yet supported)
- **Simple Slippage Model**: Fixed basis points slippage (no volume-based slippage)
- **No Partial Fills**: Orders are filled completely or not at all
- **Grid Search Only**: Parameter optimization uses grid search (no Bayesian optimization yet)

## Future Enhancements

- Multi-symbol portfolio backtesting
- Limit and stop order simulation
- Volume-based slippage models
- Bayesian parameter optimization
- Monte Carlo simulation
- Transaction cost analysis

## Troubleshooting

### Empty Results

If the backtest produces no trades:
1. Check that data has enough bars (strategy may need minimum lookback period)
2. Verify strategy signals are being generated
3. Check risk_check() is not filtering out all orders

### P&L Verification

To verify P&L calculation:
1. Use known-good scenario (see sprint-3-multi.md)
2. Check trade-level P&L matches manual calculation
3. Verify equity curve updates correctly

### Performance Issues

For large datasets:
- Consider filtering data by date range
- Use appropriate timeframe (daily vs. minute bars)
- Profile the backtest to identify bottlenecks

## See Also

- `docs/sprint-3-multi.md` - Sprint 3 requirements and verification
- `packages/strategies/base.py` - Strategy interface
- `packages/common/schemas.py` - Data schemas
