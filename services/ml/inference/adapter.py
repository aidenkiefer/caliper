"""
Model inference adapter: converts model outputs to trading signals.

This module bridges the ML layer and the strategy layer by:
1. Loading trained models
2. Running inference on feature vectors
3. Applying confidence gating
4. Converting to Signal objects for the execution pipeline

References:
    - docs/sprint-7-ml-problem-definition.md
    - packages/common/ml_schemas.py (ModelInput, ModelPrediction, ModelInferenceOutput)
    - services/ml/confidence/gating.py (ConfidenceGating)
"""

import pickle
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from packages.common.ml_schemas import ModelInput, ModelPrediction, ModelInferenceOutput
from packages.strategies.base import Signal
from services.ml.confidence.gating import ConfidenceGating, ConfidenceConfig
from services.ml.confidence.uncertainty import compute_entropy


class ModelInferenceAdapter:
    """
    Adapter for loading models and converting predictions to signals.

    This class handles:
    - Model loading and initialization
    - Feature vector preparation
    - Inference execution
    - Confidence gating application
    - Signal generation

    Usage:
        adapter = ModelInferenceAdapter.from_file('models/first_model_v1.pkl')
        signal = adapter.predict_and_convert(
            symbol='SPY',
            timestamp=datetime.now(),
            features={'sma_20': 450.0, 'rsi_14': 65.0, ...}
        )
    """

    def __init__(
        self,
        model: Any,
        feature_names: list[str],
        metadata: Dict[str, Any],
        confidence_config: Optional[ConfidenceConfig] = None,
    ):
        """
        Initialize adapter with model and configuration.

        Args:
            model: Trained scikit-learn model
            feature_names: List of feature names expected by model
            metadata: Training metadata
            confidence_config: Confidence gating config (uses defaults if None)
        """
        self.model = model
        self.feature_names = feature_names
        self.metadata = metadata

        # Default confidence config if not provided
        if confidence_config is None:
            confidence_config = ConfidenceConfig(
                strategy_id="ml_strategy_v1",
                abstain_threshold=0.55,
                low_confidence_threshold=0.65,
                high_confidence_threshold=0.85,
            )

        self.gating = ConfidenceGating(confidence_config)

    @classmethod
    def from_file(
        cls,
        model_path: str,
        confidence_config: Optional[ConfidenceConfig] = None,
    ) -> "ModelInferenceAdapter":
        """
        Load model from disk and create adapter.

        Args:
            model_path: Path to pickled model file
            confidence_config: Optional confidence config

        Returns:
            Initialized adapter
        """
        model_path = Path(model_path)

        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")

        with open(model_path, "rb") as f:
            package = pickle.load(f)

        return cls(
            model=package["model"],
            feature_names=package["feature_names"],
            metadata=package["metadata"],
            confidence_config=confidence_config,
        )

    def prepare_features(self, features: Dict[str, float]) -> np.ndarray:
        """
        Convert feature dictionary to numpy array in correct order.

        Args:
            features: Dictionary of feature values

        Returns:
            Feature array [1, n_features] ready for model input

        Raises:
            ValueError: If any required features are missing
        """
        # Check for missing features
        missing = set(self.feature_names) - set(features.keys())
        if missing:
            raise ValueError(f"Missing required features: {missing}")

        # Build feature array in correct order
        feature_array = np.array([features[name] for name in self.feature_names])

        # Check for NaN
        if np.any(np.isnan(feature_array)):
            nan_features = [
                name for name, val in zip(self.feature_names, feature_array) if np.isnan(val)
            ]
            raise ValueError(f"NaN values in features: {nan_features}")

        # Reshape for single prediction
        return feature_array.reshape(1, -1)

    def predict_raw(self, feature_array: np.ndarray) -> ModelPrediction:
        """
        Run model inference and return raw prediction.

        Args:
            feature_array: Prepared feature array [1, n_features]

        Returns:
            ModelPrediction with raw model output
        """
        # Get prediction and probability
        prediction = int(self.model.predict(feature_array)[0])  # 0 or 1
        probabilities = self.model.predict_proba(feature_array)[0]  # [p_down, p_up]

        # Extract UP probability (class 1)
        raw_probability = float(probabilities[1])

        # Confidence: distance from decision boundary (max of p_up, p_down)
        confidence = float(max(probabilities))

        return ModelPrediction(
            prediction=prediction,
            confidence=confidence,
            raw_probability=raw_probability,
            features_used=self.feature_names,
        )

    def apply_confidence_gating(
        self,
        raw_pred: ModelPrediction,
    ) -> ModelInferenceOutput:
        """
        Apply confidence gating to raw prediction.

        Args:
            raw_pred: Raw model prediction

        Returns:
            Gated output (may convert to ABSTAIN)
        """
        # Determine raw signal
        raw_signal = raw_pred.to_signal_side()  # BUY or SELL

        # Compute uncertainty (entropy of probability distribution)
        p_up = raw_pred.raw_probability
        p_down = 1.0 - p_up
        uncertainty = compute_entropy([p_down, p_up])

        # Apply gating
        if self.gating.should_abstain(raw_pred.confidence):
            signal = "ABSTAIN"
            abstain_reason = f"confidence {raw_pred.confidence:.3f} below threshold {self.gating.config.abstain_threshold:.3f}"
        else:
            signal = raw_signal
            abstain_reason = None

        return ModelInferenceOutput(
            signal=signal,
            confidence=raw_pred.confidence,
            uncertainty=uncertainty,
            raw_probability=raw_pred.raw_probability,
            features_used=raw_pred.features_used,
            abstain_reason=abstain_reason,
        )

    def to_signal(
        self,
        symbol: str,
        inference_output: ModelInferenceOutput,
    ) -> Signal:
        """
        Convert ModelInferenceOutput to Signal object.

        Args:
            symbol: Trading symbol
            inference_output: Gated inference output

        Returns:
            Signal for strategy layer
        """
        return Signal(
            symbol=symbol,
            side=inference_output.signal,
            strength=inference_output.confidence,
            reason=f"ML model prediction (confidence={inference_output.confidence:.3f})",
        )

    def predict_and_convert(
        self,
        symbol: str,
        timestamp: datetime,
        features: Dict[str, float],
    ) -> Signal:
        """
        Complete inference pipeline: features → prediction → gating → signal.

        This is the main entry point for strategies using ML models.

        Args:
            symbol: Trading symbol
            timestamp: Prediction timestamp
            features: Feature dictionary

        Returns:
            Signal (BUY/SELL/ABSTAIN)
        """
        # Prepare features
        feature_array = self.prepare_features(features)

        # Run inference
        raw_pred = self.predict_raw(feature_array)

        # Apply gating
        inference_output = self.apply_confidence_gating(raw_pred)

        # Convert to signal
        signal = self.to_signal(symbol, inference_output)

        return signal

    def predict(
        self,
        model_input: ModelInput,
    ) -> ModelInferenceOutput:
        """
        Alternative entry point using ModelInput schema.

        Args:
            model_input: Structured model input

        Returns:
            Complete inference output
        """
        feature_array = self.prepare_features(model_input.features)
        raw_pred = self.predict_raw(feature_array)
        return self.apply_confidence_gating(raw_pred)

    def _build_model_input(
        self,
        symbol: str,
        timestamp: datetime,
        features: Dict[str, float],
    ) -> ModelInput:
        """
        Helper to build ModelInput from components.

        Args:
            symbol: Trading symbol
            timestamp: Prediction timestamp
            features: Feature dictionary

        Returns:
            ModelInput schema
        """
        return ModelInput(
            symbol=symbol,
            timestamp=timestamp,
            features=features,
        )
