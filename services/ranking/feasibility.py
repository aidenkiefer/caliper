from __future__ import annotations

from dataclasses import dataclass

from services.ranking.schemas import CandidateMarket, FeasibilityReport


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


@dataclass(frozen=True)
class FeasibilityScorerConfig:
    exclusion_threshold: float = 0.2
    epsilon: float = 1e-9


class FeasibilityScorer:
    """Liquidity / fill-probability feasibility estimator."""

    def __init__(self, config: FeasibilityScorerConfig | None = None) -> None:
        self._config = config or FeasibilityScorerConfig()

    def score(self, candidate: CandidateMarket) -> FeasibilityReport:
        spread_bps = max(float(candidate.spread_bps), self._config.epsilon)
        btc_rv_5m = max(float(candidate.metadata.get("btc_rv_5m", 0.0)), self._config.epsilon)
        bid_depth = float(candidate.book_depth_bid_5tick)
        ask_depth = float(candidate.book_depth_ask_5tick)
        liquidity_score = (bid_depth + ask_depth) / (spread_bps * btc_rv_5m + self._config.epsilon)
        normalized_liquidity = liquidity_score / (1.0 + liquidity_score) if liquidity_score > 0 else 0.0

        trade_intensity = _clamp(float(candidate.recent_trade_intensity))
        queue_proxy = _clamp(float(candidate.queue_position_proxy))
        fill_probability = _clamp(0.2 + 0.5 * trade_intensity + 0.3 * (1.0 - queue_proxy))

        feasibility_score = _clamp(normalized_liquidity * fill_probability)
        exclude = feasibility_score < self._config.exclusion_threshold

        return FeasibilityReport(
            liquidity_score=liquidity_score,
            normalized_liquidity=normalized_liquidity,
            fill_probability=fill_probability,
            feasibility_score=feasibility_score,
            exclude=exclude,
            exclusion_reason="feasibility_below_threshold" if exclude else None,
        )

