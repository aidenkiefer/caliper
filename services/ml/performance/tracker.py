"""
Performance tracker for ML models.

Logs prediction vs outcome, computes rolling accuracy/error metrics,
and tracks abstention rates over time.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
from collections import deque


class PerformanceRecord:
    """Single prediction-outcome pair."""

    def __init__(
        self,
        prediction_id: str,
        model_id: str,
        timestamp: datetime,
        symbol: str,
        predicted_direction: int,  # 0 (DOWN) or 1 (UP)
        confidence: float,
        signal: str,  # "BUY", "SELL", "ABSTAIN"
        bar_close: float,
        outcome_close: Optional[float] = None,
        outcome_direction: Optional[int] = None,
        is_correct: Optional[bool] = None,
        outcome_timestamp: Optional[datetime] = None,
    ):
        self.prediction_id = prediction_id
        self.model_id = model_id
        self.timestamp = timestamp
        self.symbol = symbol
        self.predicted_direction = predicted_direction
        self.confidence = confidence
        self.signal = signal
        self.bar_close = bar_close
        self.outcome_close = outcome_close
        self.outcome_direction = outcome_direction
        self.is_correct = is_correct
        self.outcome_timestamp = outcome_timestamp

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prediction_id": self.prediction_id,
            "model_id": self.model_id,
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
            "predicted_direction": self.predicted_direction,
            "confidence": self.confidence,
            "signal": self.signal,
            "bar_close": self.bar_close,
            "outcome_close": self.outcome_close,
            "outcome_direction": self.outcome_direction,
            "is_correct": self.is_correct,
            "outcome_timestamp": self.outcome_timestamp.isoformat()
            if self.outcome_timestamp
            else None,
        }


class PerformanceTracker:
    """
    Track model performance over time.

    Maintains:
    - Prediction-outcome records
    - Rolling accuracy metrics
    - Abstention rates
    - Error metrics
    """

    def __init__(
        self,
        model_id: str,
        storage_path: str = "logs/performance.jsonl",
        rolling_window_days: int = 30,
    ):
        """
        Initialize tracker.

        Args:
            model_id: Model identifier
            storage_path: Path to performance log file
            rolling_window_days: Window for rolling metrics (days)
        """
        self.model_id = model_id
        self.storage_path = Path(storage_path)
        self.rolling_window_days = rolling_window_days

        # In-memory cache for fast rolling calculations
        self.records: deque[PerformanceRecord] = deque(maxlen=10000)

        # Ensure directory exists
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing records
        self._load_records()

    def _load_records(self):
        """Load existing records from storage."""
        if not self.storage_path.exists():
            return

        with open(self.storage_path, "r") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    if data.get("model_id") == self.model_id:
                        record = PerformanceRecord(
                            prediction_id=data["prediction_id"],
                            model_id=data["model_id"],
                            timestamp=datetime.fromisoformat(data["timestamp"]),
                            symbol=data["symbol"],
                            predicted_direction=data["predicted_direction"],
                            confidence=data["confidence"],
                            signal=data["signal"],
                            bar_close=data["bar_close"],
                            outcome_close=data.get("outcome_close"),
                            outcome_direction=data.get("outcome_direction"),
                            is_correct=data.get("is_correct"),
                            outcome_timestamp=datetime.fromisoformat(data["outcome_timestamp"])
                            if data.get("outcome_timestamp")
                            else None,
                        )
                        self.records.append(record)
                except Exception as e:
                    print(f"Warning: Failed to load record: {e}")

    def log_prediction(
        self,
        prediction_id: str,
        timestamp: datetime,
        symbol: str,
        predicted_direction: int,
        confidence: float,
        signal: str,
        bar_close: float,
    ):
        """
        Log a new prediction (outcome not yet known).

        Args:
            prediction_id: Unique prediction identifier
            timestamp: Prediction timestamp
            symbol: Trading symbol
            predicted_direction: 0 (DOWN) or 1 (UP)
            confidence: Model confidence
            signal: "BUY", "SELL", or "ABSTAIN"
            bar_close: Close price of the bar
        """
        record = PerformanceRecord(
            prediction_id=prediction_id,
            model_id=self.model_id,
            timestamp=timestamp,
            symbol=symbol,
            predicted_direction=predicted_direction,
            confidence=confidence,
            signal=signal,
            bar_close=bar_close,
        )

        self.records.append(record)
        self._append_to_storage(record)

    def update_outcome(
        self,
        prediction_id: str,
        outcome_close: float,
        outcome_timestamp: datetime,
    ):
        """
        Update a prediction record with the realized outcome.

        Args:
            prediction_id: Prediction ID to update
            outcome_close: Close price of the outcome bar
            outcome_timestamp: Outcome timestamp
        """
        # Find record in cache
        record = None
        for r in self.records:
            if r.prediction_id == prediction_id:
                record = r
                break

        if record is None:
            print(f"Warning: Prediction {prediction_id} not found")
            return

        # Compute outcome direction
        outcome_direction = 1 if outcome_close > record.bar_close else 0

        # Check if prediction was correct
        is_correct = record.predicted_direction == outcome_direction

        # Update record
        record.outcome_close = outcome_close
        record.outcome_direction = outcome_direction
        record.is_correct = is_correct
        record.outcome_timestamp = outcome_timestamp

        # Re-write to storage (append updated record)
        self._append_to_storage(record)

    def _append_to_storage(self, record: PerformanceRecord):
        """Append record to storage file."""
        with open(self.storage_path, "a") as f:
            f.write(json.dumps(record.to_dict()) + "\n")

    def get_rolling_accuracy(self, window_days: Optional[int] = None) -> Optional[float]:
        """
        Compute rolling accuracy over recent predictions.

        Args:
            window_days: Window in days (uses default if None)

        Returns:
            Accuracy (0.0 to 1.0) or None if no completed predictions
        """
        window = window_days or self.rolling_window_days
        cutoff = datetime.now() - timedelta(days=window)

        completed = [
            r
            for r in self.records
            if r.is_correct is not None and r.signal != "ABSTAIN" and r.timestamp >= cutoff
        ]

        if not completed:
            return None

        correct = sum(1 for r in completed if r.is_correct)
        return correct / len(completed)

    def get_abstention_rate(self, window_days: Optional[int] = None) -> float:
        """
        Compute abstention rate over recent predictions.

        Args:
            window_days: Window in days (uses default if None)

        Returns:
            Abstention rate (0.0 to 1.0)
        """
        window = window_days or self.rolling_window_days
        cutoff = datetime.now() - timedelta(days=window)

        recent = [r for r in self.records if r.timestamp >= cutoff]

        if not recent:
            return 0.0

        abstained = sum(1 for r in recent if r.signal == "ABSTAIN")
        return abstained / len(recent)

    def get_metrics(self, window_days: Optional[int] = None) -> Dict[str, Any]:
        """
        Get comprehensive performance metrics.

        Args:
            window_days: Window in days (uses default if None)

        Returns:
            Dictionary of metrics
        """
        window = window_days or self.rolling_window_days
        cutoff = datetime.now() - timedelta(days=window)

        recent = [r for r in self.records if r.timestamp >= cutoff]
        completed = [r for r in recent if r.is_correct is not None and r.signal != "ABSTAIN"]

        total = len(recent)
        completed_count = len(completed)
        abstained = sum(1 for r in recent if r.signal == "ABSTAIN")

        # Accuracy metrics
        accuracy = None
        avg_confidence = None
        if completed_count > 0:
            correct = sum(1 for r in completed if r.is_correct)
            accuracy = correct / completed_count
            avg_confidence = sum(r.confidence for r in completed) / completed_count

        # Confidence by correctness
        correct_confidence = None
        incorrect_confidence = None
        if completed_count > 0:
            correct_preds = [r for r in completed if r.is_correct]
            incorrect_preds = [r for r in completed if not r.is_correct]
            if correct_preds:
                correct_confidence = sum(r.confidence for r in correct_preds) / len(correct_preds)
            if incorrect_preds:
                incorrect_confidence = sum(r.confidence for r in incorrect_preds) / len(
                    incorrect_preds
                )

        return {
            "model_id": self.model_id,
            "window_days": window,
            "total_predictions": total,
            "completed_predictions": completed_count,
            "abstained_predictions": abstained,
            "abstention_rate": abstained / total if total > 0 else 0.0,
            "accuracy": accuracy,
            "avg_confidence": avg_confidence,
            "correct_avg_confidence": correct_confidence,
            "incorrect_avg_confidence": incorrect_confidence,
            "timestamp": datetime.now().isoformat(),
        }
