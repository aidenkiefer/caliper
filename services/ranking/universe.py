from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Awaitable, Callable, Mapping, Optional, Sequence

from services.ranking.schemas import CandidateMarket


def _to_decimal(value: Any, default: str = "0") -> Decimal:
    if value is None:
        return Decimal(default)
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _to_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "t", "yes", "y"}
    return bool(value)


def _parse_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _text_blob(raw: Mapping[str, Any]) -> str:
    parts = [
        str(raw.get("slug") or ""),
        str(raw.get("question") or ""),
        str(raw.get("category") or ""),
        str(raw.get("marketType") or raw.get("market_type") or ""),
        str(raw.get("tags") or ""),
    ]
    return " ".join(parts).lower()


def _is_btc_hourly(raw: Mapping[str, Any], *, include_chainlink_short_intervals: bool) -> bool:
    blob = _text_blob(raw)
    if not include_chainlink_short_intervals and ("chainlink" in blob or "5m" in blob or "15m" in blob):
        return False
    if "btc" in blob and any(token in blob for token in ("hour", "1h", "hourly")):
        return True
    if raw.get("tag_slug") == "btc":
        return True
    if raw.get("series") == "BTC":
        return True
    return False


def _extract_tokens(raw: Mapping[str, Any]) -> list[dict[str, Any]]:
    tokens = raw.get("tokens") or []
    if isinstance(tokens, list):
        return [dict(token) for token in tokens if isinstance(token, Mapping)]
    return []


@dataclass(frozen=True)
class UniverseBuilderConfig:
    min_volume_usd: Decimal = Decimal("10000")
    max_spread_pct: Decimal = Decimal("0.03")
    include_chainlink_short_intervals: bool = False


class UniverseBuilder:
    """Discover and filter eligible Polymarket BTC hourly markets."""

    def __init__(
        self,
        *,
        config: UniverseBuilderConfig | None = None,
        market_source: Optional[Callable[[], Awaitable[Sequence[Mapping[str, Any]]]]] = None,
    ) -> None:
        self._config = config or UniverseBuilderConfig()
        self._market_source = market_source

    async def discover(self) -> list[CandidateMarket]:
        if self._market_source is None:
            raise RuntimeError("UniverseBuilder requires a market_source for discovery")
        raw_markets = await self._market_source()
        return self.build_from_raw(raw_markets)

    def build_from_raw(
        self,
        raw_markets: Sequence[Mapping[str, Any]],
        *,
        now: Optional[datetime] = None,
    ) -> list[CandidateMarket]:
        reference_time = now.astimezone(timezone.utc) if now is not None else datetime.now(timezone.utc)
        candidates: list[CandidateMarket] = []
        for raw in raw_markets:
            if not self._eligible(raw):
                continue

            condition_id = str(raw.get("conditionId") or raw.get("condition_id") or "")
            slug = raw.get("slug")
            question = raw.get("question")
            market_type = raw.get("marketType") or raw.get("market_type")
            fees_enabled = _to_bool(raw.get("feesEnabled", raw.get("enableOrderBook", True)), default=True)
            reward_eligible = _to_bool(raw.get("rewardEligible", False), default=False) or any(
                raw.get(field) is not None
                for field in ("rewardsMaxSpread", "rewards_max_spread", "rewardsMinSize", "rewards_min_size")
            )

            volume = _to_decimal(raw.get("volume") or raw.get("totalVolume") or raw.get("total_volume") or 0)
            spread = _to_decimal(raw.get("spread") or 0)
            midpoint = raw.get("midpoint") or raw.get("mid_price") or raw.get("midPrice")
            if spread <= 0 and raw.get("bestBid") is not None and raw.get("bestAsk") is not None:
                spread = _to_decimal(raw.get("bestAsk")) - _to_decimal(raw.get("bestBid"))
            spread_pct = _to_decimal(
                raw.get("spreadPct")
                or raw.get("spread_pct")
                or (spread / _to_decimal(midpoint, default="1") if midpoint is not None else 0),
                default="0",
            )
            spread_bps = _to_decimal(raw.get("spreadBps") or raw.get("spread_bps") or spread_pct * Decimal("10000"), default="0")

            bid_depth = _to_decimal(raw.get("book_depth_bid_5tick") or raw.get("bid_depth_5tick") or 0)
            ask_depth = _to_decimal(raw.get("book_depth_ask_5tick") or raw.get("ask_depth_5tick") or 0)
            time_to_close_seconds = self._time_to_close_seconds(raw, reference_time)
            fee_rate_bps = _to_decimal(raw.get("feeRateBps") or raw.get("fee_rate_bps") or 0, default="0")
            p_pm = _to_decimal(
                raw.get("impliedProbability")
                or raw.get("implied_probability")
                or raw.get("yes_price")
                or raw.get("mid_price")
                or 0.5,
                default="0.5",
            )
            sigma = _to_decimal(raw.get("sigma") or raw.get("volatility") or 1.0, default="1")
            confidence = _to_decimal(raw.get("confidence") or raw.get("model_confidence") or 1.0, default="1")
            recent_trade_intensity = _to_decimal(raw.get("recent_trade_intensity") or raw.get("trade_intensity") or 0, default="0")
            queue_position_proxy = _to_decimal(raw.get("queue_position_proxy") or raw.get("queue_position") or 0.5, default="0.5")
            staleness_seconds = float(raw.get("staleness_seconds") or raw.get("staleness") or 0.0)
            last_updated = _parse_datetime(raw.get("lastUpdated") or raw.get("last_updated"))

            tokens = _extract_tokens(raw)
            if tokens:
                for token in tokens:
                    outcome = str(token.get("outcome") or token.get("side") or "").strip().upper()
                    token_id = str(token.get("token_id") or token.get("tokenId") or "")
                    if outcome not in {"YES", "NO"} or not token_id:
                        continue
                    side_probability = p_pm if outcome == "YES" else Decimal("1") - p_pm
                    candidates.append(
                        CandidateMarket(
                            market_id=token_id,
                            condition_id=condition_id,
                            token_id=token_id,
                            side=outcome,  # type: ignore[arg-type]
                            slug=slug,
                            question=question,
                            market_type=market_type,
                            active=True,
                            closed=False,
                            fees_enabled=fees_enabled,
                            reward_eligible=reward_eligible,
                            total_volume_usd=volume,
                            spread=spread,
                            spread_pct=spread_pct,
                            spread_bps=spread_bps,
                            book_depth_bid_5tick=bid_depth,
                            book_depth_ask_5tick=ask_depth,
                            time_to_close_seconds=time_to_close_seconds,
                            p_pm=side_probability,
                            p_hat=None,
                            sigma=sigma,
                            confidence=confidence,
                            recent_trade_intensity=recent_trade_intensity,
                            queue_position_proxy=queue_position_proxy,
                            fee_rate_bps=fee_rate_bps,
                            reward_max_spread=_to_decimal(raw.get("rewardsMaxSpread") or raw.get("rewards_max_spread"), default="0") if reward_eligible else None,
                            reward_min_size=_to_decimal(raw.get("rewardsMinSize") or raw.get("rewards_min_size"), default="0") if reward_eligible else None,
                            staleness_seconds=staleness_seconds,
                            last_updated=last_updated,
                            metadata=dict(raw),
                        )
                    )
                continue

            token_id = str(raw.get("token_id") or raw.get("tokenId") or condition_id)
            candidates.append(
                CandidateMarket(
                    market_id=token_id,
                    condition_id=condition_id,
                    token_id=token_id,
                    side="YES",  # type: ignore[arg-type]
                    slug=slug,
                    question=question,
                    market_type=market_type,
                    active=True,
                    closed=False,
                    fees_enabled=fees_enabled,
                    reward_eligible=reward_eligible,
                    total_volume_usd=volume,
                    spread=spread,
                    spread_pct=spread_pct,
                    spread_bps=spread_bps,
                    book_depth_bid_5tick=bid_depth,
                    book_depth_ask_5tick=ask_depth,
                    time_to_close_seconds=time_to_close_seconds,
                    p_pm=p_pm,
                    p_hat=None,
                    sigma=sigma,
                    confidence=confidence,
                    recent_trade_intensity=recent_trade_intensity,
                    queue_position_proxy=queue_position_proxy,
                    fee_rate_bps=fee_rate_bps,
                    reward_max_spread=_to_decimal(raw.get("rewardsMaxSpread") or raw.get("rewards_max_spread"), default="0") if reward_eligible else None,
                    reward_min_size=_to_decimal(raw.get("rewardsMinSize") or raw.get("rewards_min_size"), default="0") if reward_eligible else None,
                    staleness_seconds=staleness_seconds,
                    last_updated=last_updated,
                    metadata=dict(raw),
                )
            )

        return candidates

    def _eligible(self, raw: Mapping[str, Any]) -> bool:
        if not _to_bool(raw.get("active", raw.get("isActive", True)), default=True):
            return False
        if _to_bool(raw.get("closed", raw.get("isClosed", False)), default=False):
            return False
        if not _is_btc_hourly(raw, include_chainlink_short_intervals=self._config.include_chainlink_short_intervals):
            return False

        volume = _to_decimal(raw.get("volume") or raw.get("totalVolume") or raw.get("total_volume") or 0)
        if volume < self._config.min_volume_usd:
            return False

        spread_pct = _to_decimal(
            raw.get("spreadPct")
            or raw.get("spread_pct")
            or raw.get("spread")
            or 0,
            default="0",
        )
        if spread_pct > self._config.max_spread_pct:
            return False

        fees_enabled = _to_bool(raw.get("feesEnabled", raw.get("enableOrderBook", True)), default=True)
        reward_eligible = _to_bool(raw.get("rewardEligible", False), default=False) or any(
            raw.get(field) is not None
            for field in ("rewardsMaxSpread", "rewards_max_spread", "rewardsMinSize", "rewards_min_size")
        )
        if not (fees_enabled or reward_eligible):
            return False
        return True

    def _time_to_close_seconds(self, raw: Mapping[str, Any], reference_time: datetime) -> float:
        if raw.get("time_to_close_seconds") is not None:
            try:
                return max(float(raw.get("time_to_close_seconds")), 0.0)
            except (TypeError, ValueError):
                pass
        end_dt = _parse_datetime(raw.get("endDate") or raw.get("window_end") or raw.get("close_time"))
        if end_dt is None:
            return 0.0
        return max((end_dt - reference_time).total_seconds(), 0.0)

