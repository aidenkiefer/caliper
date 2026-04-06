from __future__ import annotations

from decimal import Decimal

from services.ranking.ranker import MarketRanker, MarketRankerConfig
from services.ranking.schemas import CandidateMarket


def _candidate(
    market_id: str,
    condition_id: str,
    *,
    side: str = "YES",
    p_hat: str = "0.60",
    p_pm: str = "0.50",
    spread: str = "0.00",
    spread_bps: str = "10",
    bid_depth: str = "100",
    ask_depth: str = "100",
    time_to_close_seconds: float = 3600.0,
    confidence: str = "1.0",
    sigma: str = "1.0",
    recent_trade_intensity: str = "0.9",
    queue_position_proxy: str = "0.1",
):
    return CandidateMarket(
        market_id=market_id,
        condition_id=condition_id,
        token_id=market_id,
        side=side,  # type: ignore[arg-type]
        p_hat=Decimal(p_hat),
        p_pm=Decimal(p_pm),
        spread=Decimal(spread),
        spread_bps=Decimal(spread_bps),
        book_depth_bid_5tick=Decimal(bid_depth),
        book_depth_ask_5tick=Decimal(ask_depth),
        time_to_close_seconds=time_to_close_seconds,
        confidence=Decimal(confidence),
        sigma=Decimal(sigma),
        recent_trade_intensity=Decimal(recent_trade_intensity),
        queue_position_proxy=Decimal(queue_position_proxy),
        fees_enabled=True,
        metadata={"btc_rv_5m": 0.001},
    )


def test_ranker_never_selects_both_sides_of_same_condition() -> None:
    ranker = MarketRanker()
    candidates = [
        _candidate("yes-1", "cond-1", side="YES", p_hat="0.70", p_pm="0.50"),
        _candidate("no-1", "cond-1", side="NO", p_hat="0.35", p_pm="0.50"),
        _candidate("other-1", "cond-2", p_hat="0.65", p_pm="0.50"),
    ]

    universe = ranker.rank_once(candidates)
    selected_ids = {score.candidate.market_id for score in universe.selected_markets}

    assert "yes-1" in selected_ids
    assert "no-1" not in selected_ids


def test_ranker_enforces_diversification_and_cooldown() -> None:
    ranker = MarketRanker(config=MarketRankerConfig(max_active_markets=1, cooldown_cycles=3))
    cycle_one = [
        _candidate("a", "cond-a", p_hat="0.70", p_pm="0.50", time_to_close_seconds=3600.0),
        _candidate("b", "cond-b", p_hat="0.65", p_pm="0.50", time_to_close_seconds=3650.0),
        _candidate("c", "cond-c", p_hat="0.64", p_pm="0.50", time_to_close_seconds=3700.0),
    ]
    universe1 = ranker.rank_once(cycle_one)
    assert [score.candidate.market_id for score in universe1.selected_markets] == ["a"]

    cycle_two = [
        _candidate("a", "cond-a", p_hat="0.55", p_pm="0.50", time_to_close_seconds=3600.0),
        _candidate("b", "cond-b", p_hat="0.75", p_pm="0.50", time_to_close_seconds=3650.0),
        _candidate("c", "cond-c", p_hat="0.64", p_pm="0.50", time_to_close_seconds=3700.0),
    ]
    universe2 = ranker.rank_once(cycle_two)
    selected_two = {score.candidate.market_id for score in universe2.selected_markets}
    assert selected_two == {"a", "b"}
    assert universe2.cooldown_protected == ["a"]

    universe3 = ranker.rank_once(cycle_two)
    selected_three = {score.candidate.market_id for score in universe3.selected_markets}
    assert selected_three == {"a", "b"}
    assert universe3.cooldown_protected == ["a"]

    universe4 = ranker.rank_once(cycle_two)
    selected_four = {score.candidate.market_id for score in universe4.selected_markets}
    assert selected_four == {"b"}
    assert universe4.cooldown_protected == []

