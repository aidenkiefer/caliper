from __future__ import annotations

from datetime import datetime, timedelta, timezone

from services.ranking.universe import UniverseBuilder


def _raw_market(
    *,
    condition_id: str = "cond-1",
    slug: str = "btc-hourly-up",
    question: str = "BTC hourly up?",
    volume: float = 25000.0,
    spread_pct: float = 0.02,
    active: bool = True,
    closed: bool = False,
    fees_enabled: bool = True,
    reward_eligible: bool = False,
):
    now = datetime.now(timezone.utc)
    return {
        "conditionId": condition_id,
        "slug": slug,
        "question": question,
        "active": active,
        "closed": closed,
        "feesEnabled": fees_enabled,
        "rewardEligible": reward_eligible,
        "volume": volume,
        "spreadPct": spread_pct,
        "bestBid": 0.45,
        "bestAsk": 0.47,
        "midpoint": 0.46,
        "tokens": [
            {"outcome": "YES", "token_id": f"{condition_id}-yes"},
            {"outcome": "NO", "token_id": f"{condition_id}-no"},
        ],
        "endDate": (now + timedelta(hours=1)).isoformat(),
        "time_to_close_seconds": 3600.0,
    }


def test_universe_builder_filters_and_expands_sides() -> None:
    builder = UniverseBuilder()
    raw_markets = [
        _raw_market(condition_id="keep"),
        _raw_market(condition_id="low-vol", volume=5000.0),
        _raw_market(condition_id="wide", spread_pct=0.05),
        _raw_market(condition_id="chainlink", slug="chainlink-5m", question="Chainlink 5m"),
    ]

    candidates = builder.build_from_raw(raw_markets, now=datetime.now(timezone.utc))
    ids = {candidate.market_id for candidate in candidates}

    assert ids == {"keep-yes", "keep-no"}
    assert all(candidate.condition_id == "keep" for candidate in candidates)
    assert all(candidate.side in {"YES", "NO"} for candidate in candidates)


def test_universe_builder_respects_reward_only_markets() -> None:
    builder = UniverseBuilder()
    raw_market = _raw_market(condition_id="reward", fees_enabled=False, reward_eligible=True)
    candidates = builder.build_from_raw([raw_market], now=datetime.now(timezone.utc))
    assert len(candidates) == 2

