"""
Test fixtures and factory functions for ML services.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timezone
from decimal import Decimal

from services.ml.drift.metrics import DriftMetrics
from services.ml.confidence.gating import ModelOutput, ConfidenceConfig
from services.ml.explainability.schemas import TradeExplanation, FeatureContribution
from services.backtest.models import BacktestConfig, BacktestResult, PerformanceMetrics


def get_mock_drift_metrics(
    model_id: str = "model-1",
    feature_name: str = "feature1",
    psi: float = 0.1,
    kl_divergence: float = 0.1,
    mean_shift: float = 1.0,
) -> DriftMetrics:
    """Factory for DriftMetrics test data."""
    return DriftMetrics(
        feature_name=feature_name,
        model_id=model_id,
        psi=psi,
        kl_divergence=kl_divergence,
        mean_shift=mean_shift,
        timestamp=datetime.utcnow().isoformat(),
    )


def get_mock_model_output(
    signal: str = "BUY",
    confidence: float = 0.75,
    uncertainty: float = 0.2,
) -> ModelOutput:
    """Factory for ModelOutput test data."""
    return ModelOutput(
        signal=signal,
        confidence=confidence,
        uncertainty=uncertainty,
        features_used=["feature1", "feature2", "feature3"],
        raw_probability=confidence,
    )


def get_mock_confidence_config(
    strategy_id: str = "strategy-1",
    abstain_threshold: float = 0.55,
    low_confidence_threshold: float = 0.65,
    high_confidence_threshold: float = 0.85,
) -> ConfidenceConfig:
    """Factory for ConfidenceConfig test data."""
    return ConfidenceConfig(
        strategy_id=strategy_id,
        abstain_threshold=abstain_threshold,
        low_confidence_threshold=low_confidence_threshold,
        high_confidence_threshold=high_confidence_threshold,
    )


def get_mock_trade_explanation(
    trade_id: str = "trade-1",
    signal: str = "BUY",
    confidence: float = 0.8,
    model_id: str = "model-1",
) -> TradeExplanation:
    """Factory for TradeExplanation test data."""
    return TradeExplanation(
        trade_id=trade_id,
        signal=signal,
        confidence=confidence,
        top_features=[
            FeatureContribution(
                feature_name="RSI_14",
                value=35.2,
                contribution=0.15,
                direction="positive",
            ),
            FeatureContribution(
                feature_name="MACD",
                value=2.5,
                contribution=0.12,
                direction="positive",
            ),
            FeatureContribution(
                feature_name="Volume_SMA_20",
                value=1.2,
                contribution=-0.08,
                direction="negative",
            ),
        ],
        model_id=model_id,
        base_value=0.65,
    )


def get_mock_backtest_result(
    strategy_id: str = "strategy-1",
    total_return: Decimal = Decimal("0.10"),
) -> BacktestResult:
    """Factory for BacktestResult test data."""
    return BacktestResult(
        strategy_id=strategy_id,
        config=BacktestConfig(initial_capital=Decimal("100000")),
        equity_curve=[],
        trades=[],
        metrics=PerformanceMetrics(
            total_return=total_return,
            total_return_pct=total_return * Decimal("100"),
            sharpe_ratio=Decimal("1.5"),
            max_drawdown=Decimal("-0.05"),
            max_drawdown_pct=Decimal("-5.0"),
            win_rate=Decimal("0.6"),
            total_trades=20,
            winning_trades=12,
            losing_trades=8,
            avg_win=Decimal("500"),
            avg_loss=Decimal("-300"),
            profit_factor=Decimal("2.0"),
        ),
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc),
        metadata={
            "abstention_metrics": {
                "total_signals": 100,
                "abstentions": 20,
                "abstention_rate": "0.2",
            }
        },
    )


def get_risky_order() -> dict:
    """Order that should fail risk checks (>2% risk)."""
    return {
        "symbol": "AAPL",
        "side": "BUY",
        "quantity": 1000,  # Very large quantity
        "order_type": "MARKET",
    }


def get_safe_order() -> dict:
    """Order that should pass all risk checks."""
    return {
        "symbol": "AAPL",
        "side": "BUY",
        "quantity": 10,  # Small quantity
        "order_type": "MARKET",
    }
