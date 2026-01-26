# Drift Detection Service

Monitors model performance and data distribution changes to detect when models are degrading.

## Features

- **Feature Distribution Drift**: PSI, KL divergence, mean shift
- **Confidence Drift**: Tracks changes in prediction confidence
- **Error Drift**: Monitors prediction errors when ground truth available
- **Health Score**: Composite 0-100 score based on all drift signals
- **Threshold Alerts**: Automatic warnings and critical alerts

## Usage

```python
from services.ml.drift import DriftDetector, HealthScore, DriftAlertManager

# Initialize with reference data
detector = DriftDetector(
    reference_features={"feature1": ref_array, "feature2": ref_array2},
    reference_confidence=0.75
)

# Detect feature drift
current_features = {"feature1": current_array, "feature2": current_array2}
metrics = detector.detect_feature_drift(current_features, model_id="model-1")

# Calculate health score
health_score = HealthScore(last_retraining_date=datetime(2024, 1, 1))
score = health_score.calculate(
    feature_metrics=metrics,
    confidence_metric=confidence_metric
)

# Check for alerts
alert_manager = DriftAlertManager()
alerts = alert_manager.check_thresholds(metrics[0])
```

## Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| PSI | 0.1 | 0.25 |
| KL Divergence | 0.1 | 0.2 |
| Mean Shift | 2 std | 3 std |
| Confidence Drift | 10% | 20% |

## Health Score Components

- Feature drift (30%)
- Confidence drift (30%)
- Error drift (20%)
- Staleness (20%)
