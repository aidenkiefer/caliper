from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, Optional

from services.regime.schemas import ConnectivityMetrics, RegimeLabel


@dataclass(frozen=True)
class ThresholdRegimeClassifier:
    """
    Deterministic baseline regime classifier (Sprint 15).

    Precedence is safety-first and matches the spec:
      1) R4 connectivity risk
      2) R5 dead market
      3) R3 near-close toxic
      4) R2 choppy
      5) else R1 favorable
    """

    # Connectivity: highest priority
    R4_latency_threshold_ms: float = 2000.0
    R4_heartbeat_miss_count: int = 2

    # Dead market
    R5_max_spread_bps: float = 500.0
    R5_min_depth: Decimal = Decimal("10")

    # Near-close toxic
    R3_time_to_close_threshold_s: int = 600  # last 10 min
    R3_vpin_threshold: float = 0.65

    # Choppy
    R2_rv_5m_threshold: float = 0.002
    R2_sign_persistence_threshold: float = 0.6  # below = directionless

    def classify(
        self,
        snapshot: Any,
        connectivity: Optional[ConnectivityMetrics] = None,
    ) -> RegimeLabel:
        # R4: connectivity override
        if connectivity is not None:
            if (
                connectivity.api_latency_ms >= self.R4_latency_threshold_ms
                or connectivity.heartbeat_miss_count >= self.R4_heartbeat_miss_count
            ):
                return "R4"

        # R5: dead market
        spread_bps = float(getattr(snapshot, "spread_bps", 0.0) or 0.0)
        depth_bid = getattr(snapshot, "book_depth_bid_5tick", None)
        depth_ask = getattr(snapshot, "book_depth_ask_5tick", None)

        # Depth fields are Decimals in FeatureSnapshot; be forgiving for tests.
        depth_bid_d = Decimal(str(depth_bid)) if depth_bid is not None else Decimal("0")
        depth_ask_d = Decimal(str(depth_ask)) if depth_ask is not None else Decimal("0")
        min_depth = min(depth_bid_d, depth_ask_d)

        if spread_bps >= self.R5_max_spread_bps or min_depth < self.R5_min_depth:
            return "R5"

        # R3: near-close toxic
        time_to_close = float(getattr(snapshot, "time_to_close_seconds", 0.0) or 0.0)
        near_close_flag = bool(getattr(snapshot, "near_close_flag", False))
        toxicity_regime = getattr(snapshot, "toxicity_regime", None)
        vpin_proxy = float(getattr(snapshot, "vpin_proxy", 0.0) or 0.0)

        if (
            near_close_flag
            or time_to_close <= float(self.R3_time_to_close_threshold_s)
            or toxicity_regime == "high"
            or vpin_proxy >= self.R3_vpin_threshold
        ):
            return "R3"

        # R2: choppy
        btc_rv_5m = float(getattr(snapshot, "btc_rv_5m", 0.0) or 0.0)
        sign_persistence = float(getattr(snapshot, "btc_sign_persistence_5m", 1.0) or 1.0)
        if btc_rv_5m >= self.R2_rv_5m_threshold and sign_persistence < self.R2_sign_persistence_threshold:
            return "R2"

        return "R1"

    @staticmethod
    def one_hot(label: RegimeLabel) -> Dict[RegimeLabel, float]:
        return {
            "R1": 1.0 if label == "R1" else 0.0,
            "R2": 1.0 if label == "R2" else 0.0,
            "R3": 1.0 if label == "R3" else 0.0,
            "R4": 1.0 if label == "R4" else 0.0,
            "R5": 1.0 if label == "R5" else 0.0,
        }

