# Stress Scenarios & Failure Modes Runbook

## Overview

This runbook documents the system's behavior under stress and failure conditions. Each scenario includes:
- **Trigger:** What causes the scenario
- **Expected Behavior:** How the system should respond
- **Monitoring:** How to detect the scenario
- **Mitigation:** Steps to resolve or prevent
- **Simulation:** How to reproduce for testing

**Last Updated:** 2026-02-02
**Applies To:** Sprint 7-8 ML model (`ml_direction_v1`)

---

## Scenario 1: Missing Data / NaN Features

### Trigger

- **Insufficient bars:** Fewer than 200 bars available for indicator computation
- **Data gaps:** Market closures, data provider downtime, network issues
- **Feature pipeline failure:** Errors during feature computation

### Expected Behavior

1. **Strategy:** Returns empty signal list (no trades)
2. **When features computed:** NaN values in feature vector
3. **Inference adapter:** Raises `ValueError` in `prepare_features()`
4. **Fallback:** Strategy catches exception, returns ABSTAIN signal
5. **Logging:** Warning logged to prediction log with error reason

```json
{
  "signal": "ABSTAIN",
  "explanation": {
    "rationale": "Inference error: NaN values in features: ['sma_200', 'ema_26']"
  }
}
```

### Monitoring

- **Alert on:** Spike in ABSTAIN signals with "NaN" in rationale
- **Check:** `logs/predictions.jsonl` for NaN-related abstentions
- **Metric:** Abstention rate > 20% (investigate)

```bash
# Count NaN-related abstentions
cat logs/predictions.jsonl | jq 'select(.signal == "ABSTAIN" and (.explanation.rationale | contains("NaN")))' | wc -l
```

### Mitigation

**Short-term:**
- System continues without trades (safe default)
- Manual verification of data feed

**Long-term:**
- Ensure minimum 200 bars before enabling strategy
- Add data quality checks before feature computation
- Fallback to last known good features (with staleness warning)

### Simulation

```python
# tests/stress/test_missing_data.py
import numpy as np
from packages.strategies.ml_direction_v1 import MLDirectionStrategyV1

strategy = MLDirectionStrategyV1('ml_direction_v1', config)
strategy.initialize('BACKTEST')

# Inject NaN into features
bars = load_bars()
bars_with_nan = bars[:50]  # Too few for indicators

signals = strategy.generate_signals(portfolio)
assert len(signals) == 0 or signals[0].side == 'ABSTAIN'
```

---

## Scenario 2: Extreme Volatility Spike

### Trigger

- **Market crash/rally:** Price movements > 3σ from recent average
- **Flash crash:** Sudden large price movement (>10% in single bar)
- **Data error:** Bad tick data from provider

### Expected Behavior

1. **Feature values:** Outlier features (e.g., ATR spike, returns > 3σ)
2. **Model confidence:** Likely drops due to distribution shift
3. **Confidence gating:** Higher chance of ABSTAIN if confidence < 0.55
4. **Risk manager:** May reject orders due to max price deviation limit
5. **Circuit breaker:** Triggers on drawdown threshold (5% strategy, 10% portfolio)

**Example:**
- Normal: `returns_1d = 0.01` (1% move)
- Spike: `returns_1d = 0.15` (15% move)
- Model sees unusual feature values → lower confidence → ABSTAIN

### Monitoring

- **Alert on:**
  - Volatility indicator (ATR) > 2x recent average
  - Returns > 3σ
  - Circuit breaker triggered
  - Sudden spike in abstentions

```bash
# Check for high volatility abstentions
cat logs/predictions.jsonl | jq 'select(.signal == "ABSTAIN" and .explanation.abstain_reason != null) | {timestamp, symbol, confidence, reason: .explanation.abstain_reason}'
```

### Mitigation

**Automatic:**
- Confidence gating filters low-confidence signals
- Risk manager rejects orders exceeding limits
- Circuit breaker pauses trading on drawdown

**Manual:**
- Review abstention log during high volatility
- Consider increasing abstain_threshold temporarily (e.g., 0.55 → 0.65)
- Verify data quality (rule out bad ticks)

### Simulation

```python
# tests/stress/test_volatility_spike.py
bars = load_bars()

# Scale returns by 3x to simulate volatility spike
for bar in bars[-10:]:
    bar.high = bar.close * 1.15
    bar.low = bar.close * 0.85

strategy.on_market_data(bar)
signals = strategy.generate_signals(portfolio)

# Expect ABSTAIN or higher risk rejection rate
if signals:
    assert signals[0].confidence < 0.60  # Lower confidence
```

---

## Scenario 3: Broker API Outage

### Trigger

- **Network failure:** Loss of connection to broker
- **Broker downtime:** Scheduled maintenance or system failure
- **Rate limit:** Exceeded API request limits
- **Authentication error:** Expired credentials

### Expected Behavior

1. **Order submission fails:** `BrokerClient.submit_order()` raises exception
2. **OMS retry logic:** Attempts 3 retries with exponential backoff
3. **After retries:** Order marked as FAILED; alert raised
4. **Position reconciliation:** Cannot sync with broker; uses cached positions
5. **Trading paused:** No new orders until connection restored
6. **Dashboard:** Shows "Broker Disconnected" warning

### Monitoring

- **Alert on:**
  - Order submission failure rate > 10%
  - Position reconciliation mismatch
  - Broker connection timeout
  - No fills received for > 5 minutes (during market hours)

```bash
# Check for broker errors in logs
grep "BrokerError\|ConnectionError" logs/execution.log

# Check order failure rate
cat logs/orders.jsonl | jq 'select(.status == "FAILED") | {timestamp, symbol, reason: .reject_reason}'
```

### Mitigation

**Automatic:**
- Retry logic with backoff (3 attempts)
- Fallback to cached positions
- Trading paused after repeated failures

**Manual:**
1. **Immediate:**
   - Verify broker status (check broker website)
   - Verify network connectivity
   - Check API credentials (not expired)

2. **If broker is down:**
   - Wait for broker to restore service
   - Do NOT attempt manual orders (may cause position mismatch)
   - Monitor open positions via broker web UI

3. **If credentials expired:**
   - Rotate credentials
   - Update `configs/environments/.env`
   - Restart execution service

4. **If rate limited:**
   - Reduce polling frequency
   - Increase delay between requests

### Simulation

```python
# tests/stress/test_api_outage.py
from unittest.mock import patch, Mock
from services.execution.broker_client import BrokerClient

# Mock broker timeout
with patch.object(BrokerClient, 'submit_order', side_effect=TimeoutError("API timeout")):
    oms = OrderManagementSystem(broker_client)
    order = create_test_order()

    result = oms.submit_order(order)

    assert result.status == 'FAILED'
    assert 'timeout' in result.reject_reason.lower()
```

---

## Scenario 4: Model Drift / Stale Model

### Trigger

- **Distribution shift:** Market regime change; feature distributions diverge from training
- **Time decay:** Model trained on old data; performance degrades over time
- **Data quality change:** Data provider changes methodology

### Expected Behavior

1. **Drift detector:** PSI or KL divergence exceeds threshold (e.g., PSI > 0.2)
2. **Health score:** Drops below 70/100
3. **Alert raised:** "Model drift detected for ml_direction_v1"
4. **Performance degrades:** Accuracy drops; regret vs baselines increases
5. **Recommendation:** Human review required; consider retraining

**No automatic trading pause** (requires human decision)

### Monitoring

- **Alert on:**
  - Drift metric (PSI) > 0.2 or (KL) > 0.3
  - Health score < 70
  - Rolling accuracy < baseline (buy & hold)
  - Days since training > 90

```bash
# Check drift via API
curl http://localhost:8000/v1/drift/health/ml_direction_v1

# Check recent accuracy
curl http://localhost:8000/v1/metrics/performance/ml_direction_v1?window_days=30
```

### Mitigation

**Short-term:**
- Monitor performance closely
- Increase abstain_threshold (e.g., 0.55 → 0.65) to trade only high-confidence signals
- Compare regret vs baselines

**Long-term:**
- Retrain model on recent data
- Consider online learning or scheduled retraining (e.g., monthly)
- Evaluate if feature set needs updating

### Simulation

```python
# Simulate drift by feeding out-of-distribution features
from services.ml.drift.detector import DriftDetector

detector = DriftDetector(reference_distributions)

# Shift feature distributions
drifted_features = {
    feat: val + 2 * reference_std  # Shift by 2 std devs
    for feat, val in current_features.items()
}

drift_metrics = detector.detect_drift(drifted_features)
assert drift_metrics['psi'] > 0.2  # Significant drift
```

---

## Scenario 5: Memory / Resource Exhaustion

### Trigger

- **Long-running backtest:** Processing years of data
- **Memory leak:** Unbounded cache growth
- **Too many open positions:** Tracking hundreds of symbols

### Expected Behavior

1. **Performance degradation:** Slower signal generation
2. **Memory alert:** OS or container near memory limit
3. **Process crash:** Out-of-memory error (worst case)

### Monitoring

- **Alert on:**
  - Memory usage > 80% of limit
  - Signal generation time > 1 second
  - Process restart (crash)

### Mitigation

**Preventive:**
- Limit price history buffer (current: 250 bars max)
- Limit in-memory performance records (current: 10,000 max)
- Use generators for large backtests
- Periodic cache cleanup

**Reactive:**
- Restart process
- Reduce buffer sizes in config
- Split large backtests into chunks

---

## Emergency Procedures

### Kill Switch Activation

**When:** Severe loss, system malfunction, manual override needed

```python
# Via API
curl -X POST http://localhost:8000/v1/controls/kill-switch \
    -H "Content-Type: application/json" \
    -d '{"active": true, "reason": "Manual override - investigating anomaly"}'
```

**Effect:**
- All new orders blocked
- Open positions remain (not automatically closed)
- Requires explicit deactivation to resume

### Position Reconciliation Failure

**When:** Local position state diverges from broker

**Action:**
1. Pause trading (activate kill switch)
2. Query broker positions via web UI or API
3. Compare to local state in logs
4. Manually reconcile discrepancies
5. Update local state if needed
6. Resume trading after verification

### Data Feed Loss

**When:** No new bars received for > 15 minutes (during market hours)

**Action:**
1. Verify network connectivity
2. Check data provider status
3. Verify API credentials
4. Restart data service if needed
5. Backfill missing bars if gap exists

---

## Runbook Maintenance

**Review Frequency:** After each sprint or incident

**Update Triggers:**
- New failure mode discovered
- Mitigation strategy changed
- Monitoring threshold adjusted

**Owner:** SRE / Model Owner

---

## Related Documents

- `docs/risk-policy.md` — Risk limits and circuit breakers
- `docs/model-interface-contract.md` — Model I/O contracts and failure modes
- `docs/sprint-7-inference-and-explainability.md` — Inference pipeline details
- `docs/sprint-8-implementation-summary.md` — Observability and safety features

---

## Appendix: Simulation Scripts

All stress simulation scripts are in `tests/stress/`:

```bash
# Run all stress tests
poetry run pytest tests/stress/ -v

# Run specific scenario
poetry run pytest tests/stress/test_missing_data.py -v
poetry run pytest tests/stress/test_volatility_spike.py -v
poetry run pytest tests/stress/test_api_outage.py -v
```

**Note:** Simulations use mock data and do not affect production systems.
