# Backtest Verification Runbook

This runbook provides step-by-step procedures for verifying backtest accuracy, including known-good test scenarios and troubleshooting guidance.

---

## Prerequisites

Before running verification:

- [ ] Docker containers running: `docker-compose up -d`
- [ ] Python environment activated: `poetry shell`
- [ ] Dependencies installed: `poetry install`
- [ ] Database migrated (if using database data)

---

## Quick Verification Commands

### Run All Backtest Tests

```bash
# Run all backtest unit tests
poetry run pytest services/backtest/ -v

# Run integration tests
poetry run pytest tests/integration/test_backtest_sma_crossover.py -v

# Run with coverage
poetry run pytest services/backtest/ tests/integration/ --cov=services/backtest --cov-report=html
```

### Run Specific Test Categories

```bash
# Engine tests only
poetry run pytest services/backtest/test_engine.py -v

# P&L calculation tests only
poetry run pytest services/backtest/test_pnl.py -v

# Report generation tests only
poetry run pytest services/backtest/test_report.py -v
```

---

## Known-Good Test Scenarios

### Scenario 1: Simple Buy-Sell P&L Calculation

**Inputs:**
- Entry: Buy 100 shares @ $150.00
- Exit: Sell 100 shares @ $155.00
- Commission: $1.00 per trade ($2.00 total)

**Expected Output:**
- Gross P&L: (155 - 150) × 100 = $500.00
- Net P&L: $500.00 - $2.00 = **$498.00**
- Return %: 5/150 × 100 = **3.33%**

**Test:**
```bash
poetry run pytest services/backtest/test_pnl.py::TestTradeLevelPnL::test_known_good_pnl_scenario -v
```

### Scenario 2: Break-Even Trade

**Inputs:**
- Entry: Buy 100 shares @ $100.00
- Exit: Sell 100 shares @ $100.00
- Commission: $1.00 per trade ($2.00 total)

**Expected Output:**
- Gross P&L: (100 - 100) × 100 = $0.00
- Net P&L: $0.00 - $2.00 = **-$2.00**

**Test:**
```bash
poetry run pytest services/backtest/test_pnl.py::TestPnLEdgeCases::test_break_even_trade -v
```

### Scenario 3: Losing Trade

**Inputs:**
- Entry: Buy 100 shares @ $150.00
- Exit: Sell 100 shares @ $145.00
- Commission: $1.00 per trade ($2.00 total)

**Expected Output:**
- Gross P&L: (145 - 150) × 100 = -$500.00
- Net P&L: -$500.00 - $2.00 = **-$502.00**

**Test:**
```bash
poetry run pytest services/backtest/test_pnl.py::TestTradeLevelPnL::test_losing_trade_pnl_is_negative -v
```

---

## P&L Validation Procedures

### Manual P&L Verification

Use this formula to manually verify any trade:

```
P&L = (exit_price - entry_price) × quantity - total_commission
```

Where:
- `exit_price`: Price at which position was closed
- `entry_price`: Price at which position was opened
- `quantity`: Number of shares traded
- `total_commission`: Commission for both entry and exit trades

### Performance Metrics Validation

#### Sharpe Ratio

```
Sharpe = (mean(daily_returns) / std(daily_returns)) × sqrt(252)
```

Where:
- `daily_returns`: List of daily portfolio returns
- `252`: Trading days per year (annualization factor)

#### Max Drawdown

```
Max Drawdown = min(equity - peak_equity)
```

Track running peak and calculate difference at each point.

#### Win Rate

```
Win Rate = winning_trades / total_trades
```

Where `winning_trades` are trades with P&L > 0.

---

## Step-by-Step Verification

### Step 1: Verify Engine Runs

```python
from services.backtest.engine import BacktestEngine
from services.backtest.models import BacktestConfig
from packages.strategies.sma_crossover import SMACrossoverStrategy
from tests.fixtures.backtest_data import get_sample_aapl_bars
from decimal import Decimal

# Create components
engine = BacktestEngine()
strategy = SMACrossoverStrategy('test', {'short_period': 20, 'long_period': 50})
config = BacktestConfig(initial_capital=Decimal('100000'))
data = get_sample_aapl_bars(100)

# Run backtest
result = engine.run(strategy, data, config)

# Verify
print(f"✓ Backtest completed")
print(f"  Strategy: {result.strategy_id}")
print(f"  Trades: {len(result.trades)}")
print(f"  Total Return: {result.metrics.total_return_pct:.2f}%")
```

### Step 2: Verify P&L Accuracy

```python
# For each trade, verify P&L formula
for trade in result.trades:
    expected_pnl = (trade.exit_price - trade.entry_price) * trade.quantity - trade.commission
    actual_pnl = trade.pnl
    
    if expected_pnl == actual_pnl:
        print(f"✓ Trade P&L correct: ${actual_pnl:.2f}")
    else:
        print(f"✗ Trade P&L mismatch! Expected: ${expected_pnl:.2f}, Got: ${actual_pnl:.2f}")
```

### Step 3: Verify Report Generation

```python
from services.backtest.report import ReportGenerator
import json

report_gen = ReportGenerator()

# Generate JSON report
json_report = report_gen.generate_json(result)
print(f"✓ JSON report generated with {len(json_report['trades'])} trades")

# Verify JSON is valid
json_str = json.dumps(json_report, indent=2)
print(f"✓ JSON is valid ({len(json_str)} characters)")

# Generate HTML report
html_report = report_gen.generate_html(result)
print(f"✓ HTML report generated ({len(html_report)} characters)")

# Save reports
with open('reports/test_backtest.json', 'w') as f:
    json.dump(json_report, f, indent=2)
    
with open('reports/test_backtest.html', 'w') as f:
    f.write(html_report)
    
print("✓ Reports saved to reports/")
```

---

## Troubleshooting

### Tests Failing

#### "Module not found" errors

```bash
# Ensure you're in the poetry environment
poetry shell

# Reinstall dependencies
poetry install
```

#### "Database connection" errors

```bash
# Check Docker containers
docker-compose ps

# Restart containers
docker-compose down && docker-compose up -d
```

#### P&L calculation off

1. Check commission configuration
2. Verify slippage settings (should be 0 for exact P&L tests)
3. Confirm entry/exit prices in trade object

### Backtest Not Generating Trades

1. **Insufficient data**: SMA crossover needs at least `long_period + 1` bars
2. **No crossovers**: Price action may not have caused SMA crossovers
3. **Position already exists**: Strategy won't buy if already holding

### Performance Metrics Incorrect

1. **Sharpe ratio None**: Need at least 2 equity points with non-zero std
2. **Drawdown positive**: Should always be ≤ 0 (negative or zero)
3. **Win rate > 1**: Bug in calculation, should be 0.0-1.0

---

## Expected Test Results

### Unit Tests

| Test File | Expected Tests | Description |
|-----------|----------------|-------------|
| `test_engine.py` | ~15 tests | Engine initialization, running, error handling |
| `test_pnl.py` | ~15 tests | P&L calculation, equity curve, metrics |
| `test_report.py` | ~20 tests | JSON and HTML report generation |

### Integration Tests

| Test File | Expected Tests | Description |
|-----------|----------------|-------------|
| `test_backtest_sma_crossover.py` | ~15 tests | Full SMA crossover backtest workflow |

### Expected Output

```
================= test session starts =================
...
services/backtest/test_engine.py ............ [25%]
services/backtest/test_pnl.py .............. [50%]
services/backtest/test_report.py ........... [75%]
tests/integration/test_backtest_sma_crossover.py ... [100%]
================= X passed in Y.YYs =================
```

---

## CI/CD Integration

### GitHub Actions Workflow

```yaml
name: Backtest Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install poetry
      - run: poetry install
      - run: poetry run pytest services/backtest/ tests/integration/ -v
```

---

## Verification Checklist

### Pre-Release Checklist

- [ ] All unit tests pass: `poetry run pytest services/backtest/ -v`
- [ ] Integration test passes: `poetry run pytest tests/integration/ -v`
- [ ] Known-good P&L scenario: $498 expected, $498 actual
- [ ] JSON report contains all required fields
- [ ] HTML report renders correctly in browser
- [ ] No linter errors: `poetry run ruff check services/backtest/`

### Post-Deployment Verification

- [ ] Run smoke test with sample data
- [ ] Verify reports can be saved to storage
- [ ] Check metrics match manual calculations
- [ ] Confirm performance acceptable (< 30s for 1 year daily data)

---

## Contact

For issues with backtest verification:
- Check this runbook first
- Review test output for specific failures
- Escalate to Backend Agent if implementation bugs found

---

**Last Updated:** 2026-01-26
**Version:** 1.0
