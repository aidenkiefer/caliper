from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from packages.common.polymarket_schemas import FeatureSnapshot
from packages.common.schemas import TradingMode
from packages.strategies.base import PortfolioState
from services.ml.probability_model.schemas import PredictionRecord
from services.regime.schemas import RegimeQualityReport, RegimeState


def make_portfolio() -> PortfolioState:
    return PortfolioState(equity=Decimal("1000"), cash=Decimal("1000"), positions=[])


def make_snapshot(**overrides: Any) -> FeatureSnapshot:
    payload = {
        "market_id": "btc-hourly-1",
        "token_id": "token-1",
        "captured_at": datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        "time_to_close_seconds": 900.0,
        "time_since_open_seconds": 3600.0,
        "mid_price": Decimal("0.55"),
        "implied_probability": Decimal("0.53"),
        "spread": Decimal("0.02"),
        "spread_bps": Decimal("200"),
        "book_depth_bid_5tick": Decimal("100"),
        "book_depth_ask_5tick": Decimal("100"),
        "time_since_last_trade": 5.0,
        "time_since_last_price_change": 5.0,
        "order_book_imbalance": Decimal("0"),
        "trade_flow_imbalance_1m": Decimal("0"),
        "trade_flow_imbalance_5m": Decimal("0"),
        "last_5min_volume_share": Decimal("0.2"),
        "aggressor_buy_fraction_1m": Decimal("0.5"),
        "vpin_proxy": Decimal("0.1"),
        "fee_rate_current": Decimal("0.003"),
        "reward_eligible": True,
        "reward_max_spread": Decimal("0.05"),
        "reward_min_size": Decimal("5"),
        "btc_distance_to_open": Decimal("0"),
        "btc_rv_1m": Decimal("0.01"),
        "btc_rv_5m": Decimal("0.02"),
        "btc_rv_15m": Decimal("0.03"),
        "btc_momentum_5m": Decimal("0"),
        "btc_sign_persistence_5m": Decimal("0.7"),
        "btc_funding_rate": Decimal("0"),
        "btc_basis_proxy": Decimal("0"),
        "vol_regime": "low",
        "trend_regime": "neutral",
        "time_bucket": "mid",
        "near_close_flag": False,
        "toxicity_regime": "low",
        "spread_regime": "tight",
        "liquidity_score": Decimal("0.8"),
        "competitive_pressure": Decimal("0.2"),
        "data_staleness_flag": False,
    }
    payload.update(overrides)
    return FeatureSnapshot(**payload)


def make_prediction(mispricing: str, threshold: str, predicted_at: datetime | None = None) -> PredictionRecord:
    timestamp = predicted_at or datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    mispricing_decimal = Decimal(mispricing)
    threshold_decimal = Decimal(threshold)
    return PredictionRecord(
        market_id="btc-hourly-1",
        token_id="token-1",
        predicted_at=timestamp,
        p_hat=Decimal("0.61"),
        implied_probability=Decimal("0.50"),
        mispricing=mispricing_decimal,
        threshold=threshold_decimal,
        threshold_met=abs(mispricing_decimal) > threshold_decimal,
        model_version="logistic_v1",
        confidence=Decimal("0.4"),
        data_staleness_ok=True,
    )


def make_regime(label: str) -> RegimeState:
    return RegimeState(
        detected_at=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        market_id="btc-hourly-1",
        primary_regime=label,
        regime_probabilities={"R1": 1.0, "R2": 0.0, "R3": 0.0, "R4": 0.0, "R5": 0.0},
        quality=RegimeQualityReport(
            computed_at=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
            posterior_entropy=0.1,
            switch_rate_per_hour=0.1,
            expected_duration_minutes=60.0,
            agreement_with_threshold=1.0,
            quality_score=0.9,
        ),
        source="threshold",
    )

