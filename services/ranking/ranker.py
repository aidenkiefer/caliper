from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Awaitable, Callable, Optional, Sequence

from services.ranking.edge import EdgeEstimator
from services.ranking.feasibility import FeasibilityScorer
from services.ranking.score import RankingWeights, composite_score
from services.ranking.schemas import CandidateMarket, MarketScore, RankedUniverse


@dataclass
class MarketRankerConfig:
    max_active_markets: int = 3
    cooldown_cycles: int = 3
    diversification_window_seconds: float = 600.0
    ranking_method: str = "cross_sectional_v1"


class MarketRanker:
    """Score and select a cross-sectional Polymarket universe."""

    def __init__(
        self,
        *,
        edge_estimator: EdgeEstimator | None = None,
        feasibility_scorer: FeasibilityScorer | None = None,
        weights: RankingWeights | None = None,
        config: MarketRankerConfig | None = None,
    ) -> None:
        self._edge_estimator = edge_estimator or EdgeEstimator()
        self._feasibility_scorer = feasibility_scorer or FeasibilityScorer()
        self._weights = weights or RankingWeights()
        self._config = config or MarketRankerConfig()
        self._active_market_ids: set[str] = set()
        self._cooldown_counts: dict[str, int] = {}
        self._running = False

    def score_candidate(self, candidate: CandidateMarket) -> MarketScore:
        edge = self._edge_estimator.estimate(candidate)
        feasibility = self._feasibility_scorer.score(candidate)
        sigma = float(candidate.sigma)
        confidence = float(candidate.confidence)
        score = composite_score(
            ev_adj=edge.ev_adj,
            sigma=sigma,
            feasibility=feasibility.feasibility_score,
            confidence=confidence,
            weights=self._weights,
        )
        excluded = feasibility.exclude or edge.ev_adj < 0
        exclusion_reason = feasibility.exclusion_reason
        if edge.ev_adj < 0:
            exclusion_reason = "negative_ev"
        return MarketScore(
            candidate=candidate,
            edge=edge,
            feasibility=feasibility,
            sigma=sigma,
            confidence=confidence,
            score=score,
            selected=False,
            excluded=excluded,
            exclusion_reason=exclusion_reason,
        )

    def rank_once(
        self,
        candidates: Sequence[CandidateMarket],
        *,
        now: Optional[datetime] = None,
    ) -> RankedUniverse:
        ranked_at = now.astimezone(timezone.utc) if now is not None else datetime.now(timezone.utc)
        scored = [self.score_candidate(candidate) for candidate in candidates]
        score_by_id = {entry.candidate.market_id: entry for entry in scored}

        best_per_condition: dict[str, MarketScore] = {}
        excluded_ids: list[str] = []
        for entry in scored:
            existing = best_per_condition.get(entry.candidate.condition_id)
            if existing is None or entry.score > existing.score:
                if existing is not None:
                    excluded_ids.append(existing.candidate.market_id)
                best_per_condition[entry.candidate.condition_id] = entry
            else:
                excluded_ids.append(entry.candidate.market_id)

        unique_scores = sorted(
            best_per_condition.values(),
            key=lambda entry: (-entry.score, entry.candidate.time_to_close_seconds, entry.candidate.market_id),
        )

        provisional_selected: list[MarketScore] = []
        for entry in unique_scores:
            if len(provisional_selected) >= self._config.max_active_markets:
                break
            if self._violates_diversification(entry, provisional_selected):
                excluded_ids.append(entry.candidate.market_id)
                continue
            provisional_selected.append(entry)

        provisional_ids = {entry.candidate.market_id for entry in provisional_selected}
        cooldown_protected: list[str] = []
        final_selected = list(provisional_selected)

        for market_id in list(self._active_market_ids):
            if market_id in provisional_ids:
                self._cooldown_counts[market_id] = 0
                continue

            score_entry = score_by_id.get(market_id)
            if score_entry is None:
                self._active_market_ids.discard(market_id)
                self._cooldown_counts.pop(market_id, None)
                continue

            count = self._cooldown_counts.get(market_id, 0) + 1
            self._cooldown_counts[market_id] = count
            if count < self._config.cooldown_cycles:
                final_selected.append(score_entry)
                cooldown_protected.append(market_id)
                provisional_ids.add(market_id)
            else:
                self._active_market_ids.discard(market_id)
                self._cooldown_counts.pop(market_id, None)

        final_selected = sorted(
            final_selected,
            key=lambda entry: (-entry.score, entry.candidate.time_to_close_seconds, entry.candidate.market_id),
        )

        selected_ids = {entry.candidate.market_id for entry in final_selected}
        self._active_market_ids = set(selected_ids)
        for entry in final_selected:
            entry.selected = True
            entry.excluded = False
            entry.exclusion_reason = None
        for entry in scored:
            if entry.candidate.market_id not in selected_ids:
                entry.selected = False
                if entry.excluded is False:
                    entry.excluded = True
                    entry.exclusion_reason = entry.exclusion_reason or "not_selected"

        excluded_markets = sorted(
            set(excluded_ids)
            | {
                entry.candidate.market_id
                for entry in scored
                if entry.candidate.market_id not in selected_ids
            }
        )
        cooldown_protected = sorted(set(cooldown_protected))
        return RankedUniverse(
            ranked_at=ranked_at,
            total_candidates=len(candidates),
            selected_markets=final_selected,
            excluded_markets=excluded_markets,
            ranking_method=self._config.ranking_method,
            cooldown_protected=cooldown_protected,
        )

    def _violates_diversification(
        self,
        candidate: MarketScore,
        selected: Sequence[MarketScore],
    ) -> bool:
        for other in selected:
            if (
                abs(candidate.candidate.time_to_close_seconds - other.candidate.time_to_close_seconds)
                < self._config.diversification_window_seconds
            ):
                return True
        return False

    async def run(
        self,
        candidate_source: Callable[[], Sequence[CandidateMarket] | Awaitable[Sequence[CandidateMarket]]],
        output_queue: Optional[asyncio.Queue] = None,
        *,
        interval_seconds: float = 60.0,
    ) -> None:
        self._running = True
        while self._running:
            result = candidate_source()
            if asyncio.iscoroutine(result) or isinstance(result, asyncio.Future):
                candidates = await result
            else:
                candidates = result
            ranked = self.rank_once(candidates)
            if output_queue is not None:
                await output_queue.put(ranked)
            await asyncio.sleep(interval_seconds)

    def stop(self) -> None:
        self._running = False

