# Using the ML Direction Strategy

## Quick Start

The ML Direction Strategy (`MLDirectionStrategyV1`) is the first ML-powered strategy in Caliper. It uses a trained binary classifier to predict next-bar price direction.

---

## Prerequisites

1. **Trained model:** Run the training script first
   ```bash
   poetry run python -m services.ml.training.train_first_model \
       --data-file data/spy_daily_2020_2025.csv \
       --output-path models/first_model_v1.pkl
   ```

2. **Model file:** Verify `models/first_model_v1.pkl` exists

---

## Running a Backtest

### Python API

```python
from services.backtest.engine import BacktestEngine
from packages.strategies.ml_direction_v1 import MLDirectionStrategyV1
from packages.common.schemas import PriceBar
from decimal import Decimal

# Load your historical bars
bars = [...]  # List of PriceBar objects

# Create strategy instance
strategy = MLDirectionStrategyV1(
    strategy_id='ml_direction_v1',
    config={
        'model_path': 'models/first_model_v1.pkl',
        'position_size_pct': 0.1,  # 10% of equity per position
        'abstain_threshold': 0.55,  # Confidence threshold
        'prediction_log_path': 'logs/backtest_predictions.jsonl',
    }
)

# Run backtest
engine = BacktestEngine(
    strategy=strategy,
    bars=bars,
    initial_cash=Decimal('100000'),
    slippage_bps=5,
    commission_per_share=Decimal('0.01'),
)

result = engine.run()

# View results
print(f"Final Equity: ${result['final_equity']:,.2f}")
print(f"Total Return: {result['total_return']:.2%}")
print(f"Sharpe Ratio: {result['sharpe_ratio']:.2f}")
print(f"Max Drawdown: {result['max_drawdown']:.2%}")

# View predictions
import json
with open('logs/backtest_predictions.jsonl', 'r') as f:
    predictions = [json.loads(line) for line in f]

print(f"\nTotal Predictions: {len(predictions)}")
buy_signals = [p for p in predictions if p['signal'] == 'BUY']
sell_signals = [p for p in predictions if p['signal'] == 'SELL']
abstain_signals = [p for p in predictions if p['signal'] == 'ABSTAIN']

print(f"  BUY: {len(buy_signals)}")
print(f"  SELL: {len(sell_signals)}")
print(f"  ABSTAIN: {len(abstain_signals)} ({len(abstain_signals)/len(predictions)*100:.1f}%)")
```

### Using Config File

```python
import yaml
from packages.strategies.ml_direction_v1 import MLDirectionStrategyV1

# Load config
with open('configs/strategies/ml_direction_v1.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Create strategy
strategy = MLDirectionStrategyV1(
    strategy_id=config['strategy_id'],
    config=config,
)
```

---

## Viewing Predictions

### Python

```python
import json

# Load predictions
predictions = []
with open('logs/predictions.jsonl', 'r') as f:
    for line in f:
        predictions.append(json.loads(line))

# Analyze a prediction
pred = predictions[0]
print(f"Symbol: {pred['symbol']}")
print(f"Timestamp: {pred['timestamp']}")
print(f"Signal: {pred['signal']}")
print(f"Confidence: {pred['confidence']:.2%}")
print(f"\nExplanation:")
print(f"  {pred['explanation']['rationale']}")
print(f"\nTop Features:")
for feat in pred['explanation']['top_features'][:3]:
    print(f"  {feat['name']}: {feat['value']:.2f}")
```

### Command Line (with jq)

```bash
# View latest prediction
tail -n 1 logs/predictions.jsonl | jq .

# Count signals by type
cat logs/predictions.jsonl | jq -s 'group_by(.signal) | map({signal: .[0].signal, count: length})'

# High confidence BUY signals
cat logs/predictions.jsonl | jq 'select(.signal == "BUY" and .confidence > 0.8)'

# Abstention reasons
cat logs/predictions.jsonl | jq 'select(.signal == "ABSTAIN") | .explanation.rationale'

# Average confidence by signal type
cat logs/predictions.jsonl | jq -s '
  group_by(.signal) |
  map({
    signal: .[0].signal,
    avg_confidence: (map(.confidence) | add / length),
    count: length
  })
'
```

---

## Configuration Options

See `configs/strategies/ml_direction_v1.yaml` for all options:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `model_path` | `models/first_model_v1.pkl` | Path to trained model |
| `position_size_pct` | `0.1` | Position size as fraction of equity |
| `abstain_threshold` | `0.55` | Confidence below this → ABSTAIN |
| `low_confidence_threshold` | `0.65` | Low confidence band |
| `high_confidence_threshold` | `0.85` | High confidence band |
| `min_bars_for_features` | `200` | Min bars for feature computation |
| `prediction_log_path` | `logs/predictions.jsonl` | Prediction log path |

---

## Understanding ABSTAIN

The model can choose to **ABSTAIN** (not trade) when confidence is low:

- **Threshold:** Configurable via `abstain_threshold` (default: 0.55)
- **Behavior:** Signal is recorded but NOT converted to an order
- **Tracking:** Logged in prediction log; counted in backtest metadata
- **Goal:** Avoid trading when model is uncertain

**Example:**
- Model predicts UP with 52% confidence
- 52% < 55% threshold → Signal = ABSTAIN
- No order is generated; strategy waits for next bar

**Tuning:**
- **Lower threshold** (e.g., 0.50) → Trade more often, lower confidence
- **Higher threshold** (e.g., 0.65) → Trade less often, higher confidence
- Monitor abstention rate in backtest to find balance

---

## Comparing to SMA Crossover

Run both strategies on same data to compare:

```python
from packages.strategies.sma_crossover import SMACrossoverStrategy

# Run SMA Crossover
sma_strategy = SMACrossoverStrategy(
    strategy_id='sma_crossover_v1',
    config={'short_period': 20, 'long_period': 50}
)
sma_result = BacktestEngine(sma_strategy, bars, initial_cash).run()

# Run ML Direction
ml_strategy = MLDirectionStrategyV1(
    strategy_id='ml_direction_v1',
    config={'model_path': 'models/first_model_v1.pkl'}
)
ml_result = BacktestEngine(ml_strategy, bars, initial_cash).run()

# Compare
print(f"SMA Crossover Sharpe: {sma_result['sharpe_ratio']:.2f}")
print(f"ML Direction Sharpe: {ml_result['sharpe_ratio']:.2f}")
```

---

## Troubleshooting

### "Model file not found"

**Solution:** Train the model first:
```bash
poetry run python -m services.ml.training.train_first_model \
    --data-file data/your_data.csv \
    --output-path models/first_model_v1.pkl
```

### "Insufficient bars for features"

**Cause:** Need 200+ bars for indicator computation (e.g., SMA-200)

**Solution:** Provide more historical data or reduce `min_bars_for_features` (but this may break indicators)

### "NaN in features"

**Cause:** Early bars have NaN due to indicator lookback

**Behavior:** Strategy returns ABSTAIN signal; logs warning

**Solution:** This is expected; strategy will trade once enough bars are available

### All predictions are ABSTAIN

**Possible causes:**
1. Confidence threshold too high → Lower `abstain_threshold`
2. Model confidence genuinely low → Check validation metrics from training
3. Feature distribution mismatch → Retrain on relevant data period

---

## Next Steps

- **Sprint 8:** Drift detection, performance tracking, advanced explainability (SHAP)
- **Sprint 9:** Model observatory dashboard, comparison UI, parameter tuning
- **Multiple models:** Train models on different symbols, horizons, or features
- **Ensemble:** Combine multiple models with voting or weighted averaging

---

## References

- `docs/sprint-7-ml-problem-definition.md` — Problem definition
- `docs/training-first-model.md` — How to train the model
- `docs/model-interface-contract.md` — Model I/O specification
- `docs/sprint-7-inference-and-explainability.md` — Implementation details
- `configs/strategies/ml_direction_v1.yaml` — Strategy configuration
