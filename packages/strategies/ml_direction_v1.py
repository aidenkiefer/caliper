"""
ML Direction Strategy V1.

First ML-powered strategy: uses trained logistic regression model
to predict next-bar price direction and generate BUY/SELL/ABSTAIN signals.

This strategy integrates:
- Trained model (from 07-02)
- Feature pipeline (services/features)
- Confidence gating (services/ml/confidence)
- Prediction logging with explanations (07-05)
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from decimal import Decimal
from pathlib import Path
import json

from packages.common.schemas import (
    PriceBar,
    Order,
    Position,
    TradingMode,
    OrderSide,
    OrderType,
    TimeInForce,
)
from packages.common.ml_schemas import ModelInferenceOutput
from .base import Strategy, Signal, PortfolioState

from services.features.pipeline import FeaturePipeline
from services.ml.inference.adapter import ModelInferenceAdapter
from services.ml.confidence.gating import ConfidenceConfig
from services.ml.explainability.simple_explainer import SimpleExplainer


class MLDirectionStrategyV1(Strategy):
    """
    ML-powered direction prediction strategy.

    Uses a trained binary classifier to predict next-bar direction (UP/DOWN)
    and applies confidence gating to produce BUY/SELL/ABSTAIN signals.

    Configuration:
        - model_path: Path to trained model pickle file
        - position_size_pct: Percentage of equity per position (default: 0.1 = 10%)
        - abstain_threshold: Confidence below this triggers ABSTAIN (default: 0.55)
        - low_confidence_threshold: Low confidence band (default: 0.65)
        - high_confidence_threshold: High confidence band (default: 0.85)
        - prediction_log_path: Where to log predictions (default: logs/predictions.jsonl)
        - min_bars_for_features: Minimum bars needed for feature computation (default: 200)
    """

    def __init__(self, strategy_id: str, config: Dict[str, Any]):
        super().__init__(strategy_id, config)

        # Strategy parameters
        self.model_path = config.get("model_path", "models/first_model_v1.pkl")
        self.position_size_pct = Decimal(str(config.get("position_size_pct", 0.1)))
        self.min_bars_for_features = config.get("min_bars_for_features", 200)
        self.prediction_log_path = Path(config.get("prediction_log_path", "logs/predictions.jsonl"))

        # Confidence thresholds
        confidence_config = ConfidenceConfig(
            strategy_id=strategy_id,
            abstain_threshold=config.get("abstain_threshold", 0.55),
            low_confidence_threshold=config.get("low_confidence_threshold", 0.65),
            high_confidence_threshold=config.get("high_confidence_threshold", 0.85),
        )

        # Initialize components
        self.feature_pipeline = FeaturePipeline()
        self.adapter: Optional[ModelInferenceAdapter] = None
        self.explainer: Optional[SimpleExplainer] = None

        # Load model in initialize() to allow for mode-specific paths
        self.confidence_config = confidence_config

        # Internal state
        self.price_history: List[PriceBar] = []
        self.current_position: Optional[Position] = None
        self.prediction_count = 0

        # Ensure log directory exists
        self.prediction_log_path.parent.mkdir(parents=True, exist_ok=True)

    def initialize(self, mode: TradingMode) -> None:
        """Initialize strategy and load model."""
        self.mode = mode
        self.initialized = True
        self.price_history = []
        self.current_position = None
        self.prediction_count = 0

        # Load model
        try:
            self.adapter = ModelInferenceAdapter.from_file(
                model_path=self.model_path,
                confidence_config=self.confidence_config,
            )
            print(f"✓ Loaded model from {self.model_path}")
            print(f"  Features: {len(self.adapter.feature_names)}")
            print(f"  Abstain threshold: {self.confidence_config.abstain_threshold}")
        except Exception as e:
            raise RuntimeError(f"Failed to load model from {self.model_path}: {e}")

        # Initialize explainer
        self.explainer = SimpleExplainer(
            feature_names=self.adapter.feature_names,
            model_type=self.adapter.metadata.get("model_type", "unknown"),
        )

    def on_market_data(self, bar: PriceBar) -> None:
        """Store price bar in history."""
        self.price_history.append(bar)

        # Keep enough history for features (200+ bars for indicators)
        max_history = self.min_bars_for_features + 50
        if len(self.price_history) > max_history:
            self.price_history = self.price_history[-max_history:]

    def generate_signals(self, portfolio: PortfolioState) -> List[Signal]:
        """
        Generate ML-based trading signals.

        Process:
        1. Check if we have enough bars for feature computation
        2. Compute features via FeaturePipeline
        3. Run model inference via adapter (includes confidence gating)
        4. Convert ModelInferenceOutput to Signal
        5. Log prediction with explanation
        """
        # Need enough bars for feature computation
        if len(self.price_history) < self.min_bars_for_features:
            return []

        latest_bar = self.price_history[-1]

        try:
            # Step 1: Compute features
            features_df = self.feature_pipeline.compute_features(self.price_history)

            # Get latest feature row (after dropna)
            features_df = features_df.dropna()
            if len(features_df) == 0:
                return []

            latest_features_row = features_df.iloc[-1]

            # Convert to dictionary, excluding timestamp
            feature_dict = {
                k: float(v) for k, v in latest_features_row.to_dict().items() if k != "timestamp"
            }

            # Step 2: Run model inference (includes confidence gating)
            signal = self.adapter.predict_and_convert(
                symbol=latest_bar.symbol,
                timestamp=latest_bar.timestamp,
                features=feature_dict,
            )

            # Step 3: Generate explanation
            inference_output = self.adapter.predict(
                model_input=self.adapter._build_model_input(
                    symbol=latest_bar.symbol,
                    timestamp=latest_bar.timestamp,
                    features=feature_dict,
                )
            )

            explanation = self.explainer.explain(
                features=feature_dict,
                inference_output=inference_output,
                symbol=latest_bar.symbol,
                timestamp=latest_bar.timestamp,
            )

            # Step 4: Log prediction with explanation
            self._log_prediction(signal, inference_output, explanation, latest_bar)

            return [signal]

        except Exception as e:
            # If inference fails, return ABSTAIN signal and log error
            print(f"⚠ Inference failed: {e}")
            error_signal = Signal(
                symbol=latest_bar.symbol,
                side="ABSTAIN",
                strength=0.0,
                reason=f"Inference error: {str(e)[:100]}",
            )
            return [error_signal]

    def risk_check(self, signals: List[Signal], portfolio: PortfolioState) -> List[Order]:
        """
        Convert signals to orders with risk checks.

        Note: ABSTAIN signals are already filtered out by backtest/execution
        engines before reaching here, but we double-check for safety.
        """
        orders = []

        for signal in signals:
            # Skip ABSTAIN signals
            if signal.side == "ABSTAIN":
                continue

            # Check if we already have a position
            existing_position = next(
                (p for p in portfolio.positions if p.symbol == signal.symbol), None
            )

            # Calculate position size
            if signal.side == "BUY":
                # Don't buy if we already have a position
                if existing_position and existing_position.quantity > 0:
                    continue

                # Calculate quantity based on position size percentage
                order_value = portfolio.equity * self.position_size_pct
                quantity = Decimal(
                    str(order_value / float(signal.price or self.price_history[-1].close))
                )

                if quantity > 0:
                    order = Order(
                        order_id=None,  # Will be generated by execution engine
                        strategy_id=self.strategy_id,
                        symbol=signal.symbol,
                        contract_type="STOCK",
                        side=OrderSide.BUY,
                        quantity=quantity,
                        order_type=OrderType.MARKET,
                        time_in_force=TimeInForce.DAY,
                        mode=self.mode,
                        created_at=datetime.now(),
                        updated_at=datetime.now(),
                    )
                    orders.append(order)

            elif signal.side == "SELL":
                # Only sell if we have a position
                if not existing_position or existing_position.quantity <= 0:
                    continue

                # Sell entire position
                order = Order(
                    order_id=None,
                    strategy_id=self.strategy_id,
                    symbol=signal.symbol,
                    contract_type="STOCK",
                    side=OrderSide.SELL,
                    quantity=abs(existing_position.quantity),
                    order_type=OrderType.MARKET,
                    time_in_force=TimeInForce.DAY,
                    mode=self.mode,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )
                orders.append(order)

        return orders

    def _log_prediction(
        self,
        signal: Signal,
        inference_output: ModelInferenceOutput,
        explanation: Dict[str, Any],
        bar: PriceBar,
    ):
        """
        Log prediction with explanation to structured log file.

        Format: JSON Lines (one JSON object per line)
        """
        self.prediction_count += 1

        log_entry = {
            "prediction_id": f"{self.strategy_id}_{self.prediction_count}",
            "strategy_id": self.strategy_id,
            "timestamp": bar.timestamp.isoformat(),
            "symbol": bar.symbol,
            "bar_close": float(bar.close),
            # Model prediction
            "signal": inference_output.signal,
            "confidence": inference_output.confidence,
            "uncertainty": inference_output.uncertainty,
            "raw_probability": inference_output.raw_probability,
            # Explanation
            "explanation": explanation,
            # Metadata
            "mode": str(self.mode),
            "logged_at": datetime.now().isoformat(),
        }

        # Append to log file (JSON Lines format)
        with open(self.prediction_log_path, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

    def on_fill(self, fill: Order) -> None:
        """Update position tracking when order is filled."""
        pass

    def get_state(self) -> Dict[str, Any]:
        """Get strategy state."""
        state = super().get_state()
        state.update(
            {
                "model_path": self.model_path,
                "position_size_pct": float(self.position_size_pct),
                "price_history_length": len(self.price_history),
                "prediction_count": self.prediction_count,
                "confidence_thresholds": {
                    "abstain": self.confidence_config.abstain_threshold,
                    "low": self.confidence_config.low_confidence_threshold,
                    "high": self.confidence_config.high_confidence_threshold,
                },
            }
        )
        return state
