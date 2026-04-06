from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import numpy as np

from services.regime.classifiers.hmm import HMMRegimeClassifier
from services.regime.classifiers.threshold import ThresholdRegimeClassifier
from services.regime.quality import RegimeQualityWindow
from services.regime.schemas import ConnectivityMetrics, RegimeLabel, RegimeQualityReport, RegimeState
from services.regime.store import RegimeStore

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RegimeDetectorConfig:
    tick_seconds: float = 30.0
    min_hold_ticks: int = 3
    quality_fallback_threshold: float = 0.5


class RegimeDetector:
    """
    Real-time regime detector (Sprint 15).

    Consumes FeatureSnapshot-like objects and produces RegimeState.
    Optional DB writes are fire-and-forget to avoid blocking the loop.
    """

    def __init__(
        self,
        *,
        threshold: Optional[ThresholdRegimeClassifier] = None,
        hmm: Optional[HMMRegimeClassifier] = None,
        store: Optional[RegimeStore] = None,
        config: Optional[RegimeDetectorConfig] = None,
        market_id: Optional[str] = None,
    ) -> None:
        self._threshold = threshold or ThresholdRegimeClassifier()
        self._hmm = hmm
        self._store = store
        self._config = config or RegimeDetectorConfig()
        self._market_id = market_id

        self._quality_window = RegimeQualityWindow()

        self._running = False
        self._primary: Optional[RegimeLabel] = None
        self._pending: Optional[RegimeLabel] = None
        self._pending_count = 0

    def _apply_min_hold(self, proposed: RegimeLabel) -> RegimeLabel:
        # Safety overrides must take effect immediately.
        if proposed in ("R4", "R5", "R3"):
            self._primary = proposed
            self._pending = None
            self._pending_count = 0
            return proposed

        if self._primary is None:
            self._primary = proposed
            self._pending = None
            self._pending_count = 0
            return proposed

        if proposed == self._primary:
            self._pending = None
            self._pending_count = 0
            return self._primary

        if self._pending != proposed:
            self._pending = proposed
            self._pending_count = 1
            return self._primary

        self._pending_count += 1
        if self._pending_count >= self._config.min_hold_ticks:
            self._primary = proposed
            self._pending = None
            self._pending_count = 0
        return self._primary

    def detect(
        self,
        snapshot: Any,
        connectivity: Optional[ConnectivityMetrics] = None,
    ) -> RegimeState:
        now = datetime.now(timezone.utc)

        thr_label = self._threshold.classify(snapshot, connectivity=connectivity)

        # Hard overrides: R4 and R5 are always threshold-driven.
        if thr_label in ("R4", "R5"):
            quality = RegimeQualityReport(
                computed_at=now,
                posterior_entropy=0.0,
                switch_rate_per_hour=0.0,
                expected_duration_minutes=0.0,
                agreement_with_threshold=1.0,
                quality_score=1.0,
            )
            primary = self._apply_min_hold(thr_label)
            return RegimeState(
                detected_at=now,
                market_id=self._market_id,
                primary_regime=primary,
                regime_probabilities=self._threshold.one_hot(primary),
                quality=quality,
                source="threshold",
            )

        # Safety: R3 is threshold-triggered by near-close/toxicity.
        if thr_label == "R3":
            quality = RegimeQualityReport(
                computed_at=now,
                posterior_entropy=0.0,
                switch_rate_per_hour=0.0,
                expected_duration_minutes=0.0,
                agreement_with_threshold=1.0,
                quality_score=1.0,
            )
            primary = self._apply_min_hold("R3")
            return RegimeState(
                detected_at=now,
                market_id=self._market_id,
                primary_regime=primary,
                regime_probabilities=self._threshold.one_hot(primary),
                quality=quality,
                source="threshold",
            )

        # If no HMM available yet, fall back to threshold.
        if self._hmm is None:
            quality = RegimeQualityReport(
                computed_at=now,
                posterior_entropy=0.0,
                switch_rate_per_hour=0.0,
                expected_duration_minutes=0.0,
                agreement_with_threshold=1.0,
                quality_score=1.0,
            )
            primary = self._apply_min_hold(thr_label)
            return RegimeState(
                detected_at=now,
                market_id=self._market_id,
                primary_regime=primary,
                regime_probabilities=self._threshold.one_hot(primary),
                quality=quality,
                source="threshold",
            )

        hmm_out = self._hmm.predict(snapshot)
        hidden = np.asarray(hmm_out["hidden_posterior"], dtype=float)
        probs: Dict[RegimeLabel, float] = hmm_out["regime_probabilities"]  # type: ignore[assignment]

        proposed = max(("R1", "R2", "R3"), key=lambda k: float(probs[k]))  # type: ignore[index]

        self._quality_window.push_hidden(now, hidden)
        self._quality_window.push_primary(now, proposed, thr_label)

        transmat = getattr(self._hmm._artifact.model, "transmat_", None)  # noqa: SLF001
        quality = self._quality_window.compute(transmat=transmat)

        if quality.quality_score < self._config.quality_fallback_threshold:
            primary = self._apply_min_hold(thr_label)
            return RegimeState(
                detected_at=now,
                market_id=self._market_id,
                primary_regime=primary,
                regime_probabilities=self._threshold.one_hot(primary),
                quality=quality,
                source="threshold",
            )
        if quality.agreement_with_threshold < 0.5:
            primary = self._apply_min_hold(thr_label)
            return RegimeState(
                detected_at=now,
                market_id=self._market_id,
                primary_regime=primary,
                regime_probabilities=self._threshold.one_hot(primary),
                quality=quality,
                source="threshold",
            )

        primary = self._apply_min_hold(proposed)

        full_probs: Dict[RegimeLabel, float] = {
            "R1": float(probs["R1"]),
            "R2": float(probs["R2"]),
            "R3": float(probs["R3"]),
            "R4": 0.0,
            "R5": 0.0,
        }
        return RegimeState(
            detected_at=now,
            market_id=self._market_id,
            primary_regime=primary,
            regime_probabilities=full_probs,
            quality=quality,
            source="hmm" if primary == proposed else "blended",
        )

    async def _write_to_db(self, state: RegimeState) -> None:
        if self._store is None:
            return
        try:
            await self._store.write_state(state)
        except Exception as exc:
            logger.error("RegimeStore write failed: %s", exc)

    async def run(
        self,
        input_queue: asyncio.Queue,
        output_queue: Optional[asyncio.Queue] = None,
    ) -> None:
        self._running = True
        logger.info("RegimeDetector started (tick_seconds=%.1f)", self._config.tick_seconds)

        while self._running:
            try:
                item = await asyncio.wait_for(input_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            if item is None:
                break

            snapshot = item
            connectivity = None
            if isinstance(item, dict) and "snapshot" in item:
                snapshot = item["snapshot"]
                connectivity = item.get("connectivity")

            try:
                state = self.detect(snapshot, connectivity=connectivity)
            except Exception as exc:
                logger.error("RegimeDetector.detect failed: %s", exc, exc_info=True)
                input_queue.task_done()
                continue

            asyncio.create_task(self._write_to_db(state))

            if output_queue is not None:
                await output_queue.put(
                    {
                        "primary_regime": state.primary_regime,
                        "regime_probabilities": state.regime_probabilities,
                        "quality": state.quality,
                        "state": state,
                    }
                )

            input_queue.task_done()
            await asyncio.sleep(self._config.tick_seconds)

        logger.info("RegimeDetector stopped.")

    def stop(self) -> None:
        self._running = False
