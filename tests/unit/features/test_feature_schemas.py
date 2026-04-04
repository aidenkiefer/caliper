"""Unit tests for FeatureSnapshot Pydantic schema validation (Sprint 12)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from packages.common.polymarket_schemas import FeatureSnapshot


# ---------------------------------------------------------------------------
# Fixture: a fully valid FeatureSnapshot dict
# ---------------------------------------------------------------------------

def _valid_snapshot_dict() -> dict:
    return {
        "market_id": "0xabc123",
        "token_id": "0xtoken456",
        "captured_at": datetime(2026, 4, 4, 12, 0, 0, tzinfo=timezone.utc),
        "time_to_close_seconds": 1800.0,
        "time_since_open_seconds": 600.0,
        # Family 1
        "mid_price": Decimal("0.50"),
        "implied_probability": Decimal("0.50"),
        "spread": Decimal("0.02"),
        "spread_bps": Decimal("400"),
        "book_depth_bid_5tick": Decimal("1000"),
        "book_depth_ask_5tick": Decimal("900"),
        "time_since_last_trade": 5.0,
        "time_since_last_price_change": 3.0,
        # Family 2
        "order_book_imbalance": Decimal("0.05"),
        "trade_flow_imbalance_1m": Decimal("100"),
        "trade_flow_imbalance_5m": Decimal("250"),
        "last_5min_volume_share": Decimal("0.25"),
        "aggressor_buy_fraction_1m": Decimal("0.6"),
        "vpin_proxy": Decimal("0.3"),
        "fee_rate_current": Decimal("0.005"),
        "reward_eligible": True,
        "reward_max_spread": Decimal("0.05"),
        "reward_min_size": Decimal("10"),
        # Family 3
        "btc_distance_to_open": Decimal("0.019"),
        "btc_rv_1m": Decimal("0.0002"),
        "btc_rv_5m": Decimal("0.001"),
        "btc_rv_15m": Decimal("0.003"),
        "btc_momentum_5m": Decimal("0.009"),
        "btc_sign_persistence_5m": Decimal("0.8"),
        "btc_funding_rate": Decimal("0.0001"),
        "btc_basis_proxy": Decimal("0.0002"),
        # Family 4
        "vol_regime": "medium",
        "trend_regime": "neutral",
        "time_bucket": "early",
        "near_close_flag": False,
        "toxicity_regime": "low",
        "spread_regime": "normal",
        "liquidity_score": Decimal("0.5"),
        "competitive_pressure": Decimal("0.0025"),
        # Quality
        "data_staleness_flag": False,
    }


# ===========================================================================
# Valid construction
# ===========================================================================

class TestFeatureSnapshotValid:

    def test_feature_snapshot_valid(self):
        """Full valid dict constructs without error."""
        snap = FeatureSnapshot(**_valid_snapshot_dict())
        assert snap.market_id == "0xabc123"
        assert snap.token_id == "0xtoken456"
        assert snap.mid_price == Decimal("0.50")
        assert snap.vol_regime == "medium"
        assert snap.spread_regime == "normal"

    def test_data_staleness_flag_default_false(self):
        """data_staleness_flag defaults to False when not provided."""
        d = _valid_snapshot_dict()
        del d["data_staleness_flag"]
        snap = FeatureSnapshot(**d)
        assert snap.data_staleness_flag is False

    def test_reward_max_spread_optional(self):
        """reward_max_spread and reward_min_size are optional (None by default)."""
        d = _valid_snapshot_dict()
        del d["reward_max_spread"]
        del d["reward_min_size"]
        snap = FeatureSnapshot(**d)
        assert snap.reward_max_spread is None
        assert snap.reward_min_size is None

    def test_near_close_flag_true(self):
        """near_close_flag can be True."""
        d = _valid_snapshot_dict()
        d["near_close_flag"] = True
        snap = FeatureSnapshot(**d)
        assert snap.near_close_flag is True


# ===========================================================================
# Validation errors
# ===========================================================================

class TestFeatureSnapshotValidationErrors:

    def test_feature_snapshot_missing_required_field(self):
        """Missing market_id raises ValidationError."""
        d = _valid_snapshot_dict()
        del d["market_id"]
        with pytest.raises(ValidationError):
            FeatureSnapshot(**d)

    def test_feature_snapshot_missing_token_id(self):
        """Missing token_id raises ValidationError."""
        d = _valid_snapshot_dict()
        del d["token_id"]
        with pytest.raises(ValidationError):
            FeatureSnapshot(**d)

    def test_feature_snapshot_invalid_vol_regime_literal(self):
        """vol_regime='extreme' is not a valid Literal → ValidationError."""
        d = _valid_snapshot_dict()
        d["vol_regime"] = "extreme"
        with pytest.raises(ValidationError):
            FeatureSnapshot(**d)

    def test_feature_snapshot_invalid_trend_regime_literal(self):
        """trend_regime='sideways' is not valid → ValidationError."""
        d = _valid_snapshot_dict()
        d["trend_regime"] = "sideways"
        with pytest.raises(ValidationError):
            FeatureSnapshot(**d)

    def test_feature_snapshot_invalid_time_bucket_literal(self):
        """time_bucket='morning' is not valid → ValidationError."""
        d = _valid_snapshot_dict()
        d["time_bucket"] = "morning"
        with pytest.raises(ValidationError):
            FeatureSnapshot(**d)

    def test_feature_snapshot_invalid_spread_regime_literal(self):
        """spread_regime='compressed' is not valid → ValidationError."""
        d = _valid_snapshot_dict()
        d["spread_regime"] = "compressed"
        with pytest.raises(ValidationError):
            FeatureSnapshot(**d)

    def test_feature_snapshot_invalid_toxicity_regime_literal(self):
        """toxicity_regime='extreme' is not valid → ValidationError."""
        d = _valid_snapshot_dict()
        d["toxicity_regime"] = "extreme"
        with pytest.raises(ValidationError):
            FeatureSnapshot(**d)


# ===========================================================================
# All valid Literal values
# ===========================================================================

class TestFeatureSnapshotLiterals:

    @pytest.mark.parametrize("vol_regime", ["low", "medium", "high"])
    def test_vol_regime_all_valid(self, vol_regime):
        d = _valid_snapshot_dict()
        d["vol_regime"] = vol_regime
        snap = FeatureSnapshot(**d)
        assert snap.vol_regime == vol_regime

    @pytest.mark.parametrize("trend_regime", ["trending", "mean_reverting", "neutral"])
    def test_trend_regime_all_valid(self, trend_regime):
        d = _valid_snapshot_dict()
        d["trend_regime"] = trend_regime
        snap = FeatureSnapshot(**d)
        assert snap.trend_regime == trend_regime

    @pytest.mark.parametrize("time_bucket", ["early", "mid", "late"])
    def test_time_bucket_all_valid(self, time_bucket):
        d = _valid_snapshot_dict()
        d["time_bucket"] = time_bucket
        snap = FeatureSnapshot(**d)
        assert snap.time_bucket == time_bucket

    @pytest.mark.parametrize("spread_regime", ["tight", "normal", "wide"])
    def test_spread_regime_all_valid(self, spread_regime):
        d = _valid_snapshot_dict()
        d["spread_regime"] = spread_regime
        snap = FeatureSnapshot(**d)
        assert snap.spread_regime == spread_regime
