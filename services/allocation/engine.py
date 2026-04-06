from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Iterable, Optional

from services.allocation.methods.hrp import hrp_weights
from services.allocation.methods.kelly import bounded_kelly_weights
from services.allocation.methods.risk_parity import risk_parity_weights
from services.allocation.risk_layer import alpha_from_entropy, apply_hard_constraints, apply_soft_constraints
from services.allocation.schemas import AllocationDecision, CapitalBudgetModel, PerformanceMatrix
from services.allocation.store import AllocationStore
from services.regime.schemas import RegimeState

logger = logging.getLogger(__name__)


class AllocationEngine:
    """AllocationEngine (Sprint 15).

    Consumes RegimeState + PerformanceMatrix and outputs AllocationDecision.
    """

    def __init__(
        self,
        *,
        capital_budget: CapitalBudgetModel,
        mm_strategy_ids: Iterable[str],
        store: Optional[AllocationStore] = None,
        tick_seconds: float = 30.0,
    ) -> None:
        self._capital_budget = capital_budget
        self._mm_strategy_ids = set(mm_strategy_ids)
        self._store = store
        self._tick_seconds = tick_seconds

        self._running = False
        self._latest: Optional[AllocationDecision] = None
        self._prev_weights: Dict[str, Decimal] = {}
        self._latest_matrix: Optional[PerformanceMatrix] = None

    @property
    def latest(self) -> Optional[AllocationDecision]:
        return self._latest

    def decide(
        self,
        *,
        regime: RegimeState,
        matrix: PerformanceMatrix,
        portfolio_drawdown: Decimal = Decimal("0"),
        strategy_drawdowns: Optional[Dict[str, Decimal]] = None,
    ) -> AllocationDecision:
        decided_at = datetime.now(timezone.utc)
        alpha = alpha_from_entropy(regime.quality.posterior_entropy, n_states=4)

        primary = regime.primary_regime
        strategies = list(matrix.strategies)
        sigma_map = {s: matrix.sigma.get(s, {}).get(primary, Decimal("0")) for s in strategies}
        baseline = risk_parity_weights(sigma_map)

        cov = matrix.covariance.get(primary)
        if cov is None:
            advanced = dict(baseline)
        else:
            hrp = hrp_weights(cov, strategies)
            mu_vec = [float(matrix.mu.get(s, {}).get(primary, Decimal("0"))) for s in strategies]
            kelly = bounded_kelly_weights(mu_vec, cov, strategies, max_weight=0.40, total_weight_cap=1.0)
            # Blend HRP and Kelly equally as the "advanced" method.
            advanced = {s: (hrp.get(s, Decimal("0")) + kelly.get(s, Decimal("0"))) / Decimal("2") for s in strategies}

        blended = {
            s: (Decimal("1") - Decimal(str(alpha))) * baseline.get(s, Decimal("0"))
            + Decimal(str(alpha)) * advanced.get(s, Decimal("0"))
            for s in strategies
        }

        constrained, applied = apply_hard_constraints(
            weights=blended,
            regime=regime,
            mm_strategy_ids=self._mm_strategy_ids,
            portfolio_drawdown=portfolio_drawdown,
            strategy_drawdowns=strategy_drawdowns,
            prev_weights=self._prev_weights,
        )
        constrained = apply_soft_constraints(
            weights=constrained,
            prev_weights=self._prev_weights,
            covariance=cov,
        )

        decision = AllocationDecision(
            decided_at=decided_at,
            regime=regime,
            weights=constrained,
            method_used="blended",
            confidence=float(alpha),
            hard_constraints_applied=applied,
            capital_budget=self._capital_budget,
        )

        self._latest = decision
        self._prev_weights = dict(constrained)
        return decision

    async def run(
        self,
        regime_queue: asyncio.Queue,
        matrix_queue: asyncio.Queue,
        output_queue: Optional[asyncio.Queue] = None,
    ) -> None:
        self._running = True
        logger.info("AllocationEngine started (tick_seconds=%.1f)", self._tick_seconds)

        while self._running:
            # Update matrix if a newer one arrives.
            try:
                m = matrix_queue.get_nowait()
                if m is None:
                    break
                self._latest_matrix = m
                matrix_queue.task_done()
            except asyncio.QueueEmpty:
                pass

            try:
                regime = await asyncio.wait_for(regime_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            if regime is None:
                break

            matrix = self._latest_matrix
            if matrix is None:
                regime_queue.task_done()
                continue

            decision = self.decide(regime=regime, matrix=matrix)

            if self._store is not None:
                asyncio.create_task(self._store.write_decision(decision))
            if output_queue is not None:
                await output_queue.put(decision)

            regime_queue.task_done()
            await asyncio.sleep(self._tick_seconds)

        logger.info("AllocationEngine stopped")

    def stop(self) -> None:
        self._running = False
